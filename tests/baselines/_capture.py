"""Capture golden baselines for every scenario config in examples/*.json.

Runs each example through ``ets.run_simulation_from_file`` and serializes the
full solved output (scenario summary and per-participant-per-year detail) to
``tests/baselines/<scenario-file-stem>.json`` with round-trip-exact floats.

Usage (from the repo root)::

    uv run python tests/baselines/_capture.py [--force]

The script writes a ``MANIFEST.json`` next to the baseline files recording the
git SHA (and dirty state), capture date, exact command, capture environment
(interpreter / numpy / scipy / pandas versions — REQUIRED fields), and
per-scenario status (CAPTURED / UNRUNNABLE with the error). Existing
baselines captured at the same SHA in the same environment are reused unless
``--force`` is given. The existing manifest ``audit_log`` is preserved and
appended to, never overwritten.
"""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
import traceback
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
BASELINE_DIR = REPO_ROOT / "tests" / "baselines"
MANIFEST_PATH = BASELINE_DIR / "MANIFEST.json"
COMMAND = "uv run python tests/baselines/_capture.py"


def capture_environment() -> dict[str, str]:
    """Interpreter and numeric-stack versions the baselines were solved under.

    REQUIRED manifest fields: ULP-level differences between numpy / scipy /
    interpreter versions amplify through solver regime boundaries, so a
    baseline is only meaningful together with the environment that produced
    it.
    """
    import numpy
    import scipy

    return {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
    }


def git_state() -> tuple[str, bool]:
    """Return (HEAD sha, dirty) for the working tree the capture ran in."""
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    return sha, dirty


def _json_safe(value: object) -> object:
    """Convert a cell to a deterministic, JSON-serializable value.

    Floats are kept as Python floats (json emits repr -> shortest round-trip,
    i.e. bit-exact on reload). NaN/inf become None so output is strict JSON.
    """
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (str, int, bool)):
        return value
    if hasattr(value, "item"):  # numpy scalar
        return _json_safe(value.item())
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if pd.isna(value):  # pandas NaT / NA
        return None
    return str(value)


def _frame_to_payload(df: pd.DataFrame) -> dict:
    return {
        "columns": [str(c) for c in df.columns],
        "n_rows": int(len(df)),
        "records": [
            {str(col): _json_safe(row[col]) for col in df.columns}
            for _, row in df.iterrows()
        ],
    }


def _run_example(config_path: Path) -> tuple[str, dict]:
    """Run one example through the appropriate engine entry point.

    Most examples are simulation configs for ``run_simulation_from_file``.
    Two special request formats are dispatched on their top-level keys:

    - ``{"config": ..., "sweeps": ...}`` -> ``ets.analysis.batch.run_batch``
    - ``{"config": ..., "observed_prices": ..., "participant_names": ...}``
      -> ``ets.analysis.calibration.calibrate_slopes``

    Returns (entry_point_name, payload_fragment).
    """
    from ets import run_simulation_from_file

    raw = json.loads(config_path.read_text())
    if isinstance(raw, dict) and "sweeps" in raw and "config" in raw:
        from ets.analysis.batch import run_batch

        result = run_batch(raw["config"], raw["sweeps"])
        return "ets.analysis.batch.run_batch", {"result": _json_safe(result)}
    if isinstance(raw, dict) and "observed_prices" in raw and "config" in raw:
        from ets.analysis.calibration import calibrate_slopes

        result = calibrate_slopes(
            raw["config"],
            raw["observed_prices"],
            raw["participant_names"],
        )
        return "ets.analysis.calibration.calibrate_slopes", {
            "result": _json_safe(result)
        }
    summary_df, participant_df = run_simulation_from_file(config_path)
    return "ets.run_simulation_from_file", {
        "summary": _frame_to_payload(summary_df),
        "participants": _frame_to_payload(participant_df),
    }


def capture(
    sha: str,
    dirty: bool,
    environment: dict[str, str],
    force: bool = False,
) -> dict:
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    statuses: dict[str, dict] = {}
    for config_path in sorted(EXAMPLES_DIR.glob("*.json")):
        name = config_path.stem
        out_path = BASELINE_DIR / f"{name}.json"
        if out_path.exists() and not force:
            try:
                existing = json.loads(out_path.read_text())
            except json.JSONDecodeError:
                existing = {}
            if (
                existing.get("git_sha") == sha
                and existing.get("environment") == environment
            ):
                statuses[name] = {"status": "CAPTURED", "reused": True}
                continue
        try:
            entry_point, fragment = _run_example(config_path)
        except Exception as exc:  # noqa: BLE001 - record any failure verbatim
            statuses[name] = {
                "status": "UNRUNNABLE",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback_tail": traceback.format_exc().splitlines()[-3:],
            }
            continue
        payload = {
            "scenario_file": f"examples/{config_path.name}",
            "git_sha": sha,
            "git_dirty": dirty,
            "captured": date.today().isoformat(),
            "command": COMMAND,
            "environment": environment,
            "entry_point": entry_point,
            **fragment,
        }
        out_path.write_text(
            json.dumps(payload, indent=1, sort_keys=False, allow_nan=False) + "\n"
        )
        status: dict = {"status": "CAPTURED", "reused": False, "entry_point": entry_point}
        if "summary" in fragment:
            status["summary_shape"] = [
                fragment["summary"]["n_rows"],
                len(fragment["summary"]["columns"]),
            ]
            status["participants_shape"] = [
                fragment["participants"]["n_rows"],
                len(fragment["participants"]["columns"]),
            ]
        statuses[name] = status
    return statuses


def main() -> None:
    force = "--force" in sys.argv[1:]
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    sha, dirty = git_state()
    environment = capture_environment()

    previous_audit_log: list[str] = []
    if MANIFEST_PATH.exists():
        try:
            previous_audit_log = list(
                json.loads(MANIFEST_PATH.read_text()).get("audit_log", [])
            )
        except json.JSONDecodeError:
            previous_audit_log = []

    statuses = capture(sha, dirty, environment, force=force)
    manifest = {
        "git_sha": sha,
        "git_dirty": dirty,
        "captured": date.today().isoformat(),
        "command": COMMAND + (" --force" if force else ""),
        "environment": environment,
        "entry_points": {
            "default": "ets.run_simulation_from_file (src/ets/solvers/simulation.py)",
            "batch_request": "ets.analysis.batch.run_batch",
            "calibration_request": "ets.analysis.calibration.calibrate_slopes",
        },
        "tolerance_policy": "bit-identical (rtol=0, atol=0) unless relaxed in-test "
        "with sign-off from lead-modeller and ets-lead-economist",
        "scenarios": statuses,
        "audit_log": previous_audit_log
        + [
            f"{date.today().isoformat()}: capture at {sha[:7]}"
            + (" (dirty tree)" if dirty else "")
            + f" under python {environment['python']} / numpy {environment['numpy']}"
            + f" / scipy {environment['scipy']} / pandas {environment['pandas']}"
            + (" [--force]" if force else ""),
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + "\n")
    for name, st in sorted(statuses.items()):
        print(f"{st['status']:<11} {name}" + (f"  ({st.get('error')})" if st.get("error") else ""))


if __name__ == "__main__":
    main()
