r"""Regression tests for the hoarding feature module (O10, Friction provider).

Reference
---------
``docs/feature-modules-plan.md`` PLAN v2 §3 (hoarding split) and the binding
Arbitration O10 item: ONLY the inflow schedule reader moves to
``features/hoarding/plugin.py``; the EXTENDED HOST SET — the static-year
supply reduction S_t − h_t, the no-arbitrage-prune exemption for hoarding
years (the documented λ ≈ 0 violation), the window-start constraint
a > max{t : h_t > 0}, and the bank accumulation — stays in the banking host
(``solvers/banking.py:solve_banking_window``). The ``Friction`` protocol
docstring pins those semantics as the contract.

Equivalence anchors: the closed forms of ``tests/test_banking.py``'s hoarding
tests (S = (70, 95, 80), h = (5, 0, 0): static year at S_0 − h_0, window
budget + h_0) and the ``k_ets_hoarding_basic`` golden baseline (bit-exact in
the golden gate).
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from pe.config_io import build_markets_from_config
from pe.core.protocols import Friction
from pe.features.hoarding.plugin import HoardingInflow
from pe.engine import solve_banking_path
from pe.engine.wiring import default_friction as _default_friction

E = 100.0  # BAU emissions per year [Mt]
C = 100.0  # linear MAC slope [KRW per t per Mt]
R = 0.05  # carry rate [1/yr]


def _config(supplies: list[float], hoarding: list[float] | None = None) -> dict:
    years = []
    for index, supply in enumerate(supplies):
        years.append(
            {
                "year": str(2030 + index),
                "hoarding_inflow": float(hoarding[index]) if hoarding else 0.0,
                "total_cap": supply,
                "auction_mode": "derive_from_cap",
                "banking_allowed": False,
                "borrowing_allowed": False,
                "expectation_rule": "next_year_baseline",
                "price_lower_bound": 0.0,
                "price_upper_bound": 100000.0,
                "participants": [
                    {
                        "name": "Industry",
                        "initial_emissions": E,
                        "free_allocation_ratio": 0.0,
                        "penalty_price": 0.0,
                        "abatement_type": "linear",
                        "max_abatement": E,
                        "cost_slope": C,
                    }
                ],
            }
        )
    return {
        "scenarios": [
            {
                "name": "hoarding-friction",
                "model_approach": "banking",
                "discount_rate": R,
                "banking_initial_bank": 0.0,
                "years": years,
            }
        ]
    }


def _prices(path: list[dict]) -> list[float]:
    return [float(item["equilibrium"]["price"]) for item in path]


# ── The reader (all that moved) ──────────────────────────────────────────────


def test_hoarding_inflow_satisfies_the_friction_protocol():
    assert isinstance(HoardingInflow(), Friction)


def test_inflow_reads_the_year_field_and_is_neutral_when_unconfigured():
    reader = HoardingInflow()
    assert reader.inflow(SimpleNamespace(hoarding_inflow=5.0)) == 5.0
    assert reader.inflow(SimpleNamespace(hoarding_inflow=None)) == 0.0
    assert reader.inflow(SimpleNamespace(hoarding_inflow=0.0)) == 0.0
    assert reader.inflow(SimpleNamespace()) == 0.0  # field absent


def test_default_friction_attaches_only_when_configured():
    """Transitional wiring gate: the feature's reader when any year hoards,
    None (neutral) otherwise."""
    hoarding_markets = [SimpleNamespace(hoarding_inflow=0.0), SimpleNamespace(hoarding_inflow=5.0)]
    assert isinstance(_default_friction(hoarding_markets), HoardingInflow)
    assert _default_friction([SimpleNamespace(), SimpleNamespace(hoarding_inflow=0.0)]) is None


# ── Equivalence: injected reader vs default wiring vs closed forms ───────────


def test_injected_friction_matches_the_default_wiring_bit_for_bit():
    """Passing HoardingInflow() explicitly (what engine/wiring.py will do) is
    the same solve as the default gate — including the host-set behaviour:
    static hoarding year at S_0 − h_0 and the window budget gaining h_0
    (closed forms from tests/test_banking.py)."""
    config = _config([70.0, 95.0, 80.0], hoarding=[5.0, 0.0, 0.0])
    default = solve_banking_path(build_markets_from_config(config), discount_rate=R)
    injected = solve_banking_path(
        build_markets_from_config(config), discount_rate=R, friction=HoardingInflow()
    )
    for a, b in zip(default, injected, strict=True):
        np.testing.assert_allclose(
            float(a["equilibrium"]["price"]), float(b["equilibrium"]["price"]), rtol=0, atol=0
        )
        np.testing.assert_allclose(
            float(a["banking_aggregate_bank"]), float(b["banking_aggregate_bank"]), rtol=0, atol=0
        )

    # Host-set closed forms (the extended host set stayed in banking):
    prices = _prices(default)
    np.testing.assert_allclose(prices[0], C * (E - 65.0), rtol=1e-6)  # S_0 − h_0
    p1_expected = C * (2 * E - 95.0 - 80.0 - 5.0) / (2.0 + R)  # window + h_0
    np.testing.assert_allclose(prices[1], p1_expected, rtol=1e-5)
    np.testing.assert_allclose(prices[2], p1_expected * (1 + R), rtol=1e-5)
    np.testing.assert_allclose(default[0]["banking_aggregate_bank"], 5.0, atol=1e-4)
    assert default[0]["banking_regime"] == "static"
    assert default[1]["banking_regime"] == "hotelling"


def test_zero_friction_override_neutralizes_configured_hoarding():
    """Injection discriminator: a zero Friction on a hoarding-configured
    scenario reproduces the no-hoarding equilibrium bit-for-bit — the solver
    reads h_t ONLY through the injected reader."""

    class _ZeroFriction:
        def inflow(self, market) -> float:
            return 0.0

    hoarded_config = _config([70.0, 95.0, 80.0], hoarding=[5.0, 0.0, 0.0])
    clean_config = _config([70.0, 95.0, 80.0])
    neutralized = solve_banking_path(
        build_markets_from_config(hoarded_config), discount_rate=R, friction=_ZeroFriction()
    )
    clean = solve_banking_path(build_markets_from_config(clean_config), discount_rate=R)
    for a, b in zip(neutralized, clean, strict=True):
        np.testing.assert_allclose(
            float(a["equilibrium"]["price"]), float(b["equilibrium"]["price"]), rtol=0, atol=0
        )
        np.testing.assert_allclose(
            float(a["banking_aggregate_bank"]), float(b["banking_aggregate_bank"]), rtol=0, atol=0
        )
    # And it genuinely differs from the hoarded solve (h_0 = 5 moves year 0).
    hoarded = solve_banking_path(build_markets_from_config(hoarded_config), discount_rate=R)
    assert abs(_prices(hoarded)[0] - _prices(neutralized)[0]) > 100.0
