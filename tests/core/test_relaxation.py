"""Hand-verified unit tests for the T0 path-map relaxation kernels.

Covers the three public helpers of :mod:`pe.core.relaxation`:

* ``relax_pathmap`` — the (1-w)·prev + w·cur under-relaxation step, checked
  against hand values at w=0.5 and at the two boundary weights (w=1 returns
  the current map exactly, w=0 returns the previous map exactly);
* ``max_pathmap_change`` — the absolute max |Δ| convergence metric;
* ``max_pathmap_relative_change`` — the D2 per-market dimensionless norm
  (docs/joint-equilibrium.md §5), including the div-by-zero guard as the
  current price is driven to zero (the ``max(ref, |cur|)`` floor).

The keys mirror the coupling loop's ``(scenario, year)`` path keys, but the
kernels treat them as opaque, so the values are what these tests pin.
"""

from __future__ import annotations

import pytest

from pe.core.relaxation import (
    max_pathmap_change,
    max_pathmap_relative_change,
    relax_pathmap,
)

# Two-year, two-scenario path map (opaque keys; only the scalars matter).
_A = ("base", "2030")
_B = ("base", "2031")
_C = ("policy", "2030")


def test_relax_pathmap_half_weight_hand_values() -> None:
    """w=0.5: (1-0.5)*10 + 0.5*20 = 15, per key per year."""
    previous = {_A: 10.0, _B: 4.0}
    current = {_A: 20.0, _B: 8.0}
    relaxed = relax_pathmap(previous, current, 0.5)
    assert relaxed == {_A: pytest.approx(15.0), _B: pytest.approx(6.0)}


def test_relax_pathmap_weight_one_returns_current_exactly() -> None:
    """w=1 is a plain (undamped) Gauss-Seidel step: the current map, unchanged."""
    previous = {_A: 10.0, _B: 4.0, _C: 1.0}
    current = {_A: 20.0, _B: 8.0, _C: 3.0}
    assert relax_pathmap(previous, current, 1.0) == pytest.approx(current)


def test_relax_pathmap_weight_zero_returns_previous_exactly() -> None:
    """w=0 freezes the signal at the previous map."""
    previous = {_A: 10.0, _B: 4.0, _C: 1.0}
    current = {_A: 20.0, _B: 8.0, _C: 3.0}
    assert relax_pathmap(previous, current, 0.0) == pytest.approx(previous)


def test_max_pathmap_change_hand_value() -> None:
    """Max absolute change across keys: max(|12-10|, |100-5|) = 95."""
    previous = {_A: 10.0, _B: 5.0}
    current = {_A: 12.0, _B: 100.0}
    assert max_pathmap_change(previous, current) == pytest.approx(95.0)


def test_max_pathmap_change_empty_is_zero() -> None:
    """Empty maps converge trivially (default 0.0)."""
    assert max_pathmap_change({}, {}) == 0.0


def test_max_pathmap_relative_change_mixed_magnitudes() -> None:
    """Per-market dimensionless norm across mixed magnitudes (spec §5).

    key _A: |110-100| / max(ref=50, |110|) = 10/110
    key _B: |12-10|   / max(ref=50, |12|)  = 2/50 = 0.04
    The large-price key dominates because its own magnitude sets the scale.
    """
    previous = {_A: 100.0, _B: 10.0}
    current = {_A: 110.0, _B: 12.0}
    result = max_pathmap_relative_change(previous, current, ref=50.0)
    assert result == pytest.approx(10.0 / 110.0)


def test_max_pathmap_relative_change_ref_floor_dominates_small_prices() -> None:
    """When |cur| < ref, the ref floor sets the denominator: 0.5/100 = 0.005."""
    previous = {_A: 1.0}
    current = {_A: 1.5}
    assert max_pathmap_relative_change(previous, current, ref=100.0) == pytest.approx(0.005)


def test_max_pathmap_relative_change_div_by_zero_guard_at_zero_price() -> None:
    """cur -> 0 must not divide by zero: the ref floor carries the denominator.

    |0-5| / max(ref=10, |0|) = 5/10 = 0.5, no ZeroDivisionError.
    """
    previous = {_A: 5.0}
    current = {_A: 0.0}
    assert max_pathmap_relative_change(previous, current, ref=10.0) == pytest.approx(0.5)
