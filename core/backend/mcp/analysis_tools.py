"""Stateless tool implementations behind the pe-run server's *analysis* surface.

The running/analysis server has two halves: model *operation* (``pe.mcp.
models_tools`` — run/compare/sweep the registry) and *post-processing*
analysis (this module). These wrap the ``pe.analysis`` package (the same T4
workflows ``pe.web.api``'s ``/api/batch-run``/``/api/narrative``/
``/api/import-csv`` endpoints expose) up as MCP tools:

* ``run_batch`` — multi-axis parameter sweep of a registered model,
  reduced to per-combination headlines (``pe.analysis.batch``).
* ``narrate_model`` — plain-language summary of a model's price/abatement
  path (``pe.analysis.narrative``).
* ``import_csv`` — turn a per-year CSV into a runnable config
  (``pe.analysis.csv_import``).
* ``investment_trigger`` — Dixit–Pindyck real-options trigger multiple and
  break-even dating (``pe.analysis.investment_trigger`` -> ``pe.core.investment``).
* ``calibrate_slopes`` — inverse-fit participant MAC slopes to observed
  prices; ``calibrate_from_elasticity`` / ``calibrate_abatement_from_reference``
  — forward calibration of a demand/supply/abatement block from one anchor
  (``pe.analysis.calibration``).

These functions are plain and side-effect-free (they run solves and read
configs; they never write the registry), imported directly by
``pe.mcp.run.server`` (wrapped as MCP tools) and by
``tests/apps/mcp/test_mcp_analysis.py`` (exercised directly, no MCP transport).

Dependency law: same as any T5 app — imports ``pe.analysis``,
``pe.model_store``, ``pe.engine``, and stdlib.
"""

from __future__ import annotations

from typing import Any

from .. import model_store
from ..analysis import batch, calibration, csv_import, investment_trigger, narrative
from ..engine import run_simulation_from_config
from .compact import compact_sweep_summary

# ── 1. run_batch ─────────────────────────────────────────────────────────


def run_batch(model_id: str, sweeps: list[dict[str, Any]]) -> dict[str, Any]:
    """Sweep a registered model over one or more parameter axes.

    Runs every combination of the swept values and returns one headline row
    per combination — the multi-axis generalisation of the governor's
    ``sweep_model`` (which sweeps a single path). Use it for "what happens as
    I vary the cap AND the floor together" grids.

    Args:
        model_id: An example stem or registry ``"user_<slug>"`` id (see the
            run server's ``list_models``).
        sweeps: One entry per axis, each ``{"path": <dotted config path>,
            "values": [...], "label": <optional>}`` — e.g. ``[{"path":
            "scenarios[0].years[*].total_cap", "values": [90, 100, 110]}]``.

    Returns:
        ``{"model_id", "sweep_axes", "runs": [{"params", "error",
        "final_year", "final_price", "cumulative_abatement"}, ...], "n_runs",
        "n_errors"}`` — one ``runs`` entry per value combination, reduced to
        final-year price and cumulative abatement (see
        ``pe.mcp.compact.compact_sweep_summary``); never every year of every
        run.

    Raises:
        ModelStoreError: ``model_id`` matches no known model.
        ValueError: ``sweeps`` is empty or malformed.
    """
    if not sweeps:
        raise ValueError("Pass at least one sweep axis: [{'path': ..., 'values': [...]}].")
    base_config = model_store.resolve_model_config(model_id)
    result = batch.run_batch(base_config=base_config, sweeps=sweeps)
    return {
        "model_id": model_id,
        "sweep_axes": result["sweep_axes"],
        **compact_sweep_summary(result),
    }


# ── 2. narrate_model ─────────────────────────────────────────────────────

# The one summary column narrative keys its per-year records off (it reads
# each record's "year" and nested "summary"); mirrors pe.web.api's narrative
# handler input shape. Not an economic parameter — a wire-format constant.
_YEAR_COLUMN = "Year"
_SCENARIO_COLUMN = "Scenario"


