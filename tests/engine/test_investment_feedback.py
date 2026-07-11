"""EI-5 gate: the endogenous-investment outer loop, dispatch guard, columns.

Covers, against hand-solvable anchors (``docs/invest-feedback-spec.md``):

* V8 synthetic termination — a deterministic adoption-count → price map with
  adversarial triggers: convergence in exactly N + 1 iterations, ONE flip
  per iteration in the declared tie-break order, ``converged = 1.0``.
* Host-enforced monotone one-flip invariants (spec D1.4) — a malicious
  ``PathFeedback`` that drops, re-dates, or double-flips raises loudly.
* The missed-adoption ex-post check (spec D1.1) — a rule that lies about
  convergence cannot certify itself: the INDEPENDENT reference rule catches
  the crossing on the final path.
* Dispatch-guard NEUTRALITY (merge-critical) — half-configured scenarios
  raise (flag without specs; specs without flag); fully unconfigured
  scenarios solve through the byte-identical legacy branch with no
  investment columns.
* End-to-end smokes (competitive and banking) — a 3-year linear-MAC economy
  whose masked path is analytic (P_t = c·(E − S_t) per year under
  competitive clearing), one flagged option with θ between the year-1 and
  year-2 prices, lag 0 → adoption year 2, capacity visibly active in years
  2–3, and the four summary columns stamped at the TAIL with correct
  values.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pe.config_io import build_markets_from_config
from pe.core.costs import linear_abatement_factory
from pe.core.market.model import CarbonMarket
from pe.core.participant.models import MarketParticipant, TechnologyOption
from pe.core.protocols import (
    AdoptionEvent,
    AdoptionSpec,
    AdoptionState,
    make_adoption_state,
    serialize_adoption_state,
)
from pe.engine.dispatch import run_simulation
from pe.engine.feedback import solve_with_investment_feedback
from pe.features.endogenous_investment.plugin import attach_adoption_specs
from pe.features.endogenous_investment.rule import InvestmentRule

R = 0.055  # scenario discount rate r [1/yr]
Y = 0.03  # payout yield y [1/yr]
FLAG = "T"  # flagged technology option name (synthetic tests)

_INVESTMENT_COLUMNS = [
    "Investment Adoptions",
    "Investment Newly Effective",
    "Investment Feedback Iterations",
    "Investment Converged",
]


# ── Synthetic building blocks ────────────────────────────────────────────────


def _flag_option(name: str = FLAG) -> TechnologyOption:
    return TechnologyOption(
        name=name,
        initial_emissions=40.0,
        free_allocation_ratio=0.0,
        penalty_price=0.0,
        marginal_abatement_cost=5.0,
        max_activity_share=0.5,
    )


def _participant(name: str, *, flagged: bool = True) -> MarketParticipant:
    return MarketParticipant(
        name=name,
        initial_emissions=100.0,
        marginal_abatement_cost=10.0,
        free_allocation_ratio=0.0,
        penalty_price=100.0,
        technology_options=[_flag_option()] if flagged else None,
    )


def _one_year_markets(*participant_names: str, year: str = "2030") -> list[CarbonMarket]:
    return [
        CarbonMarket(
            participants=[_participant(name) for name in participant_names],
            total_cap=400.0,
            auction_offered=100.0,
            scenario_name="synthetic",
            year=year,
        )
    ]


def _break_even_spec(participant: str, theta: float) -> AdoptionSpec:
    """A trigger_mode='break_even' spec (M = 1): crossing at P >= theta exactly."""
    return AdoptionSpec(
        participant_name=participant,
        technology_name=FLAG,
        break_even=theta,
        payout_yield=Y,
        trigger_mode="break_even",
    )


def _pinned_price_solver(price: float) -> Callable[[list[CarbonMarket]], list[dict[str, Any]]]:
    def solve(markets: list[CarbonMarket]) -> list[dict[str, Any]]:
        return [{"market": m, "equilibrium": {"price": float(price)}} for m in markets]

    return solve


class _StubRule:
    """A ``PathFeedback`` stub with an injectable ``propose`` map (apply = identity)."""

    def __init__(self, propose_fn: Callable[[AdoptionState], AdoptionState]) -> None:
        self._propose_fn = propose_fn

    def apply(
        self, ordered_markets: list[CarbonMarket], state: AdoptionState
    ) -> list[CarbonMarket]:
        return ordered_markets

    def propose(
        self,
        price_path: Mapping[str, float],
        state: AdoptionState,
        markets: Sequence[CarbonMarket],
    ) -> tuple[AdoptionState, dict[str, float]]:
        return self._propose_fn(state), {}


# ── V8: synthetic 2-candidate termination (spec D1.4, exact count) ───────────


def test_v8_adversarial_two_candidates_terminate_in_n_plus_one() -> None:
    """N = 2 adversarial triggers: each adoption pushes the price down past the
    previous trigger, yet the loop converges in exactly N + 1 = 3 iterations
    with ONE flip per iteration in the declared (specs tuple) order.

    Analytic map: with k flagged options available, the stub delivers
    P(k) = 120 − 15·k, so the iterates are P = 120, 105, 90. Both triggers
    sit at θ = 100 (break-even mode, M = 1): iterate 0 crosses both with
    EQUAL relative exceedance 1.2 → the declared-order leg flips A first;
    iterate 1 (P = 105) still crosses B (1.05) → flips B; iterate 2
    (P = 90) crosses nothing → converged. Both adopted pairs end BELOW
    their trigger ex post — the spec D1.1 asymmetry, logged at INFO.
    """
    markets = _one_year_markets("A", "B")
    specs = (_break_even_spec("A", 100.0), _break_even_spec("B", 100.0))

    availability_log: list[list[str]] = []
    prices_log: list[float] = []

    def stub_solver(solved_markets: list[CarbonMarket]) -> list[dict[str, Any]]:
        available = sorted(
            p.name
            for p in solved_markets[-1].participants
            if any(o.name == FLAG for o in (p.technology_options or []))
        )
        availability_log.append(available)
        price = 120.0 - 15.0 * len(available)
        prices_log.append(price)
        return [{"market": m, "equilibrium": {"price": price}} for m in solved_markets]

    path = solve_with_investment_feedback(
        markets,
        stub_solver,
        lambda: InvestmentRule(specs, R),
        specs,
        scenario_discount_rate=R,
    )

    # One flip per iteration, declared order (A before B on the exceedance tie).
    assert availability_log == [[], ["A"], ["A", "B"]]
    np.testing.assert_allclose(prices_log, [120.0, 105.0, 90.0], rtol=1e-12)

    item = path[0]
    np.testing.assert_allclose(item["investment_feedback_iterations"], 3.0, rtol=0, atol=0)
    np.testing.assert_allclose(item["investment_converged"], 1.0, rtol=0, atol=0)
    np.testing.assert_allclose(item["investment_newly_effective"], 2.0, rtol=0, atol=0)
    expected_state = make_adoption_state(
        [
            AdoptionEvent(participant_name="A", technology_name=FLAG, adoption_year="2030"),
            AdoptionEvent(participant_name="B", technology_name=FLAG, adoption_year="2030"),
        ]
    )
    assert item["investment_adoptions"] == serialize_adoption_state(expected_state)


def test_v8_adopted_below_trigger_is_logged_info_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The final V8 path (P = 90 < θ = 100) leaves both adopted pairs below
    trigger: permitted ex post, logged at INFO with the margin (spec D1.1)."""
    markets = _one_year_markets("A", "B")
    specs = (_break_even_spec("A", 100.0), _break_even_spec("B", 100.0))

    def stub_solver(solved_markets: list[CarbonMarket]) -> list[dict[str, Any]]:
        k = sum(
            1
            for p in solved_markets[-1].participants
            if any(o.name == FLAG for o in (p.technology_options or []))
        )
        return [{"market": m, "equilibrium": {"price": 120.0 - 15.0 * k}} for m in solved_markets]

    with caplog.at_level(logging.INFO, logger="pe.engine.feedback"):
        solve_with_investment_feedback(
            markets,
            stub_solver,
            lambda: InvestmentRule(specs, R),
            specs,
            scenario_discount_rate=R,
        )
    below = [rec for rec in caplog.records if "below its trigger" in rec.getMessage()]
    assert len(below) == 2  # both adopted pairs, each with its margin
    assert all(rec.levelno == logging.INFO for rec in below)


