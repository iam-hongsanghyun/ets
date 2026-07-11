"""Solve dispatch (T3): scenario grouping, approach routing, output assembly.

``run_simulation``, ``_rename_markets``, ``run_simulation_from_config``, and
``run_simulation_from_file`` moved VERBATIM from ``solvers/simulation.py`` in
the engine work order (v1 O8 / v2 O12, ``docs/feature-modules-plan.md``);
``ets/solvers/simulation.py`` re-exports them so every old import path keeps
working. The competitive path solver (``solve_scenario_path``) stays in
``solvers/simulation.py`` until the competitive feature move (v1 O10 /
v2 O14) and is imported lazily inside ``run_simulation`` — alongside the
other approach solvers — so no module-level cycle arises with the
solvers-tier re-exports of this module's names.

PURE REFACTOR (EI-2, ``docs/invest-feedback-plan.md`` D2): the per-approach
solve invocation ``run_simulation`` used to build inline is now
``_path_solver_for`` — a closure factory that captures the exact same
kwargs derivation from a scenario's first market (``m0``) and returns a
``ordered_markets -> path`` callable. Zero behaviour change: calling
``_path_solver_for(approach, m0, transmission_lambda=...)(ordered_markets)``
runs the identical branch body, with identical lazy imports, that used to
sit directly in ``run_simulation``'s if/elif ladder. This exists so a later
order (EI-5, ``engine/feedback.py``) can re-invoke the SAME approach's full
path solve on successive vintaged market lists without re-deriving or
drifting from the wiring literals — the closure is the one place they live.
The ``"all"`` comparison branch is NOT routed through the factory (it fans
a scenario out over three differently-renamed market lists, not one
``ordered_markets`` thread) and stays inline, unchanged.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ..config_io import build_markets_from_config, iter_market_bodies, load_config

# Aliased to the pre-move underscore names so the bodies below stay verbatim.
from ..core.ledger import (
    collect_path_results as _collect_path_results,
    market_year_sort_key as _market_year_sort_key,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ..core.market import CarbonMarket

logger = logging.getLogger(__name__)


def _rename_markets(markets: list[CarbonMarket], suffix: str) -> list[CarbonMarket]:
    """Return shallow copies of markets with scenario_name suffixed."""
    renamed = []
    for m in markets:
        copy = deepcopy(m)
        copy.scenario_name = f"{m.scenario_name} [{suffix}]"
        renamed.append(copy)
    return renamed


def _hot_kwargs(m0: CarbonMarket) -> dict[str, float | int]:
    """Hotelling/transmission solver kwargs derived from a scenario's first market.

    Args:
        m0: First market of the scenario's chronologically sorted path.

    Returns:
        Keyword arguments for ``solve_hotelling_path``/``solve_transmission_path``.
    """
    return dict(
        discount_rate=float(getattr(m0, "discount_rate", 0.04) or 0.04),
        risk_premium=float(getattr(m0, "risk_premium", 0.0) or 0.0),
        max_bisection_iters=int(getattr(m0, "solver_hotelling_max_bisection_iters", 80) or 80),
        max_lambda_expansions=int(getattr(m0, "solver_hotelling_max_lambda_expansions", 20) or 20),
        convergence_tol=float(getattr(m0, "solver_hotelling_convergence_tol", 1e-4) or 1e-4),
    )


def _nash_kwargs(m0: CarbonMarket) -> dict[str, object]:
    """Nash-Cournot solver kwargs derived from a scenario's first market.

    Args:
        m0: First market of the scenario's chronologically sorted path.

    Returns:
        Keyword arguments for ``solve_nash_path``.
    """
    return dict(
        strategic_participants=list(getattr(m0, "nash_strategic_participants", None) or []) or None,
        price_step=float(getattr(m0, "solver_nash_price_step", 0.5) or 0.5),
        max_iters=int(getattr(m0, "solver_nash_max_iters", 120) or 120),
        convergence_tol=float(getattr(m0, "solver_nash_convergence_tol", 1e-3) or 1e-3),
    )


def _path_solver_for(
    approach: str,
    m0: CarbonMarket,
    *,
    transmission_lambda: float | None,
) -> Callable[[list[CarbonMarket]], list[dict]]:
    """Build the closure that runs one scenario's full per-approach path solve.

    PURE extraction of ``run_simulation``'s former inline if/elif ladder
    (everything except the ``"all"`` comparison fan-out, which the caller
    keeps handling separately). Every keyword argument the returned closure
    passes downstream is derived from ``m0`` exactly once, at closure-build
    time — identical to the pre-extraction inline reads — so
    ``_path_solver_for(approach, m0, transmission_lambda=lam)(ordered_markets)``
    is bit-identical to the old inline call for the same
    ``(approach, m0, ordered_markets)`` triple. This is what lets a later
    outer loop (``engine/feedback.py``, EI-5, ``docs/invest-feedback-plan.md``)
    re-invoke the SAME approach's full solve on successive vintaged market
    lists without re-deriving or drifting from the wiring literals below —
    the closure is the one and only place they live.

    Every ``features.*``/``.wiring`` import stays lazy INSIDE the returned
    closure's body (never at factory-build time), so building the closure
    never loads a feature runtime module — only calling it does. This
    preserves the activation-scoping contract
    (``tests/engine/test_lazy_activation.py``).

    Args:
        approach: The scenario's resolved ``model_approach``. ``"all"`` is
            handled entirely by the caller and is never passed here — if it
            were, this falls through to the competitive default, which is
            NOT what ``"all"`` means, so callers must keep excluding it.
        m0: First market of the scenario's chronologically sorted path.
        transmission_lambda: The scenario's forward-transmission λ after the
            caller's competitive-only gate and warning (``None`` when unset
            or ignored for a non-competitive approach). Passed in rather
            than re-derived so the caller's warning log fires exactly once
            per scenario, not once per solve invocation.

    Returns:
        A callable ``ordered_markets -> path`` (list of per-year result
        dicts, one row per market year) that runs the wired solver for
        ``approach``.
    """
    if transmission_lambda is not None:
        lam = float(transmission_lambda)
        hot_kwargs = _hot_kwargs(m0)

        def _solve_transmission(ordered_markets: list[CarbonMarket]) -> list[dict]:
            from .wiring import solve_transmission_path

            return solve_transmission_path(ordered_markets, lam=lam, **hot_kwargs)

        return _solve_transmission

    if approach == "banking":
        discount_rate = float(getattr(m0, "discount_rate", 0.055) or 0.055)
        risk_premium = float(getattr(m0, "risk_premium", 0.0) or 0.0)

        def _solve_banking(ordered_markets: list[CarbonMarket]) -> list[dict]:
            from .wiring import solve_banking_path

            return solve_banking_path(
                ordered_markets,
                discount_rate=discount_rate,
                risk_premium=risk_premium,
            )

        return _solve_banking

    if approach == "hotelling":
        hot_kwargs = _hot_kwargs(m0)

        def _solve_hotelling(ordered_markets: list[CarbonMarket]) -> list[dict]:
            from .wiring import solve_hotelling_path

            return solve_hotelling_path(ordered_markets, **hot_kwargs)

        return _solve_hotelling

    if approach == "nash_cournot":
        nash_kwargs = _nash_kwargs(m0)

        def _solve_nash(ordered_markets: list[CarbonMarket]) -> list[dict]:
            from .wiring import solve_nash_path

            return solve_nash_path(ordered_markets, **nash_kwargs)

        return _solve_nash

    def _solve_competitive(ordered_markets: list[CarbonMarket]) -> list[dict]:
        # Default: competitive (MSR handled inside solve_scenario_path)
        from .wiring import solve_scenario_path

        return solve_scenario_path(ordered_markets)

    return _solve_competitive


def _investment_configured(m0: CarbonMarket) -> bool:
    """Gate of the endogenous-investment feedback branch (spec D6 loud guard).

    The feature is ON iff BOTH halves of its configuration are present on
    the scenario's first market: the master flag
    (``investment_feedback_enabled``, scenario-level, default absent/False)
    AND at least one participant carrying ``adoption_specs``. A mismatch is
    a config error and raises — flagged options with the gate off must
    never be a silent ignore (spec D3.2/D6; the config door's builder-level
    guard, EI-6, mirrors this belt-and-braces).

    Args:
        m0: First market of the scenario's chronologically sorted path.

    Returns:
        True iff the flag is set AND specs are attached; False when neither
        is present (the byte-identical legacy path).

    Raises:
        ValueError: Flag true with zero specs, or specs attached with the
            flag false/absent.
    """
    enabled = bool(getattr(m0, "investment_feedback_enabled", False))
    has_specs = any(getattr(participant, "adoption_specs", ()) for participant in m0.participants)
    if enabled and not has_specs:
        raise ValueError(
            f"Scenario '{m0.scenario_name}': investment_feedback_enabled is true "
            "but no participant carries an adoption spec — flag one or more "
            "technology options with an investment_trigger block, or disable "
            "the feature (spec D6)."
        )
    if has_specs and not enabled:
        raise ValueError(
            f"Scenario '{m0.scenario_name}': adoption spec(s) are attached but "
            "investment_feedback_enabled is not set — enable the master gate "
            "or remove the investment_trigger flags; flagged options with the "
            "gate off are a loud error, never a silent ignore (spec D3.2/D6)."
        )
    return enabled and has_specs


def run_simulation(markets: list[CarbonMarket]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not markets:
        raise ValueError("At least one market scenario must be provided.")

    # Lazy imports to avoid circular dependency
    from .wiring import solve_hotelling_path, solve_nash_path, solve_scenario_path

    grouped_markets: dict[str, list[CarbonMarket]] = defaultdict(list)
    for market in markets:
        grouped_markets[market.scenario_name].append(market)

    scenario_summaries: list[dict[str, float | str]] = []
    participant_frames: list[pd.DataFrame] = []

    for scenario_name, scenario_markets in grouped_markets.items():
        ordered_markets = sorted(scenario_markets, key=_market_year_sort_key)
        approach = getattr(ordered_markets[0], "model_approach", "competitive") or "competitive"

        m0 = ordered_markets[0]

        transmission_lambda = getattr(m0, "forward_transmission_lambda", None)
        if transmission_lambda is not None and approach != "competitive":
            logger.warning(
                f"Scenario '{scenario_name}': forward_transmission_lambda is only "
                f"applied under model_approach='competitive' (got '{approach}'); "
                "ignoring the λ blend."
            )
            transmission_lambda = None

        # Endogenous-investment gate (EI-5, docs/invest-feedback-plan.md D2):
        # False on every scenario without BOTH the master flag and attached
        # adoption specs — the guard raises loudly on a half-configured
        # scenario and leaves fully unconfigured ones on the byte-identical
        # legacy path below.
        investment_on = _investment_configured(m0)

        if approach == "all":
            if investment_on:
                raise ValueError(
                    f"Scenario '{scenario_name}': endogenous investment feedback "
                    "is not supported under model_approach='all' — the "
                    "comparison fan-out solves three renamed market lists, not "
                    "one path the adoption loop could wrap. Pick a single "
                    "approach (competitive or banking, spec v1 coverage)."
                )
            # Not routed through _path_solver_for: fans one scenario out over
            # three differently-renamed market lists, not one ordered_markets
            # thread (transmission_lambda is always None here — "all" != the
            # competitive-only gate above always clears it — matching the
            # pre-extraction elif ladder's effective behaviour exactly).
            comp_markets = _rename_markets(ordered_markets, "Competitive")
            hot_markets = _rename_markets(ordered_markets, "Hotelling")
            nash_markets = _rename_markets(ordered_markets, "Nash-Cournot")

            comp_path = solve_scenario_path(comp_markets)
            hot_path = solve_hotelling_path(hot_markets, **_hot_kwargs(m0))
            nash_path = solve_nash_path(nash_markets, **_nash_kwargs(m0))

            for path, mkt_list in [
                (comp_path, comp_markets),
                (hot_path, hot_markets),
                (nash_path, nash_markets),
            ]:
                _collect_path_results(mkt_list, path, scenario_summaries, participant_frames)

        else:
            solver = _path_solver_for(approach, m0, transmission_lambda=transmission_lambda)
            if investment_on:
                # Lazy imports (activation scoping): only an investment-
                # configured scenario loads the feedback host and the
                # endogenous_investment runtime (tests/engine/
                # test_lazy_activation.py).
                from ..features.endogenous_investment.rule import InvestmentRule
                from .feedback import solve_with_investment_feedback

                # Declared config order for the spec D1.4 tie-break:
                # participant order, then per-participant spec (option)
                # order — the InvestmentRule default over this tuple.
                specs = tuple(
                    spec
                    for participant in m0.participants
                    for spec in getattr(participant, "adoption_specs", ())
                )
                r = float(getattr(m0, "discount_rate", 0.04) or 0.04)
                max_iters_raw = getattr(m0, "investment_max_iterations", None)

                def _fresh_rule(specs: tuple = specs, r: float = r) -> InvestmentRule:
                    # Early-bound defaults: a plain closure factory (one
                    # fresh rule per use — the PathFeedback lifecycle
                    # doctrine), immune to loop-variable rebinding.
                    return InvestmentRule(specs, r)

                path = solve_with_investment_feedback(
                    ordered_markets,
                    solver,
                    _fresh_rule,
                    specs,
                    scenario_discount_rate=r,
                    max_iterations=None if max_iters_raw is None else int(max_iters_raw),
                )
            else:
                path = solver(ordered_markets)
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

    summary_df = pd.DataFrame.from_records(scenario_summaries)
    participant_df = pd.concat(participant_frames, ignore_index=True)
    return summary_df, participant_df


def _run_flat_config(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve today's flat (single-market) scenarios — the byte-identical legacy path.

    VERBATIM the pre-D1-3 body of ``run_simulation_from_config``: normalize,
    split plain vs policy-event scenarios, dispatch each. The multi-market
    partition in ``run_simulation_from_config`` only ever hands this function
    scenarios WITHOUT a ``markets`` key, so a config that carries no linked
    scenario reaches this path unchanged (39 goldens bit-identical — the
    legacy branch is untouched).

    Args:
        config: A config whose every scenario is flat (no ``markets`` key).

    Returns:
        ``(summary_df, participant_df)``.
    """
    from ..config_io import normalize_config
    from .events import solve_scenario_with_events

    normalized = normalize_config(deepcopy(config))
    plain = [s for s in normalized["scenarios"] if not s.get("policy_events")]
    evented = [s for s in normalized["scenarios"] if s.get("policy_events")]

    if not evented:
        return run_simulation(build_markets_from_config(normalized))

    frames: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    if plain:
        frames.append(run_simulation(build_markets_from_config({"scenarios": plain})))
    for scenario in evented:
        frames.append(solve_scenario_with_events(scenario))
    return (
        pd.concat([f[0] for f in frames], ignore_index=True),
        pd.concat([f[1] for f in frames], ignore_index=True),
    )


