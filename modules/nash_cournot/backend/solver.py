"""
Nash-Cournot strategic-equilibrium solver for an ETS allowance market.

In the competitive model every participant is a price taker: each sets its
marginal abatement cost equal to the market price, ``MAC_i = P``. In the
Nash-Cournot model a subset of *strategic* participants internalise their own
price impact along the residual (inverse) demand curve. A net SELLER withholds
supply (under-abates) to lift the price it receives; a net BUYER withholds
demand (over-abates) to depress the price it pays. The direction of the wedge
is therefore SIGNED by the firm's net allowance position (Hahn 1984) — it is
not automatically "higher than competitive".

The equilibrium concept is a Cournot-Nash equilibrium in net allowance
positions ``{d_i}``: no strategic firm can lower its compliance cost by
unilaterally changing its position, given every other participant's position
and the price-taking fringe's response.

Algorithm — strategic FOC and residual clearing
────────────────────────────────────────────────
Notation (units):
    P        : allowance clearing price                     [currency/tCO2]
    a_i      : abatement of participant i                   [Mt CO2e]
    e_{0,i}  : baseline (BAU) emissions of i                [Mt CO2e]
    F_i      : free allocation of i                         [Mt CO2e]
    g_i      : net-demand intercept, g_i = e_{0,i} - F_i    [Mt CO2e]
    d_i      : net allowance demand, d_i = e_{0,i}-a_i-F_i  [Mt CO2e]
               (d_i > 0 buyer, d_i < 0 seller)
    phi_i    : linear MAC slope, MAC_i = phi_i * a_i        [currency/tCO2/Mt]
    Q        : effective auction volume offered (MSR-adjusted) [Mt CO2e]
    b_fringe : aggregate price-slope of the price-taking fringe,
               b_fringe = sum_{fringe f} 1/phi_f            [Mt CO2e / (currency/tCO2)]
    S_{-i}   : residual-demand price-slope facing firm i,
               S_{-i} = sum_{j != i} |d d_j / d P|
                      = sum_{strategic j != i} 1/phi_j + b_fringe

Strategic first-order condition (allowance market):

    LaTeX:
    $$ \\mathrm{MAC}_i = P + d_i\\,\\frac{\\partial P}{\\partial d_i},
       \\qquad \\frac{\\partial P}{\\partial d_i} = \\frac{1}{S_{-i}} > 0. $$

    For a linear MAC (``MAC_i = phi_i * a_i``, price-taker net demand
    ``d_i^PT(P) = g_i - P/phi_i``) this closes in quantities:

    $$ d_i^\\ast(P) = \\frac{\\varphi_i g_i - P}{\\varphi_i + 1/S_{-i}}, \\qquad
       \\mathrm{MAC}_i = P + \\frac{d_i^\\ast}{S_{-i}}. $$

    ASCII fallback:
        MAC_i          = P + d_i / S_{-i}
        d_i*(P)        = (phi_i * g_i - P) / (phi_i + 1 / S_{-i})
        MAC_i          = P + d_i*(P) / S_{-i}

The reported equilibrium (THE FIX): hold each strategic firm at its strategic
position ``d_i*(P)`` (NOT its price-taking response) and clear the residual —
solve, for the Nash price ``P^Nash``,

    LaTeX:
    $$ \\sum_{i\\in\\mathrm{strat}} d_i^\\ast(P) + D_{\\text{fringe}}(P) = Q, $$

    ASCII fallback:
        sum_i d_i*(P) + D_fringe(P) = Q

where ``D_fringe(P)`` is the fringe's aggregate price-taking net demand. The
left-hand side is strictly decreasing in ``P`` (every ``d_i*`` and the fringe
demand fall with price), so the root is unique and is found by geometric-
bracket + Brent, the same bracketing style as the competitive clearing.

The all-price-taker ``market.solve_equilibrium`` is used ONLY for the
competitive starting point / loud fallback — it is NEVER the reported
equilibrium (calling it for the report is exactly the discard that made Nash
prices come out bit-identical to competitive).

Existence/uniqueness needs an elastic residual for every strategic firm
(``S_{-i} > 0``): a fringe, or at least two strategic firms. A single strategic
firm with a perfectly inelastic residual (``S_{-i} = 0``, infinite price
impact) is ill-posed and raises (JC4).

Scope (spec §4): the MSR Q-adjustment is applied BEFORE the strategic clearing
(strategic firms compete over the MSR-adjusted Q), gated on the same
``msr_enabled``/``msr_start_year`` as the competitive path. CCR is deferred to
v1.1. Banking / intertemporal strategy is out of scope for v1 — the Nash path
clears statically per year and flags (never silently runs) a banking-enabled
market.

Wired exclusively by ``pe.engine.wiring.solve_nash_path``, which injects the
duck-typed MSR state (``features.msr.state.MSRState`` shape) iff the first
market enables the MSR; ``None`` applies no MSR.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

import pandas as pd
from scipy.optimize import brentq

from ...core.expectations import build_expectation_specs, derive_expected_prices
from ...core.market import CarbonMarket

logger = logging.getLogger(__name__)

# Module-level defaults (used when the market/config does not supply a setting).
# No magic numbers below: every tolerance either comes from these DEFAULTS or
# from the market's ``solver_*`` attributes (config-bound, builder.py).
DEFAULTS: dict[str, float] = {
    "price_step": 0.5,          # $/t finite-difference step for demand slopes
    "max_iters": 120.0,         # retained for signature/config compatibility
    "convergence_tol": 1e-3,    # $/t and Mt convergence tolerance
    "slope_guard": 1e-9,        # S_{-i} <= this => residual inelastic (JC4)
    "position_atol": 1e-6,      # strategic-position reconciliation tolerance
}


def _linear_mac_params(
    participant: Any, starting_bank: float = 0.0
) -> tuple[float, float] | None:
    """Return ``(phi, g)`` for a plain linear-MAC participant, else ``None``.

    Analytic, exact for the linear case (spec JC2). ``phi`` is the MAC slope
    [currency/tCO2 per Mt]; ``g = e_0 - F - B_0`` is the price-taker net-demand
    intercept [Mt CO2e], where ``B_0`` is the participant's opening allowance
    endowment (its beginning-of-year bank balance). The endowment shifts the
    static net-demand curve by ``-B_0`` even with banking disallowed
    (``sells = F + B_0 - residual``), which is how an OVER-ALLOCATED incumbent
    (``F + B_0 > e_0`` ⇒ ``g < 0``, a net seller at zero price) is expressed —
    plain free allocation is capped at ``e_0`` by the ``[0, 1]`` allocation
    ratio. Returns ``None`` when the participant is not a plain
    single-technology linear-MAC firm (technology menu, non-linear MAC, or an
    attached demand overlay make the net demand non-affine) so the caller
    falls back to a finite-difference linearisation.
    """
    if participant.technology_options:
        return None
    if getattr(participant, "demand_overlays", ()):  # elastic baseline => non-affine
        return None
    mac = participant.marginal_abatement_cost
    if not callable(mac) or getattr(mac, "cost_model", None) != "linear":
        return None
    phi = float(getattr(mac, "cost_slope", 0.0))
    if phi <= 0.0:
        return None
    g = float(participant.initial_emissions - participant.free_allocation - starting_bank)
    return phi, g


def _participant_net_demand(
    market: CarbonMarket,
    participant: Any,
    price: float,
    bank_balances: dict,
    expected_future_price: float,
) -> float:
    """Price-taking net allowance demand ``d_j(P)`` of one participant [Mt]."""
    return float(
        market._participant_outcome(
            participant,
            price,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        ).net_allowances_traded
    )


def _participant_slope(
    market: CarbonMarket,
    participant: Any,
    price: float,
    bank_balances: dict,
    expected_future_price: float,
    step: float,
) -> float:
    """Return ``|d d_j / d P|`` (>= 0) [Mt / (currency/tCO2)].

    Analytic ``1/phi`` for a linear-MAC participant (exact); otherwise a
    central finite difference of the price-taking net demand (spec JC2). The
    finite difference is exact for an affine net-demand curve and is the
    general fallback for a non-linear MAC.
    """
    lin = _linear_mac_params(participant)
    if lin is not None:
        phi, _ = lin
        return 1.0 / phi
    p_up = price + step
    p_dn = max(0.0, price - step)
    if p_up <= p_dn:
        return 0.0
    d_up = _participant_net_demand(market, participant, p_up, bank_balances, expected_future_price)
    d_dn = _participant_net_demand(market, participant, p_dn, bank_balances, expected_future_price)
    return max(0.0, (d_dn - d_up) / (p_up - p_dn))


def _brentq_on_demand(
    market: CarbonMarket,
    net_demand,
    target: float,
    lower_bound: float,
    upper_bound: float,
) -> float:
    """Bracket (geometric, capped) then Brent-solve ``net_demand(P) = target``.

    Mirrors the competitive clearing's bracketing discipline
    (``core/market/clearing.py:_solve_for_supply``): expand the upper bound by
    ``solver_price_bracket_expand_factor`` at most
    ``solver_price_bracket_max_expansions`` times before raising, so a
    non-bracketing configuration fails loudly rather than returning a bogus
    root.
    """
    def f(price: float) -> float:
        return net_demand(price) - target

    f_low = f(lower_bound)
    f_high = f(upper_bound)
    expansions = 0
    max_expansions = int(getattr(market, "solver_price_bracket_max_expansions", 10))
    expand_factor = float(getattr(market, "solver_price_bracket_expand_factor", 2.0))
    while f_low * f_high > 0 and expansions < max_expansions:
        upper_bound *= expand_factor
        f_high = f(upper_bound)
        expansions += 1
    if f_low * f_high > 0:
        raise RuntimeError(
            f"Nash-Cournot: could not bracket strategic clearing for "
            f"{market.scenario_name}: target={target:.4f}, "
            f"f({lower_bound:.4f})={f_low:.4f}, f({upper_bound:.4f})={f_high:.4f}"
        )
    return float(brentq(f, lower_bound, upper_bound))


def _strategic_clearing(
    market: CarbonMarket,
    bank_balances: dict,
    expected_future_price: float,
    carry_forward_in: float,
    strategic: list,
    fringe: list,
    price_step: float,
) -> tuple[dict, dict]:
    """Clear the market with strategic firms held at their Cournot positions.

    Returns ``(equilibrium, strategic_positions)`` where ``equilibrium`` has
    the SAME keys/shape as ``market.solve_equilibrium`` and
    ``strategic_positions`` maps each strategic firm's name to
    ``{"net_demand", "mac", "shadow_price"}`` — its Cournot net position
    ``d_i*`` [Mt], its marginal abatement cost ``MAC_i`` [currency/tCO2], and
    the shadow price (== ``MAC_i``) at which its abatement is the strategic
    ``a_i*``.

    Raises:
        ValueError: if any strategic firm faces a perfectly inelastic residual
            (``S_{-i} <= slope_guard``) — ill-posed, infinite price impact
            (spec JC4).
    """
    # Competitive price anchors the finite-difference slopes / linearisation.
    eq_competitive = market.solve_equilibrium(
        bank_balances=bank_balances,
        expected_future_price=expected_future_price,
        carry_forward_in=carry_forward_in,
    )
    p_anchor = float(eq_competitive["price"])

    slopes = {
        p.name: _participant_slope(
            market, p, p_anchor, bank_balances, expected_future_price, price_step
        )
        for p in market.participants
    }
    total_slope = sum(slopes.values())

    # Per strategic firm: (phi_i, g_i, S_{-i}). phi_i, g_i analytic for linear
    # MACs, else a finite-difference linearisation at the competitive price.
    slope_guard = float(DEFAULTS["slope_guard"])
    params: dict[str, tuple[float, float, float]] = {}
    for p in strategic:
        s_minus_i = total_slope - slopes[p.name]
        if s_minus_i <= slope_guard:
            raise ValueError(
                f"Nash-Cournot: strategic firm {p.name!r} faces a perfectly "
                f"inelastic residual (S_-i={s_minus_i:.3e}); the price impact is "
                "infinite and the equilibrium is ill-posed. Add a price-taking "
                "fringe or a second strategic firm (JC4)."
            )
        lin = _linear_mac_params(p, float(bank_balances.get(p.name, 0.0)))
        if lin is not None:
            phi_i, g_i = lin
        else:
            slope_i = slopes[p.name]
            if slope_i <= slope_guard:
                # Vertical own-demand: no interior strategic response; treat as
                # a fixed position at its competitive net demand.
                phi_i = float("inf")
                g_i = _participant_net_demand(
                    market, p, p_anchor, bank_balances, expected_future_price
                )
            else:
                phi_i = 1.0 / slope_i
                d_pt = _participant_net_demand(
                    market, p, p_anchor, bank_balances, expected_future_price
                )
                g_i = d_pt + slope_i * p_anchor
        params[p.name] = (phi_i, g_i, s_minus_i)

    def strategic_net_demand(price: float) -> float:
        total = 0.0
        for p in strategic:
            phi_i, g_i, s_minus_i = params[p.name]
            if phi_i == float("inf"):
                total += g_i  # fixed position
            else:
                total += (phi_i * g_i - price) / (phi_i + 1.0 / s_minus_i)
        for p in fringe:
            total += _participant_net_demand(
                market, p, price, bank_balances, expected_future_price
            )
        return total

    # ── Clear on the strategic-aware net demand (mirrors solve_equilibrium's
    #    floor / oversupply branch structure) ──────────────────────────────
    lower_bound = market.price_lower_bound if market.price_lower_bound is not None else 0.0
    if market.price_upper_bound is not None:
        upper_bound = float(market.price_upper_bound)
    else:
        max_penalty = max(p.penalty_price for p in market.participants)
        upper_bound = max_penalty * market.penalty_price_multiplier
    floor_price = max(lower_bound, market.auction_reserve_price)
    offered = market.effective_auction_offered(carry_forward_in)

    def demand_at(price: float) -> float:
        return max(0.0, strategic_net_demand(price))

    if offered <= 0.0:
        price = _brentq_on_demand(
            market, strategic_net_demand, 0.0, lower_bound, upper_bound
        )
        equilibrium = {
            "price": price,
            "auction_offered": offered,
            "auction_sold": 0.0,
            "unsold_allowances": 0.0,
            "coverage_ratio": 1.0,
        }
    else:
        demand_floor = demand_at(floor_price)
        if demand_floor + 1e-9 < offered:
            coverage = demand_floor / offered if offered > 0 else 1.0
            if coverage < market.minimum_bid_coverage:
                price = _brentq_on_demand(
                    market, strategic_net_demand, 0.0, lower_bound, upper_bound
                )
                equilibrium = {
                    "price": price,
                    "auction_offered": offered,
                    "auction_sold": 0.0,
                    "unsold_allowances": offered,
                    "coverage_ratio": coverage,
                }
            else:
                equilibrium = {
                    "price": floor_price,
                    "auction_offered": offered,
                    "auction_sold": demand_floor,
                    "unsold_allowances": max(0.0, offered - demand_floor),
                    "coverage_ratio": coverage,
                }
            price = float(equilibrium["price"])
        else:
            price = _brentq_on_demand(
                market, strategic_net_demand, offered, floor_price, upper_bound
            )
            equilibrium = {
                "price": price,
                "auction_offered": offered,
                "auction_sold": offered,
                "unsold_allowances": 0.0,
                "coverage_ratio": 1.0,
            }

    # Strategic positions at the reported price.
    strategic_positions: dict[str, dict[str, float]] = {}
    for p in strategic:
        phi_i, g_i, s_minus_i = params[p.name]
        if phi_i == float("inf"):
            d_star = g_i
        else:
            d_star = (phi_i * g_i - price) / (phi_i + 1.0 / s_minus_i)
        mac_i = price + d_star / s_minus_i
        strategic_positions[p.name] = {
            "net_demand": float(d_star),
            "mac": float(mac_i),
            "shadow_price": float(mac_i),
        }
        logger.debug(
            "Nash strat %s: d*=%.6f MAC=%.6f (P=%.6f, S_-i=%.6f)",
            p.name,
            d_star,
            mac_i,
            price,
            s_minus_i,
        )

    return equilibrium, strategic_positions


def _solve_nash_year(
    market: CarbonMarket,
    bank_balances: dict,
    expected_future_price: float,
    carry_forward_in: float,
    strategic_names: set[str],
    price_step: float = DEFAULTS["price_step"],
    max_iters: int = int(DEFAULTS["max_iters"]),
    convergence_tol: float = DEFAULTS["convergence_tol"],
) -> tuple[dict, dict]:
    """Solve the Nash-Cournot equilibrium for a single market-year.

    Returns ``(equilibrium, strategic_positions)``. ``equilibrium`` has the
    same keys/shape as ``market.solve_equilibrium`` (``price``,
    ``auction_offered``, ``auction_sold``, ``unsold_allowances``,
    ``coverage_ratio``). ``strategic_positions`` carries each strategic firm's
    Cournot position for faithful per-participant reporting (empty when the
    strategic set is empty).

    On any numerical failure the solver falls back LOUDLY (``logger.warning``)
    to the competitive equilibrium — never silently reports a strategic price
    it could not compute. The ``S_{-i} = 0`` guard (JC4) is a genuine
    mis-specification and is re-raised, not swallowed.
    """
    strategic = [p for p in market.participants if p.name in strategic_names]
    fringe = [p for p in market.participants if p.name not in strategic_names]

    if not strategic:
        # All price takers => competitive equilibrium is the Nash equilibrium.
        eq = market.solve_equilibrium(
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
            carry_forward_in=carry_forward_in,
        )
        return eq, {}

    if market.banking_allowed:
        # Banking / intertemporal strategy is out of scope for v1 (spec §4):
        # flag, never silently run the banking dynamics under Nash.
        logger.warning(
            "Nash-Cournot [%s]: banking_allowed is set but strategic "
            "intertemporal banking is out of scope (v1); clearing statically "
            "per year and ignoring the banking incentive.",
            market.year,
        )

    try:
        return _strategic_clearing(
            market,
            bank_balances,
            expected_future_price,
            carry_forward_in,
            strategic,
            fringe,
            price_step,
        )
    except ValueError:
        raise  # JC4 mis-specification — do not mask it
    except Exception as exc:  # noqa: BLE001 — loud fallback per numerical discipline
        logger.warning(
            "Nash-Cournot [%s]: strategic clearing failed (%s); falling back "
            "to the competitive equilibrium.",
            market.year,
            exc,
        )
        eq = market.solve_equilibrium(
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
            carry_forward_in=carry_forward_in,
        )
        return eq, {}


def _apply_strategic_positions(
    market: CarbonMarket,
    participant_df: pd.DataFrame,
    strategic_positions: dict,
    market_price: float,
    bank_balances: dict,
    expected_future_price: float,
) -> pd.DataFrame:
    """Overwrite strategic firms' reported rows with their Cournot outcome.

    ``participant_results`` re-optimises every firm as a price taker at
    ``market_price`` — for a strategic firm that is the WRONG physical
    position (it abates to ``MAC_i``, not to the market price). This patches
    each strategic row so the reported abatement / net position is the
    strategic ``(a_i*, d_i*)`` (recovered by evaluating the firm's price-taking
    response at its shadow price ``MAC_i``), while every monetary allowance
    quantity is settled at the MARKET price ``market_price`` (the firm trades
    ``d_i*`` at ``P^Nash``, not at its shadow price). Any attached
    participant-reporters are re-run against the re-valued outcome so their
    columns stay consistent.
    """
    if not strategic_positions:
        return participant_df
    for participant in market.participants:
        pos = strategic_positions.get(participant.name)
        if pos is None:
            continue
        shadow_outcome = market._participant_outcome(
            participant,
            pos["shadow_price"],
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        )
        buys = float(shadow_outcome.allowance_buys)
        sells = float(shadow_outcome.allowance_sells)
        allowance_cost = buys * market_price
        sales_revenue = sells * market_price
        total_cost = (
            float(shadow_outcome.fixed_cost)
            + float(shadow_outcome.abatement_cost)
            + allowance_cost
            + float(shadow_outcome.penalty_cost)
            - sales_revenue
        )
        strat_outcome = dataclasses.replace(
            shadow_outcome,
            allowance_cost=allowance_cost,
            sales_revenue=sales_revenue,
            total_cost=total_cost,
        )
        mask = participant_df["Participant"] == participant.name
        if not mask.any():
            continue
        idx = participant_df.index[mask][0]
        patch: dict[str, float] = {
            "Abatement": float(strat_outcome.abatement),
            "Residual Emissions": float(strat_outcome.residual_emissions),
            "Allowance Buys": buys,
            "Allowance Sells": sells,
            "Penalty Emissions": float(strat_outcome.penalty_emissions),
            "Net Allowances Traded": float(strat_outcome.net_allowances_traded),
            "Abatement Cost": float(strat_outcome.abatement_cost),
            "Allowance Cost": allowance_cost,
            "Penalty Cost": float(strat_outcome.penalty_cost),
            "Sales Revenue": sales_revenue,
            "Total Compliance Cost": total_cost,
        }
        for column, value in patch.items():
            if column in participant_df.columns:
                participant_df.at[idx, column] = value
        for reporter in market.participant_reporters:
            for column, value in reporter.columns(
                market, participant, strat_outcome, market_price
            ).items():
                if column in participant_df.columns:
                    participant_df.at[idx, column] = value
    return participant_df


def solve_nash_path(
    ordered_markets,
    strategic_participants: list[str] | None = None,
    price_step: float = DEFAULTS["price_step"],
    max_iters: int = int(DEFAULTS["max_iters"]),
    convergence_tol: float = DEFAULTS["convergence_tol"],
    msr_state: Any | None = None,
) -> list[dict]:
    """Simulate a multi-year path using the Nash-Cournot equilibrium per year.

    Parameters
    ----------
    ordered_markets : list[CarbonMarket]
        Markets sorted chronologically.
    strategic_participants : list[str] | None
        Names of participants that behave strategically. If ``None`` or empty,
        ALL participants are strategic.
    price_step : float
        Finite-difference step [currency/tCO2] for demand slopes / non-linear
        linearisation.
    max_iters, convergence_tol : float
        Retained for config/signature compatibility; the analytic linear-MAC
        clearing is a direct monotone root-find (no best-response iteration is
        needed for the linear case).
    msr_state : Any | None
        Duck-typed MSR state (``apply(...)`` + ``reserve_pool`` — the
        ``features.msr.state.MSRState`` shape), injected by the engine-bound
        entry point iff the first market enables the MSR. ``None`` applies no
        MSR. The MSR Q-adjustment is applied BEFORE the strategic clearing and
        gated on ``msr_enabled``/``msr_start_year`` exactly as the competitive
        path (spec §4). CCR is deferred to v1.1.

    Returns
    -------
    list[dict]
        One details dict per year, same structure as
        ``core.ledger.simulate_path_details``.
    """
    if not ordered_markets:
        return []

    all_names = {p.name for p in ordered_markets[0].participants}
    strategic_names = set(strategic_participants) if strategic_participants else all_names

    ordered_years = [str(m.year) for m in ordered_markets]
    specs = build_expectation_specs(ordered_markets)
    baseline_prices = {str(m.year): m.find_equilibrium_price() for m in ordered_markets}
    expected_prices = derive_expected_prices(ordered_years, specs, baseline_prices)

    bank_balances = {p.name: 0.0 for p in ordered_markets[0].participants}
    carry_forward = 0.0
    details = []

    for market in ordered_markets:
        expected_future_price = float(expected_prices.get(str(market.year), 0.0))
        starting_bank_balances = dict(bank_balances)

        # ── MSR: adjust the auction Q BEFORE the strategic clearing ────────
        # Gated on msr_enabled AND msr_start_year, consistent with the
        # competitive path's MSRCapRule (spec §4; fixes the previously
        # msr_start_year-ungated Nash MSR). CCR is deferred to v1.1 (no
        # Q-adjust here). No import of features.msr — the start-year gate is
        # an inline calendar-year comparison on the duck-typed state.
        msr_withheld = 0.0
        msr_released = 0.0
        msr_pool = 0.0
        effective_carry = carry_forward
        if msr_state is not None and getattr(market, "msr_enabled", False) and _msr_active(market):
            total_bank = sum(bank_balances.values())
            _, msr_withheld, msr_released = msr_state.apply(
                total_bank=total_bank,
                auction_offered=market.auction_offered,
                upper_threshold=float(getattr(market, "msr_upper_threshold", 200.0)),
                lower_threshold=float(getattr(market, "msr_lower_threshold", 50.0)),
                withhold_rate=float(getattr(market, "msr_withhold_rate", 0.12)),
                release_rate=float(getattr(market, "msr_release_rate", 50.0)),
                cancel_excess=bool(getattr(market, "msr_cancel_excess", False)),
                cancel_threshold=float(getattr(market, "msr_cancel_threshold", 400.0)),
                year_label=str(market.year),
            )
            msr_pool = msr_state.reserve_pool
            effective_carry = carry_forward + msr_released - msr_withheld

        equilibrium, strategic_positions = _solve_nash_year(
            market,
            bank_balances,
            expected_future_price,
            effective_carry,
            strategic_names,
            price_step=price_step,
            max_iters=max_iters,
            convergence_tol=convergence_tol,
        )
        equilibrium_price = float(equilibrium["price"])

        participant_df = market.participant_results(
            equilibrium_price,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        )
        participant_df = _apply_strategic_positions(
            market,
            participant_df,
            strategic_positions,
            equilibrium_price,
            bank_balances,
            expected_future_price,
        )

        details.append({
            "market": market,
            "expected_future_price": expected_future_price,
            "starting_bank_balances": starting_bank_balances,
            "equilibrium": equilibrium,
            "participant_df": participant_df,
            "msr_withheld": msr_withheld,
            "msr_released": msr_released,
            "msr_pool": msr_pool,
        })

        carry_forward = (
            float(equilibrium["unsold_allowances"])
            if market.unsold_treatment == "carry_forward"
            else 0.0
        )
        bank_balances = {
            str(row["Participant"]): float(row["Ending Bank Balance"])
            for _, row in participant_df.iterrows()
        }

    return details


def _msr_active(market: CarbonMarket) -> bool:
    """Per-year MSR start-year gate (calendar-year comparison).

    Mirrors ``features.msr.rules._msr_start_active`` WITHOUT importing the MSR
    feature (module-isolation clause (a)/(b)): ``market.year >= msr_start_year``,
    with a non-numeric year label or an unset/zero start year meaning
    "always active".
    """
    msr_start = float(getattr(market, "msr_start_year", 0.0) or 0.0)
    if msr_start <= 0.0:
        return True
    try:
        return float(str(market.year)) >= msr_start
    except (TypeError, ValueError):
        return True
