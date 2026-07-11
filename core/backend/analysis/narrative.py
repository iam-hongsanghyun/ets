"""
Rule-based narrative summary generator from simulation results.
"""
from __future__ import annotations
from typing import Any


def generate_narrative(simulation_results: list[dict[str, Any]], scenario_name: str = "") -> str:
    """
    Generate a plain-language summary paragraph from simulation results.

    Args:
        simulation_results: List of per-year result dicts, each with a "summary" key.
        scenario_name: Optional scenario name for the opening line.

    Returns:
        A plain-language narrative string.
    """
    if not simulation_results:
        return "No results available."

    summaries = [r["summary"] for r in simulation_results if "summary" in r]
    if not summaries:
        return "No summary data available."

    prices = [float(s.get("Equilibrium Carbon Price", 0)) for s in summaries]
    years = [str(r.get("year", "")) for r in simulation_results if "summary" in r]
    first_yr, last_yr = years[0] if years else "?", years[-1] if years else "?"
    p_first, p_last = prices[0], prices[-1]
    p_change = p_last - p_first
    p_change_pct = (p_change / p_first * 100) if p_first > 0 else 0.0

    total_abatement = sum(float(s.get("Total Abatement", 0)) for s in summaries)
    total_cost = sum(float(s.get("Total Compliance Cost", 0)) for s in summaries)
    total_cbam = sum(float(s.get("Total CBAM Liability", 0)) for s in summaries)
    total_auction_rev = sum(float(s.get("Total Auction Revenue", 0)) for s in summaries)
    cbam_foregone = sum(float(s.get("CBAM Foregone Revenue", 0)) for s in summaries)

    direction = "rises" if p_change > 0 else "falls" if p_change < 0 else "remains stable"
    lines = []
    sc = f"Scenario '{scenario_name}': " if scenario_name else ""
    lines.append(
        f"{sc}The equilibrium carbon price {direction} from "
        f"₩{p_first:,.0f}/t in {first_yr} to ₩{p_last:,.0f}/t in {last_yr} "
        f"({p_change_pct:+.1f}% over the period)."
    )
    lines.append(
        f"Cumulative abatement across the pathway totals {total_abatement:,.1f} Mt CO₂e, "
        f"with total compliance costs of ₩{total_cost:,.0f}."
    )
    if total_cbam > 0:
        lines.append(
            f"CBAM exposure amounts to ₩{total_cbam:,.0f} cumulatively. "
            f"Of this, ₩{cbam_foregone:,.0f} represents revenue foregone to the EU — "
            f"funds that would remain in Korea if KAU prices equalled EUA levels."
        )
    if total_auction_rev > 0:
        lines.append(
            f"Domestic auction revenue totals ₩{total_auction_rev:,.0f}, "
            "available for reinvestment in green transition programmes."
        )
    return " ".join(lines)
