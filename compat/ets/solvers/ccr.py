# Backward-compatibility shim — the CCR runtime moved to features/ccr/
# (state.py / rules.py) in the engine work order (v1 O8 / v2 O12,
# docs/feature-modules-plan.md); the defaults re-export from core.defaults
# (O1) stays.
import warnings

from pe.core.defaults import CCR_DEFAULTS
from pe.features.ccr.rules import CCRCapRule
from pe.features.ccr.state import CCRState

warnings.warn(
    "ets.solvers.ccr is deprecated; import from pe.features.ccr "
    "(defaults: pe.core.defaults). Removal milestone: 0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CCRCapRule",
    "CCRState",
    "CCR_DEFAULTS",
]
