"""Plugin-door pins: trigger normalization, the sanctioned writer, the carrier.

Covers the three door objects of ``features/endogenous_investment/plugin.py``
(spec D3.2/D3.4/D6): config sub-dict validation (XOR break-even forms,
required payout_yield, unknown keys loud), ``attach_adoption_specs`` as the
only writer of ``MarketParticipant.adoption_specs`` (name-consistency
validation lives here; scenario-level flag guards arrive with the builder in
EI-6), and the ``ADOPTION_CARRIER`` splice declaration.
"""

from __future__ import annotations

from typing import Any

import pytest

from pe.core.participant.models import MarketParticipant, TechnologyOption
from pe.core.protocols import AdoptionSpec, SpliceCarrier
from pe.features.endogenous_investment.plugin import (
    ADOPTION_CARRIER,
    attach_adoption_specs,
    normalize_investment_trigger,
)


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    return normalize_investment_trigger(raw, "H2-DRI", "Steel")


def _participant() -> MarketParticipant:
    return MarketParticipant(
        name="Steel",
        initial_emissions=100.0,
        marginal_abatement_cost=10.0,
        free_allocation_ratio=0.0,
        penalty_price=100.0,
        technology_options=[
            TechnologyOption(
                name="H2-DRI",
                initial_emissions=60.0,
                free_allocation_ratio=0.0,
                penalty_price=0.0,
                marginal_abatement_cost=5.0,
                max_activity_share=0.5,
            )
        ],
    )


def _spec(**overrides: Any) -> AdoptionSpec:
    kwargs: dict[str, Any] = {
        "participant_name": "Steel",
        "technology_name": "H2-DRI",
        "break_even": 80.0,
        "payout_yield": 0.03,
    }
    kwargs.update(overrides)
    return AdoptionSpec(**kwargs)


# ── normalize_investment_trigger ─────────────────────────────────────────────


def test_scalar_form_normalizes_with_spec_defaults() -> None:
    result = _normalize({"break_even_price": 80, "payout_yield": 0.03})
    assert result == {
        "participant_name": "Steel",
        "technology_name": "H2-DRI",
        "break_even": 80.0,
        "payout_yield": 0.03,
        "sigma": 0.0,
        "credibility": 0.0,
        "discount_rate": None,
        "trigger_mode": "dixit_pindyck",
        "trigger_multiple_override": None,
        "build_lag_years": 0,
    }
    AdoptionSpec(**result)  # valid by construction


def test_mapping_form_coerces_year_labels_to_str() -> None:
    result = _normalize({"break_even_prices": {2030: 100, "2031": 90.0}, "payout_yield": 0.03})
    assert result["break_even"] == {"2030": 100.0, "2031": 90.0}


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        ({"payout_yield": 0.03}, "exactly ONE"),
        (
            {
                "break_even_price": 80,
                "break_even_prices": {"2030": 90},
                "payout_yield": 0.03,
            },
            "exactly ONE",
        ),
        ({"break_even_prices": 90.0, "payout_yield": 0.03}, "break_even_prices"),
        ({"break_even_price": 80}, "payout_yield"),
        ({"break_even_price": 80, "payout_yield": 0.03, "payout_yeild": 1}, "payout_yeild"),
        (
            {"break_even_price": 80, "payout_yield": 0.03, "build_lag_years": 1.5},
            "build_lag_years",
        ),
        ({"break_even_price": 80, "payout_yield": 0.03, "sigma": -0.1}, "sigma"),
        (
            {"break_even_price": 80, "payout_yield": 0.03, "credibility": 1.5},
            "credibility",
        ),
    ],
)
def test_structural_and_bound_violations_raise(raw: dict[str, Any], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _normalize(raw)


def test_integral_float_lag_is_accepted() -> None:
    """JSON-borne 2.0 means 2 years; 2.5 (above) is rejected."""
    result = _normalize({"break_even_price": 80, "payout_yield": 0.03, "build_lag_years": 2.0})
    assert result["build_lag_years"] == 2


# ── attach_adoption_specs (the sanctioned writer) ────────────────────────────


def test_attach_stamps_and_returns_the_same_instance() -> None:
    participant = _participant()
    spec = _spec()
    returned = attach_adoption_specs(participant, (spec,))
    assert returned is participant
    assert participant.adoption_specs == (spec,)


def test_attach_empty_is_a_noop() -> None:
    participant = _participant()
    attach_adoption_specs(participant, ())
    assert participant.adoption_specs == ()


def test_attach_rejects_a_spec_for_another_participant() -> None:
    with pytest.raises(ValueError, match="must match"):
        attach_adoption_specs(_participant(), (_spec(participant_name="Cement"),))


def test_attach_rejects_an_unknown_technology_name() -> None:
    with pytest.raises(ValueError, match="Ghost"):
        attach_adoption_specs(_participant(), (_spec(technology_name="Ghost"),))


def test_double_attach_of_the_same_pair_is_rejected() -> None:
    participant = attach_adoption_specs(_participant(), (_spec(),))
    with pytest.raises(ValueError, match="duplicate"):
        attach_adoption_specs(participant, (_spec(break_even=99.0),))


# ── ADOPTION_CARRIER ─────────────────────────────────────────────────────────


def test_carrier_declaration_matches_the_plan_schema() -> None:
    assert isinstance(ADOPTION_CARRIER, SpliceCarrier)
    assert ADOPTION_CARRIER.column == "Investment Adoptions"
    assert ADOPTION_CARRIER.config_field == "investment_initial_adoptions"
    assert ADOPTION_CARRIER.carry_if({"investment_feedback_enabled": True}) is True
    assert ADOPTION_CARRIER.carry_if({"investment_feedback_enabled": False}) is False
    assert ADOPTION_CARRIER.carry_if({}) is False
