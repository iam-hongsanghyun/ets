from __future__ import annotations

from scipy.optimize import root_scalar

from .model import CarbonMarket


def total_net_demand(
    market: CarbonMarket,
    carbon_price: float,
    bank_balances: dict[str, float] | None = None,
    expected_future_price: float = 0.0,
) -> float:
    return sum(
        _participant_outcome(
            market,
            participant,
            carbon_price,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        ).net_allowances_traded
        for participant in market.participants
    )


def _participant_outcome(
    market: CarbonMarket,
    participant,
    carbon_price: float,
    bank_balances: dict[str, float] | None = None,
    expected_future_price: float = 0.0,
):
    starting_bank_balance = 0.0
    if bank_balances is not None:
        starting_bank_balance = float(bank_balances.get(participant.name, 0.0))
    return participant.optimize_compliance(
        carbon_price,
        starting_bank_balance=starting_bank_balance,
        expected_future_price=expected_future_price,
        banking_allowed=market.banking_allowed,
        borrowing_allowed=market.borrowing_allowed,
        borrowing_limit=market.borrowing_limit,
        slsqp_max_iters=getattr(market, "solver_slsqp_max_iters", 400),
        slsqp_ftol=getattr(market, "solver_slsqp_ftol", 1e-9),
    )


def _solve_for_supply(
    market: CarbonMarket,
    target_supply: float,
    lower_bound: float,
    upper_bound: float,
    bank_balances: dict[str, float] | None,
    expected_future_price: float,
) -> float:
    f_low = total_net_demand(
        market, lower_bound,
        bank_balances=bank_balances,
        expected_future_price=expected_future_price,
    ) - target_supply
    f_high = total_net_demand(
        market, upper_bound,
        bank_balances=bank_balances,
        expected_future_price=expected_future_price,
    ) - target_supply

    expansion_count = 0
    max_expansions = getattr(market, "solver_price_bracket_max_expansions", 10)
    expand_factor  = getattr(market, "solver_price_bracket_expand_factor", 2.0)
    while f_low * f_high > 0 and expansion_count < max_expansions:
        upper_bound *= expand_factor
        f_high = total_net_demand(
            market, upper_bound,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        ) - target_supply
        expansion_count += 1

    if f_low * f_high > 0:
        raise RuntimeError(
            f"Could not bracket equilibrium price for {market.scenario_name}. "
            f"target_supply={target_supply:.2f}, "
            f"condition({lower_bound})={f_low:.2f}, condition({upper_bound})={f_high:.2f}"
        )

    solution = root_scalar(
        lambda carbon_price: total_net_demand(
            market, carbon_price,
            bank_balances=bank_balances,
            expected_future_price=expected_future_price,
        ) - target_supply,
        bracket=[lower_bound, upper_bound],
        method="brentq",
    )

    if not solution.converged:
        raise RuntimeError(
            f"Market clearing did not converge for {market.scenario_name}."
        )

    return float(solution.root)


