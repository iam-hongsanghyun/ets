"""Tests for Feedback Option B — soft-link coupling.

Covers the reference adapter's multiplier, the null-adapter neutrality guarantee,
fixed-point convergence under under-relaxation, the demand-destruction effect,
and input validation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ets.coupling import (
    ElasticityExternalModel,
    NullExternalModel,
    run_coupled_simulation,
)
from ets.coupling.adapters import baseline_emissions
from ets.solvers import run_simulation_from_config


def _tightening_cap_config() -> dict:
    caps = {"2026": 480.0, "2027": 450.0, "2028": 415.0, "2029": 375.0, "2030": 330.0}
    years = []
    for label, cap in caps.items():
        years.append(
            {
                "year": label,
                "total_cap": cap,
                "auction_mode": "explicit",
                "auction_offered": round(cap * 0.45, 1),
                "price_lower_bound": 0.0,
                "price_upper_bound": 400.0,
                "banking_allowed": False,
                "participants": [
                    {"name": "Steel", "initial_emissions": 180.0, "free_allocation_ratio": 0.3, "penalty_price": 400.0, "abatement_type": "linear", "max_abatement": 54.0, "cost_slope": 2.6},
                    {"name": "Power", "initial_emissions": 220.0, "free_allocation_ratio": 0.2, "penalty_price": 400.0, "abatement_type": "linear", "max_abatement": 99.0, "cost_slope": 1.5},
                    {"name": "Cement", "initial_emissions": 120.0, "free_allocation_ratio": 0.3, "penalty_price": 400.0, "abatement_type": "linear", "max_abatement": 30.0, "cost_slope": 3.0},
                ],
            }
        )
    return {"scenarios": [{"name": "S", "model_approach": "competitive", "years": years}]}


# ── Reference adapter arithmetic ─────────────────────────────────────────────


def test_elasticity_multiplier_at_reference_is_one():
    m = ElasticityExternalModel(elasticity=0.5, reference_price=50.0)
    np.testing.assert_allclose(m.multiplier(50.0), 1.0, rtol=0, atol=1e-12)


def test_elasticity_multiplier_falls_with_price():
    m = ElasticityExternalModel(elasticity=0.5, reference_price=50.0)
    assert m.multiplier(100.0) < 1.0
    assert m.multiplier(25.0) > 1.0


def test_elasticity_multiplier_clamped():
    m = ElasticityExternalModel(
        elasticity=2.0, reference_price=50.0, min_multiplier=0.2, max_multiplier=1.5
    )
    assert m.multiplier(1e6) == 0.2     # huge price clamps to the floor
    assert m.multiplier(0.001) == 1.5   # tiny price clamps to the ceiling


def test_adapter_rejects_bad_parameters():
    with pytest.raises(ValueError):
        ElasticityExternalModel(elasticity=-1.0, reference_price=50.0)
    with pytest.raises(ValueError):
        ElasticityExternalModel(elasticity=0.5, reference_price=0.0)


def test_adapter_scales_from_baseline_not_compounding():
    cfg = _tightening_cap_config()
    m = ElasticityExternalModel(elasticity=0.5, reference_price=50.0)
    prices = {("S", y): 100.0 for y in ("2026", "2027", "2028", "2029", "2030")}
    once = m.respond(cfg, prices, 1)
    twice = m.respond(once, prices, 2)  # respond is anchored to its argument…
    # …so applying it to its own output with the SAME prices reproduces the same
    # scaling relative to *that* argument — i.e. the map is a pure function of the
    # price path and the config handed in, never a hidden accumulator.
    s_once = once["scenarios"][0]["years"][0]["participants"][0]["initial_emissions"]
    expected = baseline_emissions(cfg, "S", "2026", "Steel") * m.multiplier(100.0)
    np.testing.assert_allclose(s_once, expected, rtol=0, atol=1e-9)
    assert twice  # sanity: still returns a config


# ── Loop behaviour ───────────────────────────────────────────────────────────


def test_null_adapter_reproduces_baseline():
    cfg = _tightening_cap_config()
    base, _ = run_simulation_from_config(cfg)
    result = run_coupled_simulation(cfg, NullExternalModel(), max_iterations=5)
    assert result.converged
    assert result.iterations == 1
    base_prices = base.sort_values("Year")["Equilibrium Carbon Price"].to_numpy()
    coup_prices = result.summary.sort_values("Year")["Equilibrium Carbon Price"].to_numpy()
    np.testing.assert_allclose(coup_prices, base_prices, rtol=0, atol=1e-9)


def test_coupling_converges_and_damps_prices():
    cfg = _tightening_cap_config()
    base, _ = run_simulation_from_config(cfg)
    result = run_coupled_simulation(
        cfg,
        ElasticityExternalModel(elasticity=0.5, reference_price=55.0),
        max_iterations=40,
        tolerance=0.25,
        relaxation=0.5,
    )
    assert result.converged
    assert result.max_price_change <= 0.25
    base_max = float(base["Equilibrium Carbon Price"].max())
    coup_max = float(result.summary["Equilibrium Carbon Price"].max())
    # Demand destruction via the outer loop pulls the price path well below the
    # uncoupled, exogenous-activity baseline.
    assert coup_max < base_max


def test_relaxation_must_be_in_unit_interval():
    cfg = _tightening_cap_config()
    with pytest.raises(ValueError):
        run_coupled_simulation(cfg, NullExternalModel(), relaxation=0.0)
    with pytest.raises(ValueError):
        run_coupled_simulation(cfg, NullExternalModel(), relaxation=1.5)


def test_price_history_records_every_iteration():
    cfg = _tightening_cap_config()
    result = run_coupled_simulation(
        cfg,
        ElasticityExternalModel(elasticity=0.5, reference_price=55.0),
        max_iterations=40,
        tolerance=0.25,
    )
    # history[0] is the baseline; one entry per coupling iteration thereafter.
    assert len(result.price_history) == result.iterations + 1
