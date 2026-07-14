"""AI-guided ETS MCP (Model Context Protocol) servers: config, run, modules.

A T5 app, same tier as ``pe.web``/``pe.cli`` (``tests/test_module_isolation.py``):
every server wires the same primitives ``pe.web``'s endpoints use
(``pe.blocks``, ``pe.model_store``, ``pe.engine``, ``pe.analysis``,
``pe.registry``) up as MCP tools instead of HTTP routes, so an AI assistant
can hold a conversation with a user over stdio.

Three servers, split by what the user is doing:

* **pe-config** (``config/``) CONFIGURES the platform — model *authoring*
  (the composer graph: ``new_graph``/``add_block``/``set_params``/``check``/
  ``save_model``) plus deployment *settings* (read-only ``PE_*`` inspection
  via ``settings_tools``).
* **pe-run** (``run/``) OPERATES and ANALYSES the model registry — the
  governor (``list_models``/``describe_model``/``run_model``/
  ``compare_models``/``sweep_model``/``rename``/``delete``) plus
  post-processing analysis (``analysis_tools``, wrapping ``pe.analysis``:
  batch sweeps, narrative, CSV import, investment trigger, calibration).
* **pe-modules** (``modules/``) is a FACTORY server — one uniform
  describe/configure/run-scoped surface per feature module, derived from the
  block catalogue (``modules/registry.py``).

Package layout — the stateless tool implementations (importable and testable
directly, no MCP transport) live flat under ``pe.mcp``; each server is a thin
subpackage that registers a selection of them:

* ``tools.py`` — composer graph tools (pe-config). ``models_tools.py`` —
  governor tools (pe-run); ``models_tools.list_models`` is re-exported from
  ``tools.py`` rather than reimplemented — both list the identical registry.
* ``settings_tools.py`` — read-only ``PE_*`` deployment settings (pe-config).
* ``analysis_tools.py`` — ``pe.analysis`` post-processing wrappers (pe-run).
* ``suggestions.py`` — the rule -> plain-language-suggestion table behind the
  composer's ``check`` tool's ``next_steps``.
* ``compact.py`` — the compact result/manifest shapes shared across servers.
* ``config/``, ``run/``, ``modules/`` — the FastMCP server subpackages, each
  with a ``server.py`` (registers tools + holds the server-level
  ``instructions`` playbook) and a ``__main__.py`` stdio entry point
  (``python -m pe.mcp.config`` / ``.run`` / ``.modules``). ``modules/`` also
  holds its own ``registry.py`` + ``tools.py`` factory input.

Legacy: ``server.py`` (``python -m pe.mcp``, pe-composer) and
``models_server.py`` + ``models/`` (``python -m pe.mcp.models``, pe-models)
remain importable and runnable for backward compatibility, but ``.mcp.json``
now registers the three servers above. pe-composer's authoring is a subset of
pe-config; pe-models' operation is a subset of pe-run.

Install: the ``mcp`` optional-dependency group (``uv sync --extra mcp`` or
``--all-extras``). Registration: the repo-root ``.mcp.json`` (all three).
"""

from __future__ import annotations

__all__: list[str] = []
