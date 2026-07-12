"""Nash-Cournot strategic-equilibrium correctness tests.

The oracle is the hand-anchored 2-genco example of ``docs/nash-cournot-spec.md``
§3: two symmetric strategic firms (linear MAC slope ``phi_s = 1``, net-demand
intercept ``g_s``) plus a competitive price-taking fringe (slope ``b_f = 1``),
auction ``Q = 0``. With ``S_-i = b_f + 1/phi_s = 2`` and ``dP/dd_i = 1/2`` the
closed-form prices are hand-solvable, which is exactly what pins the strategic
price as genuinely DISTINCT from the competitive price (the whole point of the
fix — before it, Nash came out bit-identical to competitive).

Two representations of the same anchor:

* Exact spec anchor (``g_s = -7``, net SELLERS / over-allocated incumbents):
  ``P^c = 7`` vs ``P^Nash = 11``, each firm ``d* = -12``, ``MAC_s = 5``. The
  over-allocation ``F + B_0 > e_0`` is expressed via an opening allowance
  endowment ``B_0 = 7`` (plain free allocation is capped at ``e_0`` by the
  ``[0, 1]`` ratio), which shifts the static net-demand intercept to
  ``g = e_0 - F - B_0 = -7`` even with banking disallowed.
* Config-expressible seller anchor (``g_s = 0``, fully allocated firms that
  become sellers through abatement): ``P^c = 7`` vs ``P^Nash = 9``, each firm
  ``d* = -6``, ``MAC_s = 6``. This is what ``examples/nash_cournot_strategic``
  ships (no over-allocation needed), so it is the golden's oracle.
"""

from __future__ import annotations

import numpy as np
import pytest

from pe.core.costs import linear_abatement_factory
from pe.core.market import CarbonMarket
from pe.core.participant import MarketParticipant
from pe.features.nash_cournot.solver import _solve_nash_year, solve_nash_path

_RTOL = 0.0
_ATOL = 1e-6


def _firm(name: str, e0: float, ratio: float, slope: float, max_abate: float) -> MarketParticipant:
    """A single-technology linear-MAC firm (``MAC = slope * abatement``)."""
    return MarketParticipant(
        name=name,
        initial_emissions=e0,
        marginal_abatement_cost=linear_abatement_factory(max_abatement=max_abate, cost_slope=slope),
        free_allocation_ratio=ratio,
        penalty_price=1000.0,
        max_abatement_share=max_abate / e0,
    )


def _market(participants: list[MarketParticipant], auction_offered: float = 0.0) -> CarbonMarket:
    total_free = sum(p.free_allocation for p in participants)
    return CarbonMarket(
        participants=participants,
        total_cap=total_free + auction_offered,
        auction_offered=auction_offered,
        price_upper_bound=1000.0,
        year="2025",
        scenario_name="nash-anchor",
    )


def test_exact_spec_anchor_net_sellers() -> None:
    """Spec §3 exact anchor: g_s=-7 => P^c=7, P^Nash=11, d*=-12, MAC_s=5."""
    gencos = [_firm("GencoA", 10.0, 1.0, 1.0, 10.0), _firm("GencoB", 10.0, 1.0, 1.0, 10.0)]
    fringe = _firm("Fringe", 35.0, 0.0, 1.0, 35.0)
    market = _market([*gencos, fringe])
    # Opening endowment B_0 = 7 makes each genco over-allocated (g = 10-10-7 = -7).
    banks = {"GencoA": 7.0, "GencoB": 7.0, "Fringe": 0.0}

    p_competitive = float(market.solve_equilibrium(bank_balances=banks)["price"])
    np.testing.assert_allclose(p_competitive, 7.0, rtol=_RTOL, atol=_ATOL)

    equilibrium, positions = _solve_nash_year(market, banks, 0.0, 0.0, {"GencoA", "GencoB"})
    np.testing.assert_allclose(equilibrium["price"], 11.0, rtol=_RTOL, atol=_ATOL)
    for name in ("GencoA", "GencoB"):
        np.testing.assert_allclose(positions[name]["net_demand"], -12.0, rtol=_RTOL, atol=_ATOL)
        np.testing.assert_allclose(positions[name]["mac"], 5.0, rtol=_RTOL, atol=_ATOL)
    # Net seller: MAC strictly below the market price (under-abates to withhold).
    assert positions["GencoA"]["mac"] < equilibrium["price"]