# ── Host-enforced monotone one-flip invariants (spec D1.4) ───────────────────


def _carried_market() -> list[CarbonMarket]:
    markets = _one_year_markets("A")
    markets[0].investment_initial_adoptions = [
        {"participant": "A", "technology": FLAG, "adoption_year": "2029"}
    ]
    return markets


def test_host_rejects_a_proposal_that_drops_an_event() -> None:
    with pytest.raises(ValueError, match="DROPPED"):
        solve_with_investment_feedback(
            _carried_market(),
            _pinned_price_solver(50.0),
            lambda: _StubRule(lambda state: ()),
            (),
            scenario_discount_rate=R,
        )


def test_host_rejects_a_proposal_that_redates_an_event() -> None:
    redated = make_adoption_state(
        [AdoptionEvent(participant_name="A", technology_name=FLAG, adoption_year="2031")]
    )
    with pytest.raises(ValueError, match="RE-DATED"):
        solve_with_investment_feedback(
            _carried_market(),
            _pinned_price_solver(50.0),
            lambda: _StubRule(lambda state: redated),
            (),
            scenario_discount_rate=R,
        )


def test_host_rejects_more_than_one_flip_per_iteration() -> None:
    double = make_adoption_state(
        [
            AdoptionEvent(participant_name="A", technology_name=FLAG, adoption_year="2030"),
            AdoptionEvent(participant_name="B", technology_name=FLAG, adoption_year="2030"),
        ]
    )
    with pytest.raises(ValueError, match="ONE flip"):
        solve_with_investment_feedback(
            _one_year_markets("A", "B"),
            _pinned_price_solver(50.0),
            lambda: _StubRule(lambda state: double),
            (),
            scenario_discount_rate=R,
        )


