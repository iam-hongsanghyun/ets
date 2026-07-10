# Backward-compatibility shim — re-exports from solvers.hotelling.
# New location: src/ets/solvers/hotelling.py.
import warnings

from .solvers.hotelling import solve_hotelling_path

warnings.warn(
    "ets.hotelling is deprecated; import from ets.solvers.hotelling instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["solve_hotelling_path"]
