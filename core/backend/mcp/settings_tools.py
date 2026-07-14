"""Stateless tool implementations behind the pe-config server's *settings* surface.

The configuration server has two halves: model *authoring* (``pe.mcp.tools`` —
the composer graph) and deployment *settings* (this module). Settings are the
``PE_*`` environment variables ``pe.registry.config`` reads to decide which
model-registry storage backend is active and where it lives — the one part of
the platform that is a genuine deployment choice (``CLAUDE.md``'s "load via
``config.py`` from ``.env``" convention), mirrored one-for-one in the
project-root ``.env.example``.

Read-only by design. There is deliberately no ``set_setting`` tool: one of
these vars (``PE_SUPABASE_KEY``) is an API credential, and writing credentials
into a file on the user's behalf is exactly the class of action an assistant
must not take — the user edits ``.env`` themselves. Secret-typed values are
redacted in every reported payload here; a tool never echoes the key back.

These functions are plain and side-effect-free (they only *read*
``os.environ``), imported directly by ``pe.mcp.config.server`` (wrapped as MCP
tools) and by ``tests/apps/mcp/test_mcp_settings.py`` (exercised directly, no
MCP transport involved).

Dependency law: same as any T5 app — imports ``pe.registry`` and stdlib only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..registry import config as registry_config


@dataclass(frozen=True)
class _Setting:
    """One deployment setting: its env var, purpose, default, and secrecy.

    Args:
        name: The environment variable name (e.g. ``PE_REGISTRY_BACKEND``).
        purpose: One-line, plain-language description of what it controls.
        default: The effective value when the var is unset (as a string, or
            ``""`` for "empty/unset by default"); mirrors ``.env.example``.
        enum: Allowed values when the setting is a closed set, else ``None``.
        secret: Whether the value is a credential — redacted in all output.
    """

    name: str
    purpose: str
    default: str
    enum: tuple[str, ...] | None = None
    secret: bool = False


# ── The settings catalogue ───────────────────────────────────────────────
# One row per PE_* var in `.env.example`. `pe.registry.config` is the single
# source of truth for the names/defaults/enum below — kept in lockstep by
# `tests/apps/mcp/test_mcp_settings.py`, which asserts every ENV_* constant
# and DEFAULT_* / SUPPORTED_BACKENDS value this table quotes still matches the
# config module, so this list can never silently drift.
_SETTINGS: tuple[_Setting, ...] = (
    _Setting(
        name="PE_PROJECT_DIR",
        purpose=(
            "Absolute path to the project root that anchors every relative "
            "registry/example path. Unset means 'infer from the installed "
            "package location'."
        ),
        default="",
    ),
    _Setting(
        name=registry_config.ENV_BACKEND,
        purpose="Which model-registry storage adapter is active.",
        default=registry_config.DEFAULT_BACKEND,
        enum=registry_config.SUPPORTED_BACKENDS,
    ),
    _Setting(
        name=registry_config.ENV_DB_PATH,
        purpose=(
            "Where the SQLite registry file lives (only meaningful when the "
            "backend is 'sqlite'). A relative path resolves against the "
            "project root."
        ),
        default="database/registry.sqlite",
    ),
    _Setting(
        name=registry_config.ENV_SUPABASE_URL,
        purpose="Supabase project URL (only used when the backend is 'supabase').",
        default="",
    ),
    _Setting(
        name=registry_config.ENV_SUPABASE_KEY,
        purpose="Supabase API key (only used when the backend is 'supabase').",
        default="",
        secret=True,
    ),
)

_SETTINGS_BY_NAME = {s.name: s for s in _SETTINGS}

_REDACTED = "***redacted***"


def _effective_value(setting: _Setting) -> tuple[str, bool, str]:
    """Resolve a setting's current value, whether it's set, and its source.

    Args:
        setting: The catalogue row to resolve.

    Returns:
        ``(value, is_set, source)`` — ``value`` is the environment value if
        present else the default (redacted when ``setting.secret`` and a real
        value exists); ``is_set`` is whether the env var is present and
        non-empty; ``source`` is ``"environment"`` or ``"default"``.
    """
    raw = os.environ.get(setting.name, "").strip()
    is_set = bool(raw)
    if is_set:
        value = _REDACTED if setting.secret else raw
        return value, True, "environment"
    return setting.default, False, "default"


def _describe(setting: _Setting) -> dict[str, Any]:
    """Build the reported payload for one setting (value always safe to show)."""
    value, is_set, source = _effective_value(setting)
    payload: dict[str, Any] = {
        "name": setting.name,
        "purpose": setting.purpose,
        "value": value,
        "is_set": is_set,
        "source": source,
        "default": setting.default,
        "secret": setting.secret,
    }
    if setting.enum is not None:
        payload["allowed"] = list(setting.enum)
    return payload


def list_settings() -> dict[str, Any]:
    """List every deployment setting with its current (safe-to-show) value.

    Read-only: reports the effective value of each ``PE_*`` environment
    variable ``pe.registry.config`` consults — the env value if set, else the
    ``.env.example`` default — with secret values (API keys) redacted. There
    is no companion write tool; the user edits ``.env`` themselves (see this
    module's docstring for why).

    Returns:
        ``{"settings": [{"name", "purpose", "value", "is_set", "source"
        ("environment"|"default"), "default", "secret", "allowed"?}, ...],
        "backend": <active backend kind>}``. ``backend`` is the resolved
        active adapter (``load_registry_config().backend``), the one derived
        value a user most often wants confirmed.
    """
    return {
        "settings": [_describe(s) for s in _SETTINGS],
        "backend": registry_config.load_registry_config().backend,
    }


def describe_setting(name: str) -> dict[str, Any]:
    """Describe one deployment setting by its environment-variable name.

    Args:
        name: A ``PE_*`` variable name (see ``list_settings``). Case-sensitive.

    Returns:
        The same per-setting shape ``list_settings`` returns for one row.

    Raises:
        ValueError: ``name`` is not a known setting.
    """
    setting = _SETTINGS_BY_NAME.get(name)
    if setting is None:
        known = ", ".join(sorted(_SETTINGS_BY_NAME))
        raise ValueError(f"Unknown setting '{name}'. Known settings: {known}.")
    return _describe(setting)
