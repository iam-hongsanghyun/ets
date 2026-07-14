"""The pe-config server: model authoring + deployment settings.

The configuration MCP app. Two halves under one server:

* **authoring** — the composer surface (``pe.mcp.tools``): hold a
  conversational block graph and build a scenario turn by turn
  (``new_graph``/``add_block``/``set_params``/``check``/``save_model``).
* **settings** — the deployment surface (``pe.mcp.settings_tools``): read the
  ``PE_*`` environment variables that pick the model-registry backend and
  where it lives (read-only; secrets redacted).

Together these are "everything that configures the platform" — what a model
is, and where models live. The counterpart pe-run server *operates* the
models this server produces; the pe-modules server is the per-feature expert.

Package layout: ``server.py`` builds the FastMCP server from the shared
stateless tool modules (``pe.mcp.tools`` + ``pe.mcp.settings_tools``);
``__main__.py`` is the ``python -m pe.mcp.config`` stdio entry point. T5 by
the ``pe.mcp.*`` prefix (``tests/test_module_isolation.py``); registered in
the repo-root ``.mcp.json`` as ``pe-config``.
"""

from __future__ import annotations

__all__: list[str] = []
