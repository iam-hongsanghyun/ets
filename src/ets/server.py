# Backward-compatibility shim — re-exports from web.server.
# New location: src/ets/web/server.py.
import warnings

from .web.server import app, create_app, _json_response, _file_response, _safe_path

warnings.warn(
    "ets.server is deprecated; import from ets.web.server instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["app", "create_app", "_json_response", "_file_response", "_safe_path"]
