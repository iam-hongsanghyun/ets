# Backward-compatibility shim — re-exports from solvers.ccr.
# New location: src/ets/solvers/ccr.py.
import warnings

from .solvers.ccr import CCRState, CCR_DEFAULTS

warnings.warn(
    "ets.ccr is deprecated; import from ets.solvers.ccr instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CCRState", "CCR_DEFAULTS"]
