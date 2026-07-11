"""InvestmentRule anchors: crossing dating, one-flip tie-break, monotonicity.

Pins the spec D1.4/D2 behaviour of the ``PathFeedback`` implementation
(``docs/invest-feedback-spec.md``): trigger evaluation is DELEGATED to
``core.investment`` (multiples asserted against ``trigger_multiple``/
``credible_floor_multiple``, never re-derived); at most one flip per call
with the earliest-year → largest-exceedance → declared-order tie-break;
existing state never shrinks or re-dates; the event records the DECISION
year (lag applies at vintaging, spec D2.3).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from pe.core.investment import credible_floor_multiple, trigger_multiple
from pe.core.protocols import (
    AdoptionEvent,
    AdoptionSpec,
    PathFeedback,
    make_adoption_state,
)
from pe.features.endogenous_investment.rule import InvestmentRule

R, Y = 0.055, 0.03  # scenario discount rate r, payout yield y (paper values)
RY = R / Y  # certainty-limit multiple r/y = 11/6


def _spec(participant: str = "Steel", technology: str = "H2-DRI", **overrides: Any) -> AdoptionSpec:
    kwargs: dict[str, Any] = {
        "participant_name": participant,
        "technology_name": technology,
        "break_even": 48.0,
        "payout_yield": Y,
    }
    kwargs.update(overrides)
    return AdoptionSpec(**kwargs)


def _rule(
    *specs: AdoptionSpec, declared_order: dict[tuple[str, str], int] | None = None
) -> InvestmentRule:
    return InvestmentRule(tuple(specs), scenario_discount_rate=R, declared_order=declared_order)


def _pairs(state: tuple[AdoptionEvent, ...]) -> set[tuple[str, str, str]]:
    return {(e.participant_name, e.technology_name, e.adoption_year) for e in state}


# ── Crossing detection and trigger modes ─────────────────────────────────────


def test_break_even_mode_dates_first_crossing() -> None:
    """trigger_mode='break_even' pins M = 1: adoption at the first P >= θ."""
    rule = _rule(_spec(trigger_mode="break_even", break_even=90.0))
    path = {"2030": 80.0, "2031": 90.0, "2032": 100.0}
    proposal, metrics = rule.propose(path, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2031")}
    assert metrics["candidates"] == 1.0
    assert metrics["flipped"] == 1.0
    np.testing.assert_allclose(metrics["flip_exceedance"], 1.0, rtol=1e-12)


def test_dixit_pindyck_certainty_multiple_gates_crossing() -> None:
    """σ = 0 gives M = r/y (NOT 1): θ = 48 → P* = 88; 80 < 88 <= 90."""
    rule = _rule(_spec())  # sigma 0, r -> scenario, θ = 48
    np.testing.assert_allclose(rule.multiples[("Steel", "H2-DRI")], RY, rtol=1e-12)
    path = {"2030": 80.0, "2031": 90.0}
    proposal, _ = rule.propose(path, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2031")}
    # Below the trigger everywhere (87.9 < 88): no flip at break-even alone.
    proposal, metrics = rule.propose({"2030": 87.9}, (), [])
    assert proposal == ()
    assert metrics["flipped"] == 0.0


def test_override_wins_over_sigma() -> None:
    """trigger_multiple_override pins M even when σ would say wait longer."""
    spec = _spec(sigma=0.48, trigger_multiple_override=1.0, break_even=90.0)
    rule = _rule(spec)
    assert rule.multiples[("Steel", "H2-DRI")] == 1.0  # not ≈ 6.4
    proposal, _ = rule.propose({"2030": 90.0}, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2030")}


def test_override_wins_over_break_even_mode() -> None:
    """Precedence is override > mode: break_even mode with override = 2."""
    spec = _spec(trigger_mode="break_even", trigger_multiple_override=2.0, break_even=50.0)
    rule = _rule(spec)
    proposal, _ = rule.propose({"2030": 60.0}, (), [])  # 60 < 2*50
    assert proposal == ()
    proposal, _ = rule.propose({"2030": 100.0}, (), [])  # 100 >= 2*50
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2030")}


def test_full_credibility_reduces_multiple_to_timing_wedge() -> None:
    """q = 1 with σ > 0: σ_eff = 0, M = r/y == credible_floor_multiple."""
    rule = _rule(_spec(sigma=0.48, credibility=1.0))
    M = rule.multiples[("Steel", "H2-DRI")]
    np.testing.assert_allclose(M, credible_floor_multiple(R, Y), rtol=1e-12)
    np.testing.assert_allclose(M, trigger_multiple(0.0, R, Y), rtol=1e-12)
    # Behavioural: crossing exactly at (r/y)·θ = 88, not at σ = 0.48's ≈ 6.4·θ.
    proposal, _ = rule.propose({"2030": 88.0}, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2030")}


def test_partial_credibility_uses_the_documented_linear_mapping() -> None:
    """q = 0.5, σ = 0.48 → M == trigger_multiple(0.24, r, y) — called, not re-derived."""
    rule = _rule(_spec(sigma=0.48, credibility=0.5))
    np.testing.assert_allclose(
        rule.multiples[("Steel", "H2-DRI")], trigger_multiple(0.24, R, Y), rtol=1e-12
    )


def test_per_spec_discount_rate_overrides_scenario_rate() -> None:
    """spec.discount_rate replaces the scenario r in the multiple."""
    rule = _rule(_spec(sigma=0.2, discount_rate=0.08))
    np.testing.assert_allclose(
        rule.multiples[("Steel", "H2-DRI")], trigger_multiple(0.2, 0.08, Y), rtol=1e-12
    )


# ── Per-year thresholds (activation_year semantics reused) ───────────────────


def test_per_year_theta_mapping_dates_against_each_years_threshold() -> None:
    """Declining θ_t: 90 < 100 (no), 85 >= 80 (yes) → adoption 2031."""
    spec = _spec(trigger_mode="break_even", break_even={"2030": 100.0, "2031": 80.0})
    proposal, _ = _rule(spec).propose({"2030": 90.0, "2031": 85.0}, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2031")}


def test_missing_year_in_theta_mapping_raises() -> None:
    """core.investment.activation_year's missing-year ValueError propagates."""
    spec = _spec(trigger_mode="break_even", break_even={"2030": 100.0})
    with pytest.raises(ValueError, match="no threshold"):
        _rule(spec).propose({"2030": 90.0, "2031": 85.0}, (), [])


