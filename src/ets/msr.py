# Backward-compatibility shim — re-exports from solvers.msr.
# New location: src/ets/solvers/msr.py.
import warnings

from .solvers.msr import MSRState, MSR_DEFAULTS

warnings.warn(
    "ets.msr is deprecated; import from ets.solvers.msr instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MSRState", "MSR_DEFAULTS"]
