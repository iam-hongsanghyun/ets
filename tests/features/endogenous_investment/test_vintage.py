"""Vintaging pins: masking, τ+L boundary, identity guarantee, input purity.

Pins spec D2.5/D3 (``docs/invest-feedback-spec.md``): a flagged option is
ABSENT from the participant's choice set before its adoption becomes
effective (and in every year when never adopted — the "flagged option
DELETED" equivalence, anchor V3), PRESENT from τ + L onward at its
configured cap; the inputs are never mutated; the neutral case is
is-identity (the off-by-default proof chain's vintage link).
"""

from __future__ import annotations

from typing import Any

import pytest

from pe.core.market.model import CarbonMarket
from pe.core.participant.models import MarketParticipant, TechnologyOption
from pe.core.protocols import AdoptionEvent, AdoptionSpec, make_adoption_state
from pe.features.endogenous_investment.vintage import apply_adoption_state

FLAGGED = "H2-DRI"
OTHER = "Efficiency"


def _option(name: str) -> TechnologyOption:
    return TechnologyOption(
        name=name,
        initial_emissions=60.0,
        free_allocation_ratio=0.0,
        penalty_price=0.0,
        marginal_abatement_cost=5.0,
        max_activity_share=0.5,
    )


def _participant(name: str, option_names: tuple[str, ...]) -> MarketParticipant:
    return MarketParticipant(
        name=name,
        initial_emissions=100.0,
        marginal_abatement_cost=10.0,
        free_allocation_ratio=0.0,
        penalty_price=100.0,
        technology_options=[_option(n) for n in option_names],
    )


def _markets(years: tuple[str, ...]) -> list[CarbonMarket]:
    """Fresh participant instances per year, like the config builder."""
    return [
        CarbonMarket(
            participants=[
                _participant("Steel", (FLAGGED, OTHER)),
                _participant("Cement", (OTHER,)),
            ],
            total_cap=100.0,
            auction_offered=50.0,
            scenario_name="vintage-test",
            year=year,
        )
        for year in years
    ]


def _spec(lag: int = 0) -> AdoptionSpec:
    return AdoptionSpec(
        participant_name="Steel",
        technology_name=FLAGGED,
        break_even=80.0,
        payout_yield=0.03,
        build_lag_years=lag,
    )


def _event(year: str) -> AdoptionEvent:
    return AdoptionEvent(participant_name="Steel", technology_name=FLAGGED, adoption_year=year)


def _steel_options(market: CarbonMarket) -> list[str]:
    steel = next(p for p in market.participants if p.name == "Steel")
    return [option.name for option in steel.technology_options or []]


def _snapshot(markets: list[CarbonMarket]) -> list[list[tuple[str, list[str]]]]:
    return [
        [(p.name, [o.name for o in p.technology_options or []]) for p in m.participants]
        for m in markets
    ]


# ── Identity guarantee (off-by-default proof chain) ──────────────────────────


def test_empty_specs_and_state_returns_the_same_list_object() -> None:
    markets = _markets(("2030", "2031"))
    assert apply_adoption_state(markets, (), ()) is markets


# ── Masking pin: flagged option absent pre-adoption ──────────────────────────


def test_flagged_unadopted_is_masked_in_every_year() -> None:
    """No adoption: the flagged option is DELETED from the choice set (V3)."""
    markets = _markets(("2030", "2031", "2032"))
    result = apply_adoption_state(markets, (_spec(),), ())
    for market in result:
        assert _steel_options(market) == [OTHER]


def test_masking_boundary_lag_zero() -> None:
    """Adoption 2031, L = 0: masked 2030; present from 2031 (τ itself)."""
    markets = _markets(("2030", "2031", "2032"))
    state = make_adoption_state([_event("2031")])
    result = apply_adoption_state(markets, (_spec(lag=0),), state)
    assert _steel_options(result[0]) == [OTHER]
    assert _steel_options(result[1]) == [FLAGGED, OTHER]
    assert _steel_options(result[2]) == [FLAGGED, OTHER]


def test_masking_boundary_with_lag() -> None:
    """Adoption 2031, L = 2: masked 2030-2032; present from 2033 = τ + L."""
    markets = _markets(("2030", "2031", "2032", "2033", "2034"))
    state = make_adoption_state([_event("2031")])
    result = apply_adoption_state(markets, (_spec(lag=2),), state)
    for masked_year in (0, 1, 2):
        assert _steel_options(result[masked_year]) == [OTHER]
    for present_year in (3, 4):
        assert _steel_options(result[present_year]) == [FLAGGED, OTHER]


def test_post_effective_years_pass_by_identity() -> None:
    """Years with nothing masked reuse the input market object itself."""
    markets = _markets(("2030", "2031"))
    state = make_adoption_state([_event("2030")])
    result = apply_adoption_state(markets, (_spec(lag=0),), state)
    assert result[0] is markets[0]
    assert result[1] is markets[1]


