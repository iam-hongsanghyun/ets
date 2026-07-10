"""AI-guided ETS model composer, exposed as an MCP (Model Context Protocol) server.

A T5 app, same tier as ``ets.web``/``ets.cli`` (``tests/test_module_isolation.py``):
it wires the same block-graph primitives ``ets.web``'s composer endpoints use
(``ets.blocks``, ``ets.model_store``, ``ets.engine``) up as MCP tools instead
of HTTP routes, so an AI assistant can hold a conversation with a user and
build a scenario graph turn by turn.

Package layout:

* ``tools.py`` — the stateless tool implementations (importable and testable
  directly, with no MCP transport involved).
* ``suggestions.py`` — the rule -> plain-language-suggestion table behind the
  ``check`` tool's ``next_steps``.
* ``compact.py`` — the compact per-scenario/per-year result shape
  ``run_model`` returns.
* ``server.py`` — the FastMCP server that registers ``tools.py``'s functions
  and holds the server-level ``instructions`` playbook.
* ``__main__.py`` — ``python -m ets.mcp`` entry point (stdio transport).

Install: the ``mcp`` optional-dependency group (``uv sync --extra mcp`` or
``--all-extras``). Registration: the repo-root ``.mcp.json``.
"""

from __future__ import annotations

__all__: list[str] = []
