"""Wire-format serialization for ``BlockSpec``/``ParamSpec``/``PortSpec``.

Shared by every app that hands a block/param/port description to a client —
today ``ets.web`` (``GET /api/blocks``, ``docs/blocks-graph-plan.md`` §5) and
``ets.mcp`` (``list_blocks``/``describe_block``). Kept here, next to the
catalogue it describes, rather than duplicated in each app: the wire shape is
metadata about the catalogue, not transport or engine logic.

Dependency law: this module imports only ``ets.blocks`` siblings
(``registry``) and stdlib.
"""

from __future__ import annotations

from typing import Any

from .registry import BlockRegistry, BlockSpec, ParamSpec


def serialize_param(param: ParamSpec) -> dict[str, Any]:
    """One ``ParamSpec`` -> the wire shape (``docs/blocks-graph-plan.md`` §5).

    Args:
        param: The parameter spec to serialize.

    Returns:
        ``{"name", "type", "default", "unit", "min", "max", "enum",
        "config_key", "scope"}``.
    """
    low, high = param.bounds if param.bounds is not None else (None, None)
    return {
        "name": param.name,
        "type": param.type,
        "default": param.default,
        "unit": param.unit,
        "min": low,
        "max": high,
        "enum": list(param.enum) if param.enum is not None else None,
        "config_key": param.config_key,
        "scope": param.scope,
    }


def serialize_ports(block: BlockSpec) -> dict[str, Any]:
    """One block's ports -> ``{"inputs": [...], "outputs": [...]}``.

    Args:
        block: The block spec whose ports to serialize.
    """
    return {
        "inputs": [
            {"name": port.name, "accepts": [port.kind], "cardinality": port.cardinality}
            for port in block.in_ports()
        ],
        "outputs": [{"name": port.name, "type": port.kind} for port in block.out_ports()],
    }


def serialize_constraints(block: BlockSpec) -> list[dict[str, str]]:
    """One block's ``requires``/``excludes`` -> a flat constraint list."""
    constraints = [{"kind": "requires", "block": other} for other in block.requires]
    constraints += [{"kind": "excludes", "block": other} for other in block.excludes]
    return constraints


def serialize_block(block: BlockSpec) -> dict[str, Any]:
    """One ``BlockSpec`` -> the full palette/param-form wire shape.

    Args:
        block: The block spec to serialize.

    Returns:
        ``{"id", "label", "category", "doc", "params", "ports", "constraints"}``.
    """
    return {
        "id": block.id,
        "label": block.label,
        "category": block.category,
        "doc": block.doc,
        "params": [serialize_param(p) for p in block.params],
        "ports": serialize_ports(block),
        "constraints": serialize_constraints(block),
    }


def serialize_catalogue(
    catalogue: BlockRegistry, *, category: str | None = None
) -> list[dict[str, Any]]:
    """Every block in ``catalogue`` (optionally filtered), serialized.

    Args:
        catalogue: The block registry to serialize (usually
            ``ets.blocks.BLOCK_CATALOGUE``).
        category: If given, only blocks whose ``category`` matches are
            included (e.g. ``"policy"``); ``None`` returns every block.

    Returns:
        A list of :func:`serialize_block` dicts, catalogue order preserved.
    """
    blocks = catalogue if category is None else catalogue.by_category(category)
    return [serialize_block(block) for block in blocks]
