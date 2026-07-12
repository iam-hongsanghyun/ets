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

Parameterized routes (the SESSION tier, pe.command) — ``GET/DELETE/PATCH
/api/session/<id>`` and ``GET /api/model/<id>`` — are matched by
:data:`PREFIX_ROUTES` in :func:`resolve_route`, which extracts the trailing
path segment and injects it as ``query["id"]`` so the handler reads it
exactly like an ``?id=`` query param — no per-transport path parsing. Both
servers call :func:`resolve_route` (exact :data:`ROUTES` win first), so
``GET /api/sessions`` (list) never shadows ``GET /api/session/<id>``.

Static file and docs serving stays server-specific; only ``/api/``
endpoints are listed. Both ``ETSRequestHandler`` (http.server) and
``web/server.py:app`` (WSGI) dispatch through :func:`resolve_route`.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

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
    _handle_model_get,
    _handle_model_manifest_get,
    _handle_model_manifest_post,
    _handle_model_save,
    _handle_narrative,
    _handle_session_delete,
    _handle_session_get,
    _handle_session_rename,
    _handle_session_save,
    _handle_sessions_list,
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


# ── Session tier (pe.command) + save-back-to-model ─────────────────────────


def _route_session_save(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_session_save(_parse_json(body))


def _route_sessions_list(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_sessions_list()


def _route_session_get(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_session_get(query.get("id"))


def _route_session_delete(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_session_delete(query.get("id"))


def _route_session_rename(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_session_rename(query.get("id"), _parse_json(body))


def _route_model_get(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_model_get(query.get("id"))


def _route_model_save(body: bytes, headers: Any, query: dict) -> dict:
    return _handle_model_save(_parse_json(body))


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
    ("POST", "/api/session"): _route_session_save,
    ("GET", "/api/sessions"): _route_sessions_list,
    ("POST", "/api/model"): _route_model_save,
}

# Parameterized routes: matched by trailing-path-segment in resolve_route, which
# injects that segment as query["id"]. Exact ROUTES always win first, so
# GET /api/sessions (list) is never shadowed by GET /api/session/<id>.
PREFIX_ROUTES: dict[tuple[str, str], RouteHandler] = {
    ("GET", "/api/session/"): _route_session_get,
    ("DELETE", "/api/session/"): _route_session_delete,
    ("PATCH", "/api/session/"): _route_session_rename,
    ("GET", "/api/model/"): _route_model_get,
}


def resolve_route(method: str, path: str) -> tuple[RouteHandler, dict[str, str]] | None:
    """Resolve ``(method, path)`` to a handler plus any path parameters.

    Exact :data:`ROUTES` are checked first; then :data:`PREFIX_ROUTES` match a
    ``/prefix/<id>`` shape, returning the single trailing segment as
    ``{"id": <segment>}`` for the caller to merge into ``query``. A trailing
    segment that is empty or itself contains a ``/`` (a deeper path) does not
    match.

    Args:
        method: The HTTP method (``"GET"``, ``"POST"``, ``"DELETE"``,
            ``"PATCH"``).
        path: The request path (no query string).

    Returns:
        ``(handler, path_params)`` on a match, else ``None``.
    """
    exact = ROUTES.get((method, path))
    if exact is not None:
        return exact, {}
    for (prefix_method, prefix), handler in PREFIX_ROUTES.items():
        if prefix_method == method and path.startswith(prefix):
            tail = path[len(prefix) :]
            if tail and "/" not in tail:
                return handler, {"id": unquote(tail)}
    return None


__all__ = ["ROUTES", "PREFIX_ROUTES", "RouteHandler", "resolve_route"]
