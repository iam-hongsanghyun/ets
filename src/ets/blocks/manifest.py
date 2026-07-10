"""``derive_manifest``: which feature modules a config/model uses.

Powers a model-scoped UI (``GET``/``POST /api/model-manifest``, see
``ets/web/api.py``): given a scenario-config dict, report the block/feature
vocabulary it exercises so the frontend can show only the panels relevant to
that model instead of every block the catalogue knows about.

Design: the manifest is derived from the *compiled block graph*
(:func:`ets.blocks.decompile.graph_from_config`), not from the raw config
directly — every node the decompiler synthesises maps onto exactly one
:class:`~ets.blocks.registry.BlockSpec`, and every ``BlockSpec`` declares
exactly one ``feature``, so ``{node.block for node in graph.nodes}`` mapped
through the catalogue is the whole of the graph-derived signal. This mirrors
``decompile.py``'s documented scope reduction: blocks it never synthesises a
node for (``sector``, ``technology_option``, ``oba`` — round-tripped as
opaque pass-through data rather than drawn nodes, see ``decompile.py``'s
module docstring) are therefore also invisible to graph-derived feature
detection. That is inherited, not new, and is not filled in here — see
:func:`_direct_detectors` below for the one config-shape signal
(``policy_events``) that genuinely has no node representation today.

Dependency law: this module imports only ``ets.blocks`` siblings
(``catalogue``, ``decompile``) and ``ets.config_io`` — never
``ets.engine``/``ets.solvers``. ``blocks/`` stays engine-blind so the
Vercel graph/manifest path never imports a solver (plan §1 clause (g)).
"""

from __future__ import annotations

from typing import Any

from ..config_io import normalize_config
from .catalogue import BLOCK_CATALOGUE
from .decompile import graph_from_config
from .graph import Node

# "all" is a comparison-run shorthand (plan §1 "compare_all"), not a solver
# of its own — it means "solve every deterministic price-formation approach
# for this scenario", which is exactly these three (banking is excluded: it
# requires banking_allowed/borrowing state the other three don't share, and
# is never implied by "all" in config_io/builder.py).
_ALL_APPROACH_EXPANSION: tuple[str, ...] = ("competitive", "hotelling", "nash_cournot")


def _scenario_approach(scenario: dict[str, Any]) -> list[str]:
    """Expand one scenario's ``model_approach`` into its constituent solver ids.

    Args:
        scenario: A normalised scenario dict (``config_io.normalize_scenario``
            output) — must contain ``model_approach``.

    Returns:
        ``["competitive", "hotelling", "nash_cournot"]`` if the scenario's
        ``model_approach`` is ``"all"``; otherwise a single-element list
        holding that approach verbatim (``"competitive"``, ``"banking"``,
        ``"hotelling"``, or ``"nash_cournot"``).
    """
    approach = str(scenario.get("model_approach", "competitive"))
    if approach == "all":
        return list(_ALL_APPROACH_EXPANSION)
    return [approach]


def _direct_detectors(scenarios: list[dict[str, Any]]) -> set[str]:
    """Config-shape feature signals the compiled block graph cannot see.

    THE place to add future non-graph detectors: one clause per detector,
    each keyed off a config-shape predicate that has no node representation
    in :func:`ets.blocks.decompile.graph_from_config` (today: the
    ``policy_events`` timeline — splicing is engine composition, not a
    drawable block, per ``docs/feature-modules-plan.md`` §1 "policy_events
    → engine module"). Do not special-case a detector's result inline in
    :func:`derive_manifest`; add a clause here instead so every non-graph
    signal lives in one auditable place.

    Args:
        scenarios: Normalised scenario dicts to scan (typically either every
            scenario in a config, for the top-level manifest, or a single
            scenario, for its per-scenario breakdown).

    Returns:
        The set of feature names any clause matched.
    """
    detected: set[str] = set()
    if any(scenario.get("policy_events") for scenario in scenarios):
        detected.add("policy_events")
    return detected


def _market_node_ids(nodes: list[Node], market_id: str) -> set[str]:
    """Node ids belonging to one market (``decompile.py``'s ``market{i}`` id
    plus every node id it prefixes, e.g. ``market0_pf``, ``market0_p0``)."""
    prefix = f"{market_id}_"
    return {n.id for n in nodes if n.id == market_id or n.id.startswith(prefix)}


def _features_for_blocks(block_ids: set[str]) -> set[str]:
    return {BLOCK_CATALOGUE.get(block_id).feature for block_id in block_ids}


def derive_manifest(config: dict[str, Any]) -> dict[str, Any]:
    """Derive the block/feature-module manifest of a scenario-config dict.

    Args:
        config: A ``{"scenarios": [...]}`` document (or anything
            ``config_io.normalize_config`` accepts — the same input
            ``ets.blocks.graph_from_config`` takes).

    Returns:
        A dict with:

        * ``features``: sorted list of every feature name in play across
          the whole config, always including ``"core"``.
        * ``blocks``: sorted list of every distinct block id the compiled
          graph uses.
        * ``approach``: sorted list of every price-formation approach any
          scenario resolves to (``"all"`` expanded per
          :func:`_scenario_approach`).
        * ``categories``: ``{category: [block_id, ...]}`` (each block-id
          list sorted), grouping ``blocks`` by
          :attr:`~ets.blocks.registry.BlockSpec.category`.
        * ``scenarios``: ``{scenario_name: {"features": [...],
          "approach": [...]}}`` — the same two keys, scoped to one
          scenario's own nodes.
    """
    normalized = normalize_config(config)
    graph = graph_from_config(normalized)
    blocks = sorted({node.block for node in graph.nodes})

    features = (
        {"core"}
        | _features_for_blocks(set(blocks))
        | _direct_detectors(normalized["scenarios"])
    )

    approach: set[str] = set()
    for scenario in normalized["scenarios"]:
        approach.update(_scenario_approach(scenario))

    categories: dict[str, list[str]] = {}
    for block_id in blocks:
        categories.setdefault(BLOCK_CATALOGUE.get(block_id).category, []).append(block_id)

    scenarios: dict[str, dict[str, Any]] = {}
    for index, scenario in enumerate(normalized["scenarios"]):
        market_node_ids = _market_node_ids(graph.nodes, f"market{index}")
        scenario_block_ids = {n.block for n in graph.nodes if n.id in market_node_ids}
        scenario_features = (
            {"core"}
            | _features_for_blocks(scenario_block_ids)
            | _direct_detectors([scenario])
        )
        scenarios[str(scenario["name"])] = {
            "features": sorted(scenario_features),
            "approach": _scenario_approach(scenario),
        }

    return {
        "features": sorted(features),
        "blocks": blocks,
        "approach": sorted(approach),
        "categories": categories,
        "scenarios": scenarios,
    }
