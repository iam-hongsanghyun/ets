r"""Adoption vintaging — per-year availability gating of flagged options (T2 runtime).

Implements spec D2.5/D3 (``docs/invest-feedback-spec.md``): a technology
flagged with an ``invest_trigger`` block is REMOVED from the reversible
choice set until its adoption becomes effective, entering at its configured
``max_activity_share`` thereafter. Availability gating ONLY — this module
never mutates MAC blocks or ``initial_emissions`` (D3.1: adoption is the
flagged option JOINING the participant's technology set, an explicit
portfolio member; mutating base-technology MACs would be uninspectable and
double-count).

The mask is SOLVE-TIME STATE, not a build transform (D3.2): it is applied
to fresh per-year copies where the technology list is read, after the
entire build pipeline. Pinned order: sector → trajectory → OBA (build) →
Option A multiplier (in-clearing) → adoption mask (outer state). Shared
participants are never mutated mid-solve — every changed participant/market
is a copy; untouched objects pass through by identity (base MACs stay
bytewise identical pre/post, identity D4.5).

Algorithm:
    Availability of a flagged (participant i, technology j) in year t
    (spec D2.3/D2.5):

    LaTeX:
    $$ \text{available}_{ij}(t) \iff (i,j) \in A \ \wedge\
       t \ge \tau_{ij} + L_j $$

    ASCII fallback:
        available(i, j, t) = adopted(i, j) and t >= tau_ij + L_j
        choice_set_t(i)    = technology_options(i)
                             - {j flagged and not available(i, j, t)}

    Symbols (units):
        A       : the adoption state (set of adopted pairs)   [-]
        tau_ij  : adoption (DECISION) year label of the pair  [yr]
        L_j     : the spec's build_lag_years                  [yr, int >= 0]
        t       : the market's year label, ordered by the
                  ``core.ledger.market_year_sort_key`` semantics
                  (numeric labels numerically, via
                  ``core.expectations.expectation_sort_key``)  [yr]

    A flagged pair NOT in the adoption state is available in NO year —
    "feature ON but never triggered" equals the flagged option DELETED,
    not the flag removed (binding consequence, spec D2.5; anchor V3).
    Utilization stays reversible post-adoption: the option is AVAILABLE at
    its cap, never forced — the existing portfolio optimizer chooses
    within it (capex irreversible, dispatch reversible, D2.4).

References:
    docs/invest-feedback-spec.md D2.3-D2.5, D3.1-D3.3, D4.4-D4.5.
    docs/invest-feedback-plan.md — "Feature module" (vintage.py).
"""

from __future__ import annotations

import copy
import math
from typing import TYPE_CHECKING

from ...core.expectations import expectation_sort_key
from ...core.protocols import AdoptionSpec, AdoptionState

if TYPE_CHECKING:
    from ...core.market.model import CarbonMarket
    from ...core.participant.models import MarketParticipant

__all__ = ["apply_adoption_state"]


def _availability_key(spec: AdoptionSpec, adoption_year: str) -> tuple[float, str]:
    """Sort key of the first year the adopted pair's option is available.

    ``build_lag_years == 0`` compares by the adoption year's own label key
    (exact, label-preserving); a positive lag requires a NUMERIC adoption
    year label to compute τ + L.

    Args:
        spec: The pair's adoption spec (carries ``build_lag_years``).
        adoption_year: The pair's adoption (decision) year label τ.

    Returns:
        A ``(numeric_year, label)`` key comparable with
        ``expectation_sort_key(year_label)``; the option is available in
        every year whose key is >= this key.

    Raises:
        ValueError: ``build_lag_years > 0`` with a non-numeric adoption
            year label (τ + L is undefined).
    """
    if spec.build_lag_years == 0:
        return expectation_sort_key(adoption_year)
    tau_num, _ = expectation_sort_key(adoption_year)
    if not math.isfinite(tau_num):
        raise ValueError(
            f"AdoptionSpec({spec.participant_name!r}, {spec.technology_name!r}): "
            f"adoption year {adoption_year!r} is not numeric — "
            f"build_lag_years={spec.build_lag_years} cannot compute tau + L."
        )
    return (tau_num + float(spec.build_lag_years), "")


