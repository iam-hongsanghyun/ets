from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path

import pandas as pd

from ..core.expectations import (
    build_expectation_specs,
    derive_expected_prices,
    expectation_sort_key,
)
from ..core.market import CarbonMarket
from ..core.protocols import CapRule
from .msr import MSRCapRule, MSRState
from .ccr import CCRCapRule, CCRState
from ..config_io import build_markets_from_config, load_config

logger = logging.getLogger(__name__)


def _market_year_sort_key(market: CarbonMarket) -> tuple[float, str]:
    return expectation_sort_key(market.year)


def solve_scenario_path(
    ordered_markets: list[CarbonMarket],
    max_iterations: int | None = None,
    tolerance: float | None = None,
) -> list[dict]:
    # Use solver settings from the first market if not explicitly supplied
    if max_iterations is None:
        max_iterations = int(getattr(ordered_markets[0], "solver_competitive_max_iters", 25) or 25)
    if tolerance is None:
        tolerance = float(getattr(ordered_markets[0], "solver_competitive_tolerance", 1e-3) or 1e-3)
    if not ordered_markets:
        return []

    ordered_years = [str(market.year) for market in ordered_markets]
    baseline_prices = {
        str(market.year): market.find_equilibrium_price() for market in ordered_markets
    }
    expectation_specs = build_expectation_specs(ordered_markets)

    expected_prices = derive_expected_prices(
        ordered_years,
        expectation_specs,
        baseline_prices,
    )

    if any(spec.rule == "perfect_foresight" for spec in expectation_specs.values()):
        for _ in range(max_iterations):
            realized_prices = _simulate_realized_prices(
                ordered_markets,
                expected_prices,
            )
            updated_expected_prices = derive_expected_prices(
                ordered_years,
                expectation_specs,
                baseline_prices,
                realized_prices=realized_prices,
            )
            max_delta = max(
                abs(updated_expected_prices[year] - expected_prices.get(year, 0.0))
                for year in ordered_years
            )
            expected_prices = updated_expected_prices
            if max_delta <= tolerance:
                break

    msr_state = MSRState() if getattr(ordered_markets[0], "msr_enabled", False) else None
    ccr_state = CCRState() if getattr(ordered_markets[0], "ccr_enabled", False) else None
    return _simulate_path_details(
        ordered_markets, expected_prices, msr_state=msr_state, ccr_state=ccr_state
    )


def _simulate_realized_prices(
    ordered_markets: list[CarbonMarket],
    expected_prices: dict[str, float],
) -> dict[str, float]:
    # MSR / CCR are NOT applied in the inner convergence loop (prices only):
    # perfect-foresight expectations are formed on the RULE-FREE path (R29,
    # docs/blocks-composition-rules.md), hence the explicit empty rule list.
    details = _simulate_path_details(ordered_markets, expected_prices, cap_rules=())
    return {
        str(item["market"].year): float(item["equilibrium"]["price"])
        for item in details
    }


