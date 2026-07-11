"""Single route table shared by both web servers (Order 4; extended Order 8).

Every route has the uniform signature
``(body: bytes, headers, query: dict[str, str]) -> dict`` where ``headers``
is any object exposing ``.get(name, default)`` (the http.server message
object or the WSGI ``_FakeHeaders`` adapter), and ``query`` is the parsed
query string (each key's first value only — ``?id=x&id=y`` yields
``{"id": "x"}``), always a plain ``dict`` regardless of transport. Routes
only adapt the transport payload to the transport-free functions in
``web/api.py`` — no handler logic lives here.

``query`` was added in Order 8 for ``GET /api/graph/from-template?id=...``;
the seven pre-existing routes ignore it, so their responses are unchanged.

Static file and docs serving stays server-specific; only ``/api/``
endpoints are listed. Both ``ETSRequestHandler`` (http.server) and
``web/server.py:app`` (WSGI) dispatch through ``ROUTES``.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .api import (
    _build_dashboard_payload,
    _handle_batch_run,
    _handle_calibrate,
    _handle_csv_import,
    _handle_graph_compile,
    _handle_graph_from_template,
    _handle_graph_run,
    _handle_graph_save_model,
    _handle_graph_validate,
    _handle_model_manifest_get,
    _handle_model_manifest_post,
    _handle_narrative,
    _predefined_templates,
    _save_user_scenario,
    _serialize_block_catalogue,
)

RouteHandler = Callable[[bytes, Any, dict], dict]


def _parse_json(body: bytes) -> dict:
    return json.loads(body.decode("utf-8")) if body else {}


def _route_templates(body: bytes, headers: Any, query: dict) -> dict:
    return {"templates": _predefined_templates()}


def _route_run(body: bytes, headers: Any, query: dict) -> dict:
    return _build_dashboard_payload(_parse_json(body))


def _route_save_scenario(body: bytes, headers: Any, query: dict) -> dict:
    return _save_user_scenario(_parse_json(body))


def _route_calibrate(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_calibrate(_parse_json(body))


def _route_batch_run(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_batch_run(_parse_json(body))


def _route_narrative(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_narrative(_parse_json(body))


def _route_import_csv(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_csv_import(body, headers)


def _route_blocks(body: bytes, headers: Any, query: dict) -> dict:
    return _serialize_block_catalogue()


def _route_graph_validate(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_graph_validate(_parse_json(body))


def _route_graph_compile(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_graph_compile(_parse_json(body))


def _route_graph_run(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_graph_run(_parse_json(body))


def _route_graph_from_template(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_graph_from_template(query.get("id"))


def _route_graph_save_model(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_graph_save_model(_parse_json(body))


def _route_model_manifest_get(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_model_manifest_get(query.get("id"))


def _route_model_manifest_post(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_model_manifest_post(_parse_json(body))


ROUTES: dict[tuple[str, str], RouteHandler] = {
    ("GET", "/api/templates"): _route_templates,
    ("POST", "/api/run"): _route_run,
    ("POST", "/api/save-scenario"): _route_save_scenario,
    ("POST", "/api/calibrate"): _route_calibrate,
    ("POST", "/api/batch-run"): _route_batch_run,
    ("POST", "/api/narrative"): _route_narrative,
    ("POST", "/api/import-csv"): _route_import_csv,
    ("GET", "/api/blocks"): _route_blocks,
    ("POST", "/api/graph/validate"): _route_graph_validate,
    ("POST", "/api/graph/compile"): _route_graph_compile,
    ("POST", "/api/graph/run"): _route_graph_run,
    ("GET", "/api/graph/from-template"): _route_graph_from_template,
    ("POST", "/api/graph/save-model"): _route_graph_save_model,
    ("GET", "/api/model-manifest"): _route_model_manifest_get,
    ("POST", "/api/model-manifest"): _route_model_manifest_post,
}

__all__ = ["ROUTES", "RouteHandler"]
