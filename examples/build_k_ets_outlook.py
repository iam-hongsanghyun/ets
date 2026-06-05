"""Generate an ETS-framework config that mimics the K-ETS Outlook model.

Reads the K-ETS dashboard's published model output
(``k-ets/src/lib/model_output.json``) and translates its inputs into the
ETS simulator's scenario/year/participant JSON schema.

K-ETS model (v0.6): "Staircase MACC + Hotelling banking (constrained). Coase:
equilibrium price set by BAU - Cap; free allocation affects only fiscal."

Mapping onto this framework
---------------------------
* model_approach = "hotelling"  -> P(t) = lambda * (1 + r)^(t - t0), with lambda
  (= p0) chosen so cumulative residual emissions equal the cumulative carbon
  budget. This is exactly K-ETS's constrained Hotelling banking (stock >= 0).
* discount_rate = r = 0.055 (the K-ETS Hotelling growth rate).
* carbon_budget[year] = total_cap[year] = K-ETS cap path (per scenario).
* Each of the 6 K-ETS sectors becomes a participant. Yearly initial_emissions
  follow the K-ETS BAU path, split by the sector's share of the static sector
  baselines. mac_blocks are the sector's technologies as a staircase
  (potential_Mt -> amount, cost_krw -> marginal_cost), sorted by ascending cost.
  Negative-cost "no-regret" measures are kept verbatim (framework now supports
  negative marginal_cost).
* TRANSITION: K-ETS's technology transition is a learning curve (NOT timeline
  gating — its `timeline` strings are descriptive only). RE/H2/electrification
  costs decay cost*(1-rate)^(year-2026) with rate 2%/4%/6% for base/middle/ideal.
  mac_blocks are rebuilt per year with adjusted costs and re-sorted ascending.
* free_allocation_ratio = 0 with auction_mode "derive_from_cap": the whole cap
  is tradable, so the clearing price depends only on BAU - cap (the Coase
  property). The free-allocation split is price-neutral here, as in K-ETS.
* international_offset_* fields reconstruct K-ETS's "international reduction
  smoothed step": above INTL_COST_KRW, up to INTL_CAPACITY_MT of overseas
  credits enter (ramped over INTL_BAND_KRW), acting as the soft price ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

KETS_MODEL = Path("/Users/sanghyun/github/k-ets/src/lib/model_output.json")
OUT_CONFIG = Path(__file__).resolve().parent / "climate_solutions_k_ets_outlook.json"

HOTELLING_RATE = 0.055           # K-ETS Hotelling growth rate r
PRICE_UPPER_BOUND = 2_000_000.0  # KRW/tCO2 — loose solver bracket, non-binding
BASE_YEAR = 2026

# International reduction (국제감축) smoothed-step backstop.
INTL_CAPACITY_MT = 100.0         # max overseas credits available per year (Mt)
INTL_COST_KRW = 200_000.0        # international credit cost (KRW/tCO2), tunable
INTL_BAND_KRW = 20_000.0         # price band over which the step ramps in

# K-ETS technology TRANSITION = a learning curve, not timeline gating.
# (k-ets/src/components/Simulator.tsx): RE/H2/electrification tech costs decay
# adjusted_cost = cost * (1 - rate)^(year - 2026); negative-cost measures exempt.
LEARNING_RATE = {"base": 0.02, "middle": 0.04, "ideal": 0.06}
RE_KEYWORDS = ("태양광", "풍력", "수소", "H₂", "전기크래킹", "전기가열", "열펌프", "암모니아")


def adjusted_cost(cost_krw: float, tech_name: str, year: int, rate: float) -> float:
    """Learning-curve-adjusted marginal cost for a technology in a given year.

    Only positive-cost RE/hydrogen/electrification technologies decay; negative-
    cost "no-regret" measures and conventional measures keep their cost.
    """
    if cost_krw > 0 and any(k in tech_name for k in RE_KEYWORDS):
        return cost_krw * (1.0 - rate) ** (year - BASE_YEAR)
    return cost_krw

SCENARIO_LABELS = {
    "base": "K-ETS Outlook — Base (current policy)",
    "middle": "K-ETS Outlook — Middle (NDC-linked auction)",
    "ideal": "K-ETS Outlook — Ideal (CBAM-aligned, free alloc -> 0 by 2034)",
}
SECTOR_KO = {
    "steel": "Steel",
    "petrochem": "Petrochem",
    "power": "Power",
    "cement": "Cement",
    "refinery": "Refinery",
    "other": "Other",
}


def load_kets() -> dict:
    with KETS_MODEL.open(encoding="utf-8") as fh:
        return json.load(fh)


def build_sector_mac_blocks(
    techs: list[dict], year: int, rate: float
) -> dict[str, list[dict]]:
    """Group K-ETS technologies by sector into ascending-cost staircase blocks,
    applying the learning curve for the given year and scenario learning rate.

    Blocks are re-sorted by (learning-adjusted) ascending cost each year because
    declining RE costs can reorder the staircase; the framework requires
    non-decreasing marginal_cost.
    """
    by_sector: dict[str, list[tuple[float, dict]]] = {}
    for tech in techs:
        cost = adjusted_cost(float(tech["cost_krw"]), tech["technology"], year, rate)
        block = {"amount": round(float(tech["potential_Mt"]), 4),
                 "marginal_cost": round(cost, 2)}
        by_sector.setdefault(tech["sector"], []).append((cost, block))
    out: dict[str, list[dict]] = {}
    for sector, items in by_sector.items():
        items.sort(key=lambda pair: pair[0])  # ascending adjusted cost
        out[sector] = [block for _cost, block in items]
    return out


def build_config(kets: dict) -> dict:
    start = int(kets["analysis_period"]["start"])
    end = int(kets["analysis_period"]["end"])
    years = list(range(start, end + 1))

    baselines = kets["sector_baselines"]
    total_baseline = sum(baselines.values())
    techs = kets["macc_technologies"]

    scenarios = []
    for scen_id, label in SCENARIO_LABELS.items():
        sd_by_year = {int(p["year"]): p for p in kets["supply_demand"][scen_id]}
        rate = LEARNING_RATE[scen_id]

        year_blocks = []
        for y in years:
            sd = sd_by_year[y]
            bau_total = float(sd["bau_Mt"])
            cap = float(sd["cap_Mt"])
            # Per-year, per-scenario staircase MACC with learning-curve transition.
            mac_by_sector = build_sector_mac_blocks(techs, y, rate)

            participants = []
            for sector, baseline in baselines.items():
                share = baseline / total_baseline
                participants.append({
                    "name": SECTOR_KO[sector],
                    "initial_emissions": round(bau_total * share, 4),
                    "free_allocation_ratio": 0.0,   # price-neutral; cap fully tradable
                    "penalty_price": 0.0,           # 0 == no ceiling (+inf)
                    "abatement_type": "piecewise",
                    "mac_blocks": mac_by_sector[sector],
                    "sector_group": SECTOR_KO[sector],
                })

            year_blocks.append({
                "year": str(y),
                "total_cap": round(cap, 4),
                "carbon_budget": round(cap, 4),     # Hotelling cumulative budget
                "auction_mode": "derive_from_cap",
                "banking_allowed": True,
                "borrowing_allowed": False,
                "price_lower_bound": 0.0,
                "price_upper_bound": PRICE_UPPER_BOUND,
                "expectation_rule": "perfect_foresight",
                # International reduction smoothed step (soft price ceiling)
                "international_offset_cost": INTL_COST_KRW,
                "international_offset_limit": INTL_CAPACITY_MT,
                "international_offset_band": INTL_BAND_KRW,
                "participants": participants,
            })

        scenarios.append({
            "name": label,
            "model_approach": "hotelling",
            "discount_rate": HOTELLING_RATE,
            "risk_premium": 0.0,
            "years": year_blocks,
        })

    return {"scenarios": scenarios}


def main() -> None:
    kets = load_kets()
    config = build_config(kets)
    with OUT_CONFIG.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_CONFIG}")
    print(f"Scenarios: {[s['name'] for s in config['scenarios']]}")
    print(f"Years per scenario: {len(config['scenarios'][0]['years'])}")
    print(f"Participants/year: {len(config['scenarios'][0]['years'][0]['participants'])}")
    steel = config['scenarios'][0]['years'][0]['participants'][0]
    print(f"Steel mac_blocks (note negative first block): {steel['mac_blocks']}")


if __name__ == "__main__":
    main()