def solve_equilibrium(
    market: CarbonMarket,
    lower_bound: float = 0.0,
    upper_bound: float | None = None,
    bank_balances: dict[str, float] | None = None,
    expected_future_price: float = 0.0,
    carry_forward_in: float = 0.0,
) -> dict[str, float]:
    r"""Clear one year's auction against aggregate net demand.

    The reserve-price floor branch below is KERNEL, not a policy overlay
    (feature-modules plan, PLAN v2 §3 price_controls REMAINDER; Arbitration
    outcomes item 6): with ``auction_reserve_price = 0`` it is the OVERSUPPLY
    BOUNDARY CONDITION of static clearing — the complementary-slackness
    boundary of the market-clearing problem — and without it the Brent
    bracket cannot be formed when supply exceeds demand at the floor (net
    demand never crosses the offered volume on ``[F, P_max]``).

    Algorithm:
        LaTeX:
        $$ 0 \le \big(P_t - F_t\big) \;\perp\; \big(Q_t - e^{+}_t(P_t)\big)
           \ge 0 $$
        i.e. either the price clears the full offered volume above the
        floor, or the price sits AT the floor and only demand-at-floor
        sells:
        $$ P_t > F_t \Rightarrow \text{sold} = Q_t, \qquad
           P_t = F_t \Rightarrow \text{sold} = e^{+}_t(F_t) \le Q_t . $$
        With $F_t = 0$ this is the oversupply boundary $P_t = 0$,
        $\text{sold} = e^{+}_t(0)$ (zero price on slack supply).

        ASCII fallback:
            demand_at(F) >= offered -> Brent-solve demand(P) = offered on
                                       [F, P_max]; sold = offered
            demand_at(F) <  offered -> price = F; sold = demand_at(F);
                                       unsold = offered - sold
                                       (coverage < minimum_bid_coverage:
                                       auction fails — sold = 0 and the
                                       price re-solves at zero net supply)

        Symbols (units):
            P_t    : clearing price of year t                [currency/tCO2]
            F_t    : max(price_lower_bound, auction_reserve_price)
                                                             [currency/tCO2]
            Q_t    : effective auction volume offered        [Mt CO2e]
            e+_t(p): max(0, aggregate net auction demand at p)   [Mt CO2e]
            P_max  : price ceiling, or the penalty-derived bracket top
                                                             [currency/tCO2]

    Host guarantee (documented, PERMANENT property test in
    ``tests/test_price_boundary_property.py``, alongside the F4 golden):
    this branch is never reordered or extracted into a feature — every
    price-formation path relies on clearing being TOTAL (always returning a
    price without raising) at every supply level, including oversupply.

    Args:
        market: The year's market.
        lower_bound: Bracket bottom [currency/tCO2]; defaults to the
            market's ``price_lower_bound``.
        upper_bound: Bracket top [currency/tCO2]; defaults to the market's
            ``price_upper_bound``, else the penalty-derived ceiling.
        bank_balances: Beginning-of-year bank balances by participant name
            [Mt CO2e].
        expected_future_price: Expected next-period price [currency/tCO2]
            (the banking incentive inside compliance).
        carry_forward_in: Additive supply adjustment entering this year's
            auction [Mt CO2e] (cap rules, unsold carry-forward).

    Returns:
        Dict with ``price``, ``auction_offered``, ``auction_sold``,
        ``unsold_allowances``, and ``coverage_ratio``.
    """
    if lower_bound == 0.0 and market.price_lower_bound is not None:
        lower_bound = market.price_lower_bound

    if upper_bound is None:
        if market.price_upper_bound is not None:
            upper_bound = market.price_upper_bound
        else:
            max_penalty = max(
                participant.penalty_price for participant in market.participants
            )
            upper_bound = max_penalty * market.penalty_price_multiplier

    floor_price = max(lower_bound, market.auction_reserve_price)
    offered = market.effective_auction_offered(carry_forward_in)

    def demand_at(price: float) -> float:
        return max(
            0.0,
            total_net_demand(
                market, price,
                bank_balances=bank_balances,
                expected_future_price=expected_future_price,
            ),
        )

    if offered <= 0.0:
        sold = 0.0
        unsold = 0.0
        price = _solve_for_supply(
            market, 0.0, lower_bound, upper_bound, bank_balances, expected_future_price,
        )
        return {
            "price": price,
            "auction_offered": offered,
            "auction_sold": sold,
            "unsold_allowances": unsold,
            "coverage_ratio": 1.0,
        }

    demand_floor = demand_at(floor_price)
    if demand_floor + 1e-9 < offered:
        coverage = demand_floor / offered if offered > 0 else 1.0
        if coverage < market.minimum_bid_coverage:
            sold = 0.0
            unsold = offered
            price = _solve_for_supply(
                market, 0.0, lower_bound, upper_bound, bank_balances, expected_future_price,
            )
        else:
            sold = demand_floor
            unsold = max(0.0, offered - sold)
            price = floor_price
        return {
            "price": price,
            "auction_offered": offered,
            "auction_sold": sold,
            "unsold_allowances": unsold,
            "coverage_ratio": coverage,
        }

    price = _solve_for_supply(
        market, offered, floor_price, upper_bound, bank_balances, expected_future_price,
    )
    return {
        "price": price,
        "auction_offered": offered,
        "auction_sold": offered,
        "unsold_allowances": 0.0,
        "coverage_ratio": 1.0,
    }
