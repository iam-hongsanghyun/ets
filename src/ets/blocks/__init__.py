"""GUI-composability block graph: metadata + a deterministic compiler.

Public surface (deliberate — no underscore exports):

* ``BLOCK_CATALOGUE`` — every drawable block (``registry``/``catalogue``).
* ``Graph``, ``Node``, ``Edge`` — the graph document type (``graph``).
* ``validate_graph`` — structural validation, rules R1-R32 (``validate``).
* ``compile_graph`` — graph -> scenario-config dict (``compile``).
* ``graph_from_config`` — scenario-config dict -> graph (``decompile``).

Dependency law: this package imports only ``ets.config_io`` and stdlib —
never ``ets.web``, never ``ets.solvers``, never ``ets.market``/``ets.participant``.
Running a compiled config is the caller's job.
"""

from __future__ import annotations

from .catalogue import BLOCK_CATALOGUE
from .compile import CompileError, compile_graph
from .decompile import graph_from_config
from .graph import Edge, Graph, Node
from .validate import ValidationIssue, validate_graph

__all__ = [
    "BLOCK_CATALOGUE",
    "compile_graph",
    "CompileError",
    "validate_graph",
    "ValidationIssue",
    "graph_from_config",
    "Graph",
    "Node",
    "Edge",
]
