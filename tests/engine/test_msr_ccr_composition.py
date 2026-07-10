r"""Regression tests for F1 — additive MSR + CCR supply composition.

Reference
---------
`docs/blocks-composition-rules.md` §0 F1 and `docs/blocks-graph-plan.md`
Work Order 1b. The competitive per-year pipeline
(`src/ets/solvers/simulation.py:_simulate_path_details`) used to REASSIGN
``effective_carry = carry_forward_allowances + msr_net`` after having added
the CCR cap adjustment, silently discarding ``ccr_adjustment`` in any year
where both rules were active. The economist-approved composition is additive.

Algorithm:
    LaTeX:
    $$ Q_t \;=\; \overline{Q}_t \;+\; \Delta Q_t^{CCR}
              \;+\; \left( r_t - w_t \right) $$

    ASCII fallback:
        Q_t = Qbar_t + dQ_CCR_t + (released_t - withheld_t)

    Symbols (units):
        Q_t        : effective auction supply cleared in year t     [Mt CO2e]
        Qbar_t     : scheduled auction volume (+ any carry-forward) [Mt CO2e]
        dQ_CCR_t   : CCR cap adjustment from lagged deviations,
                     phi_e*(e_{t-1}-ebar)/ebar + phi_z*(z_{t-1}-zbar)/zbar
                                                                    [Mt CO2e]
        r_t        : MSR release from the reserve pool in year t    [Mt CO2e]
        w_t        : MSR withholding from auction in year t         [Mt CO2e]

Both supply operators read only beginning-of-year state (previous bank for
the MSR; previous realised emissions / abatement cost for the CCR), so their
adjustments are independent inputs to the same clearing and must add.

Test design (end-to-end scenario, hand-solvable):
    Two participants, linear MACs with unit slope (cost = 0.5 * a^2):
      * Buyer:  e0 = 100 Mt, no free allocation  -> demand D(p) = 100 - p.
      * Banker: e0 = 50 Mt, 100% free allocation -> with manual expected
        price V > p it banks its surplus (net trade 0) and abates a = V.
    Clearing therefore satisfies 100 - p = Q_t, i.e. p_t = 100 - Q_t.

    Year 1 (2030, V = 25): no rule history/bank -> Q_1 = 80, p_1 = 20.
      Buyer abates 20 (cost 200), Banker abates 25 (cost 312.5), so
      e_1 = 80 + 25 = 105 Mt, z_1 = 512.5, bank_1 = 50 - 25 = 25 Mt.
    Year 2 (2031, V = 45):
      MSR: bank_1 = 25 > upper threshold 20 -> w_2 = 0.25 * 80 = 20 Mt.
      CCR: dQ_2 = -50*(105-100)/100 + 40*(512.5-500)/500 = -2.5 + 1.0 = -1.5.
      Additive composition -> Q_2 = 80 - 1.5 - 20 = 58.5 Mt, p_2 = 41.5.
      Pre-fix (overwrite)   -> Q_2 = 80 - 20 = 60.0 Mt, p_2 = 40.0,
      so the equality assertions below fail if the reassignment returns.
"""

from __future__ import annotations

import numpy as np
import pytest

from ets.ccr import CCRState
from ets.msr import MSRState
from ets.solvers import run_simulation_from_config

# ── Closed-form: the composition arithmetic itself ───────────────────────────


