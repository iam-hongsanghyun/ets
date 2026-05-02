"""
Batch / sensitivity runner: sweep one or more parameters and collect results.

A "sweep" specifies a JSON-path into the config and a list of values to try.
All combinations are run and results aggregated.

Usage:
  sweeps = [
    {"path": "scenarios[0].years[*].eua_price", "values": [40, 60, 80, 100]},
  ]
  results = run_batch(base_config, sweeps)
"""
from __future__ import annotations
import copy
import itertools
from typing import Any


def _set_path(cfg: dict, path: str, value: Any) -> dict:
    """
    Set a value at a dotted/bracketed path. Supports:
      scenarios[0].years[*].eua_price   -> sets eua_price on ALL years
      scenarios[0].discount_rate        -> sets scalar
    """
    cfg = copy.deepcopy(cfg)
    parts = path.replace("[", ".").replace("]", "").split(".")
    obj = cfg
    for i, part in enumerate(parts[:-1]):
        if part == "*":
            # wildcard: apply to remaining path on each list element
            sub_path = ".".join(parts[i + 1:])
            for item in obj:
                _set_path_inplace(item, sub_path, value)
            return cfg
        elif part.isdigit():
            obj = obj[int(part)]
        else:
            obj = obj[part]
    last = parts[-1]
    if last.isdigit():
        obj[int(last)] = value
    else:
        obj[last] = value
    return cfg


def _set_path_inplace(obj: Any, path: str, value: Any) -> None:
    parts = path.replace("[", ".").replace("]", "").split(".")
    for part in parts[:-1]:
        if part.isdigit():
            obj = obj[int(part)]
        else:
            obj = obj[part]
    last = parts[-1]
    if last.isdigit():
        obj[int(last)] = value
    else:
        obj[last] = value


def run_batch(
    base_config: dict[str, Any],
    sweeps: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run all combinations of sweep values and return aggregated results.

    Args:
        base_config: Base simulation config.
        sweeps: List of {"path": str, "values": list, "label": str (optional)}.

    Returns:
        {"runs": [...], "sweep_axes": [...], "summary_table": [...]}
        Each run has "params" (dict of path->value) and "results" (list of year summaries).
    """
    from ..config_io.builder import build_markets_from_config
    from ..solvers.simulation import run_simulation

    paths = [s["path"] for s in sweeps]
    value_lists = [s["values"] for s in sweeps]
    labels = [s.get("label", s["path"]) for s in sweeps]

    runs = []
    for combo in itertools.product(*value_lists):
        cfg = copy.deepcopy(base_config)
        params = {}
        for path, val in zip(paths, combo):
            cfg = _set_path(cfg, path, val)
            params[path] = val
        try:
            markets = build_markets_from_config(cfg)
            summary_df, _ = run_simulation(markets)
            year_summaries = []
            if not summary_df.empty:
                for _, row in summary_df.iterrows():
                    year_summaries.append({
                        "year": str(row.get("Year", "")),
                        "price": float(row.get("Equilibrium Carbon Price", 0)),
                        "total_abatement": float(row.get("Total Abatement", 0)),
                        "total_compliance_cost": float(row.get("Total Compliance Cost", 0)),
                        "total_cbam_liability": float(row.get("Total CBAM Liability", 0)),
                        "total_auction_revenue": float(row.get("Total Auction Revenue", 0)),
                    })
            runs.append({"params": params, "results": year_summaries, "error": None})
        except Exception as exc:
            runs.append({"params": params, "results": [], "error": str(exc)})

    return {
        "sweep_axes": [{"path": p, "label": l, "values": v}
                       for p, l, v in zip(paths, labels, value_lists)],
        "runs": runs,
        "n_runs": len(runs),
        "n_errors": sum(1 for r in runs if r["error"]),
    }
