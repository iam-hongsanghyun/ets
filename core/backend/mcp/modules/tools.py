"""Stateless tool implementations behind the pe-modules factory server.

A uniform per-feature-module surface, built once over every module in
``pe.mcp.modules.registry``:

* ``list_modules`` — the module roster (blocks, categories, doc/params counts).
* ``describe_module`` — a module's block descriptors (params, defaults, units,
  bounds, enums, requires/excludes) plus its ``doc/reference.md`` mechanism
  text — the per-feature "explain" surface.
* ``configure_module`` — add/configure one of a module's blocks onto a
  composer graph, reusing the config server's ``add_block`` (so the wiring
  rules are identical); the "configure into a graph" surface.
* ``run_module_scoped`` — run a registered model and report just this module's
  own output columns (bank path, MSR reserve, CCR adjustment, ...); the
  "run/analyze scoped" surface.

These functions are plain and side-effect-free (``configure_module`` mutates
only the graph dict it is handed and returns a new one; nothing is held
server-side), imported directly by ``pe.mcp.modules.server`` (wrapped as MCP
tools) and by ``tests/apps/mcp/test_mcp_modules.py`` (exercised directly, no
MCP transport involved).

Dependency law: same as any T5 app — imports ``pe.blocks``, and reuses the
sibling ``pe.mcp.tools``/``pe.mcp.models_tools`` implementations rather than
duplicating graph-mutation or run logic.
"""

from __future__ import annotations

from typing import Any

from ...blocks.serialize import serialize_block
from .. import models_tools, tools
from .registry import ModuleInfo, get_module, module_registry


def _module_summary(info: ModuleInfo) -> dict[str, Any]:
    """One roster row for ``list_modules`` (no heavy param/doc payload)."""
    return {
        "name": info.name,
        "block_ids": list(info.block_ids),
        "categories": sorted({b.category for b in info.blocks}),
        "docs": [b.doc for b in info.blocks],
        "has_reference": info.doc_path is not None,
        "scoped_columns": list(info.scoped_columns),
    }


def list_modules() -> dict[str, Any]:
    """List every feature module this server exposes.

    Returns:
        ``{"modules": [{"name", "block_ids", "categories", "docs",
        "has_reference", "scoped_columns"}, ...]}`` — one row per module, in
        catalogue order. ``docs`` is the one-line description of each of the
        module's blocks; ``has_reference`` says whether ``describe_module``
        will return a full mechanism doc; ``scoped_columns`` lists the
        compact-result keys ``run_module_scoped`` will report for it (empty
        when the module has no dedicated output column).
    """
    return {"modules": [_module_summary(info) for info in module_registry().values()]}


def _read_reference(info: ModuleInfo) -> str | None:
    """Return the module's ``doc/reference.md`` text, or ``None`` if it has none."""
    if info.doc_path is None:
        return None
    return info.doc_path.read_text(encoding="utf-8")


def describe_module(module: str) -> dict[str, Any]:
    """Describe one module: its blocks, their params, and its mechanism doc.

    The per-feature "explain" surface. Every param carries its declared
    default, unit, bounds, and enum (from the block catalogue), so an
    assistant can propose economically meaningful values without guessing.

    Args:
        module: A feature-module name (see ``list_modules``).

    Returns:
        ``{"name", "blocks": [<serialize_block>, ...], "scoped_columns",
        "reference"}`` — ``blocks`` is the full catalogue descriptor for each
        of the module's blocks (params/ports/requires/excludes);
        ``reference`` is the module's ``doc/reference.md`` text, or ``None``
        if it ships none.

    Raises:
        ValueError: ``module`` is not a known module.
    """
    try:
        info = get_module(module)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    return {
        "name": info.name,
        "blocks": [serialize_block(b) for b in info.blocks],
        "scoped_columns": list(info.scoped_columns),
        "reference": _read_reference(info),
    }


