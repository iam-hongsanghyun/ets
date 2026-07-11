"""Multi-market scenario accessor (D1-1 schema layer).

``docs/platform-plan-d0-d1.md`` D1's COMPAT RULE, verbatim: "a scenario
WITHOUT markets normalizes down the byte-identical legacy path; the flat
shape REMAINS the canonical normalized form for single-market scenarios
(markets view is derived via ``config_io.iter_market_bodies(scenario)`` ->
``[(None, scenario)]`` degenerate)." This module is that one accessor.

Dependency law (``tests/test_module_isolation.py`` clause (e)): this module
is T1 (``pe.config_io``) — it may import ``pe.core.*`` freely and exactly
one feature door, ``pe.features.market_links.plugin`` (the link
field/structural validator), and nothing else outside its own tier.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..features.market_links.plugin import validate_links
from .builder import _normalize_market_body, normalize_scenario

__all__ = ["iter_market_bodies"]


def iter_market_bodies(scenario: Mapping[str, Any]) -> list[tuple[str | None, dict[str, Any]]]:
    """Iterate a scenario's market bodies, normalized, market_id-keyed.

    The uniform reader D1-3's engine will use to build markets regardless of
    scenario shape — see the module docstring's COMPAT RULE quote.

    Degenerate case (no ``markets`` key): today's single-market scenario,
    normalized via :func:`normalize_scenario` exactly as it always has
    been — the flat shape stays the canonical normalized form (D1 COMPAT
    RULE; this is what keeps all 39 goldens bit-identical). Returns
    ``[(None, normalized_scenario)]``.

    Multi-market case (a ``markets`` key present): each ``markets[i]``
    entry is normalized via :func:`~.builder._normalize_market_body` — the
    SAME per-market internals :func:`normalize_scenario` itself calls, so a
    market body normalizes identically whether it arrives flat or inside a
    ``markets`` list (no duplicated logic). ``market_id`` is required,
    non-empty, and unique across the list. Every ``links`` entry (default
    ``[]``, spec §6) is validated through
    ``pe.features.market_links.plugin.validate_links`` (the plugin-door
    contract) — field/structural validation and the price_unit-touching
    check only; nothing here applies a link, solves a market, or checks
    graph structure (DAG-ness is R34, D1-4). Returns
    ``[(market_id, normalized_body), ...]`` in declaration order.

    Note: :func:`normalize_scenario` itself LOUDLY REJECTS a
    ``markets``-shaped scenario (the D1-1 interim safety rail — see
    ``builder._MARKETS_KEY_GUARD_MESSAGE``) until D1-4 wires the engine/
    blocks; this function is the one sanctioned reader of that shape until
    then.

    Args:
        scenario: A raw (not yet normalized) scenario dict — either
            today's flat single-market shape, or the D1 ``markets``/
            ``links`` shape (docs/platform-spec-d0-d1.md §6).

    Returns:
        Market bodies keyed by market id (``None`` for the degenerate
        single-market case), in declaration order.

    Raises:
        ValueError: An empty/malformed ``markets`` list; a missing,
            empty, or duplicate ``market_id``; any per-market body
            validation error (:func:`~.builder._normalize_market_body`);
            or any link validation error
            (``pe.features.market_links.plugin.validate_links``).
    """
    if "markets" not in scenario:
        return [(None, normalize_scenario(dict(scenario)))]

    raw_markets = scenario.get("markets")
    if not isinstance(raw_markets, list) or not raw_markets:
        raise ValueError("Scenario 'markets' must be a non-empty list.")

    bodies: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, raw_market in enumerate(raw_markets):
        if not isinstance(raw_market, dict):
            raise ValueError(f"Scenario markets[{index}] must be an object.")
        market_id = str(raw_market.get("market_id", "")).strip()
        if not market_id:
            raise ValueError(f"Scenario markets[{index}] must have a non-empty 'market_id'.")
        if market_id in bodies:
            raise ValueError(f"Scenario markets contains duplicate market_id '{market_id}'.")
        bodies[market_id] = _normalize_market_body(raw_market, label=f"Market '{market_id}'")
        order.append(market_id)

    raw_links = scenario.get("links") or []
    validate_links(raw_links, bodies)

    return [(market_id, bodies[market_id]) for market_id in order]
