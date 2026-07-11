r"""Economist validation anchors V2-V7 (EI-7, docs/invest-feedback-spec.md D4-D5).

Anchor coverage map (the binding D5 table; earlier orders own the rest —
verified, not duplicated here):

* V1a break-even dating on a hand-solved 3-yr competitive path —
  ``tests/config_io/test_investment_config.py``
  ``test_end_to_end_config_driven_activation`` (EI-6).
* V1b/V1c multiples — ``tests/core/test_investment_math.py`` (EI-1).
* V8 adversarial termination — ``tests/engine/test_investment_feedback.py``
  ``test_v8_adversarial_two_candidates_terminate_in_n_plus_one`` (EI-5).
* V2-V7 — THIS FILE. V7 lives here (not ``tests/engine/test_policy_events
  .py``) because it needs the same hand-solvable flagged economy as the
  other anchors; the splice host itself is exercised through
  ``run_simulation_from_config`` exactly as a user config would.

The shared economy (REPLACEMENT shape — deliberately no SLSQP):

Algorithm:
    One participant, linear MAC, one flagged option that REPLACES the base
    technology on adoption (a single configured ``technology_options`` entry
    routes ``optimize_compliance`` through the exact single-technology
    optimizer — no mixed-portfolio SLSQP step, so every clearing price below
    is analytic):

    LaTeX:
    $$ e^{\mathrm{base}}(P) = E - P/c, \qquad
       e^{\mathrm{post}}(P) = E_h - P/c, \qquad
       e(P^*_t) = S_t \;\Rightarrow\;
       P_t = c\,(E - S_t) \;\text{masked},\;\; c\,(E_h - S_t)\;\text{adopted} $$

    ASCII fallback:
        masked years : P_t = c * (E - S_t)   = 2 * (100 - S_t)
        adopted years: P_t = c * (E_h - S_t) = 2 * (70  - S_t)

    Symbols (units):
        E    : base BAU emissions, 100 [Mt CO2e]
        E_h  : flagged option's BAU emissions, 70 [Mt CO2e] (30% cleaner)
        c    : linear MAC slope, 2 [currency/tCO2 per Mt]
        S_t  : year-t circulating supply (auction, derive_from_cap) [Mt CO2e]
        P_t  : competitive clearing price of year t [currency/tCO2]

    Trigger (spec D2.1): P* = M(σ_eff, r, y) · θ with σ_eff = (1-q)σ;
    σ = 0 (V2/V5) gives the certainty wedge M = r/y = 11/6 exactly at
    r = 0.055, y = 0.03, so θ = 48 puts P* = 88 strictly between the
    year-1 (80) and year-2 (100) masked prices.
"""

from __future__ import annotations

import copy
import json
import math
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ets import run_simulation_from_config

R = 0.055  # scenario discount rate r [1/yr]
Y = 0.03  # payout yield y [1/yr]

_INVESTMENT_COLUMNS = [
    "Investment Adoptions",
    "Investment Newly Effective",
    "Investment Feedback Iterations",
    "Investment Converged",
]

_TWO_YEARS = (("2031", 60.0), ("2032", 50.0))
_THREE_YEARS = (("2031", 60.0), ("2032", 50.0), ("2033", 40.0))
_FOUR_YEARS = (("2031", 60.0), ("2032", 50.0), ("2033", 45.0), ("2034", 40.0))


