"""Tests for the policy-event timeline (announcement vs execution timing).

Anchored on the hand-solvable linear-MAC economy of test_banking: one
participant, BAU E, MAC p = c·a, banking window price
P_a = c·(ΣE − ΣS − B_in)/Σ(1+r)^k.
"""

from __future__ import annotations

import numpy as np
import pytest

from ets.solvers import run_simulation_from_config
from ets.solvers.events import validate_policy_events

E = 100.0
C = 100.0
R = 0.05


def _config(
    approach: str,
    events: list[dict] | None = None,
    cancel_2031: float = 0.0,
) -> dict:
    years = []
    for year, supply in [("2030", 95.0), ("2031", 85.0), ("2032", 75.0)]:
        years.append(
            {
                "year": year,
                "total_cap": supply,
                "cancelled_allowances": cancel_2031 if year == "2031" else 0.0,
                "auction_mode": "derive_from_cap",
                "banking_allowed": False,
                "borrowing_allowed": False,
                "expectation_rule": "next_year_baseline",
                "price_lower_bound": 0.0,
                "price_upper_bound": 100000.0,
                "participants": [
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
        )
    scenario = {
        "name": "event-test",
        "model_approach": approach,
        "discount_rate": R,
        "years": years,
    }
    if events is not None:
        scenario["policy_events"] = events
    return {"scenarios": [scenario]}


CANCEL_EVENT = [
    {"announced": "2031", "year_overrides": {"2031": {"cancelled_allowances": 10.0}}}
]


def _prices(summary) -> dict[str, float]:
    return dict(zip(summary["Year"], summary["Equilibrium Carbon Price"]))


def test_banking_announcement_timing_changes_the_path():
    """λ→1: a cancellation announced in 2031 leaves 2030 on the no-event path
    (surprise), while the same cancellation announced up front moves 2030."""
    no_event = _prices(run_simulation_from_config(_config("banking"))[0])
    surprise = _prices(run_simulation_from_config(_config("banking", CANCEL_EVENT))[0])
    upfront = _prices(
        run_simulation_from_config(_config("banking", cancel_2031=10.0))[0]
    )

    # Closed forms: window budget over the full horizon.
    growth = 1.0 + (1.0 + R) + (1.0 + R) ** 2
    p_no_event = C * (3 * E - 255.0) / growth
    p_upfront = C * (3 * E - 245.0) / growth
    np.testing.assert_allclose(no_event["2030"], p_no_event, rtol=1e-5)
    np.testing.assert_allclose(upfront["2030"], p_upfront, rtol=1e-5)

    # Surprise: 2030 is priced WITHOUT the event (information timing) …
    np.testing.assert_allclose(surprise["2030"], p_no_event, rtol=1e-5)
    # … and 2031–32 re-solve with the cancellation and the inherited bank.
    bank_2030 = 95.0 - (E - p_no_event / C)
    p_resolve = C * (2 * E - 150.0 - bank_2030) / (1.0 + (1.0 + R))
    np.testing.assert_allclose(surprise["2031"], p_resolve, rtol=1e-5)
    np.testing.assert_allclose(surprise["2032"], p_resolve * (1 + R), rtol=1e-5)
    # The announcement event is visible: 2031 jumps off the smooth path.
    assert surprise["2031"] > no_event["2031"]
    assert upfront["2030"] > surprise["2030"]


def test_competitive_announcement_timing_is_irrelevant():
    """λ≈0: with year-by-year clearing, announcing early or late is identical —
    only execution moves the price (the paper's weak-transmission result)."""
    surprise = _prices(
        run_simulation_from_config(_config("competitive", CANCEL_EVENT))[0]
    )
    upfront = _prices(
        run_simulation_from_config(_config("competitive", cancel_2031=10.0))[0]
    )
    for year in ("2030", "2031", "2032"):
        np.testing.assert_allclose(surprise[year], upfront[year], rtol=1e-9)
    # And the execution year is where the price moves.
    np.testing.assert_allclose(surprise["2030"], C * (E - 95.0), rtol=1e-6)
    np.testing.assert_allclose(surprise["2031"], C * (E - 75.0), rtol=1e-6)


def test_event_validation():
    with pytest.raises(ValueError):
        run_simulation_from_config(
            _config("banking", [{"announced": "2050", "changes": {}}])
        )
    with pytest.raises(ValueError):
        validate_policy_events(
            {"name": "x", "years": [{"year": "2030"}], "policy_events": [{"changes": {}}]}
        )
    with pytest.raises(ValueError):
        validate_policy_events(
            {
                "name": "x",
                "years": [{"year": "2030"}],
                "policy_events": [
                    {"announced": "2030", "year_overrides": {"2099": {}}}
                ],
            }
        )


def test_late_announced_decree_keeps_its_prefunded_reserve():
    """A decree announced mid-horizon with msr_initial_reserve_mt must keep
    that funding — the splice must not overwrite it with the (rule-less)
    previous segment's zero pool. Bands set so every signal is neutral."""
    cfg = _config(
        "banking",
        [
            {
                "announced": "2031",
                "changes": {
                    "msr_enabled": True,
                    "msr_mode": "hybrid",
                    "msr_initial_reserve_mt": 50.0,
                    "msr_price_band_low": 1.0,
                    "msr_price_band_high": 1e9,
                    "msr_surplus_lower_ratio": 1e-9,
                    "msr_surplus_upper_ratio": 0.99,
                },
            }
        ],
    )
    summary, _ = run_simulation_from_config(cfg)
    pool = dict(zip(summary["Year"], summary["MSR Reserve Pool"]))
    np.testing.assert_allclose(pool["2031"], 50.0, atol=1e-9)
    np.testing.assert_allclose(pool["2032"], 50.0, atol=1e-9)


def test_msr_start_year_gates_the_rule():
    """A decree MSR with msr_start_year beyond the horizon never fires."""
    cfg = _config("banking")
    cfg["scenarios"][0].update(
        {
            "msr_enabled": True,
            "msr_mode": "hybrid",
            "msr_initial_reserve_mt": 50.0,
            "msr_start_year": 2099.0,
        }
    )
    summary, _ = run_simulation_from_config(cfg)
    np.testing.assert_allclose(summary["MSR Withheld"].to_numpy(), 0.0, atol=1e-12)
    np.testing.assert_allclose(summary["MSR Released"].to_numpy(), 0.0, atol=1e-12)