# ── One-flip selection and the D1.4 tie-break ────────────────────────────────


def test_one_flip_even_with_multiple_crossings() -> None:
    """Two candidates cross; exactly ONE event is added."""
    spec_a = _spec("A", "T", trigger_mode="break_even", break_even=50.0)
    spec_b = _spec("B", "T", trigger_mode="break_even", break_even=50.0)
    proposal, metrics = _rule(spec_a, spec_b).propose({"2030": 60.0}, (), [])
    assert len(proposal) == 1
    assert metrics["candidates"] == 2.0
    assert metrics["flipped"] == 1.0


def test_same_year_tiebreak_largest_relative_exceedance_wins() -> None:
    """Same crossing year: P/P* = 99/80 beats 99/90."""
    spec_a = _spec("A", "T", trigger_mode="break_even", break_even=90.0)
    spec_b = _spec("B", "T", trigger_mode="break_even", break_even=80.0)
    proposal, metrics = _rule(spec_a, spec_b).propose({"2030": 99.0}, (), [])
    assert _pairs(proposal) == {("B", "T", "2030")}
    np.testing.assert_allclose(metrics["flip_exceedance"], 99.0 / 80.0, rtol=1e-12)


def test_three_way_equal_exceedance_declared_order_wins() -> None:
    """Same year, same exceedance: the declared config order decides."""
    specs = tuple(
        _spec(name, "T", trigger_mode="break_even", break_even=50.0) for name in ("A", "B", "C")
    )
    declared = {("A", "T"): 2, ("B", "T"): 1, ("C", "T"): 0}
    rule = InvestmentRule(specs, scenario_discount_rate=R, declared_order=declared)
    proposal, _ = rule.propose({"2030": 60.0}, (), [])
    assert _pairs(proposal) == {("C", "T", "2030")}


