from __future__ import annotations

import sys
import warnings
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

warnings.warn(
    "app.py is deprecated; use the pe.web entry points instead "
    "(pe.web.server:app / create_app for WSGI, pe.web.handlers:launch_web_app "
    "for the local server). "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

from pe.web.server import app  # noqa: E402,F401  (re-exported as the ASGI/WSGI entry)
