"""Competitive path solver + compat re-exports of the moved engine/ledger names.

Since the engine work order (v1 O8 / v2 O12, ``docs/feature-modules-plan.md``)
this module keeps ONLY the competitive path solver (``solve_scenario_path``
and its perfect-foresight helper ``_simulate_realized_prices``) until the
competitive feature move (v1 O10 / v2 O14). Everything else is a re-export:

* ``run_simulation``, ``_rename_markets``, ``run_simulation_from_config``,
  ``run_simulation_from_file`` → ``ets.engine.dispatch`` (v1 O8 / v2 O12);
* ``_simulate_path_details``, ``_collect_path_results``,
  ``_market_year_sort_key`` → ``ets.core.ledger`` public names (v1 O7 /
  v2 O11).

DeprecationWarning arms in the app-tier tidy order (v1 O13 / v2 O17,
milestone 0.3.0).
"""

from __future__ import annotations

import logging

from ..core.expectations import (
    build_expectation_specs,
    derive_expected_prices,
)
from ..core.market import CarbonMarket

# The path-details ledger moved to core/ledger.py in the ledger work order
# (v1 O7 / v2 O11, docs/feature-modules-plan.md) under public names; the
# underscore names are re-exported so this module's surface is unchanged
# until the solvers compat surface retires.
from ..core.ledger import (
    collect_path_results as _collect_path_results,  # noqa: F401
    market_year_sort_key as _market_year_sort_key,  # noqa: F401
    simulate_path_details as _simulate_path_details,
)

# The dispatch tier moved to engine/dispatch.py in the engine work order
# (v1 O8 / v2 O12); re-exported so this module's surface is unchanged.
# No import cycle: engine.dispatch imports THIS module's
# solve_scenario_path lazily (function-level), never at module level.
from ..engine.dispatch import (  # noqa: F401
    _rename_markets,
    run_simulation,
    run_simulation_from_config,
    run_simulation_from_file,
)

logger = logging.getLogger(__name__)


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

    # Default cap rules come from the engine wiring literal (v1 O8 / v2 O12):
    # identical composition to the retired legacy-kwarg translation (CCR
    # before MSR, each rule iff its m0 enable flag — equivalence pinned by
    # tests/test_cap_rule_injection.py). Lazy import, exactly as
    # engine/events.py does, to avoid the solvers → engine → solvers cycle.
    from ..engine.wiring import default_cap_rules

    return _simulate_path_details(
        ordered_markets,
        expected_prices,
        cap_rules=default_cap_rules(ordered_markets[0], "competitive"),
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
