"""
CSV -> ETS config converter.

Accepts a CSV with columns (all lowercase, snake_case):
  year, participant_name, sector_group, initial_emissions, free_allocation_ratio,
  penalty_price, abatement_cost_slope, max_abatement_share,
  cbam_export_share, cbam_coverage_ratio, electricity_consumption,
  grid_emission_factor, scope2_cbam_coverage, production_output,
  benchmark_emission_intensity, sector_allocation_share

Produces a valid ETS config dict.
"""
from __future__ import annotations
import csv
import io
from typing import Any


def csv_to_config(csv_text: str, scenario_name: str = "Imported Scenario") -> dict[str, Any]:
    """
    Convert a CSV string to a valid ETS simulation config dict.

    Args:
        csv_text: CSV text with header row. Required columns: year, participant_name.
        scenario_name: Name to use for the generated scenario.

    Returns:
        A config dict with the structure {"scenarios": [...]}.
    """
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    rows = list(reader)

    def _f(row: dict, key: str, default: float = 0.0) -> float:
        v = row.get(key, "")
        try:
            return float(v) if str(v).strip() else default
        except (ValueError, AttributeError):
            return default

    # Group by year
    years_data: dict[str, list] = {}
    for row in rows:
        yr = str(row.get("year", "")).strip()
        if not yr:
            continue
        if yr not in years_data:
            years_data[yr] = []
        years_data[yr].append(row)

    years = []
    for yr in sorted(years_data.keys()):
        participants = []
        for row in years_data[yr]:
            name = str(row.get("participant_name", "")).strip()
            if not name:
                continue
            slope = _f(row, "abatement_cost_slope", 5.0)
            ie = _f(row, "initial_emissions", 0.0)
            max_abatement_share = _f(row, "max_abatement_share", 0.5)
            participants.append({
                "name": name,
                "sector_group": str(row.get("sector_group", "")).strip(),
                "initial_emissions": ie,
                "free_allocation_ratio": _f(row, "free_allocation_ratio", 0.0),
                "penalty_price": _f(row, "penalty_price", 100.0),
                "abatement_type": "linear",
                "abatement_cost_slope": slope,
                "cost_slope": slope,
                "max_abatement": ie * max_abatement_share,
                "max_abatement_share": max_abatement_share,
                "cbam_export_share": _f(row, "cbam_export_share", 0.0),
                "cbam_coverage_ratio": _f(row, "cbam_coverage_ratio", 1.0),
                "electricity_consumption": _f(row, "electricity_consumption", 0.0),
                "grid_emission_factor": _f(row, "grid_emission_factor", 0.0),
                "scope2_cbam_coverage": _f(row, "scope2_cbam_coverage", 0.0),
                "production_output": _f(row, "production_output", 0.0),
                "benchmark_emission_intensity": _f(row, "benchmark_emission_intensity", 0.0),
                "sector_allocation_share": _f(row, "sector_allocation_share", 0.0),
            })
        total_ie = sum(p["initial_emissions"] for p in participants)
        years.append({
            "year": yr,
            "total_cap": round(total_ie * 0.95, 2),
            "auction_offered": round(total_ie * 0.05, 2),
            "auction_mode": "explicit",
            "price_lower_bound": 0.0,
            "price_upper_bound": 200.0,
            "banking_allowed": True,
            "borrowing_allowed": False,
            "borrowing_limit": 0.0,
            "expectation_rule": "next_year_baseline",
            "participants": participants,
        })

    return {
        "scenarios": [{
            "name": scenario_name,
            "model_approach": "competitive",
            "years": years,
        }]
    }