def test_effective_supply_composes_additively_withhold_case():
    """Q = Qbar + dQ_CCR + (r - w) with a nonzero CCR term and MSR withhold."""
    auction_offered = 80.0  # Mt CO2e scheduled for auction
    carry_forward = 0.0  # Mt CO2e carried from unsold prior auctions

    ccr = CCRState()
    ccr.record(emissions=105.0, abatement_cost=512.5)  # year t-1 outcomes
    dq_ccr, _, _ = ccr.cap_adjustment(
        phi_emissions=-50.0,
        phi_abatement_cost=40.0,
        reference_emissions=100.0,
        reference_abatement_cost=500.0,
    )
    np.testing.assert_allclose(dq_ccr, -1.5, rtol=0, atol=1e-12)

    msr = MSRState()
    _, withheld, released = msr.apply(
        total_bank=25.0,  # beginning-of-year bank > upper threshold
        auction_offered=auction_offered,
        upper_threshold=20.0,
        lower_threshold=0.0,
        withhold_rate=0.25,
        release_rate=0.0,
    )
    np.testing.assert_allclose(withheld, 20.0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(released, 0.0, rtol=0, atol=1e-12)

    effective_supply = auction_offered + carry_forward + dq_ccr + (released - withheld)
    np.testing.assert_allclose(effective_supply, 58.5, rtol=0, atol=1e-12)
    # The pre-fix overwrite would have produced Qbar + (r - w) = 60.0.
    assert abs(effective_supply - 60.0) > 1.0


def test_effective_supply_composes_additively_release_case():
    """Same identity when the MSR releases from a funded reserve pool."""
    auction_offered = 80.0

    ccr = CCRState()
    ccr.record(emissions=95.0, abatement_cost=550.0)
    dq_ccr, _, _ = ccr.cap_adjustment(
        phi_emissions=-50.0,
        phi_abatement_cost=40.0,
        reference_emissions=100.0,
        reference_abatement_cost=500.0,
    )
    # -50*(-0.05) + 40*(0.10) = +2.5 + 4.0 = +6.5
    np.testing.assert_allclose(dq_ccr, 6.5, rtol=0, atol=1e-12)

    msr = MSRState(initial_reserve=30.0)
    _, withheld, released = msr.apply(
        total_bank=5.0,  # bank below the lower threshold triggers release
        auction_offered=auction_offered,
        upper_threshold=200.0,
        lower_threshold=10.0,
        withhold_rate=0.12,
        release_rate=15.0,
    )
    np.testing.assert_allclose(withheld, 0.0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(released, 15.0, rtol=0, atol=1e-12)

    effective_supply = auction_offered + dq_ccr + (released - withheld)
    np.testing.assert_allclose(effective_supply, 101.5, rtol=0, atol=1e-12)


# ── End-to-end: both rules active in the same competitive year ───────────────


def _year(label: str, manual_expected_price: float) -> dict:
    return {
        "year": label,
        "total_cap": 130.0,
        "auction_mode": "explicit",
        "auction_offered": 80.0,
        "price_lower_bound": 0.0,
        "price_upper_bound": 300.0,
        "banking_allowed": True,
        "expectation_rule": "manual",
        "manual_expected_price": manual_expected_price,
        "participants": [
            {
                "name": "Buyer",
                "initial_emissions": 100.0,
                "free_allocation_ratio": 0.0,
                "penalty_price": 1000.0,
                "abatement_type": "linear",
                "max_abatement": 100.0,
                "cost_slope": 1.0,
            },
            {
                "name": "Banker",
                "initial_emissions": 50.0,
                "free_allocation_ratio": 1.0,
                "penalty_price": 1000.0,
                "abatement_type": "linear",
                "max_abatement": 60.0,
                "cost_slope": 1.0,
            },
        ],
    }


def _scenario(name: str, msr_enabled: bool, ccr_enabled: bool) -> dict:
    scenario: dict = {
        "name": name,
        "model_approach": "competitive",
        "msr_enabled": msr_enabled,
        "ccr_enabled": ccr_enabled,
        # V_1 = 25 > p_1 = 20 and V_2 = 45 > p_2 in every variant, so the
        # Banker banks (never sells) and clearing stays D(p) = Q_t.
        "years": [_year("2030", 25.0), _year("2031", 45.0)],
    }
    if msr_enabled:
        scenario.update(
            msr_upper_threshold=20.0,
            msr_lower_threshold=0.0,
            msr_withhold_rate=0.25,
            msr_release_rate=0.0,
        )
    if ccr_enabled:
        scenario.update(
            ccr_phi_emissions=-50.0,
            ccr_phi_abatement_cost=40.0,
            ccr_reference_emissions=100.0,
            ccr_reference_abatement_cost=500.0,
        )
    return scenario


@pytest.fixture(scope="module")
def summary():
    config = {
        "scenarios": [
            _scenario("Both", msr_enabled=True, ccr_enabled=True),
            _scenario("MSR only", msr_enabled=True, ccr_enabled=False),
            _scenario("CCR only", msr_enabled=False, ccr_enabled=True),
        ]
    }
    summary_df, _ = run_simulation_from_config(config)
    return summary_df


def _row(summary_df, scenario: str, year: str):
    rows = summary_df[
        (summary_df["Scenario"] == scenario) & (summary_df["Year"] == year)
    ]
    assert len(rows) == 1
    return rows.iloc[0]

# Participant abatement optima come from bounded scalar minimisation
# (xatol ~1e-5), so hand values are matched to ~1e-4; atol=1e-3 is safely
# above solver noise and far below the 1.5 Mt / 1.5 EUR discriminating gap.
ATOL = 1e-3


def test_first_year_is_rule_neutral(summary):
    """Year 1 has no bank and no CCR history: all variants clear identically."""
    for scenario in ("Both", "MSR only", "CCR only"):
        row = _row(summary, scenario, "2030")
        np.testing.assert_allclose(row["Auction Offered"], 80.0, rtol=0, atol=ATOL)
        np.testing.assert_allclose(
            row["Equilibrium Carbon Price"], 20.0, rtol=0, atol=ATOL
        )
        np.testing.assert_allclose(row["MSR Withheld"], 0.0, rtol=0, atol=ATOL)
        np.testing.assert_allclose(row["CCR Cap Adjustment"], 0.0, rtol=0, atol=ATOL)


def test_msr_and_ccr_adjustments_both_reach_clearing(summary):
    """Year 2, both rules on: Q_2 = 80 + (-1.5) + (-20) = 58.5, p_2 = 41.5.

    The pre-fix overwrite discarded the CCR term and produced Q_2 = 60.0
    (p_2 = 40.0); these equality assertions fail if the reassignment returns.
    """
    row = _row(summary, "Both", "2031")
    # Both rule signals fired, and with hand-computed magnitudes.
    np.testing.assert_allclose(row["MSR Withheld"], 20.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["CCR Cap Adjustment"], -1.5, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["CCR Emissions Deviation"], 0.05, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["CCR Cost Deviation"], 0.025, rtol=0, atol=ATOL)
    # The cleared supply and price reflect BOTH adjustments additively.
    np.testing.assert_allclose(row["Auction Offered"], 58.5, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["Auction Sold"], 58.5, rtol=0, atol=ATOL)
    np.testing.assert_allclose(
        row["Equilibrium Carbon Price"], 41.5, rtol=0, atol=ATOL
    )
    # Explicit guard against the pre-fix (CCR-discarding) values.
    assert abs(float(row["Auction Offered"]) - 60.0) > 1.0
    assert abs(float(row["Equilibrium Carbon Price"]) - 40.0) > 1.0


def test_msr_only_year_unchanged(summary):
    """MSR alone: Q_2 = 80 - 20 = 60, p_2 = 40 (identical pre/post fix)."""
    row = _row(summary, "MSR only", "2031")
    np.testing.assert_allclose(row["MSR Withheld"], 20.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["CCR Cap Adjustment"], 0.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["Auction Offered"], 60.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(
        row["Equilibrium Carbon Price"], 40.0, rtol=0, atol=ATOL
    )


def test_ccr_only_year_unchanged(summary):
    """CCR alone: Q_2 = 80 - 1.5 = 78.5, p_2 = 21.5 (identical pre/post fix)."""
    row = _row(summary, "CCR only", "2031")
    np.testing.assert_allclose(row["MSR Withheld"], 0.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["CCR Cap Adjustment"], -1.5, rtol=0, atol=ATOL)
    np.testing.assert_allclose(row["Auction Offered"], 78.5, rtol=0, atol=ATOL)
    np.testing.assert_allclose(
        row["Equilibrium Carbon Price"], 21.5, rtol=0, atol=ATOL
    )
