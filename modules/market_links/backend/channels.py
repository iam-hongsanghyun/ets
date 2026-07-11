r"""market_links runtime door — the two v1 ``LinkChannel`` channels (T2 runtime).

Pure link-application math for D1 (``docs/platform-plan-d0-d1.md`` D1-2;
binding economic spec ``docs/platform-spec-d0-d1.md`` §2). Each channel is a
``core.protocols.LinkChannel`` implementation that writes ONE field family of
a downstream market B from the SOLVED delivered price path of an upstream
market A, applying the additive-linear rule (spec §2a):

    x_B(t) = x_B_base(t) + phi * P_A(t)      (contemporaneous, spec §2c)

Both channels are PURE and COPY-ON-WRITE (spec §2d, F4 purity): they NEVER
mutate ``target_markets`` or anything reachable from it. Changed markets /
participants / technology options / adoption specs are fresh copies
(``copy.copy`` on the mutable dataclasses + ``dataclasses.replace`` on the
frozen leaves ``TechnologyOption`` / ``AdoptionSpec``); untouched objects
pass through BY IDENTITY, and a call with nothing to shift returns the SAME
input list object (the ``features.endogenous_investment.vintage`` /
``PathFeedback.apply`` copy-on-write identity precedent).

This module is the RUNTIME door: it imports ONLY ``pe.core.*`` (the T2->T0
edge the AST ratchet permits) and stdlib, and is reachable only from the
engine's ``LINK_CHANNELS`` registry (``engine/wiring.py``), never from
``config_io`` — which sees only the ``plugin`` door.

References:
    docs/platform-spec-d0-d1.md §2a (additive-linear only), §2b (channels:
    mac_cost fields + cost_slope dimensional exclusion; invest_break_even
    compilation), §2c (contemporaneous), §2d (placement/purity), §7 E8
    (horizon strict-subset).
    docs/platform-plan-d0-d1.md D1-2.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from ...core.costs import piecewise_abatement_factory

if TYPE_CHECKING:
    from ...core.market.model import CarbonMarket
    from ...core.participant.models import MarketParticipant
    from ...core.protocols import LinkSpec

__all__ = ["InvestBreakEvenChannel", "MacCostChannel"]

_WILDCARD = "*"


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────


def _source_price(
    source_price_path: Mapping[str, float], year: str | None, link: LinkSpec
) -> float:
    """Read the contemporaneous source price ``P_A(t)`` at a target year.

    Args:
        source_price_path: Source market A's solved delivered price by year
            label [currency_A/unit_A].
        year: The target market's own year label ``t`` (same year, not
            lagged — spec §2c).
        link: The link (for error attribution only).

    Returns:
        ``P_A(t)`` [currency_A/unit_A].

    Raises:
        ValueError: The target year is missing from the source path (spec §7
            E8 strict-subset: every target year must exist in the source's
            solved path), or the market carries no year label.
    """
    if year is None:
        raise ValueError(
            f"Link {link.from_market}->{link.to_market}: a target market has no year "
            "label — a linked market's years must be declared to read P_A(t)."
        )
    if year not in source_price_path:
        raise ValueError(
            f"Link {link.from_market}->{link.to_market}: source price path has no "
            f"entry for target year {year!r} — every target year must exist in the "
            f"source's solved path (spec §7 E8 strict-subset). Known source years: "
            f"{sorted(source_price_path)}."
        )
    return float(source_price_path[year])


def _matches_participant(link: LinkSpec, participant_name: str) -> bool:
    """Return whether a participant is targeted (explicit name or ``"*"`` wildcard)."""
    return _WILDCARD in link.target_participants or participant_name in link.target_participants


def _rebuild_market(
    market: CarbonMarket, replacements: dict[int, MarketParticipant]
) -> CarbonMarket:
    """Shallow-copy a market and swap in the replaced participants (copy-on-write).

    Mirrors ``features.endogenous_investment.vintage``: ``copy.copy`` the
    market, rebuild only the ``participants`` list from ``replacements``, and
    leave every other attribute (and every untouched participant) shared by
    identity.

    Args:
        market: The input market (never mutated).
        replacements: Index -> replacement participant for the changed
            participants only.

    Returns:
        A fresh market with the replacements applied.
    """
    market_clone = copy.copy(market)
    market_clone.participants = [replacements.get(i, p) for i, p in enumerate(market.participants)]
    return market_clone


# ──────────────────────────────────────────────────────────────────────────────
# Channel 1 — mac_cost (spec §2b, ranked first)
# ──────────────────────────────────────────────────────────────────────────────


def _shift_mac(mac: Any, shift: float, link: LinkSpec, where: str) -> Any:
    r"""Return a MAC representation shifted by an additive price ``shift``.

    Applies ``x -> x + shift`` to the technology option's marginal-abatement
    cost, dispatching on its representation (``core.costs`` /
    ``config_io.builder``):

    * a plain ``float`` — the THRESHOLD MAC level (``threshold_cost``):
      returns ``mac + shift``;
    * a callable carrying ``mac_blocks`` — PIECEWISE: rebuilds the callable
      (``piecewise_abatement_factory``) with every block's ``marginal_cost``
      shifted by the same ``shift`` (order-preserving, so the factory's
      non-decreasing-cost invariant survives);
    * a callable carrying ``cost_slope`` — LINEAR: DIMENSIONALLY EXCLUDED
      (``cost_slope`` [currency/t per Mt] is a slope, not a price level,
      spec §2b). The ``plugin`` door already rejects a ``mac_cost`` link
      targeting a linear option; this is the defensive backstop the work
      order requires — an ``AssertionError``, never a silent shift.

    Args:
        mac: The option's ``marginal_abatement_cost`` (float or callable).
        shift: The additive price shift ``phi * P_A(t)`` [currency/t].
        link: The link (for error attribution).
        where: ``"participant/technology"`` for error attribution.

    Returns:
        The shifted MAC (a new float, or a freshly built piecewise callable).

    Raises:
        AssertionError: ``mac`` is a linear callable (``cost_slope``) — the
            channel must never see it (spec §2b); or a callable of an
            unrecognised cost model.
    """
    if callable(mac):
        if hasattr(mac, "cost_slope"):
            raise AssertionError(
                f"Link {link.from_market}->{link.to_market}: mac_cost reached a "
                f"linear-abatement option ({where}) — cost_slope [currency/t per Mt] "
                "is a slope, dimensionally excluded from an additive price-LEVEL "
                "shift (spec §2b); the plugin door must have rejected this."
            )
        blocks = getattr(mac, "mac_blocks", None)
        if blocks is None:
            raise AssertionError(
                f"Link {link.from_market}->{link.to_market}: mac_cost reached a "
                f"callable MAC of an unrecognised cost model ({where}) — expected a "
                "piecewise callable carrying mac_blocks."
            )
        shifted_blocks = [
            {"amount": block["amount"], "marginal_cost": block["marginal_cost"] + shift}
            for block in blocks
        ]
        return piecewise_abatement_factory(shifted_blocks)
    return float(mac) + shift


class MacCostChannel:
    r"""Additive shift on targeted technologies' MAC price levels (spec §2b).

    The v1 rank-1 channel. For every targeted participant (an explicit name
    in ``link.target_participants``, or ALL of them when the list is the
    wildcard ``("*",)``) and every targeted technology option (name in
    ``link.target_technologies``), shifts the option's marginal-abatement
    cost by ``phi * P_A(t)`` at the option's market year ``t``:

    Algorithm:
        LaTeX:
        $$ c_j^{\mathrm{blk}}(t) \mapsto c_j^{\mathrm{blk}}(t) + \phi\,P_A(t),
           \qquad \theta_j(t) \mapsto \theta_j(t) + \phi\,P_A(t) $$

        ASCII fallback:
            piecewise:  each mac_blocks[k].marginal_cost += phi * P_A(t)
            threshold:  marginal_abatement_cost (the level) += phi * P_A(t)

        Symbols (units):
            c_j_blk(t) : a piecewise block's marginal_cost of option j  [currency/t]
            theta_j(t) : a threshold option j's MAC level               [currency/t]
            phi        : link coefficient, sign-free                    [units_B per units_A]
            P_A(t)     : source A's delivered price at year t           [currency_A/unit_A]

    The linear ``cost_slope`` is dimensionally EXCLUDED and never shifted
    (spec §2b) — the plugin door rejects such a link; ``_shift_mac`` asserts
    defensively as a backstop. Pure copy-on-write: shifted options are new
    ``TechnologyOption`` values (``dataclasses.replace``), their participant
    a shallow copy, its market a shallow copy; everything else shared by
    identity, and a no-match call returns the input list itself.
    """

    def apply(
        self,
        link: LinkSpec,
        source_price_path: Mapping[str, float],
        target_markets: list[CarbonMarket],
    ) -> list[CarbonMarket]:
        """Apply the additive MAC shift to the target markets (see class docstring)."""
        if not target_markets:
            return target_markets
        want_techs = frozenset(link.target_technologies)
        # Defensive: the plugin door REQUIRES target_technologies for mac_cost
        # (spec §6); a channel must never be handed an empty target set.
        assert want_techs, (
            f"Link {link.from_market}->{link.to_market}: mac_cost requires a non-empty "
            "target_technologies (spec §6) — the plugin door must have enforced it."
        )

        result: list[CarbonMarket] = []
        changed_any = False
        for market in target_markets:
            shift = link.phi * _source_price(source_price_path, market.year, link)
            replacements: dict[int, MarketParticipant] = {}
            for index, participant in enumerate(market.participants):
                if not _matches_participant(link, participant.name):
                    continue
                options = participant.technology_options or []
                new_options = list(options)
                option_changed = False
                for opt_index, option in enumerate(options):
                    if option.name not in want_techs:
                        continue
                    new_mac = _shift_mac(
                        option.marginal_abatement_cost,
                        shift,
                        link,
                        f"{participant.name}/{option.name}",
                    )
                    new_options[opt_index] = replace(option, marginal_abatement_cost=new_mac)
                    option_changed = True
                if option_changed:
                    clone = copy.copy(participant)
                    clone.technology_options = new_options
                    replacements[index] = clone
            if replacements:
                changed_any = True
                result.append(_rebuild_market(market, replacements))
            else:
                result.append(market)
        if not changed_any:
            return target_markets
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Channel 2 — invest_break_even (spec §2b, ranked second — the K-MSR loop)
# ──────────────────────────────────────────────────────────────────────────────


def _compile_break_even(
    base: float | Mapping[str, float], shift_by_year: Mapping[str, float], link: LinkSpec
) -> dict[str, float]:
    r"""Compile a break-even threshold into a per-year map with the additive shift.

    Reuses the ``AdoptionSpec.break_even`` semantics
    (``features.endogenous_investment``): the threshold is scalar OR a
    ``{year label: value}`` map (spec §2b).

    * scalar ``base`` -> ``{year: base + phi*P_A(year)}`` for EVERY scenario
      year present in ``shift_by_year`` (the K-MSR input-price-endogenous
      threshold: a constant θ base plus the contemporaneous input price);
    * ``{year: value}`` map -> ``{year: value + phi*P_A(year)}`` per year
      already in the map.

    Args:
        base: The existing ``break_even`` (scalar or ``{year: value}``).
        shift_by_year: ``{year: phi * P_A(year)}`` over the target years.
        link: The link (for error attribution).

    Returns:
        The compiled ``{year: base + phi*P_A(year)}`` mapping.

    Raises:
        ValueError: A map-base year is absent from ``shift_by_year`` (its
            price is unknown — spec §7 E8 strict-subset).
    """
    if isinstance(base, Mapping):
        compiled: dict[str, float] = {}
        for year, value in base.items():
            if year not in shift_by_year:
                raise ValueError(
                    f"Link {link.from_market}->{link.to_market}: break_even names "
                    f"year {year!r} with no source price — every threshold year must "
                    "exist in the source's solved path (spec §7 E8 strict-subset)."
                )
            compiled[year] = float(value) + shift_by_year[year]
        return compiled
    return {year: float(base) + shift for year, shift in shift_by_year.items()}


class InvestBreakEvenChannel:
    r"""Compile targeted adoption specs' break-even into an input-price-endogenous map.

    The v1 rank-2 channel — closes the K-MSR input-price-endogenous threshold
    loop (spec §2b): the downstream investment trigger's break-even price is
    the constant base PLUS the contemporaneous upstream input price. For every
    targeted participant (explicit name or the ``("*",)`` wildcard) and every
    targeted ``AdoptionSpec`` (its ``technology_name`` in
    ``link.target_technologies``, or EVERY spec when ``target_technologies``
    is empty — it is optional for this channel, spec §6), rewrites
    ``break_even``:

    Algorithm:
        LaTeX:
        $$ \theta_j(t) \;=\; \theta_j^{\mathrm{base}} \;+\; \phi\,P_A(t)
           \quad \forall\, t $$

        ASCII fallback:
            scalar base : break_even -> {t: base + phi * P_A(t)} for all t
            {t: v} map  : break_even -> {t: v   + phi * P_A(t)} per year t

        Symbols (units):
            theta_j(t)     : compiled break-even threshold of option j  [currency/t]
            theta_j_base   : the scalar (or per-year) base threshold     [currency/t]
            phi            : link coefficient (e.g. 30 kgH2/tCO2)        [units_B per units_A]
            P_A(t)         : source A's delivered price at year t         [currency_A/unit_A]

    The per-year shift map is built ONCE across all target markets' years, so
    the SAME compiled mapping is stamped on the matching spec in every year's
    participant copy (the threshold is evaluated at the adoption year, spec
    D2.1). Pure copy-on-write: rewritten specs are new ``AdoptionSpec`` values
    (``dataclasses.replace``), their participant a shallow copy, its market a
    shallow copy; everything else shared by identity; a no-match call returns
    the input list itself.
    """

    def apply(
        self,
        link: LinkSpec,
        source_price_path: Mapping[str, float],
        target_markets: list[CarbonMarket],
    ) -> list[CarbonMarket]:
        """Compile the break-even thresholds of the target markets (see class docstring)."""
        if not target_markets:
            return target_markets
        want_techs = frozenset(link.target_technologies)  # empty => every spec

        # Build the per-year shift map ONCE across all target years, so the
        # compiled {year: base + phi*P_A(year)} mapping is identical wherever a
        # matching spec is stamped (specs recur across per-year participant copies).
        shift_by_year = {
            market.year: link.phi * _source_price(source_price_path, market.year, link)
            for market in target_markets
        }

        result: list[CarbonMarket] = []
        changed_any = False
        for market in target_markets:
            replacements: dict[int, MarketParticipant] = {}
            for index, participant in enumerate(market.participants):
                if not _matches_participant(link, participant.name):
                    continue
                specs = participant.adoption_specs
                if not specs:
                    continue
                new_specs = list(specs)
                spec_changed = False
                for spec_index, spec in enumerate(specs):
                    if want_techs and spec.technology_name not in want_techs:
                        continue
                    new_break_even = _compile_break_even(spec.break_even, shift_by_year, link)
                    new_specs[spec_index] = replace(spec, break_even=new_break_even)
                    spec_changed = True
                if spec_changed:
                    clone = copy.copy(participant)
                    clone.adoption_specs = tuple(new_specs)
                    replacements[index] = clone
            if replacements:
                changed_any = True
                result.append(_rebuild_market(market, replacements))
            else:
                result.append(market)
        if not changed_any:
            return target_markets
        return result
