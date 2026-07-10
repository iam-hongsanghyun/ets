"""MSR feature (T2) — Market Stability Reserve state, rules, and decree.

Two-door layout (``docs/feature-modules-plan.md`` PLAN v2): ``plugin.py`` is
the config door (summary-placeholder reporter + the ``RESERVE_CARRIER``
splice declaration); the runtime modules are ``state.py`` (``MSRState``),
``rules.py`` (``MSRCapRule``, ``ThresholdMSRSupplyRule``), and ``decree.py``
(``decree_msr_action``, ``DecreeSupplyRule``) — moved from ``solvers/msr.py``
in the engine work order (v1 O8 / v2 O12) and wired exclusively by
``ets.engine``. ``ets/solvers/msr.py`` remains as a re-export shim.

This ``__init__`` is the feature's deliberate public surface.
"""

from .decree import DecreeSupplyRule, decree_msr_action
from .rules import MSRCapRule, ThresholdMSRSupplyRule
from .state import MSRState

__all__ = [
    "DecreeSupplyRule",
    "MSRCapRule",
    "MSRState",
    "ThresholdMSRSupplyRule",
    "decree_msr_action",
]
