from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# `pe` resolves from the installed wheel (requirements.txt `.`), not sys.path:
# a split package (core/backend + modules/*/backend) is not reconstructable by
# putting directories on the path — only the package_dir finder reunites it.
from pe.web.server import app  # noqa: E402

