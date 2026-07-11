r"""InvestmentRule — the ``PathFeedback`` implementation (T2 runtime).

Trigger evaluation on the DELIVERED price path via ``core.investment`` —
the single source of the Dixit–Pindyck math (spec D2: "the feature adds
state, never re-derives"): the multiple comes from
``trigger_multiple(effective_volatility(σ, q), r, y)``, crossing dating
from ``activation_year`` (including its missing-year ValueError semantics
for per-year thresholds). This module adds exactly two things the core
math does not have: the ONE-FLIP candidate selection with the spec D1.4
tie-break, and the delegation to ``vintage.apply_adoption_state``.

Lifecycle (``core.protocols.PathFeedback``): the host constructs a FRESH
rule per outer iteration via a ``PathFeedbackFactory``; the host-owned
``AdoptionState`` is the only cross-iteration state. The rule itself holds
only construction-time constants (specs, resolved trigger multiples,
declared order) — nothing written during ``propose``/``apply`` survives.

Algorithm:
    Trigger and selection (spec D2.1, D1.4):

    LaTeX:
    $$ P^*_j(t) = M_j\,\theta_j(t), \qquad
       \tau_j = \min\{t : P^{\mathrm{delivered}}(t) \ge P^*_j(t)\} $$

    ASCII fallback:
        For each spec not already adopted:
            M     = trigger_multiple_override        (when set)
                  | 1                                (trigger_mode break_even)
                  | trigger_multiple((1-q)*sigma, r, y)
            tau   = activation_year(price_path, break_even, M)
        Among crossing candidates select AT MOST ONE by the tie-break:
            earliest crossing year
            -> largest relative exceedance P(tau)/P*(tau)
            -> declared config order

    Symbols (units):
        theta_j(t) : Marshallian break-even [currency/tCO2] (scalar or
                     {year label: value})
        M_j        : trigger multiple [dimensionless, >= 1]
        P(t)       : DELIVERED price of year t [currency/tCO2] (spec D1.2)
        tau_j      : crossing (DECISION) year label [yr] — the event
                     records tau, NOT tau + L (lag applies at vintaging)
        r, y, q    : discount rate [1/yr], payout yield [1/yr],
                     credibility [dimensionless]

Monotonicity is belt-and-braces: ``propose`` only ever APPENDS one event
to the state it was given (never removes, never re-dates), and the host
independently enforces the same invariants (spec D1.4 — host-enforced,
not trusted).

References:
    docs/invest-feedback-spec.md D1.2 (delivered path), D1.4 (one flip,
    tie-break), D2 (decision rule).
    core/investment.py — trigger math (worked anchors V1a-V1c).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from ...core.expectations import expectation_sort_key
from ...core.investment import activation_year, effective_volatility, trigger_multiple
from ...core.protocols import (
    AdoptionEvent,
    AdoptionSpec,
    AdoptionState,
    make_adoption_state,
)
from .vintage import apply_adoption_state

if TYPE_CHECKING:
    from ...core.market.model import CarbonMarket

__all__ = ["InvestmentRule"]


def _resolve_multiple(spec: AdoptionSpec, scenario_discount_rate: float) -> float:
    """Resolve one spec's trigger multiple M at rule construction.

    Precedence (spec D2.1): ``trigger_multiple_override`` wins when set;
    ``trigger_mode == "break_even"`` pins M = 1 (NPV activation dating,
    anchor V1a); otherwise the Dixit–Pindyck multiple at the effective
    volatility, with ``discount_rate = None`` resolving to the scenario
    rate HERE, at rule construction.

    Args:
        spec: The pair's adoption spec.
        scenario_discount_rate: Scenario r [1/yr], used when the spec does
            not override it.

    Returns:
        M [dimensionless, >= 1].

    Raises:
        ValueError: Propagated from ``core.investment`` with the spec's
            (participant, technology) prepended — e.g. r <= 0, or the
            σ_eff = 0 certainty limit's y < r requirement.
    """
    if spec.trigger_multiple_override is not None:
        return spec.trigger_multiple_override
    if spec.trigger_mode == "break_even":
        return 1.0
    r = scenario_discount_rate if spec.discount_rate is None else spec.discount_rate
    try:
        return trigger_multiple(
            effective_volatility(spec.sigma, spec.credibility), r, spec.payout_yield
        )
    except ValueError as exc:
        raise ValueError(
            f"AdoptionSpec({spec.participant_name!r}, {spec.technology_name!r}): {exc}"
        ) from exc


class InvestmentRule:
    """One outer iteration's trigger evaluation and vintaging operator.

    Implements ``core.protocols.PathFeedback``. Construction resolves every
    spec's trigger multiple once (they are time-invariant; per-year
    variation lives in θ_j(t)), so mis-parameterized specs fail loudly at
    rule construction, not mid-path.

    Attributes:
        multiples: Read-only diagnostic — (participant, technology) →
            resolved trigger multiple M [dimensionless]. Exposed so tests
            and diagnostics can pin the σ_eff endpoints (q = 1 → M = r/y)
            against ``core.investment`` without re-deriving.
    """

    def __init__(
        self,
        specs: tuple[AdoptionSpec, ...],
        scenario_discount_rate: float,
        declared_order: Mapping[tuple[str, str], int] | None = None,
    ) -> None:
        """Resolve trigger multiples and the deterministic candidate order.

        Args:
            specs: Every flagged pair's spec (at most one per pair).
            scenario_discount_rate: Scenario r [1/yr] — the default for
                specs with ``discount_rate=None`` (spec D6).
            declared_order: (participant, technology) → rank for the final
                tie-break leg (spec D1.4 "declared config order"). ``None``
                uses the ``specs`` tuple order. When given, it must cover
                every spec's pair with unique ranks.

        Raises:
            ValueError: Duplicate (participant, technology) pairs in
                ``specs``; a declared order missing a pair or carrying
                duplicate ranks; or an unresolvable trigger multiple.
        """
        self._specs = tuple(specs)
        pairs = [(spec.participant_name, spec.technology_name) for spec in self._specs]
        duplicates = sorted({pair for pair in pairs if pairs.count(pair) > 1})
        if duplicates:
            raise ValueError(
                f"InvestmentRule: duplicate spec(s) for {duplicates} — at most "
                "one AdoptionSpec per (participant, technology) pair (spec D2.4)."
            )
        if declared_order is None:
            self._order: dict[tuple[str, str], int] = {
                pair: rank for rank, pair in enumerate(pairs)
            }
        else:
            missing = sorted(pair for pair in pairs if pair not in declared_order)
            if missing:
                raise ValueError(
                    f"InvestmentRule: declared_order is missing pair(s) {missing} "
                    "— the tie-break must be total over the flagged pairs "
                    "(spec D1.4)."
                )
            ranks = [declared_order[pair] for pair in pairs]
            if len(set(ranks)) != len(ranks):
                raise ValueError(
                    "InvestmentRule: declared_order ranks must be unique — a "
                    "tied rank leaves the spec D1.4 tie-break indeterminate."
                )
            self._order = {pair: declared_order[pair] for pair in pairs}
        self.multiples: dict[tuple[str, str], float] = {
            pair: _resolve_multiple(spec, scenario_discount_rate)
            for pair, spec in zip(pairs, self._specs, strict=True)
        }

    def propose(
        self,
        price_path: Mapping[str, float],
        state: AdoptionState,
        markets: Sequence[CarbonMarket],
    ) -> tuple[AdoptionState, dict[str, float]]:
        """Propose at most ONE new adoption from the delivered price path.

        For every spec not already in ``state``, dates the first crossing
        via ``core.investment.activation_year`` (missing-year ValueError
        semantics included) and selects at most one candidate by the spec
        D1.4 tie-break: earliest crossing year → largest relative
        exceedance P(τ)/P*(τ) → declared config order. The event records
        the crossing (DECISION) year τ, never τ + L — the lag applies at
        vintaging (spec D2.3).

        Args:
            price_path: Year label → DELIVERED price [currency/tCO2] of
                the previous outer iterate (spec D1.2).
            state: The host-owned adoption state the iterate was solved
                under; returned UNCHANGED (same object) when nothing
                crosses.
            markets: Read-only iterate context (unused here — the declared
                order is construction-time state; kept for the
                ``PathFeedback`` contract).

        Returns:
            ``(proposal, metrics)`` — ``state`` plus at most one new
            ``AdoptionEvent`` (re-normalized through
            ``make_adoption_state``), and the stable metric keys
            ``{"candidates", "flipped", "flip_exceedance"}``.

        Raises:
            ValueError: A per-year ``break_even`` mapping lacking a year
                present in ``price_path`` (``activation_year`` semantics).
        """
        adopted = {(event.participant_name, event.technology_name) for event in state}
        # (sort_key(tau), -exceedance, declared rank) — the D1.4 tie-break —
        # then the payload (spec, tau, exceedance).
        candidates: list[tuple[tuple[tuple[float, str], float, int], AdoptionSpec, str, float]] = []
        for spec in self._specs:
            pair = (spec.participant_name, spec.technology_name)
            if pair in adopted:
                continue
            M = self.multiples[pair]
            tau = activation_year(price_path, spec.break_even, M)
            if tau is None:
                continue
            if isinstance(spec.break_even, Mapping):
                theta = float(spec.break_even[tau])
            else:
                theta = float(spec.break_even)
            exceedance = float(price_path[tau]) / (M * theta)
            candidates.append(
                (
                    (expectation_sort_key(tau), -exceedance, self._order[pair]),
                    spec,
                    tau,
                    exceedance,
                )
            )
        metrics = {
            "candidates": float(len(candidates)),
            "flipped": 0.0,
            "flip_exceedance": 0.0,
        }
        if not candidates:
            return state, metrics
        _, spec, tau, exceedance = min(candidates, key=lambda c: c[0])
        event = AdoptionEvent(
            participant_name=spec.participant_name,
            technology_name=spec.technology_name,
            adoption_year=tau,
        )
        # Monotone by construction: state ∪ {event}, never a removal or a
        # re-dating (the host enforces the same invariants independently).
        proposal = make_adoption_state([*state, event])
        metrics["flipped"] = 1.0
        metrics["flip_exceedance"] = exceedance
        return proposal, metrics

    def apply(
        self,
        ordered_markets: list[CarbonMarket],
        state: AdoptionState,
    ) -> list[CarbonMarket]:
        """Vintage the adoption state into the horizon's markets.

        Delegates to ``vintage.apply_adoption_state`` with this rule's
        specs — including the neutral-case identity guarantee (empty specs
        and state return ``ordered_markets`` itself).

        Args:
            ordered_markets: The base horizon markets in year order.
            state: Adoptions to vintage in.

        Returns:
            Vintaged markets (see ``vintage.apply_adoption_state``).
        """
        return apply_adoption_state(ordered_markets, self._specs, state)