def _simulate_path_details(
    ordered_markets: list[CarbonMarket],
    expected_prices: dict[str, float],
    msr_state: MSRState | None = None,
    ccr_state: CCRState | None = None,
    cap_rules: Sequence[CapRule] | None = None,
) -> list[dict]:
    """Simulate the competitive per-year path with injected cap rules.

    Supply operators (``CapRule``: CCR, MSR) act BEFORE each year's clearing
    and read only beginning-of-year state; after clearing they record
    realised aggregates as the next year's lagged signal (split gating —
    see ``ets.core.protocols.CapRule``). Composition is additive in list
    order (F1): ``effective_carry += delta_q_i``, CCR before MSR.

    Args:
        ordered_markets: Markets sorted chronologically.
        expected_prices: Year label → expected future price [currency/tCO2].
        msr_state: LEGACY kwarg — translated internally to ``MSRCapRule``.
            Mutually exclusive with ``cap_rules``.
        ccr_state: LEGACY kwarg — translated internally to ``CCRCapRule``.
            Mutually exclusive with ``cap_rules``.
        cap_rules: Cap rules applied in list order. ``None`` (default)
            triggers the legacy translation: ``[CCRCapRule(ccr_state),
            MSRCapRule(msr_state)]`` from whichever states are given —
            preserving the wiring-literal order (CCR before MSR). Pass an
            empty sequence for an explicitly rule-free path.

    Returns:
        One details dict per year (market, equilibrium, participant frame,
        and the MSR/CCR diagnostics keys in their pinned order).
    """
    if cap_rules is None:
        # Legacy-kwarg translation: state objects become injected rules in
        # the fixed wiring-literal order (CCR before MSR, F1).
        rules: list[CapRule] = []
        if ccr_state is not None:
            rules.append(CCRCapRule(ccr_state))
        if msr_state is not None:
            rules.append(MSRCapRule(msr_state))
        cap_rules = rules
    elif msr_state is not None or ccr_state is not None:
        raise ValueError(
            "Pass either cap_rules or the legacy msr_state=/ccr_state= "
            "kwargs, not both."
        )

    bank_balances = {
        participant.name: 0.0 for participant in ordered_markets[0].participants
    }
    carry_forward_allowances = 0.0
    details: list[dict] = []

    for market in ordered_markets:
        expected_future_price = float(expected_prices.get(str(market.year), 0.0))
        starting_bank_balances = dict(bank_balances)

        # ── Supply operators: cap rules adjust supply before clearing ─────
        # Zero-valued defaults in the pinned key order of the details dict
        # (golden baselines are column-order-sensitive).
        diagnostics: dict[str, float] = {
            "msr_withheld": 0.0,
            "msr_released": 0.0,
            "msr_pool": 0.0,
            "ccr_adjustment": 0.0,
            "ccr_emissions_deviation": 0.0,
            "ccr_cost_deviation": 0.0,
        }
        # Additive composition in wiring-literal order (CCR before MSR):
        #   Q_t = Qbar + ΔQ_t^CCR + ΔQ_t^MSR   (F1 fix, blocks-composition-rules §0)
        # Rules read only beginning-of-year state (previous bank; their own
        # lagged aggregates), never same-year outcomes.
        effective_carry = carry_forward_allowances
        for rule in cap_rules:
            delta_q, rule_diagnostics = rule.pre_clear(market, bank_balances)
            effective_carry += delta_q
            diagnostics.update(rule_diagnostics)

        equilibrium = market.solve_equilibrium(
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
            carry_forward_in=effective_carry,
        )
        equilibrium_price = float(equilibrium["price"])
        participant_df = market.participant_results(
            equilibrium_price,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        )
        details.append(
            {
                "market": market,
                "expected_future_price": expected_future_price,
                "starting_bank_balances": starting_bank_balances,
                "equilibrium": equilibrium,
                "participant_df": participant_df,
                "msr_withheld": diagnostics["msr_withheld"],
                "msr_released": diagnostics["msr_released"],
                "msr_pool": diagnostics["msr_pool"],
                "ccr_adjustment": diagnostics["ccr_adjustment"],
                "ccr_emissions_deviation": diagnostics["ccr_emissions_deviation"],
                "ccr_cost_deviation": diagnostics["ccr_cost_deviation"],
            }
        )

        # ── Post-clearing: rules record realised aggregates as the lagged
        # signal (flag-only gating — pre-start years accumulate history).
        for rule in cap_rules:
            rule.post_clear(market, participant_df)

        carry_forward_allowances = (
            float(equilibrium["unsold_allowances"])
            if market.unsold_treatment == "carry_forward"
            else 0.0
        )
        bank_balances = {
            str(row["Participant"]): float(row["Ending Bank Balance"])
            for _, row in participant_df.iterrows()
        }

    return details


def _collect_path_results(
    ordered_markets: list[CarbonMarket],
    path_details: list[dict],
    scenario_summaries: list,
    participant_frames: list,
) -> None:
    """Append results from a solved path into the accumulator lists."""
    for item in path_details:
        market = item["market"]
        expected_future_price = item["expected_future_price"]
        equilibrium = item["equilibrium"]
        equilibrium_price = float(equilibrium["price"])
        participant_df = item["participant_df"]
        summary = market.scenario_summary(
            equilibrium_price,
            expected_future_price=expected_future_price,
            auction_outcome=equilibrium,
            participant_df=participant_df,
        )
        # Patch in MSR stats from the simulation step
        summary["MSR Withheld"] = float(item.get("msr_withheld", 0.0))
        summary["MSR Released"] = float(item.get("msr_released", 0.0))
        summary["MSR Reserve Pool"] = float(item.get("msr_pool", 0.0))
        # Patch in CCR stats from the simulation step
        summary["CCR Cap Adjustment"] = float(item.get("ccr_adjustment", 0.0))
        summary["CCR Emissions Deviation"] = float(
            item.get("ccr_emissions_deviation", 0.0)
        )
        summary["CCR Cost Deviation"] = float(item.get("ccr_cost_deviation", 0.0))
        # Patch in banking-equilibrium diagnostics when present
        if "banking_aggregate_bank" in item:
            summary["Banking Aggregate Bank"] = float(item["banking_aggregate_bank"])
            summary["Banking Regime"] = str(item["banking_regime"])
            summary["Banking Window Start"] = int(item["banking_window_start"])
            summary["Banking Window End"] = int(item["banking_window_end"])
            summary["Banking Floor Cancelled"] = float(
                item["banking_floor_cancelled"]
            )
        # Patch in forward-transmission (λ-blend) diagnostics when present
        if "transmission_lambda" in item:
            summary["Forward Transmission Lambda"] = float(item["transmission_lambda"])
            summary["Static Component Price"] = float(item["static_component_price"])
            summary["Hotelling Component Price"] = float(
                item["hotelling_component_price"]
            )
            summary["Reserve Floor Price"] = float(item["reserve_floor_price"])
        scenario_summaries.append(summary)
        participant_frames.append(participant_df)


