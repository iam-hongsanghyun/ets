r"""D0-R4 non-carbon showcase anchors (docs/platform-plan-d0-d1.md D0-R4;
docs/platform-spec-d0-d1.md §1/§8, the economist's E1b calibration).

``examples/showcase_rps_rec.json`` re-interprets the EXISTING carbon-market
kernel as an RPS/REC obligation market — zero new mechanism code, only
``flow_label``/``flow_unit``/``price_unit`` (D0-R2, display-only) differ from
a carbon example. Proves spec §1.1's reinterpretation table: ``penalty_price``
is an obligation-EXTINGUISHING buyout (the RPS Alternative Compliance
Payment), and ``investment_trigger`` is the same renewable-entry mechanism
``docs/invest-feedback-spec.md`` already ships.

Design (the "why a 4-participant market, not one piecewise MAC participant"):
the retailer itself carries ZERO abatement capacity (``abatement_type
"threshold"``, ``max_abatement 0``) and relies entirely on three genuine
counterparties — B1 (60 TWh @ $8), B2 (50 TWh @ $22), and the
investment-gated B3 (40 TWh @ $38) — each a 100%-free-allocated ``threshold``
seller. This is the ONLY way this engine's ``offered <= 0`` "OTC / net demand
0" auction branch (``core.market.clearing.solve_equilibrium``) finds a
genuine sign-changing price crossing: a lone deficit-only participant (no
possible surplus) can never drive aggregate net demand negative, so
Brent's-method search on ``core.market.clearing._solve_for_supply`` collapses
trivially to ``price_upper_bound`` instead of the marginal self-supply cost
(verified empirically while building this file — see the KNOWN DISCREPANCY
note on anchor 2's 2030 cell below for the one case this still doesn't fully
resolve).

Two anchors (docs/platform-plan-d0-d1.md D0-R4 work order; anchor 3, the
banking variant, is explicitly out of this rung's scope):

1. ACP-binding (pre-adoption): the masked path (B3 absent — spec D2.5's
   "flagged option DELETED", built here by dropping the B3 participant and
   the master gate rather than hand-duplicating the example) prices
   [8, 22, 22, ~45, ~45]; the buyout binds in 2029 (obligation 120 TWh
   crosses the below-ACP self-supply capacity, 110 TWh).
2. Buyout-triggers-entry (post-adoption): the first masked-path crossing of
   theta=40 is 2029 -> adoption tau=2029; the final path is
   [8, 22, 22, 38, ...] with the ex-post-regret INFO log firing at 2029
   (delivered 38 < theta 40).

Both anchors are run BY EXECUTING ``examples/showcase_rps_rec.json`` (or the
pre-adoption variant derived from it) through ``run_simulation_from_config``
— never re-derived by hand — per the work order's "verify by running, report
any discrepancy" instruction.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from pe import run_simulation_from_config, run_simulation_from_file
from pe.config_io import load_config

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
SHOWCASE_PATH = EXAMPLES_DIR / "showcase_rps_rec.json"

_YEARS = ("2026", "2027", "2028", "2029", "2030")
_OBLIGATIONS = {"2026": 50.0, "2027": 70.0, "2028": 90.0, "2029": 120.0, "2030": 150.0}


def _price_by_year(summary_df) -> dict[str, float]:
    return {
        str(row["Year"]): float(row["Equilibrium Carbon Price"]) for _, row in summary_df.iterrows()
    }


def _abatement_by_year(participant_df) -> dict[str, float]:
    """Aggregate self-supply delivered (all sellers) per year.

    Robust settlement-volume proxy (see module docstring's KNOWN
    DISCREPANCY note): ``obligation - self_supply_delivered`` equals the
    genuine shortfall settled at the ACP-equal clearing price in a
    capacity-constrained year (2029/2030 here), independent of the
    kernel's own ``penalty_emissions`` bookkeeping, which this
    multi-participant OTC design does not exercise (documented below).
    """
    totals: dict[str, float] = {year: 0.0 for year in _YEARS}
    for _, row in participant_df.iterrows():
        year = str(row["Year"])
        if year in totals:
            totals[year] += float(row["Abatement"])
    return totals


def _load_raw_showcase() -> dict[str, Any]:
    return json.loads(SHOWCASE_PATH.read_text())


def _pre_adoption_variant(raw: dict[str, Any]) -> dict[str, Any]:
    """B3-deleted equivalent of the showcase (spec D2.5 / V3 semantics).

    Drops the "Offshore Wind Seller" participant from every year and turns
    off ``investment_feedback_enabled`` — "feature ON but never triggered"
    is DEFINED to equal "flagged option DELETED" (D2.5), so this is the
    masked (pre-adoption) economy anchor 1 is stated against, built from
    the real example rather than hand-duplicated.
    """
    variant = copy.deepcopy(raw)
    scenario = variant["scenarios"][0]
    scenario["investment_feedback_enabled"] = False
    for year in scenario["years"]:
        year["participants"] = [
            p for p in year["participants"] if p["name"] != "Offshore Wind Seller"
        ]
    return variant


# ── Anchor 1: ACP-binding (pre-adoption / masked path) ──────────────────────


def test_anchor1_pre_adoption_prices_and_acp_binding() -> None:
    raw = _load_raw_showcase()
    pre_adoption_config = _pre_adoption_variant(raw)

    summary_df, participant_df = run_simulation_from_config(pre_adoption_config)
    prices = _price_by_year(summary_df)

    expected = {"2026": 8.0, "2027": 22.0, "2028": 22.0, "2029": 45.0, "2030": 45.0}
    np.testing.assert_allclose(
        [prices[y] for y in _YEARS],
        [expected[y] for y in _YEARS],
        atol=1e-6,
        err_msg="pre-adoption RPS/REC price path drifted from spec §8 anchor 1",
    )

    # The buyout binds in 2029: obligation (120 TWh) exceeds the below-ACP
    # self-supply capacity (B1 60 + B2 50 = 110 TWh) by 10 TWh, settled at
    # the ACP-equal clearing price (atol 1e-6 of 45.0, asserted above).
    abatement = _abatement_by_year(participant_df)
    settlement_2029 = _OBLIGATIONS["2029"] - abatement["2029"]
    assert settlement_2029 == pytest.approx(10.0, abs=1e-6)
    settlement_2030 = _OBLIGATIONS["2030"] - abatement["2030"]
    assert settlement_2030 == pytest.approx(40.0, abs=1e-6)

    # KNOWN DISCREPANCY (reported, not silently patched — docs/platform-
    # plan-d0-d1.md D0-R4 instruction): the retailer's OWN
    # ``penalty_emissions`` bookkeeping stays 0 in this multi-participant
    # OTC design. Brent's-method convergence lands the clearing price a few
    # 1e-12 BELOW 45.0 (well inside the atol 1e-6 price assertion above),
    # never strictly above the retailer's own ``penalty_price`` threshold,
    # so ``compliance.py``'s ``carbon_price <= effective_penalty`` branch
    # keeps classifying the full obligation as "Allowance Buys" rather than
    # "Penalty Emissions" for the shortfall tranche. The settlement is
    # dollar-equivalent to a buyout (price == ACP, asserted above) and the
    # volume is robustly recovered via ``obligation - Total Abatement``
    # (asserted above) — but the literal ``penalty_emissions`` code path
    # (spec §1.1's "settles shortage via penalty_emissions") is NOT
    # exercised by this config. This assertion pins that fact so a future
    # solver change that starts exercising it is a visible, reviewed diff.
    total_penalty = float(
        summary_df.loc[summary_df["Year"] == "2029", "Total Penalty Emissions"].iloc[0]
    )
    assert total_penalty == pytest.approx(0.0, abs=1e-6)


# ── Anchor 2: buyout-triggers-entry (post-adoption / final path) ────────────


def test_anchor2_buyout_triggers_investment_entry() -> None:
    summary_df, _participant_df = run_simulation_from_file(SHOWCASE_PATH)
    prices = _price_by_year(summary_df)

    # Adoption year: the first masked-path crossing of theta=40 is 2029
    # (masked price 45 >= 40 there; anchor 1 confirms 2026-2028 stay well
    # below 40). build_lag_years=0 makes capacity effective the same year.
    row_2029 = summary_df.loc[summary_df["Year"] == "2029"].iloc[0]
    adoptions = json.loads(row_2029["Investment Adoptions"])
    assert adoptions == [
        {
            "adoption_year": "2029",
            "participant": "Offshore Wind Seller",
            "technology": "Offshore Wind B3",
        }
    ]
    assert float(row_2029["Investment Newly Effective"]) == pytest.approx(1.0)

    # Final path, years 2026-2029: a clean crossing (B1+B2+B3 = 150 TWh vs
    # 120 TWh obligation in 2029 — genuine oversupply above 38, not a tie).
    expected_clean = {"2026": 8.0, "2027": 22.0, "2028": 22.0, "2029": 38.0}
    for year, expected_price in expected_clean.items():
        assert prices[year] == pytest.approx(expected_price, abs=1e-6), year

    # KNOWN DISCREPANCY (reported per the D0-R4 work order, not silently
    # retuned): the economist's hand-calc states 2030 == 38.0 too. Running
    # the example shows otherwise — 2030's obligation (150 TWh) EXACTLY
    # equals total capacity (60+50+40 = 150 TWh), so aggregate net demand
    # is identically zero across the ENTIRE [38, 45] price band (no
    # shortfall anywhere in that band, but no excess supply either until
    # the retailer's own 45 threshold also drops out). That is an
    # economically indeterminate tie; Brent's method resolves it to an
    # arbitrary interior point of the band rather than the conventional
    # "marginal cost of the last unit used" (38) — a solver tie-breaking
    # artifact, not a config error (see the module docstring). The
    # PHYSICAL outcome is unaffected: 2030's obligation is fully
    # self-supplied (settlement volume 0, unlike 2029's 10 TWh), only the
    # displayed marginal price differs from the hand-calc. Pinned here
    # (rather than asserted against 38.0) as a regression baseline,
    # deterministic under the environment recorded in
    # tests/baselines/MANIFEST.json; flagged for economist review.
    assert prices["2030"] == pytest.approx(40.131578947368425, abs=1e-6)

    settlement_2030 = _OBLIGATIONS["2030"] - float(
        summary_df.loc[summary_df["Year"] == "2030"].iloc[0]["Total Abatement"]
    )
    assert settlement_2030 == pytest.approx(0.0, abs=1e-6)


def test_anchor2_ex_post_regret_info_log(caplog: pytest.LogCaptureFixture) -> None:
    """2029's adopted price (38) sits below its own trigger (theta 40) on
    the final path — spec D1.1's permitted "ex-post regret of discrete
    entry", logged at INFO, never silently."""
    with caplog.at_level(logging.INFO, logger="pe.engine.feedback"):
        run_simulation_from_file(SHOWCASE_PATH)

    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any(
        "Offshore Wind Seller" in message
        and "Offshore Wind B3" in message
        and "2029" in message
        and "delivered 38.0000 < P* 40.0000" in message
        for message in info_messages
    ), f"expected the D1.1 ex-post-regret INFO log; got: {info_messages}"


# ── decompile round-trip (mirrors tests/workflows/blocks/test_blocks_decompile.py) ──


def test_showcase_normalizes_and_carries_flow_vocabulary() -> None:
    """Sanity check the example's D0-R2 flow vocabulary survives normalize_config."""
    normalized = load_config(SHOWCASE_PATH)
    scenario = normalized["scenarios"][0]
    assert scenario["flow_label"] == "REC"
    assert scenario["flow_unit"] == "TWh"
    assert scenario["price_unit"] == "USD/MWh"
