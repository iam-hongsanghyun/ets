from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
MPLCONFIG_DIR = PROJECT_DIR / ".mplconfig"
FRONTEND_DIR = PROJECT_DIR / "ets" / "frontend" / "clearing"
EXAMPLES_DIR = PROJECT_DIR / "examples"

os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
