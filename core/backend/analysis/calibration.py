"""
MACC calibration: fit abatement_cost_slope parameters to observed carbon prices.

Algorithm:
  For each candidate slope vector θ, run the full simulation, compute modelled
  equilibrium prices P_model(t), minimise MSE = Σ (P_model(t) - P_obs(t))².
  Uses scipy.optimize.minimize with method='Nelder-Mead'.

Usage:
  from pe.analysis.calibration import calibrate_slopes
  result = calibrate_slopes(base_config, observed_prices, participant_names)
"""
from __future__ import annotations
import copy
import numpy as np
from scipy.optimize import minimize
from typing import Any


# ── Forward calibration: elasticity + anchor -> slope config block ───────────
#
# The inverse route below (``calibrate_slopes``) runs the simulation and fits
# slopes to observed prices. These forward helpers are the cheap companion: you
# supply an elasticity (from the literature) and one reference point (P0, Q0)
# from a base year, and they emit the config block with the slope already solved
# — so authors enter elasticities and anchors, never raw slopes.


def linear_slope_from_elasticity(
    elasticity: float, price: float, quantity: float
) -> float:
    r"""Return the magnitude of a linear curve's quantity-slope at an anchor point.

    A linear schedule ``Q = a +/- s*P`` has point elasticity
    ``eps = (dQ/dP)*(P/Q)``, so ``|dQ/dP| = |eps|*Q/P``. This is the shared
    primitive behind the demand/supply builders below.

    Algorithm:
        $$ s = |\varepsilon|\,\frac{Q_0}{P_0} $$
        ASCII: s = |elasticity| * quantity / price

    Args:
        elasticity: Point price-elasticity (dimensionless). Sign is ignored — the
            builder that calls this fixes the geometry (demand slopes down, supply
            up).
        price: Anchor price ``P_0`` (currency per unit); must be > 0.
        quantity: Anchor quantity ``Q_0`` (units per period); must be > 0.

    Returns:
        ``|dQ/dP|`` at the anchor (units per period per currency), >= 0.

    Raises:
        ValueError: If ``price`` or ``quantity`` is not strictly positive.
    """
    if price <= 0.0 or quantity <= 0.0:
        raise ValueError(
            f"anchor must be strictly positive: price={price}, quantity={quantity}"
        )
    return abs(elasticity) * quantity / price


def product_demand_from_elasticity(
    elasticity: float, price: float, quantity: float
) -> dict[str, Any]:
    r"""Build a linear ``product_demand`` block from a demand elasticity + anchor.

    Product demand is read as ``Q_d = A_d - b_d * P_s`` (quantity as a function of
    price), so ``eps_D = -b_d*P/Q`` and the curve is pinned by one point.

    Algorithm:
        $$ b_d = |\varepsilon_D|\,\frac{Q_0}{P_0}, \qquad A_d = Q_0 + b_d\,P_0 $$
        ASCII: b_d = |eps_D| * Q0 / P0 ; A_d = Q0 + b_d * P0

    Args:
        elasticity: Demand elasticity ``eps_D`` (typically negative; magnitude used).
        price: Anchor product price ``P_0`` (currency per unit); > 0.
        quantity: Anchor demanded quantity ``Q_0`` (units per period); > 0.

    Returns:
        ``{"form": "linear", "A_d": ..., "b_d": ...}`` — drops straight into a
        ``product_market`` scenario's ``product_demand``.
    """
    b_d = linear_slope_from_elasticity(elasticity, price, quantity)
    return {"form": "linear", "A_d": quantity + b_d * price, "b_d": b_d}


def output_cost_from_elasticity(
    elasticity: float,
    price: float,
    quantity: float,
    *,
    gamma: float = 0.0,
    carbon_cost: float = 0.0,
) -> dict[str, Any]:
    r"""Build a producer ``output_cost`` block (gamma, delta) from a supply elasticity.

    A producer's inverse supply is ``P_s = gamma + B + delta*q`` (``B`` the
    per-unit carbon cost), so ``q = (P_s - gamma - B)/delta`` and
    ``eps_S = (1/delta)*(P/q)``. The elasticity pins ``delta``; the intercept
    ``gamma`` is then set so the anchor ``(P_0, q_0)`` lies on the curve.

    Algorithm:
        $$ \delta = \frac{P_0}{\varepsilon_S\,q_0}, \qquad
           \gamma = P_0 - B - \delta\,q_0 $$
        ASCII: delta = P0 / (eps_S * q0) ; gamma = P0 - B - delta*q0

    Args:
        elasticity: Own-price supply elasticity ``eps_S`` (> 0).
        price: Anchor product price ``P_0`` (currency per unit); > 0.
        quantity: Anchor output ``q_0`` (units per period); > 0.
        gamma: If given nonzero, used as the marginal-cost intercept directly
            (the anchor then only fixes ``delta``); default 0.0 solves ``gamma``
            from the anchor.
        carbon_cost: Per-unit carbon cost ``B`` at the anchor (currency per unit),
            subtracted when solving ``gamma`` so the *net-of-carbon* intercept is
            recovered. Default 0.0.

    Returns:
        ``{"gamma": ..., "delta": ...}`` with ``delta > 0`` (the FOC requires it).

    Raises:
        ValueError: If ``elasticity <= 0`` (supply must slope up).
    """
    if elasticity <= 0.0:
        raise ValueError(f"supply elasticity must be > 0, got {elasticity}")
    delta = price / (elasticity * quantity)
    solved_gamma = gamma if gamma else (price - carbon_cost - delta * quantity)
    return {"gamma": solved_gamma, "delta": delta}


