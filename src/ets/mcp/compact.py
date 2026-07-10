"""Compact per-scenario/per-year result summaries for the ``run_model`` tool.

``ets.engine.run_simulation_from_config`` returns full pandas DataFrames —
one row per scenario-year, with a ``f"{participant} <metric>"`` column for
*every* participant in the model — far too wide to hand an AI assistant
inline. This module keeps only the handful of scenario-level columns a
conversational "how did the model do" answer needs, and caps how many years
of one scenario it shows, so ``run_model``'s output stays a small, bounded
size regardless of how many participants or years the graph has.

Engineering caps below (``_MAX_YEARS_PER_SCENARIO``, ``_ROUND_DECIMALS``) are
not economic/model parameters — see ``ets.model_store``'s module docstring
for why this repo colocates constants of this kind in code rather than a
``.env`` loader.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

_MAX_YEARS_PER_SCENARIO = 12
_ROUND_DECIMALS = 4
_NONZERO_ATOL = 1e-9

# (compact key, summary_df column label) — see core/market/reporting.py:scenario_summary
# for where every one of these column labels is written.
_CORE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("price", "Equilibrium Carbon Price"),
    ("auction_offered", "Auction Offered"),
    ("auction_sold", "Auction Sold"),
    ("total_abatement", "Total Abatement"),
)
_BANK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("bank", "Total Ending Bank"),
    ("borrowed", "Total Borrowed Allowances"),
)
_MSR_COLUMNS: tuple[tuple[str, str], ...] = (
    ("msr_withheld", "MSR Withheld"),
    ("msr_released", "MSR Released"),
    ("msr_reserve_pool", "MSR Reserve Pool"),
)
_CCR_COLUMNS: tuple[tuple[str, str], ...] = (
    ("ccr_cap_adjustment", "CCR Cap Adjustment"),
    ("ccr_emissions_deviation", "CCR Emissions Deviation"),
    ("ccr_cost_deviation", "CCR Cost Deviation"),
)
_OPTIONAL_COLUMN_GROUPS: tuple[tuple[tuple[str, str], ...], ...] = (
    _BANK_COLUMNS,
    _MSR_COLUMNS,
    _CCR_COLUMNS,
)


def _round(value: Any) -> Any:
    try:
        return round(float(value), _ROUND_DECIMALS)
    except (TypeError, ValueError):
        return value


def _any_nonzero(frame: pd.DataFrame, columns: tuple[tuple[str, str], ...]) -> bool:
    return any(
        bool((frame[label].astype(float).abs() > _NONZERO_ATOL).any())
        for _, label in columns
        if label in frame.columns
    )


def _year_sort_index(frame: pd.DataFrame) -> pd.Index:
    """Chronological row order for one scenario's rows.

    Numeric year labels (``"2026"``) sort numerically; a non-numeric label
    (e.g. the ``"Base Year"`` fallback ``scenario_summary`` uses when a
    market has no explicit year) sorts after every numeric one, by falling
    back to the label itself only where the numeric parse failed.
    """
    if "Year" not in frame.columns:
        return frame.index
    numeric = pd.to_numeric(frame["Year"], errors="coerce")
    order_key = numeric.fillna(numeric.max(skipna=True) + 1 if numeric.notna().any() else 0)
    return order_key.sort_values().index


def compact_run_summary(
    summary_df: pd.DataFrame,
    *,
    scenario: str | None = None,
    max_years_per_scenario: int = _MAX_YEARS_PER_SCENARIO,
) -> dict[str, Any]:
    """Reduce a solved run's scenario-summary frame to a chat-sized dict.

    Args:
        summary_df: The scenario-summary frame — the first element of
            ``run_simulation_from_config``'s return tuple (one row per
            scenario-year).
        scenario: If given, only that scenario's rows are included; raises
            ``ValueError`` if no scenario in ``summary_df`` has that name.
        max_years_per_scenario: Truncate each scenario's year list to this
            many rows (chronological, from the start) — keeps the payload
            bounded for long-horizon models.

    Returns:
        ``{"scenarios": {name: {"years": [...], "total_years": int,
        "truncated": bool}}}``. Each year row always carries ``year``,
        ``price``, ``auction_offered``, ``auction_sold``,
        ``total_abatement``; ``bank``/``borrowed`` are added only if the
        scenario ever has a nonzero bank/borrow balance, and the three
        ``msr_*``/``ccr_*`` columns only if MSR/CCR is ever active — no
        participant-level columns, no raw DataFrame.

    Raises:
        ValueError: ``scenario`` is given and matches no scenario in
            ``summary_df``.
    """
    if summary_df.empty:
        return {"scenarios": {}}

    if scenario is not None:
        available = sorted(summary_df["Scenario"].unique())
        if scenario not in available:
            raise ValueError(f"Unknown scenario '{scenario}'; available: {available}")
        summary_df = summary_df[summary_df["Scenario"] == scenario]

    scenarios: dict[str, Any] = {}
    for scenario_name, frame in summary_df.groupby("Scenario", sort=False):
        ordered = frame.loc[_year_sort_index(frame)]
        total_years = len(ordered)
        truncated = total_years > max_years_per_scenario
        shown = ordered.iloc[:max_years_per_scenario]

        optional_groups = [
            columns for columns in _OPTIONAL_COLUMN_GROUPS if _any_nonzero(ordered, columns)
        ]

        years = []
        for _, row in shown.iterrows():
            year_row: dict[str, Any] = {"year": row.get("Year", "Base Year")}
            for key, label in _CORE_COLUMNS:
                if label in row:
                    year_row[key] = _round(row[label])
            for columns in optional_groups:
                for key, label in columns:
                    if label in row:
                        year_row[key] = _round(row[label])
            years.append(year_row)

        scenarios[str(scenario_name)] = {
            "years": years,
            "total_years": total_years,
            "truncated": truncated,
        }

    return {"scenarios": scenarios}
