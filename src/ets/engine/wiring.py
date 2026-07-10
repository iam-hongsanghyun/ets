"""Default rule wiring (T3): today's exact per-approach defaults, as reviewed literals.

The TRANSITIONAL default factory-builders moved here from the solver hosts in
the engine work order (v1 O8 / v2 O12, ``docs/feature-modules-plan.md``):
``default_supply_rule_factories`` and ``default_friction`` verbatim from
``solvers/banking.py``; ``default_cap_rules`` expresses the per-approach
cap-rule composition the hosts construct today. The engine wires FACTORIES,
never shared instances (``ets.core.protocols`` lifecycle doctrine): every
call of a ``default_*`` builder returns fresh rule instances or zero-argument
constructors, so no rule state can leak between scenarios, solver
invocations, or fixed-point iterations.

F2 FREEZE (binding): the per-approach variants below reproduce the
documented MSR/CCR inconsistencies of the current solvers EXACTLY
(``docs/blocks-composition-rules.md`` F2, R8, R9, R16; economist item 5d).
Harmonising any of them is a math change requiring economist sign-off and
new golden baselines — out of scope for every migration order.

Also home (transitionally) to the feature-class re-exports the LEGACY
banking host consumes via lazy import (``HoardingInflow``,
``DeliveredFloor``, ``FloorCancellationRule``) — the engine is the sole
importer of the feature tier, so ``solvers/banking.py`` reaches feature
classes only through this module until its own feature move (v1 O9 /
v2 O13).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..features.ccr import CCRCapRule
from ..features.hoarding.plugin import HoardingInflow
from ..features.msr import DecreeSupplyRule, MSRCapRule, ThresholdMSRSupplyRule
from ..features.price_controls.plugin import DeliveredFloor
from ..features.price_controls.rules import FloorCancellationRule

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core.market.model import CarbonMarket
    from ..core.protocols import CapRule, Friction, SupplyRuleFactory

__all__ = [
    "DeliveredFloor",
    "FloorCancellationRule",
    "HoardingInflow",
    "default_cap_rules",
    "default_floor_rule_factory",
    "default_friction",
    "default_supply_rule_factories",
]


def default_cap_rules(m0: CarbonMarket, approach: str) -> list[CapRule]:
    """Today's exact per-approach cap-rule wiring from ``m0``'s enable flags.

    Each call constructs FRESH rule instances — the call itself is the
    factory invocation (factories, never shared instances;
    ``ets.core.protocols``). Composition order within an approach is the
    reviewed wiring literal: CCR before MSR (F1).

    Args:
        m0: First market of the chronologically sorted scenario path.
        approach: The scenario's ``model_approach``.

    Returns:
        Cap rules in application order (possibly empty).
    """
    rules: list[CapRule] = []

    if approach == "competitive":
        # Competitive path: CCR before MSR (F1 wiring-literal order), each
        # rule attached iff its m0 enable flag; both rules then re-read
        # their per-year enable flag AND start-year gate inside pre_clear
        # (per-year-gated MSR + CCR). Identical composition to the retired
        # legacy-kwarg translation — equivalence pinned by
        # tests/test_cap_rule_injection.py.
        if bool(getattr(m0, "ccr_enabled", False)):
            rules.append(CCRCapRule())
        if bool(getattr(m0, "msr_enabled", False)):
            rules.append(MSRCapRule())
        return rules

    if approach == "hotelling":
        # F2 FREEZE (docs/blocks-composition-rules.md F2, R8, R9 — DO NOT
        # HARMONISE without economist sign-off and new golden baselines):
        # the PRIMARY Hotelling path applies neither rule (its result rows
        # hardcode msr_* = 0.0; R8 — MSR + Hotelling cannot coexist), and
        # the CCR is competitive-only (R9). This branch reproduces the
        # COMPETITIVE-FALLBACK wiring only (solvers/hotelling.py
        # ``_competitive_fallback``): a per-year-gated MSR iff
        # m0.msr_enabled, and NEVER a CCR — even when ccr_enabled is set.
        if bool(getattr(m0, "msr_enabled", False)):
            rules.append(MSRCapRule())
        return rules

    if approach == "nash_cournot":
        # F2 FREEZE (docs/blocks-composition-rules.md F2, R9, R16): the
        # Nash path's MSR is NOT a CapRule — solvers/nash.py applies a raw
        # MSRState inline, UNGATED (msr_start_year is ignored, R16) and
        # with its own literal getattr fallbacks; it never constructs a
        # CCR (R9). Faking it here as a (start-year-gated) MSRCapRule
        # would silently change solved numbers, so the Nash path keeps its
        # own inline wiring until its feature move (v1 O11 / v2 O15)
        # injects the duck-typed MSR state bit-for-bit.
        return rules

    # banking composes SupplyRules inside its fixed point (see
    # default_supply_rule_factories); "all" fans out to the three
    # sub-approaches, each of which wires itself.
    return rules


def default_supply_rule_factories(m0: CarbonMarket) -> list[SupplyRuleFactory]:
    """Today's exact supply-rule wiring, derived from ``m0``'s ``msr_*`` flags.

    Moved VERBATIM from ``solvers/banking.py:_default_supply_rule_factories``
    (v1 O8 / v2 O12); the banking host keeps a thin compat delegate until its
    own feature move (v1 O9 / v2 O13).

    Mode dispatch is if/elif — a scenario gets EITHER the decree rule
    (``msr_mode`` in {``price_band``, ``surplus_rule``, ``hybrid``}) OR the
    bank-threshold rule, never both; ``msr_initial_reserve_mt`` funds ONLY
    the decree rule (R7, ``docs/blocks-composition-rules.md``).

    Args:
        m0: First market of the chronologically sorted scenario path.

    Returns:
        Zero or one ``SupplyRuleFactory`` in a list (empty when the MSR is
        disabled).
    """
    if not bool(getattr(m0, "msr_enabled", False)):
        return []
    msr_mode = str(getattr(m0, "msr_mode", "bank_threshold") or "bank_threshold")
    # The banking path reads msr_start_year from the FIRST market only
    # (scenario-level, m0-only start-year gate), while the competitive
    # path's MSRCapRule re-reads it per year. Documented F2-family
    # inconsistency (economist item 5d, docs/feature-modules-plan.md) —
    # DO NOT HARMONISE without economist sign-off and new golden baselines.
    msr_start = float(getattr(m0, "msr_start_year", 0.0) or 0.0)
    if msr_mode != "bank_threshold":
        initial_reserve = float(getattr(m0, "msr_initial_reserve_mt", 0.0) or 0.0)
        return [
            lambda: DecreeSupplyRule(
                mode=msr_mode,
                initial_reserve_mt=initial_reserve,
                start_year=msr_start,
            )
        ]
    return [lambda: ThresholdMSRSupplyRule(start_year=msr_start)]


def default_friction(ordered_markets: list[CarbonMarket]) -> Friction | None:
    """Today's exact hoarding wiring: the feature's reader when configured.

    Moved VERBATIM from ``solvers/banking.py:_default_friction`` (v1 O8 /
    v2 O12); the banking host keeps a thin compat delegate until its own
    feature move (v1 O9 / v2 O13). The gate expresses the wiring intent (the
    hoarding feature attaches only when a scenario configures it); ``None``
    is behaviour-identical to an attached reader on unconfigured markets,
    since ``HoardingInflow.inflow`` is 0.0 without ``hoarding_inflow``
    fields.

    Args:
        ordered_markets: Markets sorted chronologically.

    Returns:
        The hoarding ``Friction`` when any year has ``hoarding_inflow > 0``,
        else ``None`` (neutral).
    """
    if any(
        float(getattr(m, "hoarding_inflow", 0.0) or 0.0) > 0.0 for m in ordered_markets
    ):
        return HoardingInflow()
    return None


def default_floor_rule_factory() -> Callable[[], FloorCancellationRule]:
    """Today's exact floor-cancellation default: the rule class as its own factory.

    ``solvers/banking.py`` defaulted ``floor_rule_factory`` to the
    ``FloorCancellationRule`` class itself (attach-always is exact — the
    rule returns the supply unchanged when no floor binds); this builder
    hands the same class to the host's dedicated slot.

    Returns:
        A zero-argument constructor of a fresh floor-cancellation rule per
        schedule evaluation.
    """
    return FloorCancellationRule