def test_config_anchor_matches_golden() -> None:
    """Config anchor (g_s=0): P^c=7, P^Nash=9, d*=-6, MAC_s=6 — the golden oracle."""
    gencos = [_firm("GencoA", 10.0, 1.0, 1.0, 10.0), _firm("GencoB", 10.0, 1.0, 1.0, 10.0)]
    fringe = _firm("Fringe", 21.0, 0.0, 1.0, 21.0)
    market = _market([*gencos, fringe])
    banks = {p.name: 0.0 for p in market.participants}

    p_competitive = float(market.solve_equilibrium(bank_balances=banks)["price"])
    np.testing.assert_allclose(p_competitive, 7.0, rtol=_RTOL, atol=_ATOL)

    equilibrium, positions = _solve_nash_year(market, banks, 0.0, 0.0, {"GencoA", "GencoB"})
    np.testing.assert_allclose(equilibrium["price"], 9.0, rtol=_RTOL, atol=_ATOL)
    for name in ("GencoA", "GencoB"):
        np.testing.assert_allclose(positions[name]["net_demand"], -6.0, rtol=_RTOL, atol=_ATOL)
        np.testing.assert_allclose(positions[name]["mac"], 6.0, rtol=_RTOL, atol=_ATOL)


def test_empty_strategic_set_is_competitive() -> None:
    """No strategic firms => the Nash solver reports the competitive price."""
    gencos = [_firm("GencoA", 10.0, 1.0, 1.0, 10.0), _firm("GencoB", 10.0, 1.0, 1.0, 10.0)]
    fringe = _firm("Fringe", 21.0, 0.0, 1.0, 21.0)
    market = _market([*gencos, fringe])
    banks = {p.name: 0.0 for p in market.participants}

    equilibrium, positions = _solve_nash_year(market, banks, 0.0, 0.0, set())
    np.testing.assert_allclose(equilibrium["price"], 7.0, rtol=_RTOL, atol=_ATOL)
    assert positions == {}


def test_net_buyer_config_flips_below_competitive() -> None:
    """Monopsony: net-BUYER strategic firms push the Nash price BELOW competitive.

    Two strategic buyers (g_s=20, net buyers) plus a price-taking fringe
    (g_f=10) buy against a fixed auction supply Q=20. Competitive P=10; the
    buyers withhold demand (over-abate), so the Nash price falls to 50/7.
    """
    gencos = [_firm("BuyerA", 20.0, 0.0, 1.0, 20.0), _firm("BuyerB", 20.0, 0.0, 1.0, 20.0)]
    fringe = _firm("Fringe", 10.0, 0.0, 1.0, 10.0)
    market = _market([*gencos, fringe], auction_offered=20.0)
    banks = {p.name: 0.0 for p in market.participants}

    # atol here is the competitive auction solver's own minimize_scalar
    # tolerance (~1e-6, underlying compliance machinery), not the Nash solver's.
    p_competitive = float(market.solve_equilibrium(bank_balances=banks)["price"])
    np.testing.assert_allclose(p_competitive, 10.0, rtol=_RTOL, atol=1e-4)

    equilibrium, positions = _solve_nash_year(market, banks, 0.0, 0.0, {"BuyerA", "BuyerB"})
    # (20-P)*2/1.5 + (10-P) = 20  =>  P = 50/7.
    np.testing.assert_allclose(equilibrium["price"], 50.0 / 7.0, rtol=_RTOL, atol=1e-4)
    assert equilibrium["price"] < p_competitive
    # Net buyer: MAC strictly ABOVE the market price (over-abates to withhold demand).
    assert positions["BuyerA"]["mac"] > equilibrium["price"]


def test_inelastic_residual_guard_raises() -> None:
    """JC4: a single strategic firm with a perfectly inelastic residual raises.

    One strategic firm buying against a fixed auction supply (Q=10) with no
    fringe and no second strategic firm => S_-i = 0 (infinite price impact,
    ill-posed).
    """
    solo = _firm("Solo", 20.0, 0.0, 1.0, 20.0)
    market = _market([solo], auction_offered=10.0)
    with pytest.raises(ValueError, match="inelastic residual"):
        _solve_nash_year(market, {"Solo": 0.0}, 0.0, 0.0, {"Solo"})


def test_path_reports_strategic_positions_in_participant_frame() -> None:
    """The reported participant frame carries the strategic (not price-taking)
    positions and balances (net traded == auction Q == 0)."""
    gencos = [_firm("GencoA", 10.0, 1.0, 1.0, 10.0), _firm("GencoB", 10.0, 1.0, 1.0, 10.0)]
    fringe = _firm("Fringe", 21.0, 0.0, 1.0, 21.0)
    market = _market([*gencos, fringe])
    market.nash_strategic_participants = ["GencoA", "GencoB"]

    details = solve_nash_path([market], strategic_participants=["GencoA", "GencoB"])
    df = details[0]["participant_df"]
    genco_row = df[df["Participant"] == "GencoA"].iloc[0]
    np.testing.assert_allclose(float(genco_row["Allowance Sells"]), 6.0, rtol=_RTOL, atol=_ATOL)
    np.testing.assert_allclose(float(genco_row["Abatement"]), 6.0, rtol=_RTOL, atol=_ATOL)
    # Sales settled at the market price P^Nash = 9, not the shadow price 6.
    np.testing.assert_allclose(float(genco_row["Sales Revenue"]), 54.0, rtol=_RTOL, atol=_ATOL)
    np.testing.assert_allclose(
        float(df["Net Allowances Traded"].sum()), 0.0, rtol=_RTOL, atol=1e-6
    )