def apply_adoption_state(
    ordered_markets: list[CarbonMarket],
    specs: tuple[AdoptionSpec, ...],
    state: AdoptionState,
) -> list[CarbonMarket]:
    """Gate flagged options' availability per year for one adoption state.

    Pure with respect to its inputs: NEVER mutates ``ordered_markets`` or
    anything reachable from it. Changed participants and their markets are
    shallow copies with rebuilt ``technology_options`` /``participants``
    lists; unchanged participants, unchanged markets, and every
    ``TechnologyOption`` object pass through BY IDENTITY (no MAC or
    ``initial_emissions`` writes anywhere — spec D3.1, identity D4.5).

    IDENTITY GUARANTEE (off-by-default proof chain, plan "Feature
    module"): ``specs == () and state == ()`` returns ``ordered_markets``
    ITSELF — the same list object, untouched.

    Adoption events whose pair has no spec here are inert (nothing is
    flagged, so nothing needs unmasking) — the host may legitimately carry
    adoptions into a segment whose config no longer flags the option
    (stamped adoptions are floors, spec D3.4; the option is then an
    ordinary reversible choice).

    Args:
        ordered_markets: The base horizon markets in year order.
        specs: Every flagged pair's ``AdoptionSpec`` (drives the mask).
        state: The canonical adoption state (drives the unmask year).

    Returns:
        A new list of markets with the per-year gating applied (or
        ``ordered_markets`` itself in the neutral case).

    Raises:
        ValueError: A spec's participant exists in a market but lacks the
            flagged technology option (inconsistent spec/market pairing);
            or a positive-lag spec adopted in a non-numeric year.
    """
    if not specs and not state:
        return ordered_markets

    adoption_year_by_pair: dict[tuple[str, str], str] = {
        (event.participant_name, event.technology_name): event.adoption_year for event in state
    }
    specs_by_participant: dict[str, list[AdoptionSpec]] = {}
    for spec in specs:
        specs_by_participant.setdefault(spec.participant_name, []).append(spec)

    result: list[CarbonMarket] = []
    for market in ordered_markets:
        year_key = expectation_sort_key(market.year)
        replacements: dict[int, MarketParticipant] = {}
        for index, participant in enumerate(market.participants):
            flagged = specs_by_participant.get(participant.name)
            if not flagged:
                continue
            options = participant.technology_options or []
            option_names = {option.name for option in options}
            missing = sorted({s.technology_name for s in flagged} - option_names)
            if missing:
                raise ValueError(
                    f"apply_adoption_state: year {market.year!r}, participant "
                    f"{participant.name!r} has no technology option(s) "
                    f"{missing} named by its adoption spec(s) — flagged "
                    "options must exist to be masked (spec D2.5)."
                )
            masked: set[str] = set()
            for spec in flagged:
                pair = (spec.participant_name, spec.technology_name)
                tau = adoption_year_by_pair.get(pair)
                if tau is None or year_key < _availability_key(spec, tau):
                    masked.add(spec.technology_name)
            if not masked:
                continue
            kept = [option for option in options if option.name not in masked]
            clone = copy.copy(participant)
            # Mirror the builder's empty-options convention (None, never []),
            # so all-flagged-masked matches "flagged option DELETED" exactly
            # (anchor V3; ``optimize_compliance`` treats both identically).
            clone.technology_options = kept if kept else None
            replacements[index] = clone
        if not replacements:
            result.append(market)
            continue
        market_clone = copy.copy(market)
        market_clone.participants = [
            replacements.get(i, p) for i, p in enumerate(market.participants)
        ]
        result.append(market_clone)
    return result