def test_carried_adoptions_seed_state_zero_and_survive() -> None:
    """``investment_initial_adoptions`` (splice landing field / user
    pre-commit) parses into state_0; an already-adopted pair is not a
    candidate, so a below-trigger path converges in ONE iteration with the
    carried event intact in every row (floors, spec D3.4)."""
    markets = _carried_market()
    specs = (_break_even_spec("A", 100.0),)
    path = solve_with_investment_feedback(
        markets,
        _pinned_price_solver(50.0),  # below theta: nothing new crosses
        lambda: InvestmentRule(specs, R),
        specs,
        scenario_discount_rate=R,
    )
    item = path[0]
    np.testing.assert_allclose(item["investment_feedback_iterations"], 1.0, rtol=0, atol=0)
    np.testing.assert_allclose(item["investment_converged"], 1.0, rtol=0, atol=0)
    carried = make_adoption_state(
        [AdoptionEvent(participant_name="A", technology_name=FLAG, adoption_year="2029")]
    )
    assert item["investment_adoptions"] == serialize_adoption_state(carried)
    np.testing.assert_allclose(item["investment_newly_effective"], 0.0, rtol=0, atol=0)


# ── Missed-adoption ex-post check (spec D1.1) ────────────────────────────────


def test_missed_adoption_expost_check_fires_on_a_lying_rule() -> None:
    """A rule claiming convergence while the delivered path crosses a flagged
    trigger is caught by the INDEPENDENT reference evaluation — loudly."""
    specs = (_break_even_spec("A", 100.0),)
    with pytest.raises(ValueError, match="missed adoption"):
        solve_with_investment_feedback(
            _one_year_markets("A"),
            _pinned_price_solver(120.0),  # crosses theta = 100
            lambda: _StubRule(lambda state: state),  # lies: "converged"
            specs,
            scenario_discount_rate=R,
        )


# ── Safety rail: cap exhaustion = WARNING + last iterate, never silent ───────


