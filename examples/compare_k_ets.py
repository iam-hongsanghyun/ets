"""Run the K-ETS-mimic config through the ETS framework and compare to K-ETS."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/Users/sanghyun/github/ets/src")))

from ets import run_simulation_from_file  # noqa: E402

KETS_MODEL = Path("/Users/sanghyun/github/k-ets/src/lib/model_output.json")
CONFIG = Path("/Users/sanghyun/github/ets/examples/climate_solutions_k_ets_outlook.json")

SCEN_MAP = {  # framework scenario name -> k-ets scenario id
    "K-ETS Outlook — Base (current policy)": "base",
    "K-ETS Outlook — Middle (NDC-linked auction)": "middle",
    "K-ETS Outlook — Ideal (CBAM-aligned, free alloc -> 0 by 2034)": "ideal",
}


def main() -> None:
    kets = json.load(KETS_MODEL.open(encoding="utf-8"))
    summary, _participants = run_simulation_from_file(CONFIG)

    for scen_name, scen_id in SCEN_MAP.items():
        rows = summary[summary["Scenario"] == scen_name].copy()
        rows["Year"] = rows["Year"].astype(int)
        rows = rows.sort_values("Year")
        fw_price = dict(zip(rows["Year"], rows["Equilibrium Carbon Price"]))

        kets_path = {int(p["year"]): p["kau_price_krw"]
                     for p in kets["scenarios"][scen_id]["price_path"]}

        print("\n" + "=" * 78)
        print(f"SCENARIO: {scen_id.upper()}  ({scen_name})")
        print("=" * 78)
        print(f"{'Year':>5} | {'K-ETS KRW':>12} | {'Framework KRW':>14} | "
              f"{'Diff':>11} | {'Diff %':>7}")
        print("-" * 78)
        for y in sorted(kets_path):
            k = kets_path[y]
            f = fw_price.get(y, float("nan"))
            diff = f - k
            pct = 100.0 * diff / k if k else float("nan")
            print(f"{y:>5} | {k:>12,.0f} | {f:>14,.0f} | {diff:>11,.0f} | {pct:>6.1f}%")

        # headline year check
        for hy in (2030, 2040):
            k = kets_path[hy]
            f = fw_price[hy]
            print(f"   -> {hy}: K-ETS {k:,.0f}  vs  framework {f:,.0f}  "
                  f"({100*(f-k)/k:+.1f}%)")


if __name__ == "__main__":
    main()