def _economy_config(
    name: str,
    *,
    with_option: bool = True,
    flag: bool = True,
    theta: float = 48.0,
    trigger_mode: str = "dixit_pindyck",
    sigma: float = 0.0,
    credibility: float | None = None,
    fixed_cost: float = 0.0,
    lag: int = 0,
    approach: str = "competitive",
    floor: float | None = None,
    unsold: str | None = None,
    msr: bool = False,
    supplies: tuple[tuple[str, float], ...] = _TWO_YEARS,
    policy_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the shared hand-solvable economy as a config dict (module docstring)."""
    h2 = {
        "name": "H2-DRI",
        "initial_emissions": 70.0,
        "abatement_type": "linear",
        "max_abatement": 70.0,
        "cost_slope": 2.0,
        "max_activity_share": 1.0,
        "fixed_cost": fixed_cost,
        "investment_trigger": {
            "break_even_price": theta,
            "payout_yield": Y,
            "sigma": sigma,
            "trigger_mode": trigger_mode,
            "build_lag_years": lag,
        },
    }
    years = []
    for year, supply in supplies:
        yr: dict[str, Any] = {
            "year": year,
            "total_cap": supply,
            "auction_mode": "derive_from_cap",
            # Pinned-zero expectations: banking_allowed is false everywhere in
            # this economy, so expected prices are payoff-IRRELEVANT — but the
            # default next_year_baseline rule REPORTS next year's baseline in
            # the participant frame's "Expected Future Price" column, which
            # legitimately differs between the ON and OFF economies (the ON
            # run's 2032 baseline is the post-adoption price). Pinning the
            # expectation to manual/0 keeps every V2/V3 row comparison exactly
            # bit-identical without dropping columns.
            "expectation_rule": "manual",
            "manual_expected_price": 0.0,
            "price_lower_bound": 0.0,
            "price_upper_bound": 100000.0,
            "participants": [
                {
                    "name": "Steel",
                    "initial_emissions": 100.0,
                    "penalty_price": 1000.0,
                    "abatement_type": "linear",
                    "max_abatement": 100.0,
                    "cost_slope": 2.0,
                    **({"technology_options": [copy.deepcopy(h2)]} if with_option else {}),
                }
            ],
        }
        if floor is not None:
            yr["auction_reserve_price"] = floor
        if unsold is not None:
            yr["unsold_treatment"] = unsold
        years.append(yr)
    scenario: dict[str, Any] = {
        "name": name,
        "model_approach": approach,
        "discount_rate": R,
        "years": years,
    }
    if approach == "banking":
        scenario["banking_initial_bank"] = 0.0
    if flag:
        scenario["investment_feedback_enabled"] = True
    if credibility is not None:
        scenario["invest_credibility"] = credibility
    if msr:
        # Bank-threshold MSR, deliberately trigger-happy (upper threshold 2 Mt
        # against interior banks of ~5-15 Mt) so the valve genuinely moves.
        scenario.update(
            msr_enabled=True,
            msr_mode="bank_threshold",
            msr_upper_threshold=2.0,
            msr_lower_threshold=0.0,
            msr_withhold_rate=0.12,
            msr_release_rate=0.0,
        )
    if policy_events:
        scenario["policy_events"] = policy_events
    return {"scenarios": [scenario]}


def _rows(summary: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["Year"]): row for _, row in summary.iterrows()}


def _adoption_year(summary: pd.DataFrame) -> float:
    """Adoption year of the single flagged pair, +inf when never adopted."""
    events = json.loads(str(summary.iloc[-1]["Investment Adoptions"]))
    if not events:
        return math.inf
    assert len(events) == 1
    return float(events[0]["adoption_year"])


# ── V2 — 2-period, 1-technology worked example ──────────────────────────────


def test_v2_adoption_year_two_and_post_adoption_price() -> None:
    r"""V2: adoption year 2; post-adoption P2 equals the hand value (atol 1e-6).

    Algorithm:
        Hand solution (module-docstring economy, S = (60, 50), L = 0):

        LaTeX:
        $$ P^{\mathrm{masked}}_1 = 2(100-60) = 80, \quad
           P^{\mathrm{masked}}_2 = 2(100-50) = 100, \quad
           P^* = \tfrac{r}{y}\,\theta = \tfrac{11}{6}\cdot 48 = 88 $$
        $$ 80 < 88 \le 100 \Rightarrow \tau = 2032, \qquad
           P^{\mathrm{post}}_2 = 2(70-50) = 40 $$

        ASCII fallback:
            masked prices 80 / 100 straddle M*theta = (0.055/0.03)*48 = 88
            -> adoption year 2032; post-adoption clearing on the replacement
            demand 70 - P/2 = 50 gives P2 = 40.

        The loop: iterate 0 solves the masked path (80, 100), dates the
        crossing at 2032; iterate 1 solves with H2-DRI active from 2032 and
        proposes nothing new -> converged in 2 iterations.
    """
    summary, _ = run_simulation_from_config(_economy_config("v2"))
    rows = _rows(summary)
    assert _adoption_year(summary) == 2032.0
    np.testing.assert_allclose(
        float(rows["2032"]["Equilibrium Carbon Price"]), 40.0, rtol=0, atol=1e-6
    )
    np.testing.assert_allclose(float(rows["2032"]["Investment Feedback Iterations"]), 2.0, atol=0)
    np.testing.assert_allclose(float(rows["2032"]["Investment Converged"]), 1.0, atol=0)


def test_v2_year_one_row_bit_identical_to_feature_off() -> None:
    """V2 second clause: the pre-adoption year-1 row is bit-identical to the
    feature-OFF economy (which, per D2.5, is the flagged-option-DELETED
    economy — the masked participant IS the option-deleted participant)."""
    summary_on, participants_on = run_simulation_from_config(_economy_config("v2"))
    summary_off, participants_off = run_simulation_from_config(
        _economy_config("v2", with_option=False, flag=False)
    )
    on_1 = summary_on[summary_on["Year"] == "2031"].drop(columns=_INVESTMENT_COLUMNS)
    off_1 = summary_off[summary_off["Year"] == "2031"]
    assert_frame_equal(on_1.reset_index(drop=True), off_1.reset_index(drop=True), check_exact=True)
    p_on_1 = participants_on[participants_on["Year"] == "2031"]
    p_off_1 = participants_off[participants_off["Year"] == "2031"]
    assert_frame_equal(
        p_on_1.reset_index(drop=True), p_off_1.reset_index(drop=True), check_exact=True
    )


# ── V3 — trigger above the path supremum == flagged option DELETED ───────────


def test_v3_trigger_above_supremum_equals_option_deleted() -> None:
    """V3: feature ON but never triggered == the flagged option DELETED —
    assert_frame_equal EXACT on both frames (the summary after dropping the
    four investment diagnostics columns, which are the feature's reporting
    surface, not its economics). The masked path supremum is 120; θ = 10000
    puts P* = 18333 far above it, so no iterate ever crosses."""
    config_on = _economy_config("v3", theta=10000.0, supplies=_THREE_YEARS)
    config_deleted = _economy_config("v3", with_option=False, flag=False, supplies=_THREE_YEARS)
    summary_on, participants_on = run_simulation_from_config(config_on)
    summary_deleted, participants_deleted = run_simulation_from_config(config_deleted)

    assert_frame_equal(
        summary_on.drop(columns=_INVESTMENT_COLUMNS),
        summary_deleted,
        check_exact=True,
    )
    assert_frame_equal(participants_on, participants_deleted, check_exact=True)
    # The feature ran (one iterate, no flip) and reported exactly that.
    rows = _rows(summary_on)
    for year in ("2031", "2032", "2033"):
        assert rows[year]["Investment Adoptions"] == "[]"
        np.testing.assert_allclose(float(rows[year]["Investment Converged"]), 1.0, atol=0)
        np.testing.assert_allclose(float(rows[year]["Investment Feedback Iterations"]), 1.0, atol=0)


# ── V4 — comparative statics: floor, credibility, volatility ────────────────


@pytest.mark.parametrize(
    ("label", "base_kwargs", "prime_kwargs", "base_year", "prime_year"),
    [
        (
            # Higher reserve floor F' = 95 delivers the trigger already in
            # 2031 (delivered = max(80, 95) >= 90); without it the crossing
            # waits for the 2032 clearing at 100 (K-MSR Results 2-3 channel).
            "floor F=0 vs F'=95",
            {"theta": 90.0, "trigger_mode": "break_even"},
            {"theta": 90.0, "trigger_mode": "break_even", "floor": 95.0},
            2032.0,
            2031.0,
        ),
        (
            # Credibility q' = 1 collapses sigma_eff = (1-q)sigma to 0:
            # M falls from 3.858 (sigma=.3) to r/y = 1.833, P* from 115.7
            # (crossed only at 120, year 2033) to 55 (crossed at 80, 2031).
            "credibility q=0 vs q'=1 (sigma=0.3)",
            {"theta": 30.0, "sigma": 0.3},
            {"theta": 30.0, "sigma": 0.3, "credibility": 1.0},
            2033.0,
            2031.0,
        ),
        (
            # Lower volatility sigma' = 0: M falls from 6.386 (sigma=.48,
            # P* = 191.6 above the path supremum 120 -> NEVER adopts) to
            # 1.833 (P* = 55 -> adopts immediately).
            "sigma=0.48 vs sigma'=0",
            {"theta": 30.0, "sigma": 0.48},
            {"theta": 30.0, "sigma": 0.0},
            math.inf,
            2031.0,
        ),
    ],
)
def test_v4_adoption_weakly_earlier_under_floor_credibility_low_sigma(
    label: str,
    base_kwargs: dict[str, Any],
    prime_kwargs: dict[str, Any],
    base_year: float,
    prime_year: float,
) -> None:
    """V4: F <= F', q <= q', sigma >= sigma' => adoption weakly earlier under
    the primed variant (weak inequality on adoption years, never adopted =
    +inf). The exact years are also pinned — they are hand-derived from the
    masked path 80/100/120 and the resolved multiples (parametrize ids)."""
    summary_base, _ = run_simulation_from_config(
        _economy_config("v4-base", supplies=_THREE_YEARS, **base_kwargs)
    )
    summary_prime, _ = run_simulation_from_config(
        _economy_config("v4-prime", supplies=_THREE_YEARS, **prime_kwargs)
    )
    year_base = _adoption_year(summary_base)
    year_prime = _adoption_year(summary_prime)
    assert year_prime <= year_base, label
    assert year_base == base_year, label
    assert year_prime == prime_year, label


# ── V5 — capex double-count guard ────────────────────────────────────────────


def test_v5_capex_in_theta_books_once_fixed_cost_double_counts_visibly() -> None:
    r"""V5: capex belongs inside θ ONLY (spec D2.4); ``fixed_cost`` carries
    per-period overhead. θ is a TRIGGER input — it books no solve-side cost —
    so the spec-compliant config's total is the hand value with the capex
    counted once; stuffing the (annualized) capex into ``fixed_cost`` as well
    books it a second time, shifting the total by exactly that amount.

    Algorithm:
        Post-adoption year 2032 at the hand price P2 = 40 (V2):

        LaTeX:
        $$ C = \underbrace{\tfrac{1}{2}c\,a^2}_{=400}
             + \underbrace{P\,(E_h - a)}_{=2000} + F, \qquad a = P/c = 20 $$

        ASCII fallback:
            abatement 20, abatement cost 0.5*2*20^2 = 400,
            allowance buys (70-20)*40 = 2000, plus fixed cost F
            -> spec-compliant F = 10 (overhead only):    total 2410
            -> double-count F = 10 + 20 (capex again):   total 2430

        The fixed cost never enters the demand curve (single technology, no
        share choice), so BOTH configs clear at P2 = 40 — the double count
        shifts cost, never the price.
    """
    summary_spec, _ = run_simulation_from_config(
        _economy_config("v5-spec-compliant", fixed_cost=10.0)
    )
    summary_double, _ = run_simulation_from_config(
        _economy_config("v5-double-count", fixed_cost=30.0)
    )
    row_spec = _rows(summary_spec)["2032"]
    row_double = _rows(summary_double)["2032"]
    np.testing.assert_allclose(float(row_spec["Total Compliance Cost"]), 2410.0, rtol=0, atol=1e-6)
    np.testing.assert_allclose(
        float(row_double["Total Compliance Cost"]), 2430.0, rtol=0, atol=1e-6
    )
    np.testing.assert_allclose(
        float(row_double["Total Compliance Cost"]) - float(row_spec["Total Compliance Cost"]),
        20.0,
        rtol=0,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        float(row_spec["Equilibrium Carbon Price"]),
        float(row_double["Equilibrium Carbon Price"]),
        rtol=0,
        atol=1e-9,
    )


# ── V6 — waterbed / release-valve identities (spec D4.1-D4.2) ────────────────


def _v6_totals(kwargs: dict[str, Any], investment_on: bool) -> dict[str, float]:
    """Solve one V6 banking run; return the identity ingredients [Mt CO2e]."""
    config = _economy_config(
        f"v6-{'on' if investment_on else 'off'}",
        with_option=investment_on,
        flag=investment_on,
        theta=95.0,
        trigger_mode="break_even",
        approach="banking",
        supplies=_FOUR_YEARS,
        **kwargs,
    )
    summary, participants = run_simulation_from_config(config)
    rows = _rows(summary)
    years = [y for y, _ in _FOUR_YEARS]
    if investment_on:
        adopted = 0.0 if _adoption_year(summary) == math.inf else 1.0
    else:
        # Feature off: the guarded investment columns do not exist (plan D3).
        assert "Investment Adoptions" not in summary.columns
        adopted = 0.0
    return {
        "cum_residual": float(participants["Residual Emissions"].sum()),
        "base_supply": float(sum(s for _, s in _FOUR_YEARS)),
        "terminal_bank": float(rows[years[-1]]["Banking Aggregate Bank"]),
        "cancelled": float(sum(float(rows[y]["Banking Floor Cancelled"]) for y in years)),
        "msr_net": float(
            sum(float(rows[y]["MSR Withheld"]) - float(rows[y]["MSR Released"]) for y in years)
        ),
        "adopted": adopted,
    }


@pytest.mark.parametrize(
    ("label", "kwargs", "valve_moves"),
    [
        ("no MSR, no cancellation", {}, False),
        ("floor cancellation only", {"floor": 65.0, "unsold": "cancel"}, True),
        ("MSR only", {"msr": True}, True),
        ("MSR + floor cancellation", {"floor": 65.0, "unsold": "cancel", "msr": True}, True),
    ],
)
def test_v6_waterbed_and_release_valve_identities(
    label: str, kwargs: dict[str, Any], valve_moves: bool
) -> None:
    r"""V6: the D4.1/D4.2 accounting identities, investment ON vs OFF, 1e-3 Mt.

    Algorithm:
        Per run (banking, hoarding-free, initial bank B_0 = 0):

        LaTeX:
        $$ \sum_t e_t \;=\; \sum_t S_t + B_0 - B_T
           \;-\; \sum_t x_t \;-\; \sum_t (w_t - r_t) $$
        and across runs (ON $-$ OFF):
        $$ \Delta \sum_t e_t \;=\; -\,\Delta\Big(\sum_t x_t
           + \sum_t (w_t - r_t) + B_T\Big) $$

        ASCII fallback:
            cum_residual = base_supply + B0 - B_T - cancelled - msr_net
            delta(cum_residual) = -delta(cancelled + msr_net + B_T)

        Symbols (units, all Mt CO2e):
            e_t     : realised residual emissions of year t
            S_t     : configured circulating supply (free alloc + auction)
            B_0,B_T : initial / terminal aggregate bank
            x_t     : floor-unsold volume cancelled in year t
            w_t,r_t : MSR intake / release in year t

        D4.1 is the no-valve special case (x = w = r = 0): adoption shifts
        WHO abates and WHEN, never the cumulative total. D4.2 is the general
        case: the release valve (cancellation + net MSR retention) is the
        ONLY legal channel for the total to change.
    """
    on = _v6_totals(kwargs, investment_on=True)
    off = _v6_totals(kwargs, investment_on=False)

    for tag, run in (("ON", on), ("OFF", off)):
        np.testing.assert_allclose(
            run["cum_residual"],
            run["base_supply"] - run["terminal_bank"] - run["cancelled"] - run["msr_net"],
            rtol=0,
            atol=1e-3,
            err_msg=f"{label} [{tag}]: supply-accounting identity",
        )

    delta_emissions = on["cum_residual"] - off["cum_residual"]
    delta_valve = (on["cancelled"] + on["msr_net"] + on["terminal_bank"]) - (
        off["cancelled"] + off["msr_net"] + off["terminal_bank"]
    )
    np.testing.assert_allclose(
        delta_emissions, -delta_valve, rtol=0, atol=1e-3, err_msg=f"{label}: D4.2"
    )
    if not kwargs:
        # D4.1 fixed-cap waterbed: no valve, equal cumulative emissions.
        np.testing.assert_allclose(
            delta_emissions, 0.0, rtol=0, atol=1e-3, err_msg=f"{label}: D4.1"
        )

    # Bite guards: the run must actually exercise what its label claims.
    assert on["adopted"] == 1.0, f"{label}: the ON run must adopt"
    assert off["adopted"] == 0.0
    if "unsold" in kwargs:
        assert on["cancelled"] > 1.0, f"{label}: cancellation valve never moved"
    if kwargs.get("msr"):
        # The MSR must move somewhere in the PAIR (the D4.2 delta is what is
        # asserted). In the combined combo it moves in the OFF run only: the
        # ON run's floor-cancellation keeps the aggregate bank flat, so the
        # bank-threshold rule stays silent there — the two valves move in
        # opposite directions across the pair, which is exactly the
        # composition D4.2 has to absorb.
        assert on["msr_net"] > 1.0 or off["msr_net"] > 1.0, f"{label}: MSR valve never moved"
    if not valve_moves:
        assert on["cancelled"] == 0.0 and on["msr_net"] == 0.0


# ── V7 — splice irreversibility: a late event cannot un-adopt ────────────────


def test_v7_event_after_adoption_cannot_unadopt() -> None:
    r"""V7: a policy event announced AFTER the adoption year that prices the
    technology out — adoption persists across the splice (the carrier stamps
    ``investment_initial_adoptions`` into the next segment; monotone across
    segments; spec D3.4).

    Algorithm:
        Segment 1 (information set without the event) solves 2031-2034 on
        caps (60, 50, 50, 50): masked prices 80/100/100/100, θ = 90
        (break-even) -> τ = 2032; keeps 2031-2032. The event announced 2033
        raises the 2033/2034 caps to 60 — post-adoption clearing
        P = 2(70 - 60) = 20 < 90, so segment 2's OWN loop would never adopt
        (a re-solve from an empty state keeps H2-DRI masked and clears the
        BASE demand at 2(100 - 60) = 80). The carried adoption is a FLOOR:
        H2-DRI stays available, 2033/2034 clear at the hand value 20.

        ASCII: seg1: 80/100/... tau=2032 | event@2033: S->60
               seg2 with carrier   : P = 2*(70-60) = 20, H2-DRI active
               seg2 without carrier: P = 2*(100-60) = 80, H2-DRI masked
    """
    events = [
        {
            "announced": "2033",
            "year_overrides": {"2033": {"total_cap": 60.0}, "2034": {"total_cap": 60.0}},
        }
    ]
    config = _economy_config(
        "v7",
        theta=90.0,
        trigger_mode="break_even",
        supplies=(("2031", 60.0), ("2032", 50.0), ("2033", 50.0), ("2034", 50.0)),
        policy_events=events,
    )
    summary, participants = run_simulation_from_config(config)
    rows = _rows(summary)

    # Adoption dated in segment 1 and PERSISTING through segment 2's rows.
    expected = [{"adoption_year": "2032", "participant": "Steel", "technology": "H2-DRI"}]
    assert json.loads(str(rows["2032"]["Investment Adoptions"])) == expected
    assert json.loads(str(rows["2033"]["Investment Adoptions"])) == expected
    assert json.loads(str(rows["2034"]["Investment Adoptions"])) == expected

    # Monotone across segments: each row's adoption set contains the previous.
    previous: set[tuple[str, str, str]] = set()
    for year in ("2031", "2032", "2033", "2034"):
        current = {
            (e["participant"], e["technology"], e["adoption_year"])
            for e in json.loads(str(rows[year]["Investment Adoptions"]))
        }
        assert previous <= current, f"adoption set shrank entering {year}"
        previous = current

    # The carried floor kept the option AVAILABLE although the post-event
    # path (20) sits far below the trigger (90): hand price 2(70-60) = 20,
    # not the option-masked 2(100-60) = 80.
    for year in ("2033", "2034"):
        np.testing.assert_allclose(
            float(rows[year]["Equilibrium Carbon Price"]), 20.0, rtol=0, atol=1e-6
        )
    steel = participants[participants["Participant"] == "Steel"]
    chosen = {str(r["Year"]): str(r["Chosen Technology"]) for _, r in steel.iterrows()}
    assert chosen["2031"] == "Base Technology"
    for year in ("2032", "2033", "2034"):
        assert chosen[year] == "H2-DRI"
