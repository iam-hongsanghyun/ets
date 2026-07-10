# Backward-compatibility shim — the policy-event splicer moved to
# engine/events.py in the engine work order (v1 O8 / v2 O12,
# docs/feature-modules-plan.md). DeprecationWarning arms in the app-tier
# tidy order (v1 O13 / v2 O17, milestone 0.3.0).

from ..engine.events import solve_scenario_with_events, validate_policy_events

__all__ = [
    "solve_scenario_with_events",
    "validate_policy_events",
]
