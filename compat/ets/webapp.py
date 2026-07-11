# Backward-compatibility shim — re-exports from web.handlers.
# New location: src/ets/web/handlers.py (transport) and src/ets/web/api.py
# (transport-free functions).
import warnings

from pe.web.handlers import (
    ASSET_CONTENT_TYPES,
    ETSRequestHandler,
    launch_web_app,
    build_analysis,
    _predefined_templates,
    _decorate_frontend_config,
    _build_dashboard_payload,
    _save_user_scenario,
    _slugify_filename,
    _lookup_sector,
    _json_safe,
    _WarningCollector,
)

warnings.warn(
    "ets.webapp is deprecated; import from pe.web.handlers (or pe.web.api "
    "for the transport-free functions) instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ASSET_CONTENT_TYPES",
    "ETSRequestHandler",
    "launch_web_app",
    "build_analysis",
    "_predefined_templates",
    "_decorate_frontend_config",
    "_build_dashboard_payload",
    "_save_user_scenario",
    "_slugify_filename",
    "_lookup_sector",
    "_json_safe",
    "_WarningCollector",
]