def configure_module(
    graph: dict[str, Any],
    module: str,
    params: dict[str, Any] | None = None,
    block_id: str | None = None,
    target_market: str | None = None,
) -> dict[str, Any]:
    """Add/configure one of a module's blocks onto a composer graph.

    The "configure into a graph" surface. This is a thin, feature-scoped
    wrapper over the config server's ``add_block`` — it validates that
    ``block_id`` actually belongs to ``module`` and then delegates, so the
    auto-wiring and validation are byte-for-byte identical to composing the
    same block on the config server.

    Args:
        graph: Current graph document (``Graph.to_dict()`` shape) to add to.
        module: A feature-module name (see ``list_modules``).
        params: Initial param values for the new node (see ``describe_module``
            for each param's name/type/default/unit).
        block_id: Which of the module's blocks to add. Required only when the
            module owns more than one block; inferred when it owns exactly one.
        target_market: Which ``carbon_market`` node to wire into (required
            only when the graph has more than one market).

    Returns:
        ``{"graph", "node_id", "issues", "notes", "module", "block_id"}`` —
        the config server's ``add_block`` result, tagged with the module and
        the block actually added.

    Raises:
        ValueError: Unknown ``module``; a ``block_id`` that isn't one of the
            module's blocks; or an ambiguous choice (module owns >1 block and
            ``block_id`` was omitted).
    """
    try:
        info = get_module(module)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc

    if block_id is None:
        if len(info.block_ids) != 1:
            raise ValueError(
                f"Module '{module}' owns {len(info.block_ids)} blocks "
                f"({list(info.block_ids)}); pass block_id=<one of them>."
            )
        block_id = info.block_ids[0]
    elif block_id not in info.block_ids:
        raise ValueError(
            f"Block '{block_id}' is not part of module '{module}' "
            f"(its blocks: {list(info.block_ids)})."
        )

    result = tools.add_block(graph, block_id, params=params, target_market=target_market)
    return {**result, "module": module, "block_id": block_id}


def run_module_scoped(model_id: str, module: str, scenario: str | None = None) -> dict[str, Any]:
    """Run a registered model and report just this module's own output columns.

    The "run/analyze scoped" surface. Runs the model via the run server's
    ``run_model`` and projects each year onto the module's scoped compact
    columns (the bank path for banking, the reserve pool for MSR, ...),
    dropping the shared price/abatement headline to focus on this feature's
    effect.

    Args:
        model_id: An example stem or registry ``"user_<slug>"`` id.
        module: A feature-module name (see ``list_modules``).
        scenario: If given, only that scenario's results are returned.

    Returns:
        ``{"model_id", "module", "scoped_columns", "active", "scenarios":
        {name: {"years": [{"year", <scoped keys present>}, ...]}}}``. ``active``
        is ``False`` when none of the module's scoped columns appear in the run
        (the feature was disabled or produced only neutral values), in which
        case ``years`` carries just the ``year`` label. A module with no
        declared scoped columns reports ``active`` ``False`` with an empty
        ``scoped_columns`` — use the run server's ``run_model`` for its price
        effect.

    Raises:
        ValueError: ``module`` is not a known module.
        ModelStoreError: ``model_id`` matches no known model.
    """
    try:
        info = get_module(module)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc

    run = models_tools.run_model(model_id, scenario=scenario)
    scoped = set(info.scoped_columns)
    present: set[str] = set()
    scenarios: dict[str, Any] = {}
    for name, payload in run["scenarios"].items():
        years = []
        for year in payload.get("years", []):
            row = {"year": year.get("year")}
            for key in info.scoped_columns:
                if key in year:
                    row[key] = year[key]
                    present.add(key)
            years.append(row)
        scenarios[name] = {"years": years}

    return {
        "model_id": model_id,
        "module": module,
        "scoped_columns": list(info.scoped_columns),
        "active": bool(scoped and present),
        "scenarios": scenarios,
    }
