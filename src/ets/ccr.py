# Backward-compatibility shim — re-exports from solvers.ccr.
# Logic lives in src/ets/solvers/ccr.py.
from .solvers.ccr import CCRState, CCR_DEFAULTS

__all__ = ["CCRState", "CCR_DEFAULTS"]
