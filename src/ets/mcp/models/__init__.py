"""``python -m ets.mcp.models`` entry-point subpackage for the ets-models server.

Not where the server is implemented — that's ``ets.mcp.models_server``/
``ets.mcp.models_tools`` (flat modules directly under ``ets.mcp``, alongside
``server.py``/``tools.py``, so both MCP servers share one package's
dependency law and ``tests/test_module_isolation.py`` T5 classification with
no extra rule needed). This subpackage exists only so
``python -m ets.mcp.models`` is a valid, distinct module path from
``python -m ets.mcp`` (the composer) — see ``__main__.py``.
"""

from __future__ import annotations

__all__: list[str] = []