def run_simulation_from_config(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve a config, routing linked (multi-market) scenarios to the DAG solver.

    Partition (D1-3): a scenario carrying a ``markets`` key is a multi-market
    (linked) scenario and is routed to :func:`solve_multi_market_scenario`;
    every other scenario is flat and stays on the byte-identical legacy path
    (:func:`_run_flat_config`). A config with NO markets-shaped scenario — every
    committed golden — is handed WHOLE to ``_run_flat_config``, so the single-
    market path is bit-for-bit unchanged (the multi-market path is only taken by
    a linked config, of which none ship yet).

    Args:
        config: A raw config dict with a ``scenarios`` list.

    Returns:
        ``(summary_df, participant_df)`` — flat results first, then each
        multi-market scenario in declaration order.

    Raises:
        ValueError: ``scenarios`` is not a list; or any downstream validation
            error (link validation, cycle, E7 events-on-multi-market, E8
            horizon).
    """
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("Config must contain a 'scenarios' list.")

    multi = [s for s in scenarios if isinstance(s, dict) and "markets" in s]
    if not multi:
        # No linked scenario: the whole config down the untouched legacy path.
        return _run_flat_config(config)

    flat = [s for s in scenarios if not (isinstance(s, dict) and "markets" in s)]
    frames: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    if flat:
        frames.append(_run_flat_config({"scenarios": flat}))
    for scenario in multi:
        frames.append(solve_multi_market_scenario(scenario))
    return (
        pd.concat([f[0] for f in frames], ignore_index=True),
        pd.concat([f[1] for f in frames], ignore_index=True),
    )


def _build_leg_markets(body: dict, composite_scenario_name: str) -> list[CarbonMarket]:
    """Build one market's ``CarbonMarket`` list under the composite scenario name.

    Wraps the already-normalized market ``body`` back into a single-scenario
    config keyed by the composite grouping name ``"{scenario} :: {market_id}"``
    (the ``_rename_markets`` suffix precedent) and hands it to
    ``build_markets_from_config`` — REUSING the whole builder pipeline (meta
    derivation, per-year construction, investment-spec stamping) rather than
    duplicating it. ``build_markets_from_config`` re-normalizes; the body is
    already normalized and normalization is idempotent (the legacy path already
    double-normalizes: ``normalize_config`` then ``build_markets_from_config``).

    Args:
        body: A normalized market body (from ``iter_market_bodies``).
        composite_scenario_name: ``"{scenario_name} :: {market_id}"``.

    Returns:
        The market's per-year ``CarbonMarket`` objects.
    """
    synthetic = {"scenarios": [{"name": composite_scenario_name, **body, "policy_events": []}]}
    return build_markets_from_config(synthetic)


def _solve_market_leg(
    shifted_markets: list[CarbonMarket], composite_scenario_name: str, market_id: str
) -> tuple[list[CarbonMarket], list[dict]]:
    """Solve ONE market of a chain — mirrors ``run_simulation``'s per-scenario body.

    Runs the SAME per-approach solve ``run_simulation`` runs for a single
    scenario (the ``_path_solver_for`` closure, UNTOUCHED), with the SAME
    investment-feedback wrapping — PER-MARKET, in topological order
    (block-triangular: one-way links make sequential per-market fixed points
    compose exactly to the chain equilibrium, spec §7 E4). ``model_approach
    "all"`` is rejected inside a multi-market scenario (the comparison fan-out
    is not one ``ordered_markets`` thread a link/adoption loop could wrap).

    Args:
        shifted_markets: The market's ``CarbonMarket`` list AFTER inbound-link
            application (link-shifted MACs / break-even thresholds).
        composite_scenario_name: For log/error attribution.
        market_id: For error attribution.

    Returns:
        ``(ordered_markets, path_details)`` — the chronologically sorted
        markets and the solved per-year detail dicts.

    Raises:
        ValueError: ``model_approach`` is ``"all"``; a half-configured
            investment scenario (via ``_investment_configured``); or a solve
            failure propagated from the wrapped path solver.
    """
    ordered_markets = sorted(shifted_markets, key=_market_year_sort_key)
    m0 = ordered_markets[0]
    approach = getattr(m0, "model_approach", "competitive") or "competitive"

    if approach == "all":
        raise ValueError(
            f"Scenario leg '{composite_scenario_name}' (market '{market_id}'): "
            "model_approach 'all' is not permitted inside a multi-market scenario "
            "— the comparison fan-out solves three renamed market lists, not one "
            "linkable/adoptable path. Pick a single approach per market."
        )

    transmission_lambda = getattr(m0, "forward_transmission_lambda", None)
    if transmission_lambda is not None and approach != "competitive":
        logger.warning(
            f"Scenario leg '{composite_scenario_name}': forward_transmission_lambda "
            f"is only applied under model_approach='competitive' (got '{approach}'); "
            "ignoring the λ blend."
        )
        transmission_lambda = None

    investment_on = _investment_configured(m0)
    solver = _path_solver_for(approach, m0, transmission_lambda=transmission_lambda)
    if investment_on:
        # Lazy imports (activation scoping) — identical to run_simulation.
        from ..features.endogenous_investment.rule import InvestmentRule
        from .feedback import solve_with_investment_feedback

        specs = tuple(
            spec
            for participant in m0.participants
            for spec in getattr(participant, "adoption_specs", ())
        )
        r = float(getattr(m0, "discount_rate", 0.04) or 0.04)
        max_iters_raw = getattr(m0, "investment_max_iterations", None)

        def _fresh_rule(specs: tuple = specs, r: float = r) -> InvestmentRule:
            return InvestmentRule(specs, r)

        path = solve_with_investment_feedback(
            ordered_markets,
            solver,
            _fresh_rule,
            specs,
            scenario_discount_rate=r,
            max_iterations=None if max_iters_raw is None else int(max_iters_raw),
        )
    else:
        path = solver(ordered_markets)
    return ordered_markets, path


def _delivered_path(path_details: list[dict]) -> dict[str, float]:
    """Extract ``{year_label: delivered_price}`` from a solved path (the E4 signal)."""
    return {
        str(item["market"].year): float(item["equilibrium"]["price"])
        for item in path_details
    }


def solve_multi_market_scenario(scenario: Mapping[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve one linked (multi-market) scenario as a one-way recursive-PE DAG.

    The D1-3 multi-market dispatch (``docs/platform-spec-d0-d1.md`` §2d, §3, §7):

    1. Guard policy events (E7): events × multi-market is deferred to D2.
    2. Read the normalized market bodies (``iter_market_bodies``) and build the
       ``LinkSpec`` DAG (``engine.links.build_link_specs``).
    3. Enforce the E8 horizon strict-subset per link (at solve entry).
    4. Topologically order the markets (``engine.links.topological_market_order``
       — deterministic; cycle → ValueError, R34).
    5. Solve each market in topological order. BEFORE a market solves, apply its
       inbound links (``engine.links.apply_inbound_links``) reading the FINAL
       delivered paths of its already-solved ancestors — ONCE, before the path
       solve (spec §2d). Investment feedback wraps each market's solve PER
       MARKET (block-triangular, E4).
    6. Collect results under the composite grouping key ``"{scenario} ::
       {market_id}"`` so ``collect_path_results``/summary machinery is
       unmodified; stamp the guarded ``"Market"`` and link-diagnostic columns
       (E6). REPORT in DECLARATION order (spec §3), while SOLVING topologically.

    Args:
        scenario: A raw multi-market scenario dict (``markets``/``links``).

    Returns:
        ``(summary_df, participant_df)`` — rows in declaration order of the
        markets, each summary row carrying the guarded ``"Market"`` column and,
        for a market with inbound links, per-(from,to) ``"Link ... Price In"``
        and per-(from,to,channel) ``"Link ... Input Shift"`` diagnostic columns.

    Raises:
        ValueError: policy events present (E7); a link cycle (R34); an E8
            horizon violation; ``model_approach "all"`` in a market; or any
            link/body validation error.
    """
    from .links import (
        apply_inbound_links,
        build_link_specs,
        check_horizon_alignment,
        topological_market_order,
    )

    scenario_name = str(
        scenario.get("name") or scenario.get("scenario_name") or "Multi-Market Scenario"
    ).strip()

    if scenario.get("policy_events"):
        raise ValueError(
            f"Scenario '{scenario_name}': policy_events on a multi-market scenario "
            "are deferred to D2 (E7) — per-market carriers × link re-application × "
            "cross-market announcement semantics is an open design problem. The "
            "natural first relaxation is events on SINK markets only (no outgoing "
            "links), where the existing splice machinery is already correct; until "
            "then, keep events single-market."
        )

    market_bodies = iter_market_bodies(scenario)
    # Multi-market scenarios always key every body by a non-None market_id (the
    # None key is the degenerate flat case, which the partition never routes
    # here); str() keeps the ids typed for the ordering/link machinery.
    declared_ids = [str(market_id) for market_id, _ in market_bodies]
    bodies_by_id = {str(market_id): body for market_id, body in market_bodies}

    links = build_link_specs(scenario)
    check_horizon_alignment(links, bodies_by_id)
    topo_ids = topological_market_order(declared_ids, links)

    solved_delivered_paths: dict[str, dict[str, float]] = {}
    leg_summaries: dict[str, list[dict]] = {}
    leg_frames: dict[str, list[pd.DataFrame]] = {}

    for market_id in topo_ids:
        composite = f"{scenario_name} :: {market_id}"
        base_markets = _build_leg_markets(bodies_by_id[market_id], composite)
        inbound = [link for link in links if link.to_market == market_id]
        logger.debug(
            "Multi-market solve: market %r, inbound_links=%d, ancestors_solved=%d",
            market_id,
            len(inbound),
            len(solved_delivered_paths),
        )
        shifted = apply_inbound_links(market_id, base_markets, inbound, solved_delivered_paths)
        ordered, path = _solve_market_leg(shifted, composite, market_id)
        solved_delivered_paths[market_id] = _delivered_path(path)

        local_summaries: list[dict] = []
        local_frames: list[pd.DataFrame] = []
        _collect_path_results(ordered, path, local_summaries, local_frames)
        _stamp_multi_market_columns(local_summaries, path, market_id, inbound, solved_delivered_paths)
        leg_summaries[market_id] = local_summaries
        leg_frames[market_id] = local_frames

    # SOLVE topological, REPORT in declaration order (spec §3).
    scenario_summaries: list[dict] = []
    participant_frames: list[pd.DataFrame] = []
    for market_id in declared_ids:
        scenario_summaries.extend(leg_summaries[market_id])
        participant_frames.extend(leg_frames[market_id])

    summary_df = pd.DataFrame.from_records(scenario_summaries)
    participant_df = pd.concat(participant_frames, ignore_index=True)
    return summary_df, participant_df


def _stamp_multi_market_columns(
    summaries: list[dict],
    path_details: list[dict],
    market_id: str,
    inbound_links: list,
    solved_delivered_paths: Mapping[str, Mapping[str, float]],
) -> None:
    """Stamp the guarded ``Market`` + per-link diagnostic columns onto summary rows.

    Multi-market-ONLY, key-presence-guarded (the D3 reporter-conditionality
    precedent — an always-on column fails goldens): ``collect_path_results``
    stays unmodified; these columns are appended to the summary dicts it
    produced (aligned by year — ``summaries`` and ``path_details`` are both in
    path order). E6 exact ASCII strings:

    * ``"Market"`` — the market id (every multi-market row).
    * ``"Link {from}->{to} Price In"`` — the source's delivered ``P_A(t)``, one
      column per ``(from, to)`` pair, deduped (two channels on a pair share it).
    * ``"Link {from}->{to} {channel} Input Shift"`` — ``phi·P_A(t)``, channel-
      qualified so two links on a pair with distinct channels never collide.

    Args:
        summaries: The market's summary rows (mutated in place — columns
            appended at the tail).
        path_details: The market's per-year detail dicts (same order as
            ``summaries``; source of each row's year label).
        market_id: The market id stamped into ``"Market"``.
        inbound_links: The market's inbound ``LinkSpec`` list (empty → only the
            ``"Market"`` column is stamped).
        solved_delivered_paths: ``{market_id: {year: delivered_price}}`` — read
            for each inbound link's source ``P_A(t)``.
    """
    for summary_row, item in zip(summaries, path_details, strict=True):
        summary_row["Market"] = market_id
        year = str(item["market"].year)
        priced_pairs: set[tuple[str, str]] = set()
        for link in inbound_links:
            price_in = float(solved_delivered_paths[link.from_market][year])
            pair = (link.from_market, link.to_market)
            if pair not in priced_pairs:
                summary_row[f"Link {link.from_market}->{link.to_market} Price In"] = price_in
                priced_pairs.add(pair)
            shift_col = f"Link {link.from_market}->{link.to_market} {link.channel} Input Shift"
            summary_row[shift_col] = float(link.phi) * price_in


def run_simulation_from_file(config_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return run_simulation_from_config(load_config(config_path))
