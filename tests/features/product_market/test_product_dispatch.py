"""D3-3 smoke: route a product market through dispatch (golden-inert shell).

A single ``model_approach: "product"`` scenario at a FIXED exogenous carbon
price is dispatched through ``run_simulation_from_config`` and asserted against
the carbon-side-fixed slice of the V-D3-5b hand anchor
(``docs/multi-commodity-spec.md`` §7). This exercises the whole D3-3 shell:
config door (``product_market.plugin``) → builder (inert-cap ``CarbonMarket``) →
dispatch ``"product"`` branch → runtime door (``product_market.solver``) → T0
``solve_product_equilibrium`` → ledger frames.

Anchor (P_c fixed at 10; the joint carbon price of V-D3-5b): 2 identical
producers γ=5, δ=2, σ=5, β=10, a_max=5; linear demand A_d=40, b_d=0.3;
carbon-free imports m=0.2. Closed form:

    a* = clip(P_c/β, 0, a_max) = clip(10/10, 0, 5) = 1
    B  = ½·β·a*² + P_c(σ − a*) = 5 + 10·4 = 45
    q* = (P_s − γ − B)/δ = (P_s − 50)/2         (per firm)
    S_dom + M = D:  (P_s − 50) + 0.2·P_s = 40 − 0.3·P_s
                 => 1.5·P_s = 90 => P_s* = 60, q* = 5, e* = (5 − 1)·5 = 20
    aggregate emissions = 2·20 = 40 = Cap (the anchor's binding cap)

This is the standalone slice; the true joint (P_s, P_c) cycle is D3-4.
"""

from __future__ import annotations

import numpy as np

from pe.engine import run_simulation_from_config

_PRODUCER = {
    "kind": "producer",
    "output_cost": {"gamma": 5.0, "delta": 2.0},
    "intensity": 5.0,
    "abatement": {"beta": 10.0, "a_max": 5.0},
}

_SCENARIO = {
    "scenarios": [
        {
            "name": "steel-standalone",
            "model_approach": "product",
            "carbon_price": 10.0,
            "product_demand": {"form": "linear", "intercept": 40.0, "slope": 0.3},
            "import_supply": {"world_price": 0.0, "slope": 0.2},
            "years": [
                {
                    "year": "2030",
                    "participants": [
                        {"name": "SteelCo A", **_PRODUCER},
                        {"name": "SteelCo B", **_PRODUCER},
                    ],
                }
            ],
        }
    ]
}


def test_product_market_clears_to_the_anchor_price() -> None:
    """P_s = 60, per-firm q = 5, aggregate emissions = 40 (V-D3-5b P_c-fixed slice)."""
    summary_df, participant_df = run_simulation_from_config(_SCENARIO)

    # One market-year, two producer rows.
    assert len(summary_df) == 1
    assert len(participant_df) == 2

    # Cleared steel price P_s* = 60 (the summary host carries it under the
    # generic price column).
    np.testing.assert_allclose(
        float(summary_df.iloc[0]["Equilibrium Carbon Price"]), 60.0, rtol=0.0, atol=1e-6
    )

    # Per-firm output q* = 5.
    np.testing.assert_allclose(
        participant_df["Output"].to_numpy(dtype=float),
        np.array([5.0, 5.0]),
        rtol=0.0,
        atol=1e-6,
    )
    # Aggregate residual emissions Σe* = 40 (= binding cap of the anchor).
    np.testing.assert_allclose(float(participant_df["Emissions"].sum()), 40.0, rtol=0.0, atol=1e-6)
    # Per-firm intensity abatement a* = 1.
    np.testing.assert_allclose(
        participant_df["Intensity Abatement"].to_numpy(dtype=float),
        np.array([1.0, 1.0]),
        rtol=0.0,
        atol=1e-6,
    )


def test_product_dispatch_is_deterministic() -> None:
    """Identical config → identical solved price/output/emissions (fixed Brent)."""
    summary_a, participants_a = run_simulation_from_config(_SCENARIO)
    summary_b, participants_b = run_simulation_from_config(_SCENARIO)

    np.testing.assert_array_equal(
        summary_a["Equilibrium Carbon Price"].to_numpy(dtype=float),
        summary_b["Equilibrium Carbon Price"].to_numpy(dtype=float),
    )
    for column in ("Output", "Emissions", "Profit", "Intensity Abatement"):
        np.testing.assert_array_equal(
            participants_a[column].to_numpy(dtype=float),
            participants_b[column].to_numpy(dtype=float),
        )


def test_producer_delta_zero_is_rejected_at_config_time() -> None:
    """δ ≤ 0 (indeterminate output, spec §2 [JC3]) raises loudly in the config door."""
    import pytest

    bad = {
        "scenarios": [
            {
                "name": "bad-steel",
                "model_approach": "product",
                "carbon_price": 10.0,
                "product_demand": {"form": "linear", "intercept": 40.0, "slope": 0.3},
                "import_supply": {"world_price": 0.0, "slope": 0.2},
                "years": [
                    {
                        "year": "2030",
                        "participants": [
                            {
                                "name": "FlatCo",
                                "kind": "producer",
                                "output_cost": {"gamma": 5.0, "delta": 0.0},
                                "intensity": 5.0,
                                "abatement": {"beta": 10.0, "a_max": 5.0},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    with pytest.raises(ValueError, match="delta must be > 0"):
        run_simulation_from_config(bad)
