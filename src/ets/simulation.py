# Backward-compatibility shim — re-exports from solvers.simulation.
# New location: src/ets/solvers/simulation.py.
import warnings

from .solvers.simulation import (
    solve_scenario_path,
    run_simulation,
    run_simulation_from_config,
    run_simulation_from_file,
    _simulate_path_details,
    _simulate_realized_prices,
    _collect_path_results,
    _rename_markets,
    _market_year_sort_key,
)

warnings.warn(
    "ets.simulation is deprecated; import from ets.solvers.simulation instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "solve_scenario_path",
    "run_simulation",
    "run_simulation_from_config",
    "run_simulation_from_file",
    "_simulate_path_details",
    "_simulate_realized_prices",
    "_collect_path_results",
    "_rename_markets",
    "_market_year_sort_key",
]
