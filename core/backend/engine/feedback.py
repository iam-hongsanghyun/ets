r"""Endogenous-investment feedback: the adoption outer loop around a FULL path solve.

The self-coupling sibling of ``coupling/loop.py`` (plan D2,
``docs/invest-feedback-plan.md``): where Option B iterates the ETS engine
against an EXTERNAL model, this host iterates the engine against its own
demand system — a ``core.protocols.PathFeedback`` rule proposes irreversible
technology adoptions from the solved DELIVERED price path, the adoptions are
vintaged into the markets, and the SAME approach's full path solve
(``engine/dispatch._path_solver_for``'s closure — competitive fixed point,
or the complete Rubin/Schennach banking solve including its window search
and supply-rule fixed point, spec D1.3) is re-run untouched. Strictly
OUTSIDE the expectations inner loop (R29) and outside ``solve_banking_path``
(spec D1.3).

Which price adoption reads (spec D1.2, NOT configurable): the DELIVERED
per-year price of the previous outer iterate — ``item["equilibrium"]
["price"]`` of every per-year detail dict, which every approach writes
post-overlay and floor-clipped: the banking solver stamps ``delivered[t]``
(the ``DeliveredFloor`` clip-LAST output), the competitive kernel's clearing
embeds the reserve-floor boundary condition, and the hotelling/transmission
solvers stamp their clipped effective price. The pre-clip price would make
the auction reserve — the K-MSR paper's central instrument — invisible to
the investment rule.

Algorithm:
    The spec D1 trigger-consistent adoption equilibrium loop, exactly
    (``docs/invest-feedback-spec.md`` D1.1-D1.4; plan "Outer loop"):

    LaTeX:
    $$ A_0 = \text{carried adoptions}, \qquad
       \mathcal{M}_k = \mathrm{apply}(\mathcal{M}_0, A_k), \qquad
       P_k = \Pi\big(\mathcal{M}_k\big), $$
    $$ A_{k+1} = \mathrm{propose}\big(P_k, A_k\big) \quad\text{s.t.}\quad
       A_k \subseteq A_{k+1},\;\; |A_{k+1}| \le |A_k| + 1, $$
    $$ A_{k+1} = A_k \;\Rightarrow\; \text{converged: } (P_k, A_k)
       \text{ is the equilibrium}. $$

    ASCII fallback:
        state_0 = carried adoptions (splice carrier / config); k = 0
        loop:
          markets_k = fresh_rule().apply(base_markets, state_k)  # vintaging
          path_k    = path_solver(markets_k)                     # FULL solve
          P_k       = delivered price path of path_k
          proposal  = fresh_rule().propose(P_k, state_k, markets_k)
          host enforces: proposal >= state_k (set superset), no re-dating,
                         at most ONE new event
          if proposal == state_k: converged (final = path_k)
          state_{k+1} = proposal

    Symbols (units):
        A_k        : adoption state of outer iteration k — sorted tuple of
                     (participant, technology, adoption year tau) [-]
        M_0, M_k   : base / vintaged market lists (one CarbonMarket per
                     year; flagged options masked before tau + L) [-]
        Pi(.)      : the approach's own FULL path solve (the EI-2 closure)
        P_k        : year label -> delivered price of iterate k
                     [currency/tCO2]
        tau, L     : adoption (decision) year [yr]; build lag [yr, int >= 0]
        N          : number of flagged (participant, technology) pairs [-]

    Termination theorem (spec D1.4, binding — COMBINATORIAL, no price
    relaxation, no price tolerance): adoption is monotone (once adopted,
    never un-adopted — that IS irreversibility) and at most ONE pair flips
    per iteration, so ``|A_k|`` strictly increases on every non-converged
    iteration and is bounded by N. Hence at most N flipping iterations can
    occur, and the (N+1)-th iteration must return ``proposal == state`` —
    the loop terminates in at most N + 1 iterations, each one full inner
    solve:

    $$ A_0 \subseteq A_1 \subseteq \dots \subseteq A_{k},\quad
       |A_{k+1}| \le |A_k| + 1,\quad |A_k| \le N
       \;\Longrightarrow\; k^{*} \le N + 1 . $$

    ``max_iterations`` is a SAFETY RAIL only (default N + 1): exhaustion —
    only reachable with a rule that violates its own contract — logs a
    WARNING (mirroring the banking host's supply-rule cap) and returns the
    last solved iterate with ``investment_converged = 0.0``, never silently.

Ex-post validity checks on the final path (spec D1.1, part of the
equilibrium concept, not optional):

* MISSED ADOPTION (loud ``ValueError``): no NON-adopted flagged pair may
  cross its trigger on the final path — the investment analogue of the
  banking window's boundary no-arbitrage checks. Evaluated with an
  INDEPENDENT ``InvestmentRule`` built from the specs (never the possibly
  buggy injected factory), so a lying rule cannot certify itself. When the
  safety rail already fired (``converged=False``) the residual crossing is
  the known reason and is logged at WARNING instead of raised — the rail's
  "return the last iterate" contract would otherwise be unreachable.
* ADOPTED BELOW TRIGGER (INFO with the margin, never silent): an adopted
  pair MAY sit below its trigger on the final path — the entrant depresses
  the post-adoption price; standard discrete entry. Ex-post regret is
  permitted, ex-ante violation is not (the loop's stopping consistency).

References:
    docs/invest-feedback-spec.md D1 (equilibrium concept), D1.4
    (termination), D2 (decision rule), D3.4 (splice carrier).
    docs/invest-feedback-plan.md — "Outer loop (engine/feedback.py)".
    core/protocols.py — ``PathFeedback`` lifecycle doctrine.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..core.expectations import expectation_sort_key
from ..core.protocols import (
    AdoptionSpec,
    AdoptionState,
    make_adoption_state,
    parse_adoption_state,
    serialize_adoption_state,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core.market.model import CarbonMarket
    from ..core.protocols import PathFeedbackFactory

logger = logging.getLogger(__name__)

__all__ = ["solve_with_investment_feedback"]


def _delivered_price_path(path_details: list[dict[str, Any]]) -> dict[str, float]:
    """Extract the DELIVERED per-year price path from a solved path.

    The spec D1.2 price signal: ``item["equilibrium"]["price"]`` — the
    post-overlay, floor-clipped price every approach's detail rows carry
    (banking stamps ``delivered[t]`` after the ``DeliveredFloor`` clip-LAST
    overlay; the competitive kernel's clearing embeds the reserve-floor
    boundary; hotelling/transmission stamp their clipped effective price).
    This is the same value ``core.ledger.collect_path_results`` reports as
    ``"Equilibrium Carbon Price"``.

    Args:
        path_details: Per-year detail dicts in the
            ``simulate_path_details`` structure.

    Returns:
        Year label -> delivered price [currency/tCO2].
    """
    return {str(item["market"].year): float(item["equilibrium"]["price"]) for item in path_details}


def _enforce_monotone_one_flip(state: AdoptionState, proposal: AdoptionState) -> None:
    """Host-enforced spec D1.4 invariants on one iteration's proposal.

    Belt and braces (the lifecycle doctrine, ``core.protocols
    .PathFeedback``): implementations promise monotone one-flip proposals,
    and the host verifies INDEPENDENTLY — a proposal that drops an adopted
    pair, re-dates one, or adds more than one new event is a contract
    violation, never something to repair silently.

    Args:
        state: The host-owned adoption state the iterate was solved under.
        proposal: The rule's proposed next state (already re-normalized
            through ``make_adoption_state``).

    Raises:
        ValueError: A dropped event (proposal is not a superset of the
            state), a re-dated event (same pair, different adoption year),
            or more than one new (participant, technology) pair.
    """
    proposed_year_by_pair = {
        (event.participant_name, event.technology_name): event.adoption_year for event in proposal
    }
    for event in state:
        pair = (event.participant_name, event.technology_name)
        if pair not in proposed_year_by_pair:
            raise ValueError(
                f"investment feedback: proposal DROPPED adopted pair {pair} "
                "(adoption is monotone across outer iterations — once adopted, "
                "never un-adopted; spec D1.4)."
            )
        if proposed_year_by_pair[pair] != event.adoption_year:
            raise ValueError(
                f"investment feedback: proposal RE-DATED adopted pair {pair} "
                f"from {event.adoption_year!r} to "
                f"{proposed_year_by_pair[pair]!r} (adoption years are written "
                "at most once; spec D1.4 / identity D4.4)."
            )
    state_pairs = {(event.participant_name, event.technology_name) for event in state}
    new_pairs = sorted(set(proposed_year_by_pair) - state_pairs)
    if len(new_pairs) > 1:
        raise ValueError(
            f"investment feedback: proposal added {len(new_pairs)} new events "
            f"{new_pairs} in one iteration — at most ONE flip per outer "
            "iteration (sequential-entry selection; spec D1.4)."
        )


def _ex_post_trigger_checks(
    price_path: Mapping[str, float],
    final_state: AdoptionState,
    final_markets: list[CarbonMarket],
    specs: tuple[AdoptionSpec, ...],
    scenario_discount_rate: float,
    converged: bool,
) -> None:
    """Spec D1.1 stopping-consistency checks on the FINAL path.

    Evaluated with an INDEPENDENT ``InvestmentRule`` constructed from the
    specs (the single source of the trigger math via ``core.investment``)
    — never the injected factory, so a rule that lies about convergence
    cannot certify its own output.

    Args:
        price_path: Final iterate's delivered price path [currency/tCO2].
        final_state: The adoption state the final path was solved under.
        final_markets: The final iterate's (vintaged) markets — read-only
            ``propose`` context.
        specs: Every flagged pair's ``AdoptionSpec``.
        scenario_discount_rate: Scenario r [1/yr] for spec-default trigger
            multiples.
        converged: Whether the loop converged; a missed adoption RAISES
            only on a converged (equilibrium-claiming) path — on the
            safety-rail fallback it is logged at WARNING (the rail's
            return-last-iterate contract would otherwise be unreachable).

    Raises:
        ValueError: Missed adoption — a non-adopted flagged pair crosses
            its trigger on a final path claimed as converged.
    """
    if not specs:
        return
    # Lazy feature import (activation scoping): only an investment-configured
    # scenario ever reaches this host, and only this check needs the rule.
    from ..features.endogenous_investment.rule import InvestmentRule

    reference = InvestmentRule(specs, scenario_discount_rate)
    check_proposal, check_metrics = reference.propose(dict(price_path), final_state, final_markets)
    if check_proposal != final_state:
        crossed = sorted(
            (event.participant_name, event.technology_name, event.adoption_year)
            for event in set(check_proposal) - set(final_state)
        )
        message = (
            "investment feedback: missed adoption — "
            f"{check_metrics.get('candidates', 0.0):.0f} non-adopted flagged "
            "pair(s) cross their trigger on the final path (first by "
            f"tie-break: {crossed}); every non-adopted pair must satisfy "
            "P_delivered(t) < P*(t) for all t (spec D1.1)."
        )
        if converged:
            raise ValueError(message)
        logger.warning(message)
    spec_by_pair = {(s.participant_name, s.technology_name): s for s in specs}
    for event in final_state:
        pair = (event.participant_name, event.technology_name)
        spec = spec_by_pair.get(pair)
        if spec is None:
            continue  # carried adoption with no local flag: nothing to price
        tau = event.adoption_year
        if tau not in price_path:
            continue  # adopted before this horizon (splice-carried event)
        M = reference.multiples[pair]
        if isinstance(spec.break_even, Mapping):
            theta_raw = spec.break_even.get(tau)
            if theta_raw is None:
                continue
            theta = float(theta_raw)
        else:
            theta = float(spec.break_even)
        p_star = M * theta
        delivered = float(price_path[tau])
        if delivered < p_star:
            logger.info(
                f"Investment feedback: adopted pair {pair} is below its trigger "
                f"on the final path at {tau}: delivered {delivered:.4f} < "
                f"P* {p_star:.4f} [currency/tCO2] (margin "
                f"{delivered - p_star:.4f}, ratio {delivered / p_star:.4f}) — "
                "ex-post regret of discrete entry, permitted and logged "
                "(spec D1.1)."
            )


def _stamp_investment_details(
    path_details: list[dict[str, Any]],
    state: AdoptionState,
    specs: tuple[AdoptionSpec, ...],
    iterations: int,
    converged: bool,
) -> None:
    """Stamp the per-year investment diagnostics into the final path details.

    Pinned key order (plan D3 — read back by ``core.ledger
    .collect_path_results`` under a key-presence guard, and by the splice
    carrier through the ``"Investment Adoptions"`` summary column):
    ``investment_adoptions``, ``investment_newly_effective``,
    ``investment_feedback_iterations``, ``investment_converged``.

    ``investment_adoptions`` serializes the state EFFECTIVE THROUGH the row's
    year — events with adoption (decision) year tau <= year, spec D2.3's
    "state flips at tau" — so the last kept row of a policy-event segment
    carries exactly the adoptions decided within its information set.
    ``investment_newly_effective`` counts events whose CAPACITY arrives this
    year (tau + L == year; L = 0 for carried events with no local spec).

    Args:
        path_details: The final iterate's per-year detail dicts (mutated in
            place — keys appended at the tail).
        state: The adoption state the final path was solved under.
        specs: Flagged specs (source of per-pair build lags L).
        iterations: Outer iterations performed (solves run).
        converged: Whether the loop converged (1.0/0.0 in the stamp).
    """
    lag_by_pair = {
        (spec.participant_name, spec.technology_name): int(spec.build_lag_years) for spec in specs
    }
    for item in path_details:
        year_label = str(item["market"].year)
        year_key = expectation_sort_key(year_label)
        effective = tuple(
            event for event in state if expectation_sort_key(event.adoption_year) <= year_key
        )
        newly_effective = 0
        for event in state:
            lag = lag_by_pair.get((event.participant_name, event.technology_name), 0)
            if lag == 0:
                if event.adoption_year == year_label:
                    newly_effective += 1
                continue
            tau_num, _ = expectation_sort_key(event.adoption_year)
            year_num, _ = expectation_sort_key(year_label)
            if math.isfinite(tau_num) and math.isfinite(year_num) and year_num == tau_num + lag:
                newly_effective += 1
        item["investment_adoptions"] = serialize_adoption_state(effective)
        item["investment_newly_effective"] = float(newly_effective)
        item["investment_feedback_iterations"] = float(iterations)
        item["investment_converged"] = 1.0 if converged else 0.0


def solve_with_investment_feedback(
    ordered_markets: list[CarbonMarket],
    path_solver: Callable[[list[CarbonMarket]], list[dict[str, Any]]],
    rule_factory: PathFeedbackFactory,
    specs: tuple[AdoptionSpec, ...],
    *,
    scenario_discount_rate: float,
    max_iterations: int | None = None,
) -> list[dict[str, Any]]:
    """Solve one scenario's trigger-consistent adoption equilibrium (spec D1).

    Wraps ANY approach's full path solve (the ``_path_solver_for`` closure,
    EI-2) in the monotone one-flip adoption loop — see the module docstring
    for the algorithm and the D1.4 termination theorem. ``state_0`` is the
    carried/pre-committed adoptions parsed from the first market's
    ``investment_initial_adoptions`` field (the splice carrier's landing
    field, user-settable to pre-commit; empty default). Carried adoptions
    are FLOORS: the monotone host check makes every later state a superset
    of ``state_0``, so a later policy-event segment can never drop them.

    Args:
        ordered_markets: The scenario's base markets, chronologically
            sorted (never mutated — vintaging copies).
        path_solver: The approach's FULL path solve
            (``ordered_markets -> path details``), re-invoked untouched on
            each iterate's vintaged markets.
        rule_factory: Zero-argument ``PathFeedback`` constructor — a FRESH
            rule per use (lifecycle doctrine); the host-owned adoption
            state is the only cross-iteration state.
        specs: Every flagged (participant, technology) pair's
            ``AdoptionSpec`` — drives the safety-rail default, the per-pair
            build lags in the diagnostics, and the INDEPENDENT ex-post
            trigger checks.
        scenario_discount_rate: Scenario r [1/yr] (spec-default trigger
            multiples in the ex-post checks).
        max_iterations: Safety rail on outer iterations; ``None`` uses the
            spec D1.4 bound ``len(specs) + 1``. Exhaustion logs a WARNING
            and returns the last iterate with ``investment_converged=0.0``
            — no price relaxation, no price tolerance exists to loosen.

    Returns:
        The final iterate's path details (``simulate_path_details``
        structure) with the four ``investment_*`` diagnostic keys stamped
        per year (pinned order — see ``_stamp_investment_details``).

    Raises:
        ValueError: Empty ``ordered_markets``; ``max_iterations < 1``; a
            proposal violating the monotone one-flip contract; or a missed
            adoption on a converged final path (spec D1.1).
    """
    if not ordered_markets:
        raise ValueError("solve_with_investment_feedback requires at least one market.")
    if max_iterations is None:
        max_iterations = len(specs) + 1
    if max_iterations < 1:
        raise ValueError(f"max_iterations must be at least 1, got {max_iterations}.")

    initial_raw = getattr(ordered_markets[0], "investment_initial_adoptions", None)
    state: AdoptionState = parse_adoption_state(initial_raw) if initial_raw else ()

    converged = False
    iterations = 0
    solved_state: AdoptionState = state
    path: list[dict[str, Any]] = []
    markets_k: list[CarbonMarket] = ordered_markets
    for k in range(max_iterations):
        solved_state = state
        markets_k = rule_factory().apply(ordered_markets, state)
        path = path_solver(markets_k)  # FULL untouched inner solve (spec D1.3)
        iterations = k + 1
        price_path = _delivered_price_path(path)
        proposal, metrics = rule_factory().propose(price_path, state, markets_k)
        proposal = make_adoption_state(proposal)
        _enforce_monotone_one_flip(state, proposal)
        logger.debug(
            f"Investment feedback iteration {k}: adopted={len(state)}, "
            f"candidates={metrics.get('candidates', 0.0):.0f}, "
            f"flipped={metrics.get('flipped', 0.0):.0f}, "
            f"flip_exceedance={metrics.get('flip_exceedance', 0.0):.4f}"
        )
        if proposal == state:
            converged = True
            break
        state = proposal
    else:
        logger.warning(
            "Investment feedback: adoption loop did not converge within "
            f"{max_iterations} iterations; using the last iterate."
        )

    _ex_post_trigger_checks(
        _delivered_price_path(path),
        solved_state,
        markets_k,
        specs,
        scenario_discount_rate,
        converged,
    )
    _stamp_investment_details(path, solved_state, specs, iterations, converged)
    return path