def abatement_from_reference(
    carbon_price: float,
    abatement: float,
    *,
    a_max: float | None = None,
) -> dict[str, Any]:
    r"""Build a producer ``abatement`` block (beta, a_max) from one MAC anchor.

    With linear marginal abatement cost ``MAC = beta * a`` a firm abates until
    ``MAC = P_c``, so ``a = P_c/beta`` and a single observed ``(P_c, a)`` pins the
    slope exactly (linear MAC through the origin is unit-elastic, so no separate
    elasticity is needed).

    Algorithm:
        $$ \beta = \frac{P_{c,0}}{a_0} $$
        ASCII: beta = carbon_price / abatement

    Args:
        carbon_price: Reference carbon price ``P_{c,0}`` (currency per t); > 0.
        abatement: Abatement observed at that price ``a_0`` (t per period); > 0.
        a_max: Optional abatement ceiling passed through unchanged (t per period).

    Returns:
        ``{"beta": ...}`` (plus ``"a_max"`` if supplied).

    Raises:
        ValueError: If ``carbon_price`` or ``abatement`` is not strictly positive.
    """
    if carbon_price <= 0.0 or abatement <= 0.0:
        raise ValueError(
            f"anchor must be positive: carbon_price={carbon_price}, abatement={abatement}"
        )
    block: dict[str, Any] = {"beta": carbon_price / abatement}
    if a_max is not None:
        block["a_max"] = a_max
    return block


def calibrate_slopes(
    base_config: dict[str, Any],
    observed_prices: dict[str, float],
    participant_names: list[str],
    initial_slopes: list[float] | None = None,
    max_iter: int = 500,
) -> dict[str, Any]:
    """
    Fit abatement_cost_slope for named participants to minimise MSE vs observed prices.

    Args:
        base_config: Full simulation config dict (scenarios[0] used).
        observed_prices: Dict of {year_str: price}, e.g. {"2026": 18.5, "2027": 22.0}.
        participant_names: Participants whose slope to calibrate (others fixed).
        initial_slopes: Starting slopes. Defaults to current values in config.
        max_iter: Nelder-Mead iteration limit.

    Returns:
        Dict with keys:
          "calibrated_slopes": {participant_name: slope},
          "final_mse": float,
          "iterations": int,
          "success": bool,
          "modelled_prices": {year_str: price}
    """
    from ..config_io.builder import build_markets_from_config
    from ..engine import run_simulation

    scenario = base_config["scenarios"][0]
    years_order = [str(y["year"]) for y in scenario["years"]]

    obs_years = [y for y in years_order if y in observed_prices]
    obs_vals = np.array([observed_prices[y] for y in obs_years])

    # Extract initial slopes from config
    if initial_slopes is None:
        initial_slopes = []
        for name in participant_names:
            slope = 5.0
            for yr in scenario["years"]:
                for p in yr.get("participants", []):
                    if p["name"] == name and p.get("abatement_type") == "linear":
                        slope = float(p.get("abatement_cost_slope") or p.get("cost_slope") or 5.0)
                        break
            initial_slopes.append(slope)

    def _set_slopes(cfg: dict, slopes: list[float]) -> dict:
        cfg = copy.deepcopy(cfg)
        slope_map = dict(zip(participant_names, slopes))
        for yr in cfg["scenarios"][0]["years"]:
            for p in yr.get("participants", []):
                if p["name"] in slope_map and p.get("abatement_type") == "linear":
                    p["abatement_cost_slope"] = max(0.01, slope_map[p["name"]])
                    p["cost_slope"] = p["abatement_cost_slope"]
        return cfg

    def _objective(slopes: np.ndarray) -> float:
        try:
            cfg = _set_slopes(base_config, slopes.tolist())
            markets = build_markets_from_config(cfg)
            summary_df, _ = run_simulation(markets)
            year_prices: dict[str, float] = {}
            if not summary_df.empty and "Year" in summary_df.columns and "Equilibrium Carbon Price" in summary_df.columns:
                for _, row in summary_df.iterrows():
                    year_prices[str(row["Year"])] = float(row["Equilibrium Carbon Price"])
            modelled = np.array([year_prices.get(y, 0.0) for y in obs_years])
            return float(np.mean((modelled - obs_vals) ** 2))
        except Exception:
            return 1e12

    x0 = np.array(initial_slopes, dtype=float)
    xatol = float(scenario.get("solver_calibration_xatol", 0.1))
    fatol = float(scenario.get("solver_calibration_fatol", 0.01))
    result = minimize(_objective, x0, method="Nelder-Mead",
                      options={"maxiter": max_iter, "xatol": xatol, "fatol": fatol})

    final_cfg = _set_slopes(base_config, result.x.tolist())
    markets = build_markets_from_config(final_cfg)
    summary_df, _ = run_simulation(markets)
    modelled_prices: dict[str, float] = {}
    if not summary_df.empty and "Year" in summary_df.columns and "Equilibrium Carbon Price" in summary_df.columns:
        for _, row in summary_df.iterrows():
            modelled_prices[str(row["Year"])] = float(row["Equilibrium Carbon Price"])

    return {
        "calibrated_slopes": dict(zip(participant_names, result.x.tolist())),
        "final_mse": float(result.fun),
        "iterations": int(result.nit),
        "success": bool(result.success),
        "modelled_prices": modelled_prices,
        "observed_prices": observed_prices,
    }
