"""CCR feature (T2) — the Benmir-Roman-Taschini carbon cap rule.

Two-door layout (``docs/feature-modules-plan.md`` PLAN v2): ``plugin.py`` is
the config door (summary-placeholder reporter); the runtime modules are
``state.py`` (``CCRState``) and ``rules.py`` (``CCRCapRule``) — moved from
``solvers/ccr.py`` in the engine work order (v1 O8 / v2 O12) and wired
exclusively by ``ets.engine``. ``ets/solvers/ccr.py`` remains as a
re-export shim.

This ``__init__`` is the feature's deliberate public surface.
"""

from .rules import CCRCapRule
from .state import CCRState

__all__ = [
    "CCRCapRule",
    "CCRState",
]
