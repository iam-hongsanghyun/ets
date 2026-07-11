"""D2-8: the MCP compact run summary surfaces joint-equilibrium convergence.

The Joint diagnostics are stamped only on cyclic-SCC rows (dispatch
key-presence guard), so they are PRESENCE-guarded in ``compact_run_summary``,
not nonzero-guarded — a non-converged cyclic SCC stamps ``Joint Converged =
0.0``, which the user most needs to see. An acyclic run never carries the
columns, so its compact summary is unchanged (config-driven display).
"""

from __future__ import annotations

import pandas as pd

from pe.mcp.compact import compact_run_summary

_CORE = {
    "Equilibrium Carbon Price": 165.0,
    "Auction Offered": 100.0,
    "Auction Sold": 100.0,
    "Total Abatement": 40.0,
}


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_cyclic_run_surfaces_joint_columns() -> None:
    frame = _frame(
        [
            {
                "Scenario": "cyc :: A",
                "Year": "2030",
                **_CORE,
                "Joint Converged": 1.0,
                "Joint Outer Iterations": 4.0,
                "Joint Max Normalized Change": 3.2e-13,
                "Joint Cycle Detected": 0.0,
            }
        ]
    )
    out = compact_run_summary(frame)
    year_row = out["scenarios"]["cyc :: A"]["years"][0]
    assert year_row["joint_converged"] == 1.0
    assert year_row["joint_outer_iterations"] == 4.0
    assert year_row["joint_cycle_detected"] == 0.0
    assert "joint_max_normalized_change" in year_row


def test_non_converged_cyclic_run_still_shows_joint_converged_zero() -> None:
    # Joint Converged == 0.0 is the case the user MOST needs surfaced; a
    # nonzero filter would wrongly hide it. Presence-guarding keeps it.
    frame = _frame(
        [
            {
                "Scenario": "osc :: A",
                "Year": "2030",
                **_CORE,
                "Joint Converged": 0.0,
                "Joint Outer Iterations": 500.0,
                "Joint Max Normalized Change": 0.42,
                "Joint Cycle Detected": 2.0,
            }
        ]
    )
    out = compact_run_summary(frame)
    year_row = out["scenarios"]["osc :: A"]["years"][0]
    assert year_row["joint_converged"] == 0.0
    assert year_row["joint_cycle_detected"] == 2.0


def test_acyclic_run_carries_no_joint_columns() -> None:
    frame = _frame([{"Scenario": "flat", "Year": "2030", **_CORE}])
    out = compact_run_summary(frame)
    year_row = out["scenarios"]["flat"]["years"][0]
    assert not any(key.startswith("joint_") for key in year_row)
    assert year_row["price"] == 165.0
