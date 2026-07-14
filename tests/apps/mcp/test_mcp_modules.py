"""pe-modules factory-server tests.

Exercises the tool FUNCTIONS directly (``pe.mcp.modules.tools`` /
``pe.mcp.modules.registry``) — no MCP transport for most cases — mirroring
``test_mcp_composer.py``. Covers:

  (a) the module roster is derived from the catalogue and matches the
      importable ``pe.features.*`` feature packages (no drift).
  (b) ``describe_module`` returns a module's block descriptors + mechanism
      doc, and rejects an unknown module.
  (c) ``configure_module`` adds and wires a module's block onto a graph
      exactly as the config server's ``add_block`` would; it rejects an
      ambiguous multi-block module and a foreign block id.
  (d) ``run_module_scoped`` projects a run onto a module's own output columns,
      and reports ``active=false`` for a module with no scoped columns.
  (e) one in-process MCP protocol smoke test: the server lists its 4 tools and
      answers a ``call_tool`` round trip.
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

from pe.blocks import BLOCK_CATALOGUE
from pe.mcp import tools as composer_tools
from pe.mcp.modules import registry
from pe.mcp.modules import tools as module_tools

_EXAMPLE_MODEL = "banking_msr"


def test_module_registry_matches_importable_feature_packages() -> None:
    reg = registry.module_registry()
    # Every catalogue feature that imports as a pe.features package is a module;
    # nothing else is.
    expected = set()
    for feature in {b.feature for b in BLOCK_CATALOGUE}:
        try:
            importlib.import_module(f"pe.features.{feature}")
        except ModuleNotFoundError:
            continue
        expected.add(feature)
    assert set(reg) == expected
    # The non-package meta features are excluded.
    assert "core" not in reg
    assert "calibration" not in reg


def test_list_modules_reports_blocks_and_reference_flag() -> None:
    modules = {m["name"]: m for m in module_tools.list_modules()["modules"]}
    assert "banking" in modules
    banking = modules["banking"]
    assert banking["block_ids"] == ["rubin_schennach_banking"]
    assert banking["has_reference"] is True
    assert banking["scoped_columns"] == ["bank", "borrowed"]


def test_describe_module_returns_block_specs_and_doc() -> None:
    described = module_tools.describe_module("banking")
    assert described["name"] == "banking"
    assert [b["id"] for b in described["blocks"]] == ["rubin_schennach_banking"]
    # Full catalogue descriptor: params carry declared defaults/units.
    assert "params" in described["blocks"][0]
    assert isinstance(described["reference"], str)
    assert described["reference"]


def test_describe_module_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown module"):
        module_tools.describe_module("not_a_module")


def test_configure_module_adds_and_wires_block() -> None:
    graph = composer_tools.new_graph()["graph"]
    result = module_tools.configure_module(graph, "banking", params={"banking_initial_bank": 10.0})
    assert result["module"] == "banking"
    assert result["block_id"] == "rubin_schennach_banking"
    node = next(n for n in result["graph"]["nodes"] if n["id"] == result["node_id"])
    assert node["block"] == "rubin_schennach_banking"
    assert node["params"]["banking_initial_bank"] == 10.0


def test_configure_module_ambiguous_multi_block_requires_block_id() -> None:
    graph = composer_tools.new_graph()["graph"]
    with pytest.raises(ValueError, match="owns 4 blocks"):
        module_tools.configure_module(graph, "price_controls")


def test_configure_module_rejects_foreign_block_id() -> None:
    graph = composer_tools.new_graph()["graph"]
    with pytest.raises(ValueError, match="not part of module"):
        module_tools.configure_module(graph, "banking", block_id="price_floor")


def test_configure_module_picks_named_block_of_multi_block_module() -> None:
    graph = composer_tools.new_graph()["graph"]
    result = module_tools.configure_module(graph, "price_controls", block_id="price_floor")
    assert result["block_id"] == "price_floor"


def test_run_module_scoped_projects_module_columns() -> None:
    result = module_tools.run_module_scoped(_EXAMPLE_MODEL, "msr")
    assert result["module"] == "msr"
    assert result["scoped_columns"] == ["msr_withheld", "msr_released", "msr_reserve_pool"]
    scenario = next(iter(result["scenarios"].values()))
    # Every row at least carries its year label.
    assert all("year" in row for row in scenario["years"])


def test_run_module_scoped_reports_inactive_for_undecorated_module() -> None:
    # competitive has no dedicated scoped compact column.
    result = module_tools.run_module_scoped(_EXAMPLE_MODEL, "competitive")
    assert result["scoped_columns"] == []
    assert result["active"] is False


def test_pe_modules_server_lists_tools_and_answers_call_tool() -> None:
    mcp_client = pytest.importorskip("mcp.shared.memory")
    from pe.mcp.modules.server import mcp as server

    async def _run() -> None:
        async with mcp_client.create_connected_server_and_client_session(server) as session:
            listed = await session.list_tools()
            names = {t.name for t in listed.tools}
            assert names == {
                "list_modules",
                "describe_module",
                "configure_module",
                "run_module_scoped",
            }
            result = await session.call_tool("list_modules", {})
            assert result.isError is False

    asyncio.run(_run())
