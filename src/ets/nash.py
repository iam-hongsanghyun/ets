# Backward-compatibility shim — re-exports from solvers.nash.
# New location: src/ets/solvers/nash.py.
import warnings

from .solvers.nash import solve_nash_path

warnings.warn(
    "ets.nash is deprecated; import from ets.solvers.nash instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["solve_nash_path"]
