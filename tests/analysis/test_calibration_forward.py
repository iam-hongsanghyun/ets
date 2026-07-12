"""Forward calibration: elasticity + anchor -> slope config block.

Each test asserts the analytic round-trip — build the block from
``(elasticity, P0, Q0)``, then recompute the point elasticity implied by the
emitted slope and confirm it reproduces the input to tight tolerance.
"""
from __future__ import annotations

import numpy as np
import pytest

from pe.analysis.calibration import (
    abatement_from_reference,
    linear_slope_from_elasticity,
    output_cost_from_elasticity,
    product_demand_from_elasticity,
)

RTOL = 1e-12


def test_linear_slope_identity() -> None:
    # |dQ/dP| = |eps| * Q/P
    s = linear_slope_from_elasticity(-0.4, price=50.0, quantity=100.0)
    np.testing.assert_allclose(s, 0.4 * 100.0 / 50.0, rtol=RTOL)


def test_product_demand_recovers_elasticity_and_anchor() -> None:
    eps, P0, Q0 = -0.3, 60.0, 40.0
    block = product_demand_from_elasticity(eps, P0, Q0)
    assert block["form"] == "linear"
    # Anchor lies on the curve: Q0 == A_d - b_d*P0
    np.testing.assert_allclose(block["A_d"] - block["b_d"] * P0, Q0, rtol=RTOL)
    # Recomputed elasticity at the anchor: eps = -b_d * P0 / Q0
    recovered = -block["b_d"] * P0 / Q0
    np.testing.assert_allclose(recovered, eps, rtol=RTOL)


def test_output_cost_recovers_supply_elasticity() -> None:
    eps, P0, q0 = 0.8, 60.0, 5.0
    block = output_cost_from_elasticity(eps, P0, q0)
    assert block["delta"] > 0.0  # FOC requires an upward slope
    # eps_S = (1/delta) * (P0/q0)
    recovered = (1.0 / block["delta"]) * (P0 / q0)
    np.testing.assert_allclose(recovered, eps, rtol=RTOL)
    # gamma solved so the anchor sits on inverse supply P = gamma + delta*q
    np.testing.assert_allclose(block["gamma"] + block["delta"] * q0, P0, rtol=RTOL)


def test_output_cost_nets_out_carbon_cost_in_intercept() -> None:
    eps, P0, q0, B = 0.8, 60.0, 5.0, 10.0
    block = output_cost_from_elasticity(eps, P0, q0, carbon_cost=B)
    # P0 = gamma + B + delta*q0
    np.testing.assert_allclose(block["gamma"] + B + block["delta"] * q0, P0, rtol=RTOL)


def test_output_cost_explicit_gamma_passthrough() -> None:
    block = output_cost_from_elasticity(0.8, 60.0, 5.0, gamma=12.0)
    assert block["gamma"] == 12.0
    assert block["delta"] > 0.0


def test_abatement_from_reference_pins_beta() -> None:
    block = abatement_from_reference(carbon_price=20.0, abatement=4.0, a_max=6.0)
    np.testing.assert_allclose(block["beta"], 20.0 / 4.0, rtol=RTOL)
    assert block["a_max"] == 6.0
    # a = P_c/beta reproduces the anchor abatement
    np.testing.assert_allclose(20.0 / block["beta"], 4.0, rtol=RTOL)


@pytest.mark.parametrize(
    "fn,args",
    [
        (linear_slope_from_elasticity, (-0.4, 0.0, 100.0)),
        (linear_slope_from_elasticity, (-0.4, 50.0, 0.0)),
        (product_demand_from_elasticity, (-0.4, -1.0, 100.0)),
        (abatement_from_reference, (0.0, 4.0)),
        (abatement_from_reference, (20.0, 0.0)),
    ],
)
def test_nonpositive_anchor_raises(fn, args) -> None:
    with pytest.raises(ValueError):
        fn(*args)


def test_upward_supply_guard() -> None:
    with pytest.raises(ValueError):
        output_cost_from_elasticity(0.0, 60.0, 5.0)  # flat/inelastic -> ill-posed
    with pytest.raises(ValueError):
        output_cost_from_elasticity(-0.5, 60.0, 5.0)  # downward -> not supply
