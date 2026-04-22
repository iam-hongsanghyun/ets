from __future__ import annotations

import os
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / "ets" / "frontend" / "clearing"
EXAMPLES_DIR = PROJECT_DIR / "examples"
SERVERLESS_ROOT = Path(tempfile.gettempdir()) / "ets_runtime"

if os.environ.get("VERCEL"):
    OUTPUT_DIR = SERVERLESS_ROOT / "outputs"
    MPLCONFIG_DIR = SERVERLESS_ROOT / ".mplconfig"
else:
    OUTPUT_DIR = PROJECT_DIR / "outputs"
    MPLCONFIG_DIR = PROJECT_DIR / ".mplconfig"

os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
