r"""PERMANENT property test: the floor = 0 oversupply boundary of static clearing.

Status: PERMANENT — this test stands alongside the F4 golden gate and is
never deleted or weakened without joint lead-modeller + ets-lead-economist
sign-off (Arbitration outcomes, O10, binding).

What it pins (feature-modules plan, PLAN v2 §3 price_controls REMAINDER):
the in-clearing floor branch of ``core/market/clearing.py:solve_equilibrium``
is KERNEL — the complementary-slackness boundary of static clearing, not a
policy instrument. With ``auction_reserve_price = 0`` (every unconfigured
scenario) and supply exceeding demand at a zero price, the branch IS what
makes clearing total:

    LaTeX:  $$ 0 \le (P - F) \perp (Q - e^{+}(P)) \ge 0;\qquad
               F = 0:\; P = 0,\ \text{sold} = e^{+}(0) $$

    ASCII:  demand_at(0) < offered  ->  price = 0, sold = demand_at(0),
            unsold = offered - sold, and NO exception

Without the branch, Brent bracketing fails: net demand never crosses the
offered volume anywhere on [0, P_max], so ``_solve_for_supply`` would raise
"Could not bracket equilibrium price". Extracting the branch into a feature
(or reordering it after the bracket) breaks every price-formation path on
oversupplied years — which is why the price_controls feature (O10) took the
floor-cancellation rule and the delivered-price clip but deliberately left
this branch in the kernel.

The economy is the hand-solvable linear-MAC single buyer of the other solver
tests: BAU E = 100 Mt, MAC p = c·a, so demand at price 0 is exactly E
(no abatement at a zero price) and any offered volume above E is oversupply.
"""

from __future__ import annotations

import numpy as np
import pytest

from ets.config_io import build_markets_from_config
from ets.core.market.clearing import solve_equilibrium, total_net_demand

E = 100.0  # BAU emissions [Mt]
C = 100.0  # linear MAC slope [KRW per t per Mt]


def _market(
    offered: float,
    participants: list[dict] | None = None,
    minimum_bid_coverage: float = 0.0,
):
    year = {
        "year": "2030",
        "total_cap": offered,
        "auction_mode": "derive_from_cap",
        "banking_allowed": False,
        "borrowing_allowed": False,
        "expectation_rule": "next_year_baseline",
        "price_lower_bound": 0.0,
        "price_upper_bound": 100000.0,
        "minimum_bid_coverage": minimum_bid_coverage,
        "participants": participants
        if participants is not None
        else [
            {
                "name": "Industry",
                "initial_emissions": E,
                "free_allocation_ratio": 0.0,
                "penalty_price": 0.0,
                "abatement_type": "linear",
                "max_abatement": E,
                "cost_slope": C,
            }
        ],
    }
    cfg = {"scenarios": [{"name": "boundary", "model_approach": "competitive", "years": [year]}]}
    return build_markets_from_config(cfg)[0]


# Oversupply degrees from marginal (10 %) to extreme (10x BAU): the boundary
# must hold — and clearing must never raise — across the whole sweep.
@pytest.mark.parametrize("offered", [110.0, 125.0, 150.0, 300.0, 1000.0])
def test_floor_zero_oversupply_clears_at_zero_price(offered: float):
    """P = 0 and sold = demand_at(0) on every oversupplied year (no raise)."""
    market = _market(offered)
    eq = solve_equilibrium(market)  # must not raise: bracketing is bypassed
    assert eq["price"] == 0.0  # exactly the floor (= 0), not an approximation
    demand_at_zero = max(0.0, total_net_demand(market, 0.0))
    np.testing.assert_allclose(eq["auction_sold"], demand_at_zero, rtol=1e-9, atol=0)
    np.testing.assert_allclose(
        eq["unsold_allowances"], offered - eq["auction_sold"], rtol=0, atol=1e-9
    )
    np.testing.assert_allclose(
        eq["coverage_ratio"], eq["auction_sold"] / offered, rtol=0, atol=1e-12
    )
    # It really is the boundary: slack supply and zero price simultaneously
    # (complementary slackness — both sides of the perp can hold only here).
    assert eq["unsold_allowances"] > 0.0


def test_floor_zero_oversupply_with_step_demand():
    """Piecewise (step) MACs hit the same boundary: no abatement at P = 0, so
    demand_at(0) = E exactly and the branch returns it as sold."""
    participants = [
        {
            "name": "Industry",
            "initial_emissions": E,
            "free_allocation_ratio": 0.0,
            "penalty_price": 0.0,
            "abatement_type": "piecewise",
            "mac_blocks": [
                {"amount": 20.0, "marginal_cost": 1000.0},
                {"amount": 20.0, "marginal_cost": 5000.0},
            ],
        }
    ]
    market = _market(150.0, participants=participants)
    eq = solve_equilibrium(market)
    assert eq["price"] == 0.0
    # The boundary identity: sold is EXACTLY the demand evaluation at P = 0
    # (the compliance optimizer carries ~1e-6 noise around the analytic E,
    # so the tight identity is against demand_at(0), the loose one vs E).
    demand_at_zero = max(0.0, total_net_demand(market, 0.0))
    np.testing.assert_allclose(eq["auction_sold"], demand_at_zero, rtol=1e-9, atol=0)
    np.testing.assert_allclose(eq["auction_sold"], E, rtol=0, atol=1e-4)
    np.testing.assert_allclose(
        eq["unsold_allowances"], 150.0 - eq["auction_sold"], rtol=0, atol=1e-9
    )


def test_fully_allocated_market_with_zero_net_demand_still_clears():
    """The extreme boundary: free allocation covers BAU, net auction demand
    at P = 0 clips to zero — price 0, nothing sold, nothing raised."""
    year = {
        "year": "2030",
        "total_cap": 150.0,  # 100 Mt free (ratio 1.0) + 50 Mt auctioned
        "auction_mode": "derive_from_cap",
        "banking_allowed": False,
        "borrowing_allowed": False,
        "expectation_rule": "next_year_baseline",
        "price_lower_bound": 0.0,
        "price_upper_bound": 100000.0,
        "participants": [
            {
                "name": "Covered",
                "initial_emissions": E,
                "free_allocation_ratio": 1.0,
                "penalty_price": 0.0,
                "abatement_type": "linear",
                "max_abatement": E,
                "cost_slope": C,
            }
        ],
    }
    cfg = {"scenarios": [{"name": "covered", "model_approach": "competitive", "years": [year]}]}
    market = build_markets_from_config(cfg)[0]
    eq = solve_equilibrium(market)
    assert eq["price"] == 0.0
    np.testing.assert_allclose(eq["auction_sold"], 0.0, rtol=0, atol=1e-9)
    np.testing.assert_allclose(eq["unsold_allowances"], 50.0, rtol=0, atol=1e-9)


def test_undersupply_is_untouched_by_the_boundary_branch():
    """Control: with demand at the floor exceeding supply, clearing takes the
    Brent branch and returns the interior price e(P) = Q (here
    P = c·(E − Q) = 2000), selling the full volume."""
    market = _market(80.0)
    eq = solve_equilibrium(market)
    np.testing.assert_allclose(eq["price"], C * (E - 80.0), rtol=1e-5)
    np.testing.assert_allclose(eq["auction_sold"], 80.0, rtol=0, atol=1e-9)
    np.testing.assert_allclose(eq["unsold_allowances"], 0.0, rtol=0, atol=1e-9)
