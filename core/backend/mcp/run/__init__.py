"""The pe-run server: model operation + post-processing analysis.

The running/analysis MCP app. Two halves under one server:

* **operation** — the governor surface (``pe.mcp.models_tools``): list,
  inspect, run, compare, sweep, and rename/delete registry entries. It never
  edits a model's internals (that's the pe-config server's job).
* **analysis** — the post-processing surface (``pe.mcp.analysis_tools``,
  wrapping ``pe.analysis``): multi-axis batch sweeps, plain-language
  narrative, CSV import, the Dixit–Pindyck investment trigger, and forward/
  inverse calibration.

Package layout: ``server.py`` builds the FastMCP server from the shared
stateless tool modules (``pe.mcp.models_tools`` + ``pe.mcp.analysis_tools``);
``__main__.py`` is the ``python -m pe.mcp.run`` stdio entry point. T5 by the
``pe.mcp.*`` prefix (``tests/test_module_isolation.py``); registered in the
repo-root ``.mcp.json`` as ``pe-run``.
"""

from __future__ import annotations

__all__: list[str] = []