def _rename_markets(markets: list[CarbonMarket], suffix: str) -> list[CarbonMarket]:
    """Return shallow copies of markets with scenario_name suffixed."""
    renamed = []
    for m in markets:
        copy = deepcopy(m)
        copy.scenario_name = f"{m.scenario_name} [{suffix}]"
        renamed.append(copy)
    return renamed


def run_simulation(markets: list[CarbonMarket]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not markets:
        raise ValueError("At least one market scenario must be provided.")

    # Lazy imports to avoid circular dependency
    from .hotelling import solve_hotelling_path
    from .nash import solve_nash_path

    grouped_markets: dict[str, list[CarbonMarket]] = defaultdict(list)
    for market in markets:
        grouped_markets[market.scenario_name].append(market)

    scenario_summaries: list[dict[str, float | str]] = []
    participant_frames: list[pd.DataFrame] = []

    for scenario_name, scenario_markets in grouped_markets.items():
        ordered_markets = sorted(scenario_markets, key=_market_year_sort_key)
        approach = getattr(ordered_markets[0], "model_approach", "competitive") or "competitive"

        m0 = ordered_markets[0]

        def _hot_kwargs():
            return dict(
                discount_rate=float(getattr(m0, "discount_rate", 0.04) or 0.04),
                risk_premium=float(getattr(m0, "risk_premium", 0.0) or 0.0),
                max_bisection_iters=int(getattr(m0, "solver_hotelling_max_bisection_iters", 80) or 80),
                max_lambda_expansions=int(getattr(m0, "solver_hotelling_max_lambda_expansions", 20) or 20),
                convergence_tol=float(getattr(m0, "solver_hotelling_convergence_tol", 1e-4) or 1e-4),
            )

        def _nash_kwargs():
            return dict(
                strategic_participants=list(getattr(m0, "nash_strategic_participants", None) or []) or None,
                price_step=float(getattr(m0, "solver_nash_price_step", 0.5) or 0.5),
                max_iters=int(getattr(m0, "solver_nash_max_iters", 120) or 120),
                convergence_tol=float(getattr(m0, "solver_nash_convergence_tol", 1e-3) or 1e-3),
            )

        transmission_lambda = getattr(m0, "forward_transmission_lambda", None)
        if transmission_lambda is not None and approach != "competitive":
            logger.warning(
                f"Scenario '{scenario_name}': forward_transmission_lambda is only "
                f"applied under model_approach='competitive' (got '{approach}'); "
                "ignoring the λ blend."
            )
            transmission_lambda = None

        if transmission_lambda is not None:
            from .transmission import solve_transmission_path

            path = solve_transmission_path(
                ordered_markets, lam=float(transmission_lambda), **_hot_kwargs()
            )
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

        elif approach == "banking":
            from .banking import solve_banking_path

            path = solve_banking_path(
                ordered_markets,
                discount_rate=float(getattr(m0, "discount_rate", 0.055) or 0.055),
                risk_premium=float(getattr(m0, "risk_premium", 0.0) or 0.0),
            )
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

        elif approach == "hotelling":
            path = solve_hotelling_path(ordered_markets, **_hot_kwargs())
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

        elif approach == "nash_cournot":
            path = solve_nash_path(ordered_markets, **_nash_kwargs())
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

        elif approach == "all":
            comp_markets = _rename_markets(ordered_markets, "Competitive")
            hot_markets  = _rename_markets(ordered_markets, "Hotelling")
            nash_markets = _rename_markets(ordered_markets, "Nash-Cournot")

            comp_path = solve_scenario_path(comp_markets)
            hot_path  = solve_hotelling_path(hot_markets, **_hot_kwargs())
            nash_path = solve_nash_path(nash_markets, **_nash_kwargs())

            for path, mkt_list in [(comp_path, comp_markets), (hot_path, hot_markets), (nash_path, nash_markets)]:
                _collect_path_results(mkt_list, path, scenario_summaries, participant_frames)

        else:
            # Default: competitive (MSR handled inside solve_scenario_path)
            path = solve_scenario_path(ordered_markets)
            _collect_path_results(ordered_markets, path, scenario_summaries, participant_frames)

    summary_df = pd.DataFrame.from_records(scenario_summaries)
    participant_df = pd.concat(participant_frames, ignore_index=True)
    return summary_df, participant_df


def run_simulation_from_config(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
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


def run_simulation_from_file(config_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return run_simulation_from_config(load_config(config_path))
