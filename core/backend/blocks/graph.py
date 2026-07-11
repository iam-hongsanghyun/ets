"""``Graph``/``Node``/``Edge`` dataclasses and JSON (de)serialisation.

Mirrors the wire schema in ``docs/blocks-graph-plan.md`` §2:

.. code-block:: json

    {
      "version": 1,
      "nodes": [{"id": "...", "block": "...", "params": {...}}],
      "edges": [{"source": "...", "sourcePort": "...",
                 "target": "...", "targetPort": "..."}],
      "meta": {"canvas": {}}
    }

``meta.canvas`` (positions, zoom, ...) is opaque to the backend and round-trips
verbatim — nothing in this package reads or writes its contents.

Dependency law: this module imports stdlib only. It parses *graph* JSON, a
document type distinct from ``config_io``'s scenario-config JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

GRAPH_VERSION = 1


@dataclass
class Node:
    """One block instance on the canvas.

    Args:
        id: Unique node id within the graph.
        block: Block id (must resolve in ``BLOCK_CATALOGUE``).
        params: Raw param values, keyed by ``ParamSpec.name``. A value may be
            a plain scalar/list/dict (applied uniformly across market years)
            or ``{"__per_year__": {year_label: value}}`` — a per-year
            override map (see ``ets.blocks.compile``).
    """

    id: str
    block: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "block": self.block, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        node_id = data.get("id")
        block = data.get("block")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Every node must have a non-empty string 'id'.")
        if not isinstance(block, str) or not block:
            raise ValueError(f"Node '{node_id}' must have a non-empty string 'block'.")
        params = data.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"Node '{node_id}' params must be an object.")
        return cls(id=node_id, block=block, params=dict(params))


@dataclass
class Edge:
    """One directed connection between two node ports.

    Args:
        source: Source node id.
        source_port: Port name on the source node's ``out`` ports.
        target: Target node id.
        target_port: Port name on the target node's ``in`` ports.
    """

    source: str
    source_port: str
    target: str
    target_port: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "sourcePort": self.source_port,
            "target": self.target,
            "targetPort": self.target_port,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        try:
            return cls(
                source=str(data["source"]),
                source_port=str(data["sourcePort"]),
                target=str(data["target"]),
                target_port=str(data["targetPort"]),
            )
        except KeyError as exc:
            raise ValueError(f"Edge missing required field: {exc}") from exc


@dataclass
class Graph:
    """A drawn block graph: nodes, edges, and opaque canvas metadata.

    Args:
        nodes: All nodes on the canvas.
        edges: All edges connecting them.
        meta: Opaque frontend metadata (``{"canvas": {...}}``), round-tripped
            verbatim.
        version: Wire schema version.
    """

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    version: int = GRAPH_VERSION

    def node(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def edges_into(self, node_id: str, port: str | None = None) -> list[Edge]:
        return [
            e for e in self.edges
            if e.target == node_id and (port is None or e.target_port == port)
        ]

    def edges_from(self, node_id: str, port: str | None = None) -> list[Edge]:
        return [
            e for e in self.edges
            if e.source == node_id and (port is None or e.source_port == port)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "meta": dict(self.meta),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Graph":
        if not isinstance(data, dict):
            raise ValueError("Graph document must be a JSON object.")
        nodes_raw = data.get("nodes") or []
        edges_raw = data.get("edges") or []
        if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
            raise ValueError("Graph 'nodes' and 'edges' must be arrays.")
        nodes = [Node.from_dict(n) for n in nodes_raw]
        edges = [Edge.from_dict(e) for e in edges_raw]
        seen_ids: set[str] = set()
        for n in nodes:
            if n.id in seen_ids:
                raise ValueError(f"Duplicate node id: '{n.id}'")
            seen_ids.add(n.id)
        meta = data.get("meta") or {}
        if not isinstance(meta, dict):
            raise ValueError("Graph 'meta' must be an object.")
        version = int(data.get("version") or GRAPH_VERSION)
        return cls(nodes=nodes, edges=edges, meta=dict(meta), version=version)

    @classmethod
    def from_json(cls, text: str) -> "Graph":
        return cls.from_dict(json.loads(text))
