"""The pe-modules factory server: one uniform surface per feature module.

The third MCP app (alongside pe-config and pe-run), and the only *factory*
one: instead of a hand-written server per module, it derives the module roster
from the block catalogue (:mod:`pe.mcp.modules.registry`) and stamps a uniform
per-module surface — describe / configure / run-scoped / doc-resource — over
every ``modules/<name>/`` feature.

Package layout (mirrors the flat servers' split):

* ``registry.py`` — the catalogue-derived ``{name: ModuleInfo}`` factory input
  (blocks, doc path, scoped summary columns per module).
* ``tools.py`` — the stateless tool implementations (importable and testable
  directly), reusing ``pe.mcp.tools``/``pe.mcp.models_tools`` for graph
  mutation and model runs rather than duplicating them.
* ``server.py`` — the FastMCP server that registers those tools and one
  templated ``pe-module://{module}/reference`` doc resource.
* ``__main__.py`` — ``python -m pe.mcp.modules`` entry point (stdio).

T5 by the ``pe.mcp.*`` prefix (``tests/test_module_isolation.py``), same tier
as pe-config/pe-run. Registered in the repo-root ``.mcp.json`` as
``pe-modules``.
"""

from __future__ import annotations

__all__: list[str] = []
