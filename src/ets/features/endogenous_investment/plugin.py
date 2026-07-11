r"""endogenous_investment plugin door — trigger validation, spec attachment, carrier (T2).

Two-door feature (``docs/feature-modules-plan.md`` PLAN v2 §"Two-door
features"): this module is the ONLY thing ``config_io`` may import from
``ets.features.endogenous_investment`` (the door rule; the config-schema
wiring itself arrives in EI-6). The runtime lives in this feature's
``rule.py`` (``InvestmentRule``, the ``PathFeedback`` implementation) and
``vintage.py`` (adoption-state availability gating), wired exclusively by
the engine's outer feedback loop (EI-5). Imports ONLY ``ets.core.*`` and
stdlib.

Three door objects (``docs/invest-feedback-plan.md`` "Feature module"):

* ``normalize_investment_trigger`` — validates one technology option's
  ``investment_trigger`` config sub-dict into ``AdoptionSpec``-ready
  keyword arguments (spec D6 parameter table; presence of the sub-dict IS
  the flag).
* ``attach_adoption_specs`` — THE sanctioned writer of
  ``MarketParticipant.adoption_specs`` (the ``stamp_and_attach``
  precedent, ``features/elastic_baseline/plugin.py``). The scenario-level
  loud guards (flag true + zero specs; specs + flag false, spec D3.2)
  live at the builder level and arrive in EI-6; this function validates
  the participant-local consistency only.
* ``ADOPTION_CARRIER`` — the ``SpliceCarrier`` declaration for the
  policy-event segment host (spec D3.4). Appended LAST to the engine's
  ``SPLICE_CARRIERS`` literal in EI-5 (bank, reserve, adoptions), NOT by
  this order.

References:
    docs/invest-feedback-spec.md D2 (decision rule), D3.2 (sanctioned
    mutator), D3.4 (policy-event carrier), D6 (parameters).
    docs/invest-feedback-plan.md — "Feature module", "Config schema".
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ...core.protocols import AdoptionSpec, SpliceCarrier

if TYPE_CHECKING:
    from ...core.participant.models import MarketParticipant

__all__ = [
    "ADOPTION_CARRIER",
    "attach_adoption_specs",
    "normalize_investment_trigger",
]


# Config sub-dict keys the ``investment_trigger`` block may carry (plan
# "Config schema"; spec D6). ``break_even_price`` XOR ``break_even_prices``
# feeds ``AdoptionSpec.break_even``; everything else maps by name.
_ALLOWED_TRIGGER_KEYS: frozenset[str] = frozenset(
    {
        "break_even_price",
        "break_even_prices",
        "payout_yield",
        "sigma",
        "credibility",
        "discount_rate",
        "trigger_mode",
        "trigger_multiple_override",
        "build_lag_years",
    }
)


def normalize_investment_trigger(
    raw: Mapping[str, Any], technology_name: str, participant_name: str
) -> dict[str, Any]:
    """Validate an ``investment_trigger`` config sub-dict into spec kwargs.

    Structural validation of the config door (spec D6): exactly one of
    ``break_even_price`` (scalar) / ``break_even_prices`` ({year label:
    value}) — mapped onto ``AdoptionSpec.break_even``; ``payout_yield``
    REQUIRED (a defaulted y is an economic constant hiding in a fallback,
    spec D2.1); the optional fields take the spec's neutral defaults.
    Unknown keys raise loudly, naming them. The returned dict is then
    validated through ``AdoptionSpec`` itself, so every BOUND violation
    (sigma < 0, credibility outside [0, 1], ...) also fires here, at
    config time, with the field name and rule in the message.

    Args:
        raw: The ``investment_trigger`` sub-dict as parsed from config.
        technology_name: Name of the flagged technology option (for the
            spec and for error attribution).
        participant_name: Name of the owning participant (for the spec and
            for error attribution).

    Returns:
        ``AdoptionSpec``-ready keyword arguments (including
        ``participant_name`` and ``technology_name``) —
        ``AdoptionSpec(**result)`` is valid by construction.

    Raises:
        ValueError: Unknown keys; both or neither of ``break_even_price`` /
            ``break_even_prices``; a non-mapping ``break_even_prices``; a
            non-integral ``build_lag_years``; or any ``AdoptionSpec`` bound
            violation.
    """
    label = f"{participant_name}/{technology_name} investment_trigger"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label}: must be a mapping, got {type(raw).__name__}.")

    unknown = sorted(set(raw) - _ALLOWED_TRIGGER_KEYS)
    if unknown:
        raise ValueError(
            f"{label}: unknown key(s) {unknown}; allowed keys are {sorted(_ALLOWED_TRIGGER_KEYS)}."
        )

    has_scalar = "break_even_price" in raw
    has_mapping = "break_even_prices" in raw
    if has_scalar == has_mapping:
        raise ValueError(
            f"{label}: exactly ONE of break_even_price (scalar) or "
            "break_even_prices ({year: value}) is required "
            f"(got {'both' if has_scalar else 'neither'})."
        )
    break_even: float | dict[str, float]
    if has_scalar:
        break_even = float(raw["break_even_price"])
    else:
        prices = raw["break_even_prices"]
        if not isinstance(prices, Mapping):
            raise ValueError(
                f"{label}: break_even_prices must be a mapping of year label "
                f"-> price, got {type(prices).__name__}."
            )
        break_even = {str(year): float(value) for year, value in prices.items()}

    if "payout_yield" not in raw:
        raise ValueError(
            f"{label}: payout_yield is REQUIRED [1/yr] — r/y is the "
            "certainty-limit hurdle; it has no default (spec D2.1)."
        )

    lag_raw = raw.get("build_lag_years", 0)
    if isinstance(lag_raw, bool) or not (
        isinstance(lag_raw, int) or (isinstance(lag_raw, float) and lag_raw.is_integer())
    ):
        raise ValueError(
            f"{label}: build_lag_years must be an integer number of years, got {lag_raw!r}."
        )

    discount_rate = raw.get("discount_rate")
    override = raw.get("trigger_multiple_override")
    kwargs: dict[str, Any] = {
        "participant_name": participant_name,
        "technology_name": technology_name,
        "break_even": break_even,
        "payout_yield": float(raw["payout_yield"]),
        "sigma": float(raw.get("sigma", 0.0)),
        "credibility": float(raw.get("credibility", 0.0)),
        "discount_rate": None if discount_rate is None else float(discount_rate),
        "trigger_mode": str(raw.get("trigger_mode", "dixit_pindyck")),
        "trigger_multiple_override": None if override is None else float(override),
        "build_lag_years": int(lag_raw),
    }
    AdoptionSpec(**kwargs)  # bound validation fires HERE, at config time, loudly
    return kwargs


def attach_adoption_specs(
    participant: MarketParticipant, specs: tuple[AdoptionSpec, ...]
) -> MarketParticipant:
    """Attach adoption specs to a participant — the ONLY sanctioned writer.

    The ``stamp_and_attach`` precedent (``features/elastic_baseline/
    plugin.py``): plain in-place field assignment on the mutable
    participant dataclass, appending to any specs already attached, and
    returning the same instance for comprehension use. The scenario-level
    guards (feature flag true + zero specs anywhere = ValueError; specs
    present + flag false = ValueError, spec D3.2) live at the BUILDER
    level and arrive in EI-6 — this function validates only what the
    participant itself can know:

    * every spec names THIS participant (``spec.participant_name ==
      participant.name``);
    * every spec references one of the participant's actual
      ``technology_options`` by name (a flagged option must exist to be
      masked — spec D2.5);
    * the resulting tuple carries at most ONE spec per (participant,
      technology) pair (one irreversible tranche, spec D2.4; incremental
      adoption is multiple flagged OPTIONS, never repeated flags on one).

    Args:
        participant: The participant to stamp (mutated in place).
        specs: The specs to attach; ``()`` is a no-op.

    Returns:
        The same ``participant`` instance, stamped.

    Raises:
        ValueError: A spec names a different participant, references a
            technology option the participant does not have, or duplicates
            a (participant, technology) pair already attached.
    """
    if not specs:
        return participant
    option_names = {option.name for option in participant.technology_options or []}
    for spec in specs:
        if spec.participant_name != participant.name:
            raise ValueError(
                f"attach_adoption_specs: spec for participant "
                f"{spec.participant_name!r} attached to participant "
                f"{participant.name!r} — specs bind by name and must match."
            )
        if spec.technology_name not in option_names:
            raise ValueError(
                f"attach_adoption_specs: {participant.name!r} has no technology "
                f"option named {spec.technology_name!r} (available: "
                f"{sorted(option_names)}) — a flagged option must exist to be "
                "masked (spec D2.5)."
            )
    combined = (*participant.adoption_specs, *specs)
    pairs = [(spec.participant_name, spec.technology_name) for spec in combined]
    duplicates = sorted({pair for pair in pairs if pairs.count(pair) > 1})
    if duplicates:
        raise ValueError(
            f"attach_adoption_specs: duplicate spec(s) for {duplicates} — at "
            "most one AdoptionSpec per (participant, technology) pair "
            "(spec D2.4)."
        )
    participant.adoption_specs = combined
    return participant


# ── Splice-carrier declaration (spec D3.4) ───────────────────────────────────
# The adoption state is carried across policy-event segments whenever the
# feature is enabled on the finished segment: the "Investment Adoptions"
# summary column holds the serialized state (``core.protocols
# .serialize_adoption_state`` — a deterministic JSON string), and the carrier
# stamps it into the next segment's ``investment_initial_adoptions`` config
# field. Stamped adoptions are FLOORS on later segments' adoption sets — a
# late announcement cannot un-adopt an earlier investment (irreversibility
# doing policy work; monotone-across-segments is not negotiable, spec D3.4).
# Consumed by the engine's segment host literal (``engine/events.py``
# SPLICE_CARRIERS), where EI-5 appends it LAST (bank, reserve, adoptions).
ADOPTION_CARRIER = SpliceCarrier(
    column="Investment Adoptions",
    config_field="investment_initial_adoptions",
    carry_if=lambda config: bool(config.get("investment_feedback_enabled")),
)