def narrate_model(model_id: str, scenario: str | None = None) -> dict[str, Any]:
    """Generate a plain-language summary of a model's solved price/abatement path.

    Runs the model and hands its per-year summary rows to the rule-based
    narrator (``pe.analysis.narrative``) — the same paragraph the web app's
    "Narrative" panel shows.

    Args:
        model_id: An example stem or registry ``"user_<slug>"`` id.
        scenario: If the model has a labelled ``Scenario`` column and this is
            given, only that scenario's rows are narrated; otherwise all rows
            are narrated in order.

    Returns:
        ``{"model_id", "scenario", "narrative"}`` — ``narrative`` is the
        generated paragraph; ``scenario`` echoes the filter applied (or
        ``None``).

    Raises:
        ModelStoreError: ``model_id`` matches no known model.
        ValueError: ``scenario`` is given but matches no row.
    """
    config = model_store.resolve_model_config(model_id)
    summary_df, _participant_df = run_simulation_from_config(config)
    frame = summary_df
    if scenario is not None and _SCENARIO_COLUMN in frame.columns:
        frame = frame[frame[_SCENARIO_COLUMN].astype(str) == scenario]
        if frame.empty:
            raise ValueError(f"Scenario '{scenario}' matched no rows in model '{model_id}'.")
    records = [
        {"year": str(row.get(_YEAR_COLUMN, "")), "summary": row}
        for row in frame.to_dict(orient="records")
    ]
    text = narrative.generate_narrative(records, scenario_name=scenario or "")
    return {"model_id": model_id, "scenario": scenario, "narrative": text}


# ── 3. import_csv ────────────────────────────────────────────────────────


def import_csv(csv_text: str, scenario_name: str = "Imported Scenario") -> dict[str, Any]:
    """Convert a per-year CSV into a runnable model config.

    Args:
        csv_text: The CSV body (header row + one row per year), as text.
        scenario_name: Name to give the single scenario the CSV becomes.

    Returns:
        ``{"config": <full config dict>}`` — hand it to the config server's
        ``new_graph``/``save_model`` or the run server's operators. Solving is
        deliberately left to a separate call so a failed import never silently
        runs.

    Raises:
        ValueError: The CSV is empty or missing required columns (see
            ``pe.analysis.csv_import``).
    """
    return {"config": csv_import.csv_to_config(csv_text, scenario_name=scenario_name)}


# ── 4. investment_trigger ────────────────────────────────────────────────


def compute_investment_trigger(
    sigma: float,
    r: float,
    y: float,
    credibility: float | None = None,
) -> dict[str, Any]:
    """Dixit–Pindyck real-options investment trigger multiple and floor.

    Wraps ``pe.analysis.investment_trigger`` (re-exporting the ``pe.core.
    investment`` kernel). The trigger multiple ``P*/P_NPV >= 1`` is the wedge
    between the certainty break-even price and the price that actually
    justifies irreversible investment under uncertainty.

    Args:
        sigma: Annual volatility of the carbon/output price (dimensionless,
            > 0).
        r: Risk-free discount rate (per year, > 0).
        y: Convenience yield / payout rate of the underlying (per year, > 0).
        credibility: Optional floor credibility in [0, 1]; when given, the
            effective (credibility-dampened) volatility and the credible-floor
            multiple are reported alongside the raw trigger.

    Returns:
        ``{"trigger_multiple", "beta", "sigma", "r", "y"}`` plus, when
        ``credibility`` is given, ``{"credibility", "effective_volatility",
        "credible_floor_multiple"}``. All multiples are dimensionless.

    Raises:
        ValueError: Any rate is non-positive, or ``credibility`` is outside
            [0, 1] (see the kernel's own validation).
    """
    payload: dict[str, Any] = {
        "sigma": sigma,
        "r": r,
        "y": y,
        "beta": investment_trigger.beta_positive_root(sigma, r, y),
        "trigger_multiple": investment_trigger.trigger_multiple(sigma, r, y),
    }
    if credibility is not None:
        sigma_eff = investment_trigger.effective_volatility(sigma, credibility)
        payload["credibility"] = credibility
        payload["effective_volatility"] = sigma_eff
        payload["credible_floor_multiple"] = investment_trigger.credible_floor_multiple(r, y)
    return payload


# ── 5. calibration ───────────────────────────────────────────────────────


