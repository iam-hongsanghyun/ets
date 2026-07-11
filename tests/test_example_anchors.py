"""Focused hand-anchor assertions for the approach/mechanism example library.

These are closed-form arithmetic checks that each new example's mechanism
fires and obeys its defining identity -- complementary to the bit-identical
golden-baseline replay in ``test_golden_baselines.py`` (the end-to-end config
test). Each test re-solves the shipped example config and asserts the
economically load-bearing relationship (Hotelling's (1+r)^t ramp, CBAM's
price-immunity, OBA's benchmark*output grant, the CCR cap-adjustment gating,
the lambda blend and its floor-immunity) rather than a captured number.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pe import run_simulation_from_file

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"


def _by_scenario(summary, name: str):
    """Rows of one scenario, ordered by year, as a DataFrame."""
    return summary[summary["Scenario"] == name].sort_values("Year")


def test_hotelling_price_ramps_at_discount_rate() -> None:
    """Hotelling anchor: P_t / P_0 = (1 + r)^t with r = 0.05, budget binds."""
    summary, participants = run_simulation_from_file(EXAMPLES_DIR / "hotelling_budget.json")
    prices = list(summary.sort_values("Year")["Equilibrium Carbon Price"])
    p0 = prices[0]
    for t, pt in enumerate(prices):
        # The price is pinned to lambda*(1.05)^t, so the ratio is exact.
        np.testing.assert_allclose(pt / p0, 1.05**t, rtol=0, atol=1e-12)
    # Monotone rising.
    assert all(b > a for a, b in zip(prices, prices[1:]))
    # Budget binds: cumulative residual emissions exhaust the 600 Mt budget
    # to the solver's 1e-4 relative bisection tolerance (no competitive fallback).
    cumulative_residual = float(participants["Residual Emissions"].sum())
    np.testing.assert_allclose(cumulative_residual, 600.0, rtol=1e-4, atol=0)


def test_cbam_is_reporting_only_but_liability_populates() -> None:
    """CBAM anchor: prices are lambda/CBAM-immune; liability = gap*residual*share."""
    summary, participants = run_simulation_from_file(EXAMPLES_DIR / "cbam_border_adjustment.json")
    no_cbam = _by_scenario(summary, "No CBAM")
    with_cbam = _by_scenario(summary, "With CBAM")
    # F6 reporting-only: enabling CBAM cannot move a cleared price.
    np.testing.assert_array_equal(
        no_cbam["Equilibrium Carbon Price"].to_numpy(),
        with_cbam["Equilibrium Carbon Price"].to_numpy(),
    )
    # No-CBAM scenario carries zero liability; With-CBAM is strictly positive.
    assert (no_cbam["Total CBAM Liability"] == 0.0).all()
    assert (with_cbam["Total CBAM Liability"] > 0.0).all()
    # Per-firm formula: Steel 2026 liability = gap * residual * export_share.
    steel_2026 = participants[
        (participants["Scenario"] == "With CBAM")
        & (participants["Year"] == "2026")
        & (participants["Participant"] == "Steel")
    ].iloc[0]
    gap_2026 = float(with_cbam[with_cbam["Year"] == "2026"]["CBAM Gap"].iloc[0])
    expected = gap_2026 * float(steel_2026["Residual Emissions"]) * 0.30
    np.testing.assert_allclose(float(steel_2026["CBAM Liability"]), expected, rtol=0, atol=1e-9)
    # Total cost including CBAM shifts up by exactly the liability layer.
    np.testing.assert_allclose(
        with_cbam["Total Cost incl. CBAM"].to_numpy(),
        (with_cbam["Total Compliance Cost"] + with_cbam["Total CBAM Liability"]).to_numpy(),
        rtol=0,
        atol=1e-6,
    )


def test_oba_free_allocation_tracks_benchmark_times_output() -> None:
    """OBA anchor: free allocation = benchmark * output and tightens each year."""
    summary, participants = run_simulation_from_file(EXAMPLES_DIR / "oba_output_allocation.json")
    large = participants[participants["Participant"] == "Steel_Large"].sort_values("Year")
    small = participants[participants["Participant"] == "Steel_Small"].sort_values("Year")
    power = participants[participants["Participant"] == "Power"].sort_values("Year")
    # free_allocation = beta * Y with Y=25 (large) / 12 (small); beta = 2.0,1.8,1.6.
    np.testing.assert_allclose(
        large["Free Allocation"].to_numpy(), np.array([2.0, 1.8, 1.6]) * 25.0, rtol=0, atol=1e-9
    )
    np.testing.assert_allclose(
        small["Free Allocation"].to_numpy(), np.array([2.0, 1.8, 1.6]) * 12.0, rtol=0, atol=1e-9
    )
    # The tightening benchmark shrinks the OBA grant monotonically...
    assert list(large["Free Allocation"]) == sorted(large["Free Allocation"], reverse=True)
    assert list(small["Free Allocation"]) == sorted(small["Free Allocation"], reverse=True)
    # ...and the conventional (fixed-ratio) participant's grant is flat.
    assert power["Free Allocation"].nunique() == 1
    # Compliance obligation responds: allowance buys rise as free allocation falls.
    assert list(large["Allowance Buys"]) == sorted(large["Allowance Buys"])
    assert list(small["Allowance Buys"]) == sorted(small["Allowance Buys"])


def test_ccr_neutral_before_shock_and_caps_the_spike() -> None:
    """CCR anchor: dQ = 0 before the shock; loosens and caps price after."""
    summary, _ = run_simulation_from_file(EXAMPLES_DIR / "ccr_cost_containment.json")
    fixed = _by_scenario(summary, "Fixed cap")
    ccr = _by_scenario(summary, "Carbon Cap Rule").reset_index(drop=True)
    # References equal the pre-shock steady state, so the rule is neutral through
    # 2027 (it can only react to the previous year's realised cost).
    pre = ccr[ccr["Year"].isin(["2025", "2026", "2027"])]
    np.testing.assert_allclose(pre["CCR Cap Adjustment"].to_numpy(), 0.0, rtol=0, atol=1e-9)
    # From 2028 the lagged cost deviation triggers a positive (loosening) dQ...
    post = ccr[ccr["Year"].isin(["2028", "2029"])]
    assert (post["CCR Cap Adjustment"] > 1.0).all()
    assert (post["CCR Cost Deviation"] > 0.0).all()
    # dQ = phi_e*emDev + phi_z*costDev with phi_e=-5, phi_z=3 (closed form).
    for _, row in post.iterrows():
        expected = -5.0 * float(row["CCR Emissions Deviation"]) + 3.0 * float(
            row["CCR Cost Deviation"]
        )
        np.testing.assert_allclose(float(row["CCR Cap Adjustment"]), expected, rtol=0, atol=1e-9)
    # ...and the extra permits hold the sustained-phase price below the fixed cap.
    fixed_post = fixed[fixed["Year"].isin(["2028", "2029"])]["Equilibrium Carbon Price"].to_numpy()
    ccr_post = post["Equilibrium Carbon Price"].to_numpy()
    assert (ccr_post < fixed_post).all()


def test_transmission_blend_and_floor_immunity() -> None:
    """Transmission anchor: blend is the convex mean; the binding floor is lambda-immune."""
    summary, _ = run_simulation_from_file(EXAMPLES_DIR / "transmission_lambda.json")
    relapse = _by_scenario(summary, "lambda 0.0 (relapse / pure spot)").reset_index(drop=True)
    hold = _by_scenario(summary, "lambda 0.5 (hold / partial transmission)").reset_index(drop=True)
    consolidate = _by_scenario(summary, "lambda 1.0 (consolidate / pure Hotelling)").reset_index(
        drop=True
    )

    comp = relapse["Static Component Price"].to_numpy()
    hot = relapse["Hotelling Component Price"].to_numpy()
    floor = relapse["Reserve Floor Price"].to_numpy()

    # Delivered = max(blend, floor), blend-first-clip-last, for each lambda.
    for lam, delivered in ((0.0, relapse), (0.5, hold), (1.0, consolidate)):
        blended = (1.0 - lam) * comp + lam * hot
        expected = np.maximum(blended, floor)
        np.testing.assert_allclose(
            delivered["Equilibrium Carbon Price"].to_numpy(), expected, rtol=0, atol=1e-9
        )

    years = list(relapse["Year"])
    d0 = relapse["Equilibrium Carbon Price"].to_numpy()
    d1 = consolidate["Equilibrium Carbon Price"].to_numpy()
    # Floor-immune years (2026-2027): every lambda delivers the identical floor.
    for yr in ("2026", "2027"):
        i = years.index(yr)
        assert d0[i] == d1[i] == floor[i]
    # Above the floor (2028-2029): the lambda endpoints genuinely differ.
    for yr in ("2028", "2029"):
        i = years.index(yr)
        assert d0[i] != d1[i]
    # The Hotelling component itself ramps at the 5% discount rate.
    np.testing.assert_allclose(hot[1] / hot[0], 1.05, rtol=0, atol=1e-12)
    np.testing.assert_allclose(hot[3] / hot[0], 1.05**3, rtol=0, atol=1e-12)