def test_default_declared_order_is_the_specs_tuple_order() -> None:
    """No declared_order: the specs tuple order is the last tie-break leg."""
    specs = tuple(
        _spec(name, "T", trigger_mode="break_even", break_even=50.0) for name in ("B", "A")
    )
    proposal, _ = _rule(*specs).propose({"2030": 60.0}, (), [])
    assert _pairs(proposal) == {("B", "T", "2030")}


def test_earliest_crossing_year_wins_over_larger_exceedance() -> None:
    """2031 at 1.01x beats 2032 at ~3.6x — year is the first tie-break leg."""
    spec_a = _spec("A", "T", trigger_mode="break_even", break_even=100.0)
    spec_b = _spec("B", "T", trigger_mode="break_even", break_even=110.0)
    path = {"2030": 90.0, "2031": 101.0, "2032": 400.0}
    # First crossings: A at 2031 (101/100 = 1.01); B at 2032 (400/110 ≈ 3.6).
    proposal, _ = _rule(spec_a, spec_b).propose(path, (), [])
    assert _pairs(proposal) == {("A", "T", "2031")}


# ── Monotonicity and state handling ──────────────────────────────────────────


def test_existing_state_never_shrinks_or_redates() -> None:
    """Adopted pairs are skipped as candidates and survive verbatim."""
    spec_a = _spec("A", "T", trigger_mode="break_even", break_even=50.0)
    spec_b = _spec("B", "T", trigger_mode="break_even", break_even=50.0)
    prior = make_adoption_state(
        [AdoptionEvent(participant_name="A", technology_name="T", adoption_year="2030")]
    )
    proposal, metrics = _rule(spec_a, spec_b).propose({"2030": 40.0, "2031": 60.0}, prior, [])
    assert metrics["candidates"] == 1.0  # A already adopted, only B evaluated
    assert _pairs(proposal) == {("A", "T", "2030"), ("B", "T", "2031")}
    assert set(prior).issubset(set(proposal))


def test_no_crossing_returns_the_same_state_object() -> None:
    """Converged case: proposal IS the input state (value AND identity)."""
    rule = _rule(_spec(trigger_mode="break_even", break_even=1000.0))
    state = make_adoption_state(
        [AdoptionEvent(participant_name="X", technology_name="Z", adoption_year="2029")]
    )
    proposal, metrics = rule.propose({"2030": 90.0}, state, [])
    assert proposal is state
    assert metrics == {"candidates": 0.0, "flipped": 0.0, "flip_exceedance": 0.0}


def test_lag_records_the_decision_year_not_the_effective_year() -> None:
    """build_lag_years = 2, crossing 2031 → event says 2031 (τ, not τ+L)."""
    spec = _spec(trigger_mode="break_even", break_even=90.0, build_lag_years=2)
    proposal, _ = _rule(spec).propose({"2030": 80.0, "2031": 95.0, "2032": 99.0}, (), [])
    assert _pairs(proposal) == {("Steel", "H2-DRI", "2031")}


# ── Protocol conformance, delegation, constructor validation ────────────────


def test_rule_satisfies_the_path_feedback_protocol() -> None:
    assert isinstance(_rule(_spec()), PathFeedback)


def test_apply_neutral_case_is_identity() -> None:
    """No specs, no state: apply returns the SAME list object (vintage pact)."""
    rule = InvestmentRule((), scenario_discount_rate=R)
    markets: list[Any] = []
    assert rule.apply(markets, ()) is markets


def test_duplicate_spec_pairs_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate spec"):
        _rule(_spec(), _spec(break_even=99.0))


def test_declared_order_must_cover_every_pair() -> None:
    with pytest.raises(ValueError, match="missing pair"):
        _rule(_spec("A", "T"), _spec("B", "T"), declared_order={("A", "T"): 0})


def test_declared_order_ranks_must_be_unique() -> None:
    with pytest.raises(ValueError, match="unique"):
        _rule(_spec("A", "T"), _spec("B", "T"), declared_order={("A", "T"): 0, ("B", "T"): 0})


def test_bad_discount_rate_fails_loudly_at_construction() -> None:
    """r <= 0 propagates from core.investment with the spec named."""
    with pytest.raises(ValueError, match="Steel"):
        InvestmentRule((_spec(),), scenario_discount_rate=0.0)
