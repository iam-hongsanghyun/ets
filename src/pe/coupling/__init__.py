"""Feedback Option B — soft-link coupling.

Iteratively couples the ETS partial-equilibrium engine to an EXTERNAL model
(energy-system, CGE, DSGE, or any user-supplied responder). The ETS run produces
a carbon-price path; the external model maps that path to revised activity /
emissions; the ETS is re-run; repeat until the carbon price converges.

This keeps the ETS engine as the specialist allowance-market component and lets
general-equilibrium feedback live in a purpose-built model behind a thin adapter
— rather than embedding a CGE/DSGE in this codebase.

Public API:
    ExternalModel            – the adapter Protocol an external model implements
    NullExternalModel        – identity adapter (no feedback; converges in 1 step)
    ElasticityExternalModel  – reference adapter: activity responds to price via
                               a constant elasticity (runnable with no extra deps)
    CouplingResult           – per-iteration history + final converged results
    run_coupled_simulation   – the fixed-point orchestration loop
"""

from .adapters import ElasticityExternalModel, ExternalModel, NullExternalModel
from .loop import CouplingResult, run_coupled_simulation

__all__ = [
    "ExternalModel",
    "NullExternalModel",
    "ElasticityExternalModel",
    "CouplingResult",
    "run_coupled_simulation",
]