def calibrate_slopes(
    model_id: str,
    observed_prices: dict[str, float],
    participant_names: list[str],
    max_iter: int = 500,
) -> dict[str, Any]:
    """Inverse-fit participant MAC slopes so solved prices match observed anchors.

    Wraps ``pe.analysis.calibration.calibrate_slopes`` — a Nelder–Mead fit of
    the named participants' ``abatement_cost_slope`` that minimises squared
    error between the model's solved price path and the observed prices.

    Args:
        model_id: An example stem or registry ``"user_<slug>"`` id; its first
            scenario is calibrated.
        observed_prices: ``{year_label: price}`` targets, e.g.
            ``{"2026": 18.5, "2027": 22.0}``.
        participant_names: Which participants' slope to fit; all others are
            held fixed.
        max_iter: Nelder–Mead iteration cap.

    Returns:
        ``{"model_id", "calibrated_slopes", "final_mse", "iterations",
        "success", "modelled_prices"}`` — the fit result straight from the
        calibration workflow, tagged with ``model_id``.

    Raises:
        ModelStoreError: ``model_id`` matches no known model.
    """
    base_config = model_store.resolve_model_config(model_id)
    result = calibration.calibrate_slopes(
        base_config=base_config,
        observed_prices=observed_prices,
        participant_names=participant_names,
        max_iter=max_iter,
    )
    return {"model_id": model_id, **result}


def calibrate_from_elasticity(
    curve: str,
    elasticity: float,
    price: float,
    quantity: float,
    gamma: float = 0.0,
    carbon_cost: float = 0.0,
) -> dict[str, Any]:
    """Forward-calibrate a linear demand or supply block from one elasticity anchor.

    Wraps the forward calibration helpers in ``pe.analysis.calibration``: given
    a point elasticity and one ``(price, quantity)`` anchor, return the block
    coefficients that reproduce it.

    Args:
        curve: ``"product_demand"`` (returns ``{"form", "A_d", "b_d"}``) or
            ``"output_cost"`` (returns ``{"gamma", "delta"}``).
        elasticity: Point price-elasticity at the anchor (demand typically
            negative, supply positive; the builder fixes the geometry).
        price: Anchor price ``P_0`` (currency per unit); must be > 0.
        quantity: Anchor quantity ``Q_0``/``q_0`` (units per period); > 0.
        gamma: ``output_cost`` only — marginal-cost intercept override (0 =>
            derived from the anchor).
        carbon_cost: ``output_cost`` only — per-unit carbon cost at the anchor.

    Returns:
        ``{"curve", "block": {...}}`` — ``block`` is the calibrated coefficient
        dict, ready to drop into the named block's params.

    Raises:
        ValueError: Unknown ``curve``, or a non-positive anchor.
    """
    if curve == "product_demand":
        block = calibration.product_demand_from_elasticity(elasticity, price, quantity)
    elif curve == "output_cost":
        block = calibration.output_cost_from_elasticity(
            elasticity, price, quantity, gamma=gamma, carbon_cost=carbon_cost
        )
    else:
        raise ValueError(f"Unknown curve '{curve}'. Expected 'product_demand' or 'output_cost'.")
    return {"curve": curve, "block": block}


def calibrate_abatement_from_reference(
    carbon_price: float,
    abatement: float,
    a_max: float | None = None,
) -> dict[str, Any]:
    """Forward-calibrate a linear MAC (``abatement``) block from one MAC anchor.

    Wraps ``pe.analysis.calibration.abatement_from_reference``: with linear
    marginal abatement cost ``MAC = beta * a``, one ``(carbon_price,
    abatement)`` point pins ``beta = carbon_price / abatement``.

    Args:
        carbon_price: The carbon price at which the reference abatement occurs
            (currency per tCO2); > 0.
        abatement: The abatement realised at that price (MtCO2); > 0.
        a_max: Optional abatement ceiling to carry onto the block.

    Returns:
        ``{"block": {"beta", "a_max"?}}`` — the calibrated ``abatement`` block
        params.

    Raises:
        ValueError: A non-positive anchor (see the calibration helper).
    """
    return {"block": calibration.abatement_from_reference(carbon_price, abatement, a_max=a_max)}


__all__ = [
    "run_batch",
    "narrate_model",
    "import_csv",
    "compute_investment_trigger",
    "calibrate_slopes",
    "calibrate_from_elasticity",
    "calibrate_abatement_from_reference",
]
