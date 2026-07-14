"""pe-config settings-surface tests.

Exercises the tool FUNCTIONS directly (``pe.mcp.settings_tools``) — no MCP
transport — mirroring ``test_mcp_composer.py``. Covers:

  (a) ``list_settings`` reports every ``PE_*`` var with its effective value,
      and the resolved active backend.
  (b) Secret redaction: a set ``PE_SUPABASE_KEY`` is reported ``is_set`` but
      its value is never echoed.
  (c) ``describe_setting`` round-trips a known var and rejects an unknown one.
  (d) Drift guard: the settings table's names/defaults/enum still match
      ``pe.registry.config`` — the single source of truth.
  (e) The pe-config server registers the settings tools alongside the
      composer tools.
"""

from __future__ import annotations

import pytest

from pe.mcp import settings_tools
from pe.registry import config as registry_config


def test_list_settings_covers_every_pe_var_and_reports_backend() -> None:
    result = settings_tools.list_settings()
    names = {s["name"] for s in result["settings"]}
    assert names == {
        "PE_PROJECT_DIR",
        registry_config.ENV_BACKEND,
        registry_config.ENV_DB_PATH,
        registry_config.ENV_SUPABASE_URL,
        registry_config.ENV_SUPABASE_KEY,
    }
    # backend is the resolved active adapter, not a raw env echo.
    assert result["backend"] in registry_config.SUPPORTED_BACKENDS


def test_secret_value_is_redacted_even_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(registry_config.ENV_SUPABASE_KEY, "super-secret-token")
    described = settings_tools.describe_setting(registry_config.ENV_SUPABASE_KEY)
    assert described["is_set"] is True
    assert described["secret"] is True
    assert described["value"] != "super-secret-token"
    assert "secret-token" not in described["value"]


def test_non_secret_value_is_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(registry_config.ENV_BACKEND, "supabase")
    described = settings_tools.describe_setting(registry_config.ENV_BACKEND)
    assert described["is_set"] is True
    assert described["value"] == "supabase"
    assert described["source"] == "environment"


def test_unset_setting_reports_default_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(registry_config.ENV_DB_PATH, raising=False)
    described = settings_tools.describe_setting(registry_config.ENV_DB_PATH)
    assert described["is_set"] is False
    assert described["source"] == "default"
    assert described["value"] == described["default"]


def test_describe_setting_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown setting"):
        settings_tools.describe_setting("PE_NOT_A_SETTING")


def test_backend_setting_advertises_supported_enum() -> None:
    described = settings_tools.describe_setting(registry_config.ENV_BACKEND)
    assert described["allowed"] == list(registry_config.SUPPORTED_BACKENDS)
    assert described["default"] == registry_config.DEFAULT_BACKEND


def test_settings_table_does_not_drift_from_registry_config() -> None:
    # The catalogue quotes these constants; assert it still tracks the source.
    described = settings_tools.describe_setting(registry_config.ENV_BACKEND)
    assert described["name"] == registry_config.ENV_BACKEND
    assert settings_tools.describe_setting(registry_config.ENV_SUPABASE_KEY)["secret"] is True


def test_pe_config_server_registers_settings_and_composer_tools() -> None:
    import asyncio

    from pe.mcp.config.server import build_server

    async def _names() -> set[str]:
        return {t.name for t in await build_server().list_tools()}

    names = asyncio.run(_names())
    assert {"list_settings", "describe_setting"} <= names
    assert {"new_graph", "add_block", "save_model"} <= names
