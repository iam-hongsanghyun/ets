"""Capture golden baselines for every scenario config in examples/*.json.

Runs each example through ``ets.run_simulation_from_file`` and serializes the
full solved output (scenario summary and per-participant-per-year detail) to
``tests/baselines/<scenario-file-stem>.json`` with round-trip-exact floats.

Usage (from the repo root)::

    uv run python tests/baselines/_capture.py [--force]
    uv run python tests/baselines/_capture.py --only STEM[,STEM...] [--force]

The script writes a ``MANIFEST.json`` next to the baseline files recording the
git SHA (and dirty state), capture date, exact command, capture environment
(interpreter / numpy / scipy / pandas versions — REQUIRED fields), and
per-scenario status (CAPTURED / UNRUNNABLE with the error). Existing
baselines captured at the same SHA in the same environment are reused unless
``--force`` is given. The existing manifest ``audit_log`` is preserved and
appended to, never overwritten.

``--only`` restricts the capture to one or more comma-separated example
stems (e.g. ``--only showcase_rps_rec``) — a SURGICAL capture: every other
baseline file is never opened/rewritten, and the manifest's ``scenarios``
table is MERGED with the previous one (only the named stem(s) change) rather
than replaced wholesale, so a one-off addition never perturbs the recorded
status/shape of every other example. Generic over the stem set — not
special-cased to any one example — so any future surgical capture reuses it.
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
            {str(col): _json_safe(row[col]) for col in df.columns} for _, row in df.iterrows()
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
    # PROVENANCE PINS (D0-R1 landmine 2): the three returned entry_point strings
    # ("ets.run_simulation_from_file", "ets.analysis.batch.run_batch",
    # "ets.analysis.calibration.calibrate_slopes") are baked byte-for-byte into
    # every baseline JSON and asserted by test_golden_baseline_replay. They are
    # historical provenance LABELS, not live import paths — FROZEN verbatim
    # across the ets->pe rename. The imports below move to pe; the return
    # literals do NOT. Migrate only on a legitimate future recapture.
    from pe import run_simulation_from_file

    raw = json.loads(config_path.read_text())
    if isinstance(raw, dict) and "sweeps" in raw and "config" in raw:
        from pe.analysis.batch import run_batch

        result = run_batch(raw["config"], raw["sweeps"])
        return "ets.analysis.batch.run_batch", {"result": _json_safe(result)}
    if isinstance(raw, dict) and "observed_prices" in raw and "config" in raw:
        from pe.analysis.calibration import calibrate_slopes

        result = calibrate_slopes(
            raw["config"],
            raw["observed_prices"],
            raw["participant_names"],
        )
        return "ets.analysis.calibration.calibrate_slopes", {"result": _json_safe(result)}
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
    only: frozenset[str] | None = None,
) -> dict:
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    statuses: dict[str, dict] = {}
    for config_path in sorted(EXAMPLES_DIR.glob("*.json")):
        name = config_path.stem
        if only is not None and name not in only:
            continue
        out_path = BASELINE_DIR / f"{name}.json"
        if out_path.exists() and not force:
            try:
                existing = json.loads(out_path.read_text())
            except json.JSONDecodeError:
                existing = {}
            if existing.get("git_sha") == sha and existing.get("environment") == environment:
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
        out_path.write_text(json.dumps(payload, indent=1, sort_keys=False, allow_nan=False) + "\n")
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


def _parse_only(argv: list[str]) -> frozenset[str] | None:
    """Parse ``--only STEM[,STEM...]`` / ``--only=STEM[,STEM...]`` from argv."""
    for index, arg in enumerate(argv):
        if arg == "--only" and index + 1 < len(argv):
            value = argv[index + 1]
        elif arg.startswith("--only="):
            value = arg.split("=", 1)[1]
        else:
            continue
        stems = frozenset(s.strip() for s in value.split(",") if s.strip())
        if not stems:
            raise ValueError("--only requires at least one non-empty stem.")
        return stems
    return None


def main() -> None:
    argv = sys.argv[1:]
    force = "--force" in argv
    only = _parse_only(argv)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    sha, dirty = git_state()
    environment = capture_environment()

    previous_manifest: dict = {}
    if MANIFEST_PATH.exists():
        try:
            previous_manifest = json.loads(MANIFEST_PATH.read_text())
        except json.JSONDecodeError:
            previous_manifest = {}
    previous_audit_log: list[str] = list(previous_manifest.get("audit_log", []))

    statuses = capture(sha, dirty, environment, force=force, only=only)
    # --only is a SURGICAL capture (module docstring): merge into the
    # previous manifest's scenario table rather than replacing it wholesale,
    # so every untouched example's recorded status/shape is byte-identical.
    scenarios = (
        {**previous_manifest.get("scenarios", {}), **statuses} if only is not None else statuses
    )
    audit_note = f"{date.today().isoformat()}: capture at {sha[:7]}"
    if only is not None:
        audit_note += f" [only: {', '.join(sorted(only))}]"
    audit_note += (
        (" (dirty tree)" if dirty else "")
        + f" under python {environment['python']} / numpy {environment['numpy']}"
        + f" / scipy {environment['scipy']} / pandas {environment['pandas']}"
        + (" [--force]" if force else "")
    )
    manifest = {
        # Preserve any top-level manifest key this script does not itself
        # manage (e.g. a `certification_chain`/`legacy_import_sweep` record
        # added out-of-band by a different order) — a bare dict literal here
        # would silently drop it on every run, --only or not; every field
        # below OVERWRITES its previous_manifest counterpart deliberately.
        **previous_manifest,
        "git_sha": sha,
        "git_dirty": dirty,
        "captured": date.today().isoformat(),
        "command": COMMAND
        + (" --force" if force else "")
        + (f" --only {','.join(sorted(only))}" if only is not None else ""),
        "environment": environment,
        "entry_points": {
            "default": "ets.run_simulation_from_file (src/ets/solvers/simulation.py)",
            "batch_request": "ets.analysis.batch.run_batch",
            "calibration_request": "ets.analysis.calibration.calibrate_slopes",
        },
        "tolerance_policy": "bit-identical (rtol=0, atol=0) unless relaxed in-test "
        "with sign-off from lead-modeller and ets-lead-economist",
        "scenarios": scenarios,
        "audit_log": previous_audit_log + [audit_note],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + "\n")
    for name, st in sorted(statuses.items()):
        print(f"{st['status']:<11} {name}" + (f"  ({st.get('error')})" if st.get("error") else ""))


if __name__ == "__main__":
    main()
