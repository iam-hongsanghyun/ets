#!/bin/zsh

# Model Composer — Admin launcher.
# Independent of run.command: separate port, opens the Composer admin GUI
# (?mode=composer) where users assemble models from feature modules and
# save them into the registry the main app runs from.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${ETS_COMPOSER_PORT:-8801}"

if command -v uv >/dev/null 2>&1; then
  echo "Syncing environment with uv ..."
  uv sync --all-extras
  PY=(uv run python)
else
  VENV_DIR="$SCRIPT_DIR/.venv"
  PYTHON_BIN="$VENV_DIR/bin/python"
  REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
  STAMP="$VENV_DIR/.requirements-installed"

  if [[ ! -x "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    echo "Creating virtual environment in $VENV_DIR ..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  if [[ -f "$REQUIREMENTS" ]] && { [[ ! -f "$STAMP" ]] || [[ "$REQUIREMENTS" -nt "$STAMP" ]]; }; then
    echo "Installing requirements ..."
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS"
    touch "$STAMP"
  fi
  PY=("$PYTHON_BIN")
fi

echo "Starting Model Composer (admin) on port $PORT ..."
( sleep 2 && open "http://127.0.0.1:$PORT/?mode=composer" ) &
exec "${PY[@]}" "$SCRIPT_DIR/ets_framework.py" --gui --no-browser --port "$PORT"