# ── Purity: inputs never mutated, untouched objects shared ──────────────────


def test_input_markets_are_never_mutated() -> None:
    """Deep pre/post compare of the INPUT structure across a masking call."""
    markets = _markets(("2030", "2031"))
    before = _snapshot(markets)
    input_participants = [list(m.participants) for m in markets]
    input_option_lists = [[p.technology_options for p in m.participants] for m in markets]
    apply_adoption_state(markets, (_spec(),), ())
    assert _snapshot(markets) == before
    for market, participants, option_lists in zip(
        markets, input_participants, input_option_lists, strict=True
    ):
        assert market.participants == participants  # same objects, same order
        for participant, options in zip(market.participants, option_lists, strict=True):
            assert participant.technology_options is options  # list not rebuilt


def test_unflagged_participants_and_options_pass_by_identity() -> None:
    """Only the flagged participant is cloned; every other object is shared."""
    markets = _markets(("2030",))
    result = apply_adoption_state(markets, (_spec(),), ())
    market_in, market_out = markets[0], result[0]
    cement_in = next(p for p in market_in.participants if p.name == "Cement")
    cement_out = next(p for p in market_out.participants if p.name == "Cement")
    assert cement_out is cement_in
    steel_in = next(p for p in market_in.participants if p.name == "Steel")
    steel_out = next(p for p in market_out.participants if p.name == "Steel")
    assert steel_out is not steel_in
    # The surviving option is the SAME TechnologyOption object (no MAC copy).
    other_in = next(o for o in steel_in.technology_options or [] if o.name == OTHER)
    other_out = next(o for o in steel_out.technology_options or [] if o.name == OTHER)
    assert other_out is other_in


def test_present_flagged_option_is_the_original_object() -> None:
    """Post-adoption the flagged option re-enters BY IDENTITY (D4.5)."""
    markets = _markets(("2030",))
    state = make_adoption_state([_event("2030")])
    result = apply_adoption_state(markets, (_spec(lag=0),), state)
    steel_in = next(p for p in markets[0].participants if p.name == "Steel")
    steel_out = next(p for p in result[0].participants if p.name == "Steel")
    flagged_in = next(o for o in steel_in.technology_options or [] if o.name == FLAGGED)
    flagged_out = next(o for o in steel_out.technology_options or [] if o.name == FLAGGED)
    assert flagged_out is flagged_in
    assert flagged_out.max_activity_share == 0.5  # available at its cap, not forced


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_all_options_masked_mirrors_the_builder_none_convention() -> None:
    """A participant whose only option is flagged falls back to base tech."""
    market = CarbonMarket(
        participants=[_participant("Steel", (FLAGGED,))],
        total_cap=100.0,
        auction_offered=50.0,
        scenario_name="vintage-test",
        year="2030",
    )
    result = apply_adoption_state([market], (_spec(),), ())
    assert result[0].participants[0].technology_options is None


def test_missing_flagged_option_raises() -> None:
    """A spec naming an option the participant lacks is a loud error."""
    ghost = AdoptionSpec(
        participant_name="Steel",
        technology_name="Ghost",
        break_even=80.0,
        payout_yield=0.03,
    )
    with pytest.raises(ValueError, match="Ghost"):
        apply_adoption_state(_markets(("2030",)), (ghost,), ())


def test_adoption_event_without_a_spec_is_inert() -> None:
    """Carried adoptions into a segment with no flags change nothing."""
    markets = _markets(("2030", "2031"))
    state = make_adoption_state([_event("2030")])
    result = apply_adoption_state(markets, (), state)
    assert result is not markets  # not the neutral case...
    assert all(out is original for out, original in zip(result, markets, strict=True))


def test_nonnumeric_adoption_year_with_positive_lag_raises() -> None:
    """τ + L is undefined for a non-numeric year label when L > 0."""
    markets = _markets(("2030",))
    state = make_adoption_state([_event("phase-2")])
    with pytest.raises(ValueError, match="not numeric"):
        apply_adoption_state(markets, (_spec(lag=1),), state)


def test_cloned_participant_preserves_every_other_field(request: Any) -> None:
    """The masked clone differs ONLY in technology_options."""
    markets = _markets(("2030",))
    result = apply_adoption_state(markets, (_spec(),), ())
    steel_in = next(p for p in markets[0].participants if p.name == "Steel")
    steel_out = next(p for p in result[0].participants if p.name == "Steel")
    assert steel_out.initial_emissions == steel_in.initial_emissions
    assert steel_out.free_allocation_ratio == steel_in.free_allocation_ratio
    assert steel_out.penalty_price == steel_in.penalty_price
    assert steel_out.adoption_specs == steel_in.adoption_specs
    assert steel_out.demand_overlays == steel_in.demand_overlays
