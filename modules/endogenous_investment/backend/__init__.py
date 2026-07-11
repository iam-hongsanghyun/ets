"""endogenous_investment feature (T2) — adoption feedback around the full path solve.

Two-door layout (``docs/feature-modules-plan.md`` PLAN v2): ``plugin.py``
is the config door (``normalize_investment_trigger``,
``attach_adoption_specs`` — the sanctioned ``adoption_specs`` writer — and
the ``ADOPTION_CARRIER`` splice declaration); the runtime modules are
``rule.py`` (``InvestmentRule``, the ``core.protocols.PathFeedback``
implementation) and ``vintage.py`` (``apply_adoption_state``, per-year
availability gating), wired exclusively by the engine's outer feedback
loop (``engine/feedback.py``, EI-5).

This ``__init__`` is the feature's deliberate public surface, resolved
LAZILY (PEP 562 ``__getattr__``, the ``features.msr`` precedent):
``config_io`` imports this feature's ``plugin`` door unconditionally once
EI-6 lands, and importing ANY submodule of a package always runs the
package's ``__init__.py`` first — an eager ``rule``/``vintage`` import
here would force-load the investment RUNTIME for every scenario,
flagged or not, breaking the off-by-default proof chain ("feedback module
never imported", plan "Off-by-default proof chain").

References:
    docs/invest-feedback-spec.md D1-D3, D6.
    docs/invest-feedback-plan.md — "Feature module".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .plugin import (
        ADOPTION_CARRIER as ADOPTION_CARRIER,
        attach_adoption_specs as attach_adoption_specs,
        normalize_investment_trigger as normalize_investment_trigger,
    )
    from .rule import InvestmentRule as InvestmentRule
    from .vintage import apply_adoption_state as apply_adoption_state

__all__ = [
    "ADOPTION_CARRIER",
    "InvestmentRule",
    "apply_adoption_state",
    "attach_adoption_specs",
    "normalize_investment_trigger",
]


def __getattr__(name: str) -> object:
    """Lazily resolve this feature's public names on first access (PEP 562).

    Args:
        name: Attribute requested on the ``ets.features.endogenous_investment``
            package.

    Returns:
        The resolved class, function, or carrier declaration.

    Raises:
        AttributeError: ``name`` is not one of this feature's public names.
    """
    if name in {"ADOPTION_CARRIER", "attach_adoption_specs", "normalize_investment_trigger"}:
        from . import plugin

        return getattr(plugin, name)
    if name == "InvestmentRule":
        from .rule import InvestmentRule

        return InvestmentRule
    if name == "apply_adoption_state":
        from .vintage import apply_adoption_state

        return apply_adoption_state
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
