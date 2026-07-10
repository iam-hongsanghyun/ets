"""Graph composer endpoints (blocks-graph-plan.md §5, Order 8), driven
end-to-end through the WSGI app (``ets.web.server:app``) in-process.

Covers:
  (a) GET /api/blocks parses and every BLOCK_CATALOGUE id appears.
  (b) POST /api/graph/run on a canonical basic-linear graph equals
      POST /api/run on the equivalent scenario config (allowing the extra
      "graph" echo key).
  (c) POST /api/graph/validate returns ok=false with an R1 issue for a graph
      with two price-formation blocks.
  (d) GET /api/graph/from-template -> POST /api/graph/run round-trips for one
      template id.
  (e) Malformed JSON -> 400 for every graph POST endpoint.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

from ets.blocks import BLOCK_CATALOGUE, Graph
from ets.web.server import app

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _call(method: str, path: str, body: bytes = b"", query: str = "") -> tuple[int, dict[str, Any]]:
    """Invoke the WSGI app in-process; returns (status_code, decoded_json_body)."""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/json",
        "wsgi.input": BytesIO(body),
    }
    captured: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = int(status.split(" ", 1)[0])
        captured["headers"] = headers

    chunks = app(environ, start_response)
    raw = b"".join(chunks)
    return captured["status"], json.loads(raw.decode("utf-8"))


def _post_json(path: str, payload: dict) -> tuple[int, dict[str, Any]]:
    return _call("POST", path, json.dumps(payload).encode("utf-8"))


def _basic_linear_graph() -> dict[str, Any]:
    """A hand-built graph equivalent to examples/climate_solutions_basic_linear.json."""
    raw = json.loads((EXAMPLES_DIR / "climate_solutions_basic_linear.json").read_text())
    scenario = raw["scenarios"][0]
    years = scenario["years"]
    grid_keys = (
        "year", "total_cap", "auction_mode", "auction_offered", "reserved_allowances",
        "carbon_budget", "banking_allowed", "borrowing_allowed", "borrowing_limit",
    )
    nodes = [
        {
            "id": "market",
            "block": "carbon_market",
            "params": {
                "name": scenario["name"],
                "years": [{k: y[k] for k in grid_keys if k in y} for y in years],
            },
        },
        {"id": "pf", "block": "competitive_clearing", "params": {}},
        {"id": "ceil", "block": "price_ceiling", "params": {"price_upper_bound": 250.0}},
    ]
    edges = [
        {"source": "pf", "sourcePort": "price_formation", "target": "market", "targetPort": "price_formation"},
        {"source": "ceil", "sourcePort": "policy", "target": "market", "targetPort": "policies"},
    ]
    for index, participant in enumerate(years[0]["participants"]):
        pid = f"p{index}"
        nodes.append({"id": pid, "block": "participant", "params": {"order": index, **participant}})
        edges.append({"source": pid, "sourcePort": "compliance", "target": "market", "targetPort": "participants"})
    return {"version": 1, "nodes": nodes, "edges": edges, "meta": {"canvas": {}}}


def _two_price_formation_graph() -> dict[str, Any]:
    graph = _basic_linear_graph()
    graph["nodes"].append({"id": "pf2", "block": "hotelling", "params": {}})
    graph["edges"].append(
        {"source": "pf2", "sourcePort": "price_formation", "target": "market", "targetPort": "price_formation"}
    )
    return graph


# ── (a) GET /api/blocks ──────────────────────────────────────────────────


def test_api_blocks_parses_and_lists_every_catalogue_block() -> None:
    status, body = _call("GET", "/api/blocks")
    assert status == 200
    assert isinstance(body["blocks"], list)
    returned_ids = {block["id"] for block in body["blocks"]}
    assert returned_ids == set(BLOCK_CATALOGUE.ids())
    for block in body["blocks"]:
        assert set(block.keys()) == {"id", "label", "category", "doc", "params", "ports", "constraints"}
        assert set(block["ports"].keys()) == {"inputs", "outputs"}
        for param in block["params"]:
            assert set(param.keys()) == {
                "name", "type", "default", "unit", "min", "max", "enum", "config_key", "scope",
            }


# ── (b) /api/graph/run == /api/run on the equivalent config ─────────────


def test_graph_run_matches_plain_run() -> None:
    graph_payload = _basic_linear_graph()
    status_graph, body_graph = _post_json("/api/graph/run", {"graph": graph_payload})
    assert status_graph == 200, body_graph

    status_compile, body_compile = _post_json("/api/graph/compile", {"graph": graph_payload})
    assert status_compile == 200, body_compile
    config = body_compile["config"]

    status_run, body_run = _post_json("/api/run", config)
    assert status_run == 200, body_run

    graph_sans_echo = dict(body_graph)
    graph_sans_echo.pop("graph")
    assert graph_sans_echo == body_run
    assert body_graph["graph"] == graph_payload


# ── (c) /api/graph/validate: two price-formation blocks -> R1, ok=false ──


def test_graph_validate_flags_two_price_formation_blocks() -> None:
    status, body = _post_json("/api/graph/validate", {"graph": _two_price_formation_graph()})
    assert status == 200
    assert body["ok"] is False
    rules = {issue["rule"] for issue in body["issues"]}
    assert "R1" in rules


def test_graph_validate_ok_true_for_clean_graph() -> None:
    status, body = _post_json("/api/graph/validate", {"graph": _basic_linear_graph()})
    assert status == 200
    assert body["ok"] is True


# ── (d) from-template -> graph -> /api/graph/run round-trip ─────────────


def test_from_template_round_trips_through_graph_run() -> None:
    status_templates, body_templates = _call("GET", "/api/templates")
    assert status_templates == 200
    template_id = next(
        t["id"] for t in body_templates["templates"] if t["id"] == "climate_solutions_basic_linear"
    )

    status_ft, body_ft = _call("GET", "/api/graph/from-template", query=f"id={template_id}")
    assert status_ft == 200, body_ft
    graph_dict = body_ft["graph"]
    # Sanity: parses back into a real Graph.
    Graph.from_dict(graph_dict)

    status_run, body_run = _post_json("/api/graph/run", {"graph": graph_dict})
    assert status_run == 200, body_run
    assert body_run["config"]["scenarios"][0]["name"]


def test_from_template_unknown_id_is_400() -> None:
    status, body = _call("GET", "/api/graph/from-template", query="id=does-not-exist")
    assert status == 400
    assert "error" in body


# ── (e) malformed JSON -> 400 ────────────────────────────────────────────


def test_malformed_json_is_400_for_every_graph_post_endpoint() -> None:
    for path in ("/api/graph/validate", "/api/graph/compile", "/api/graph/run"):
        status, body = _call("POST", path, body=b"{not valid json")
        assert status == 400, f"{path} returned {status}"
        assert "error" in body
