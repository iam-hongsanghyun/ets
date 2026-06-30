"""The soft-link coupling fixed-point loop (Feedback Option B).

Iterates the ETS engine against an external model until the carbon-price path
stops moving:

    p_{k+1} = ETS( external_model.respond(config_0, p_k) )

solving the fixed point  p = ETS(respond(config_0, p)).  This is the outer-loop
sibling of Feedback Option A: A solves the activity↔price interaction *inside*
each period's clearing; B solves it *between* full ETS runs, with the activity
response supplied by a pluggable model.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field

import pandas as pd

from ..config_io import normalize_config
from ..solvers import run_simulation_from_config
from .adapters import ExternalModel, PriceMap

logger = logging.getLogger(__name__)


@dataclass
class CouplingResult:
    """Outcome of a coupled run."""

    summary: pd.DataFrame                 # final ETS scenario summary
    participants: pd.DataFrame            # final ETS participant results
    price_history: list[PriceMap] = field(default_factory=list)  # prices per iteration
    converged: bool = False
    iterations: int = 0
    max_price_change: float = float("inf")  # final iteration's max |Δprice|


def _extract_prices(summary: pd.DataFrame) -> PriceMap:
    """Map (scenario, year) → equilibrium carbon price from a summary frame."""
    prices: PriceMap = {}
    for _, row in summary.iterrows():
        scenario = str(row.get("Scenario", ""))
        year = str(row.get("Year", ""))
        prices[(scenario, year)] = float(row["Equilibrium Carbon Price"])
    return prices


def _max_price_change(previous: PriceMap, current: PriceMap) -> float:
    keys = set(previous) | set(current)
    return max(
        (abs(current.get(k, 0.0) - previous.get(k, 0.0)) for k in keys),
        default=0.0,
    )


def _relax(previous: PriceMap, current: PriceMap, weight: float) -> PriceMap:
    """Under-relax the price signal: (1-w)·previous + w·current, key by key."""
    keys = set(previous) | set(current)
    return {
        k: (1.0 - weight) * previous.get(k, current.get(k, 0.0))
        + weight * current.get(k, previous.get(k, 0.0))
        for k in keys
    }


def run_coupled_simulation(
    config: dict,
    external_model: ExternalModel,
    max_iterations: int = 25,
    tolerance: float = 0.5,
    relaxation: float = 0.5,
) -> CouplingResult:
    """Run the ETS↔external-model fixed-point loop to carbon-price convergence.

    Parameters
    ----------
    config : dict
        The baseline scenario config (iteration-0 activity).
    external_model : ExternalModel
        Adapter mapping a carbon-price path to revised activity. See
        :mod:`ets.coupling.adapters`.
    max_iterations : int
        Hard cap on coupling iterations.
    tolerance : float
        Convergence threshold on the maximum absolute carbon-price change
        (in price units) across all (scenario, year) cells between iterations.
    relaxation : float
        Under-relaxation weight w ∈ (0, 1] applied to the price signal fed back
        to the external model: ``input ← (1-w)·input + w·latest``. Values below 1
        damp oscillation in the fixed-point iteration; ``1.0`` is a plain
        (undamped) Gauss–Seidel step. Default 0.5.

    Returns
    -------
    CouplingResult
        Final ETS results plus the per-iteration price history and convergence
        diagnostics.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive.")
    if not 0.0 < relaxation <= 1.0:
        raise ValueError("relaxation must be in the interval (0, 1].")

    baseline_config = normalize_config(deepcopy(config))

    # Iteration 0 — the uncoupled baseline run sets the initial price signal.
    summary, participants = run_simulation_from_config(baseline_config)
    signal = _extract_prices(summary)        # price input fed to the external model
    history: list[PriceMap] = [signal]
    logger.info("Coupling iteration 0 (baseline): %d price cells", len(signal))

    converged = False
    max_change = float("inf")
    completed = 0
    for iteration in range(1, max_iterations + 1):
        # F(signal): map the (relaxed) price signal to activity, then re-clear.
        updated_config = external_model.respond(baseline_config, signal, iteration)
        summary, participants = run_simulation_from_config(updated_config)
        realised = _extract_prices(summary)
        history.append(realised)

        # Self-consistency: did the clearing reproduce the price we assumed?
        max_change = _max_price_change(signal, realised)
        completed = iteration
        logger.info(
            "Coupling iteration %d: max |Δprice| = %.4f (tol %.4f)",
            iteration,
            max_change,
            tolerance,
        )
        if max_change <= tolerance:
            converged = True
            break
        # Under-relax the signal toward the realised price for the next pass.
        signal = _relax(signal, realised, relaxation)

    if not converged:
        logger.warning(
            "Coupling did not converge in %d iterations (max |Δprice| = %.4f > tol %.4f).",
            max_iterations,
            max_change,
            tolerance,
        )

    return CouplingResult(
        summary=summary,
        participants=participants,
        price_history=history,
        converged=converged,
        iterations=completed,
        max_price_change=max_change,
    )