def test_max_iterations_exhaustion_warns_and_returns_last_iterate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A (contract-violating) rule that flips forever hits the rail: WARNING
    with the banking-host wording, last iterate returned, converged = 0.0.
    The stamped state is the one the returned path was SOLVED under."""

    def always_flip(state: AdoptionState) -> AdoptionState:
        event = AdoptionEvent(
            participant_name=f"P{len(state)}", technology_name=FLAG, adoption_year="2030"
        )
        return make_adoption_state([*state, event])

    with caplog.at_level(logging.WARNING, logger="pe.engine.feedback"):
        path = solve_with_investment_feedback(
            _one_year_markets("A"),
            _pinned_price_solver(50.0),
            lambda: _StubRule(always_flip),
            (),
            scenario_discount_rate=R,
            max_iterations=2,
        )
    assert any(
        "did not converge within 2 iterations; using the last iterate" in rec.getMessage()
        for rec in caplog.records
    )
    item = path[0]
    np.testing.assert_allclose(item["investment_converged"], 0.0, rtol=0, atol=0)
    np.testing.assert_allclose(item["investment_feedback_iterations"], 2.0, rtol=0, atol=0)
    # Iteration 2 solved under the state proposed by iteration 1 (one event).
    solved_under = make_adoption_state(
        [AdoptionEvent(participant_name="P0", technology_name=FLAG, adoption_year="2030")]
    )
    assert item["investment_adoptions"] == serialize_adoption_state(solved_under)


# ── Dispatch guard: neutrality and loud mismatches (spec D3.2/D6) ────────────


def _linear_config(name: str, approach: str) -> dict[str, Any]:
    """3-year, 1-participant linear-MAC economy: E = 100, MC(a) = 2a.

    Competitive clearing is analytic: demand E − P/2 = S_t gives
    P_t = 2 (E − S_t) → 80 / 100 / 120 for S = 60 / 50 / 40 [Mt].
    """
    years = []
    for year, supply in (("2031", 60.0), ("2032", 50.0), ("2033", 40.0)):
        years.append(
            {
                "year": year,
                "total_cap": supply,
                "auction_mode": "derive_from_cap",
                "banking_allowed": False,
                "borrowing_allowed": False,
                "expectation_rule": "next_year_baseline",
                "price_lower_bound": 0.0,
                "price_upper_bound": 100000.0,
                "participants": [
                    {
                        "name": "Steel",
                        "initial_emissions": 100.0,
                        "free_allocation_ratio": 0.0,
                        "penalty_price": 1000.0,
                        "abatement_type": "linear",
                        "max_abatement": 100.0,
                        "cost_slope": 2.0,
                    }
                ],
            }
        )
    return {
        "scenarios": [
            {
                "name": name,
                "model_approach": approach,
                "discount_rate": R,
                "years": years,
            }
        ]
    }


def _smoke_option() -> TechnologyOption:
    return TechnologyOption(
        name="H2-DRI",
        initial_emissions=40.0,
        free_allocation_ratio=0.0,
        penalty_price=1000.0,
        marginal_abatement_cost=linear_abatement_factory(max_abatement=40.0, cost_slope=2.0),
        max_activity_share=0.5,
    )


def _smoke_spec(theta: float) -> AdoptionSpec:
    return AdoptionSpec(
        participant_name="Steel",
        technology_name="H2-DRI",
        break_even=theta,
        payout_yield=Y,
        trigger_mode="break_even",
    )


def _flagged_markets(approach: str, theta: float, name: str) -> list[CarbonMarket]:
    """Config-built markets, manually flagged (the EI-6 config door is not
    built yet): option added to every year, spec attached on the first-year
    participant, master gate set — exactly what the builder will produce."""
    markets = build_markets_from_config(_linear_config(name, approach))
    ordered = sorted(markets, key=lambda m: float(str(m.year)))
    for market in ordered:
        market.investment_feedback_enabled = True
        steel = market.participants[0]
        steel.technology_options = [_smoke_option()]
    attach_adoption_specs(ordered[0].participants[0], (_smoke_spec(theta),))
    return ordered


def test_guard_flag_without_specs_raises() -> None:
    markets = build_markets_from_config(_linear_config("guard-flag", "competitive"))
    for market in markets:
        market.investment_feedback_enabled = True
    with pytest.raises(ValueError, match="no participant carries an adoption spec"):
        run_simulation(markets)


def test_guard_specs_without_flag_raises() -> None:
    markets = build_markets_from_config(_linear_config("guard-specs", "competitive"))
    ordered = sorted(markets, key=lambda m: float(str(m.year)))
    steel = ordered[0].participants[0]
    steel.technology_options = [_smoke_option()]
    attach_adoption_specs(steel, (_smoke_spec(90.0),))
    with pytest.raises(ValueError, match="investment_feedback_enabled is not set"):
        run_simulation(markets)


def test_guard_approach_all_with_investment_raises() -> None:
    markets = _flagged_markets("all", 90.0, "guard-all")
    with pytest.raises(ValueError, match="model_approach='all'"):
        run_simulation(markets)


def test_unconfigured_scenario_solves_the_untouched_branch() -> None:
    """No flag, no specs: the guard is False and the code path IS the legacy
    one — deterministic frames, and NO investment columns anywhere."""
    config = _linear_config("neutral", "competitive")
    summary_1, participants_1 = run_simulation(build_markets_from_config(config))
    summary_2, participants_2 = run_simulation(build_markets_from_config(config))
    assert_frame_equal(summary_1, summary_2)
    assert_frame_equal(participants_1, participants_2)
    assert not set(_INVESTMENT_COLUMNS) & set(summary_1.columns)
    # Analytic anchor for the linear economy: P_t = 2 (E − S_t).
    np.testing.assert_allclose(
        summary_1["Equilibrium Carbon Price"].to_numpy(),
        [80.0, 100.0, 120.0],
        rtol=1e-6,
    )


# ── End-to-end smokes: dispatch guard → feedback → summary columns ───────────


def _rows_by_year(summary: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["Year"]): row for _, row in summary.iterrows()}


def test_end_to_end_competitive_smoke() -> None:
    """3-year competitive: θ = 90 sits between P(2031) = 80 and P(2032) = 100
    on the masked (iterate-0) path → adoption year 2032, lag 0; the option
    is visibly active in 2032–2033 (prices fall, mix includes it); year 2031
    is untouched; converged in 2 iterations; columns stamped at the tail."""
    summary_off, participants_off = run_simulation(
        build_markets_from_config(_linear_config("smoke-off", "competitive"))
    )
    summary_on, participants_on = run_simulation(_flagged_markets("competitive", 90.0, "smoke-on"))

    # Tail placement: the four investment columns are the LAST summary columns.
    assert list(summary_on.columns[-4:]) == _INVESTMENT_COLUMNS

    on = _rows_by_year(summary_on)
    off = _rows_by_year(summary_off)

    # Iterate-0 (masked) path is the analytic OFF path: 80 / 100 / 120 —
    # crossing at 2032. The event is stamped from 2032 onward.
    event = AdoptionEvent(participant_name="Steel", technology_name="H2-DRI", adoption_year="2032")
    expected_serialized = serialize_adoption_state(make_adoption_state([event]))
    assert on["2031"]["Investment Adoptions"] == "[]"
    assert on["2032"]["Investment Adoptions"] == expected_serialized
    assert on["2033"]["Investment Adoptions"] == expected_serialized
    np.testing.assert_allclose(
        [on[y]["Investment Newly Effective"] for y in ("2031", "2032", "2033")],
        [0.0, 1.0, 0.0],
        rtol=0,
        atol=0,
    )
    for year in ("2031", "2032", "2033"):
        np.testing.assert_allclose(on[year]["Investment Feedback Iterations"], 2.0, rtol=0, atol=0)
        np.testing.assert_allclose(on[year]["Investment Converged"], 1.0, rtol=0, atol=0)

    # Pre-adoption year: bit-identical price to the option-deleted economy
    # (the masked participant IS the option-deleted participant, anchor V3).
    np.testing.assert_allclose(
        float(on["2031"]["Equilibrium Carbon Price"]),
        float(off["2031"]["Equilibrium Carbon Price"]),
        rtol=1e-12,
    )
    # Post-adoption years: the entrant capacity visibly lowers the price.
    assert float(on["2032"]["Equilibrium Carbon Price"]) < float(
        off["2032"]["Equilibrium Carbon Price"]
    )
    assert float(on["2033"]["Equilibrium Carbon Price"]) < float(
        off["2033"]["Equilibrium Carbon Price"]
    )
    # And the mix actually contains the adopted technology in 2032–2033 only.
    steel_on = participants_on[participants_on["Participant"] == "Steel"]
    mix_by_year = {
        str(row["Year"]): f"{row['Chosen Technology']} | {row['Technology Mix']}"
        for _, row in steel_on.iterrows()
    }
    assert "H2-DRI" not in mix_by_year["2031"]
    assert "H2-DRI" in mix_by_year["2032"]
    assert "H2-DRI" in mix_by_year["2033"]


def test_end_to_end_banking_smoke() -> None:
    """The loop wraps solve_banking_path (spec D1.3: full inner re-solve per
    adoption state). θ = 97 crosses first at 2032 on the masked path in BOTH
    banking regimes (window ≈ 94.7/99.9/105.4; static 80/100/120), so the
    adoption year is regime-robust; adoption lowers the post-adoption price
    and the banking + investment columns coexist (investment at the tail)."""
    summary_off, _ = run_simulation(
        build_markets_from_config(_linear_config("bank-off", "banking"))
    )
    summary_on, _ = run_simulation(_flagged_markets("banking", 97.0, "bank-on"))

    assert "Banking Aggregate Bank" in summary_on.columns  # inner solve ran whole
    assert list(summary_on.columns[-4:]) == _INVESTMENT_COLUMNS

    on = _rows_by_year(summary_on)
    off = _rows_by_year(summary_off)

    adoptions = json.loads(str(on["2033"]["Investment Adoptions"]))
    assert adoptions == [{"adoption_year": "2032", "participant": "Steel", "technology": "H2-DRI"}]
    np.testing.assert_allclose(on["2033"]["Investment Feedback Iterations"], 2.0, rtol=0, atol=0)
    np.testing.assert_allclose(on["2033"]["Investment Converged"], 1.0, rtol=0, atol=0)
    np.testing.assert_allclose(
        [on[y]["Investment Newly Effective"] for y in ("2031", "2032", "2033")],
        [0.0, 1.0, 0.0],
        rtol=0,
        atol=0,
    )
    # Post-adoption capacity lowers the delivered price where it is active.
    assert float(on["2032"]["Equilibrium Carbon Price"]) < float(
        off["2032"]["Equilibrium Carbon Price"]
    )
