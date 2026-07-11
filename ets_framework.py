from pathlib import Path
import sys
import warnings

PROJECT_DIR = Path(__file__).resolve().parent
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

warnings.warn(
    "ets_framework.py is deprecated; use `python -m pe.cli` instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

from pe.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
