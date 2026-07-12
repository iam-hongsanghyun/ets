"""The SESSION registry tier — a model POPULATED with a user's data, saved
from and reloadable ONLY in pe.command — plus the model-vs-session filter and
the ``kind``/``source_model_id`` schema migration.

Covers:
  (a) ``save_session`` persists ``kind="session"`` with a ``source_model_id``
      link; ``list_sessions`` returns it, ``resolve_session`` round-trips its
      config, ``rename_session`` re-keys it, ``delete_session`` removes it.
  (b) Tier isolation: a saved session is EXCLUDED from ``iter_registry_models``
      (the builder's model corpus) and vice-versa — the two lists never mix.
  (c) ``save_config_as_model`` UPDATE-EXISTING (overwrite a given model id)
      vs NEW (name-derived id) — the session→model "save back" promotion.
  (d) Backend migration: an OLD single-tier ``models`` table (no ``kind`` /
      ``source_model_id`` columns) is upgraded in place on construction — the
      columns are added, every pre-existing row backfills to ``kind="model"``
      byte-compatibly, and its models still list as models.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pe.config_io import load_config
from pe.model_store import (
    ModelStoreError,
    delete_session,
    iter_registry_models,
    list_sessions,
    rename_session,
    resolve_model_config,
    resolve_session,
    save_config_as_model,
    save_graph_as_model,
    save_session,
)
from pe.registry.config import get_backend_for_directory
from pe.registry.sqlite_backend import SqliteBackend

# TEST INFRA (not the example library): the canonical minimal competitive
# scenario recovered under tests/fixtures/ as a generic valid config.
MINIMAL_SCENARIO = (
    next(p for p in Path(__file__).resolve().parents if p.name == "tests")
    / "fixtures"
    / "minimal_scenario.json"
)


def _sample_config() -> dict:
    return load_config(MINIMAL_SCENARIO)


def _sample_graph():
    from pe.blocks import graph_from_config

    return graph_from_config(_sample_config())


# ── (a) session CRUD round trip ───────────────────────────────────────────


def test_save_session_persists_kind_and_source_link(tmp_path: Path) -> None:
    session = save_session(
        _sample_config(), "My Working Session", "user_some_model", registry_dir=tmp_path
    )

    assert session.id == "sess_my_working_session"
    assert session.name == "My Working Session"
    assert session.source_model_id == "user_some_model"
    assert session.created_at == session.updated_at

    record = get_backend_for_directory(tmp_path).get_model("sess_my_working_session")
    assert record is not None
    assert record.kind == "session"
    assert record.source_model_id == "user_some_model"


def test_list_and_resolve_session_round_trip(tmp_path: Path) -> None:
    session = save_session(_sample_config(), "Round Trip", None, registry_dir=tmp_path)

    listed = list_sessions(registry_dir=tmp_path)
    assert [s.id for s in listed] == ["sess_round_trip"]
    assert listed[0].source_model_id is None

    resolved = resolve_session(session.id, registry_dir=tmp_path)
    assert resolved.id == session.id
    assert resolved.config == session.config


def test_rename_session_rekeys_and_keeps_source_link(tmp_path: Path) -> None:
    save_session(_sample_config(), "Old Session", "user_src", registry_dir=tmp_path)

    renamed = rename_session("sess_old_session", "New Session", registry_dir=tmp_path)

    assert renamed.id == "sess_new_session"
    assert renamed.source_model_id == "user_src"
    with pytest.raises(ModelStoreError, match="Unknown session id"):
        resolve_session("sess_old_session", registry_dir=tmp_path)
    assert resolve_session("sess_new_session", registry_dir=tmp_path).config == renamed.config


def test_rename_session_collision_is_rejected(tmp_path: Path) -> None:
    save_session(_sample_config(), "Session A", None, registry_dir=tmp_path)
    save_session(_sample_config(), "Session B", None, registry_dir=tmp_path)

    with pytest.raises(ModelStoreError, match="already exists"):
        rename_session("sess_session_b", "Session A", registry_dir=tmp_path)


def test_delete_session_removes_it(tmp_path: Path) -> None:
    save_session(_sample_config(), "Doomed", None, registry_dir=tmp_path)
    delete_session("sess_doomed", registry_dir=tmp_path)

    assert list_sessions(registry_dir=tmp_path) == []
    with pytest.raises(ModelStoreError, match="Unknown session id"):
        resolve_session("sess_doomed", registry_dir=tmp_path)


def test_session_ops_reject_non_session_id(tmp_path: Path) -> None:
    for op in (resolve_session, delete_session):
        with pytest.raises(ModelStoreError, match="not a session id"):
            op("user_a_model", registry_dir=tmp_path)


# ── (b) tier isolation: sessions excluded from the model corpus ───────────


def test_session_excluded_from_model_corpus_and_vice_versa(tmp_path: Path) -> None:
    saved_model = save_graph_as_model(_sample_graph(), "A Real Model", registry_dir=tmp_path)
    saved_session = save_session(
        _sample_config(), "A Session", saved_model.id, registry_dir=tmp_path
    )

    model_ids = {mid for mid, _ in iter_registry_models(registry_dir=tmp_path)}
    session_ids = {s.id for s in list_sessions(registry_dir=tmp_path)}

    assert saved_model.id in model_ids
    assert saved_session.id not in model_ids
    assert saved_session.id in session_ids
    assert saved_model.id not in session_ids

    # A session's id does not resolve as a model (models-only resolver).
    with pytest.raises(ModelStoreError, match="Unknown model id"):
        resolve_model_config(saved_session.id, registry_dir=tmp_path)


# ── (c) save-as-model: update-existing vs new ─────────────────────────────


def test_save_config_as_model_new_derives_id_from_name(tmp_path: Path) -> None:
    saved = save_config_as_model(_sample_config(), "Brand New Model", registry_dir=tmp_path)
    assert saved.id == "user_brand_new_model"
    record = get_backend_for_directory(tmp_path).get_model("brand_new_model")
    assert record is not None
    assert record.kind == "model"


def test_save_config_as_model_update_existing_overwrites_in_place(tmp_path: Path) -> None:
    original = save_graph_as_model(_sample_graph(), "Source Model", registry_dir=tmp_path)

    # Promote a modified config back onto the SAME model id (session -> model).
    modified = _sample_config()
    modified["scenarios"][0]["name"] = "Promoted Name"
    saved = save_config_as_model(
        modified, "Ignored Display", model_id=original.id, registry_dir=tmp_path
    )

    assert saved.id == original.id  # id unchanged — overwrite, not a new slug
    resolved = resolve_model_config(original.id, registry_dir=tmp_path)
    assert resolved["scenarios"][0]["name"] == "Promoted Name"
    # Still exactly one model row for that id.
    model_ids = [mid for mid, _ in iter_registry_models(registry_dir=tmp_path)]
    assert model_ids.count(original.id) == 1


def test_save_config_as_model_update_rejects_non_registry_id(tmp_path: Path) -> None:
    with pytest.raises(ModelStoreError, match="not a registry model id"):
        save_config_as_model(
            _sample_config(), "X", model_id="an_example_stem", registry_dir=tmp_path
        )


# ── (d) schema migration: old single-tier DB upgraded in place ────────────

_OLD_SCHEMA = """
CREATE TABLE models (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    graph_json TEXT,
    source TEXT NOT NULL,
    domain TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def test_migration_adds_columns_and_backfills_existing_rows_as_models(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite"
    # Materialize a pre-``kind`` registry: the OLD 8-column schema + one row.
    conn = sqlite3.connect(db_path)
    conn.execute(_OLD_SCHEMA)
    conn.execute(
        "INSERT INTO models (id, name, config_json, graph_json, source, domain, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("legacy", "Legacy", '{"scenarios": []}', None, "config", None, "2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    # Opening through SqliteBackend runs the idempotent migration.
    backend = SqliteBackend(db_path)
    columns = {row[1] for row in sqlite3.connect(db_path).execute("PRAGMA table_info(models)")}
    assert {"kind", "source_model_id"} <= columns

    record = backend.get_model("legacy")
    assert record is not None
    assert record.kind == "model", "every pre-kind row backfills to a model"
    assert record.source_model_id is None
    # It lists as a model, and there are no sessions.
    assert [r.id for r in backend.list_models(kind="model")] == ["legacy"]
    assert backend.list_models(kind="session") == []

    # Re-opening again is a no-op (idempotent) — still one well-formed row.
    reopened = SqliteBackend(db_path)
    assert reopened.get_model("legacy") == record
