"""SESSION-tier web endpoints (pe.command) driven end-to-end through the WSGI
app (``pe.web.server:app``) in-process, plus the save-back-to-MODEL promotion.

Covers:
  (a) POST /api/session -> GET /api/sessions / GET /api/session/<id> round-trip
      (the saved config reloads verbatim, with its source_model_id link).
  (b) A saved session does NOT appear in GET /api/templates (models-only
      builder corpus) — the two tiers never mix.
  (c) PATCH /api/session/<id> renames; DELETE /api/session/<id> removes it.
  (d) POST /api/model save-back: NEW (name-derived) and UPDATE-EXISTING
      (overwrite a given model id) — both write into the models-only corpus.
  (e) GET /api/model/<id> resolves a model's config (the session seed).
  (f) Error paths: unknown session id / model id -> 400; missing name -> 400.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pe.web.api as api
from pe.web.server import app

FIXTURES_DIR = next(p for p in Path(__file__).resolve().parents if p.name == "tests") / "fixtures"


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

    raw = b"".join(app(environ, start_response))
    return captured["status"], json.loads(raw.decode("utf-8"))


def _post(path: str, payload: dict) -> tuple[int, dict[str, Any]]:
    return _call("POST", path, json.dumps(payload).encode("utf-8"))


def _config() -> dict:
    return json.loads((FIXTURES_DIR / "minimal_scenario.json").read_text())


# ── (a) save -> list -> get round trip ────────────────────────────────────


def test_session_save_list_get_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    config = _config()

    status, body = _post(
        "/api/session",
        {"name": "Client Session", "config": config, "source_model_id": "user_src_model"},
    )
    assert status == 200, body
    assert body["id"] == "sess_client_session"
    assert body["source_model_id"] == "user_src_model"

    status_list, body_list = _call("GET", "/api/sessions")
    assert status_list == 200
    assert [s["id"] for s in body_list["sessions"]] == ["sess_client_session"]

    status_get, body_get = _call("GET", "/api/session/sess_client_session")
    assert status_get == 200, body_get
    assert body_get["config"] == config
    assert body_get["source_model_id"] == "user_src_model"


# ── (b) session is NOT in the builder's models-only corpus ────────────────


def test_saved_session_absent_from_templates(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    _post("/api/session", {"name": "Hidden Session", "config": _config(), "source_model_id": None})

    status, body = _call("GET", "/api/templates")
    assert status == 200
    ids = {t["id"] for t in body["templates"]}
    assert "sess_hidden_session" not in ids
    assert not any(tid.startswith("sess_") for tid in ids)


# ── (c) rename (PATCH) + delete (DELETE) ──────────────────────────────────


def test_session_rename_and_delete(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    _post("/api/session", {"name": "Before", "config": _config(), "source_model_id": None})

    status_p, body_p = _call(
        "PATCH", "/api/session/sess_before", json.dumps({"name": "After"}).encode("utf-8")
    )
    assert status_p == 200, body_p
    assert body_p["id"] == "sess_after"

    status_d, body_d = _call("DELETE", "/api/session/sess_after")
    assert status_d == 200, body_d
    assert body_d["deleted"] is True

    status_list, body_list = _call("GET", "/api/sessions")
    assert body_list["sessions"] == []


# ── (d) save-back-to-model: new + update-existing ─────────────────────────


def test_save_as_model_new_and_update_existing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)

    # NEW: no model_id -> name-derived id, appears in the models-only corpus.
    status_new, body_new = _post(
        "/api/model", {"name": "Promoted Model", "config": _config()}
    )
    assert status_new == 200, body_new
    assert body_new["id"] == "user_promoted_model"
    assert body_new["updated"] is False

    status_tpl, body_tpl = _call("GET", "/api/templates")
    assert "user_promoted_model" in {t["id"] for t in body_tpl["templates"]}

    # UPDATE-EXISTING: overwrite that same model id in place.
    modified = _config()
    modified["scenarios"][0]["name"] = "Overwritten"
    status_upd, body_upd = _post(
        "/api/model",
        {"name": "Ignored", "config": modified, "model_id": "user_promoted_model"},
    )
    assert status_upd == 200, body_upd
    assert body_upd["id"] == "user_promoted_model"
    assert body_upd["updated"] is True

    status_get, body_get = _call("GET", "/api/model/user_promoted_model")
    assert status_get == 200, body_get
    assert body_get["config"]["scenarios"][0]["name"] == "Overwritten"


# ── (e) GET /api/model/<id> (session seed) for an example ─────────────────


def test_model_get_resolves_example_config(monkeypatch) -> None:
    monkeypatch.setattr(api, "EXAMPLES_DIR", FIXTURES_DIR)
    status, body = _call("GET", "/api/model/minimal_scenario")
    assert status == 200, body
    assert body["config"]["scenarios"][0]["name"]


# ── (f) error paths ───────────────────────────────────────────────────────


def test_session_get_unknown_id_is_400(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    status, body = _call("GET", "/api/session/sess_nope")
    assert status == 400
    assert "error" in body


def test_session_save_missing_name_is_400(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    status, body = _post("/api/session", {"config": _config()})
    assert status == 400
    assert "error" in body


def test_model_get_unknown_id_is_400(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "USER_SCENARIOS_DIR", tmp_path)
    status, body = _call("GET", "/api/model/user_missing")
    assert status == 400
    assert "error" in body
