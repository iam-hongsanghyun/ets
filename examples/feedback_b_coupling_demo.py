#!/usr/bin/env python3
"""Feedback Option B — soft-link coupling demo (runnable).

Couples the ETS partial-equilibrium engine to an EXTERNAL model via an
under-relaxed fixed-point loop:

    p_{k+1} = ETS( external_model.respond(config_0, p_k) )

Here the external model is the bundled reference adapter
(`ElasticityExternalModel`) — a self-contained stand-in for an energy-system /
CGE / DSGE model, so the demo runs with no extra dependencies. Swap it for your
own adapter (wrapping PyPSA, a CGE, a DSGE, …) by implementing the
`ExternalModel.respond` protocol; nothing else in the loop changes.

Run:
    PYTHONPATH=src python examples/feedback_b_coupling_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from ets.coupling import (
    ElasticityExternalModel,
    NullExternalModel,
    run_coupled_simulation,
)
from ets.solvers import run_simulation_from_config

REPO = Path(__file__).resolve().parents[1]


def _inelastic_baseline() -> dict:
    """Reuse the tightening-cap scenario from the Option A example (no in-engine
    feedback) as the baseline the external model will respond to."""
    cfg = json.loads((REPO / "examples" / "feedback_a_price_elastic_baseline.json").read_text())
    return {
        "scenarios": [
            s for s in cfg["scenarios"] if s["name"] == "Fixed Baseline (inelastic)"
        ]
    }


def _prices(summary) -> list[float]:
    return [round(float(x), 1) for x in summary.sort_values("Year")["Equilibrium Carbon Price"]]


def main() -> None:
    config = _inelastic_baseline()

    # 0) Uncoupled baseline — exogenous activity, the classic PE run.
    base_summary, _ = run_simulation_from_config(config)
    print("Uncoupled baseline prices :", _prices(base_summary))

    # 1) Control: the Null adapter applies no feedback → reproduces the baseline
    #    in a single iteration.
    null_result = run_coupled_simulation(config, NullExternalModel())
    print(
        f"Null-adapter coupling     : converged={null_result.converged} "
        f"in {null_result.iterations} iteration(s)"
    )

    # 2) Reference adapter: activity responds to the carbon price by a constant
    #    elasticity, anchored at a reference price. The loop under-relaxes the
    #    price signal so the fixed-point iteration does not oscillate.
    external = ElasticityExternalModel(elasticity=0.5, reference_price=55.0)
    result = run_coupled_simulation(
        config,
        external,
        max_iterations=40,
        tolerance=0.25,
        relaxation=0.5,
    )
    print(
        f"Elasticity coupling       : converged={result.converged} "
        f"in {result.iterations} iterations (max |Δprice|={result.max_price_change:.3f})"
    )
    print("Coupled (closed) prices   :", _prices(result.summary))
    print(
        "2030-cell price per iter  :",
        [round(h[("Fixed Baseline (inelastic)", "2030")], 1) for h in result.price_history],
    )
    print(
        "\nThe coupled path is far below the uncoupled one: feeding the carbon\n"
        "price back into activity (demand destruction) damps the price escalation\n"
        "the tightening cap would otherwise cause — the Option B (outer-loop)\n"
        "analogue of Option A's within-clearing feedback."
    )


if __name__ == "__main__":
    main()
