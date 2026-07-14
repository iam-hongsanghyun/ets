"""pe-run analysis-surface tests.

Exercises the tool FUNCTIONS directly (``pe.mcp.analysis_tools``) — no MCP
transport — mirroring ``test_mcp_models.py``. Covers:

  (a) ``narrate_model`` returns a plain-language paragraph for a solved model.
  (b) ``run_batch`` reduces a multi-value sweep to per-combination headlines.
  (c) ``compute_investment_trigger`` matches the ``pe.core.investment`` kernel.
  (d) forward calibration (``calibrate_from_elasticity`` /
      ``calibrate_abatement_from_reference``) reproduces the anchor, and an
      unknown curve is rejected.
  (e) ``import_csv`` turns a per-year CSV into a runnable config.
  (f) the pe-run server registers the analysis tools alongside the governor.
"""

from __future__ import annotations

import asyncio

import pytest

from pe.core import investment
from pe.mcp import analysis_tools

# A bundled example that solves to a non-trivial price path (used read-only).
_EXAMPLE_MODEL = "banking_msr"


def test_narrate_model_returns_prose() -> None:
    result = analysis_tools.narrate_model(_EXAMPLE_MODEL)
    assert result["model_id"] == _EXAMPLE_MODEL
    assert isinstance(result["narrative"], str)
    assert "price" in result["narrative"].lower()


def test_run_batch_reduces_to_per_combination_headlines() -> None:
    result = analysis_tools.run_batch(
        _EXAMPLE_MODEL,
        [{"path": "scenarios[0].years[*].total_cap", "values": [90, 100]}],
    )
    assert result["model_id"] == _EXAMPLE_MODEL
    assert result["n_runs"] == 2
    assert result["n_errors"] == 0
    assert len(result["runs"]) == 2
    # Each run carries its swept params and a final-year headline, not raw years.
    for run in result["runs"]:
        assert "params" in run
        assert set(run) == {"params", "error", "final_year", "final_price", "cumulative_abatement"}


def test_run_batch_rejects_empty_sweeps() -> None:
    with pytest.raises(ValueError, match="at least one sweep axis"):
        analysis_tools.run_batch(_EXAMPLE_MODEL, [])


def test_compute_investment_trigger_matches_kernel() -> None:
    sigma, r, y = 0.2, 0.05, 0.04
    result = analysis_tools.compute_investment_trigger(sigma, r, y)
    assert result["trigger_multiple"] == pytest.approx(investment.trigger_multiple(sigma, r, y))
    assert result["beta"] == pytest.approx(investment.beta_positive_root(sigma, r, y))
    # No credibility -> no floor keys.
    assert "credible_floor_multiple" not in result


def test_compute_investment_trigger_with_credibility_adds_floor() -> None:
    result = analysis_tools.compute_investment_trigger(0.2, 0.05, 0.04, credibility=0.5)
    assert result["credibility"] == 0.5
    assert result["effective_volatility"] == pytest.approx(
        investment.effective_volatility(0.2, 0.5)
    )
    assert result["credible_floor_multiple"] == pytest.approx(
        investment.credible_floor_multiple(0.05, 0.04)
    )


def test_calibrate_from_elasticity_reproduces_demand_anchor() -> None:
    result = analysis_tools.calibrate_from_elasticity("product_demand", -0.5, 100.0, 50.0)
    block = result["block"]
    # eps_D = -b_d * P / Q  ->  b_d = |eps| * Q / P = 0.5 * 50 / 100 = 0.25
    assert block["b_d"] == pytest.approx(0.25)
    # A_d - b_d * P = Q  (curve passes through the anchor)
    assert block["A_d"] - block["b_d"] * 100.0 == pytest.approx(50.0)


def test_calibrate_from_elasticity_rejects_unknown_curve() -> None:
    with pytest.raises(ValueError, match="Unknown curve"):
        analysis_tools.calibrate_from_elasticity("not_a_curve", -0.5, 100.0, 50.0)


def test_calibrate_abatement_from_reference_pins_beta() -> None:
    result = analysis_tools.calibrate_abatement_from_reference(30.0, 10.0, a_max=40.0)
    # MAC = beta * a -> beta = carbon_price / abatement = 30 / 10 = 3
    assert result["block"]["beta"] == pytest.approx(3.0)
    assert result["block"]["a_max"] == 40.0


def test_import_csv_builds_a_runnable_config() -> None:
    csv_text = (
        "year,participant_name,initial_emissions,total_cap\n"
        "2026,Firm A,110,100\n"
        "2027,Firm A,108,95\n"
    )
    result = analysis_tools.import_csv(csv_text, scenario_name="From CSV")
    config = result["config"]
    assert "scenarios" in config
    assert config["scenarios"], "expected at least one scenario"


def test_pe_run_server_registers_analysis_and_governor_tools() -> None:
    from pe.mcp.run.server import build_server

    async def _names() -> set[str]:
        return {t.name for t in await build_server().list_tools()}

    names = asyncio.run(_names())
    assert {"run_batch", "narrate_model", "import_csv", "compute_investment_trigger"} <= names
    assert {"list_models", "run_model", "compare_models", "sweep_model"} <= names
