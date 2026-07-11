"""Core-path anchors for the Dixit–Pindyck math in ``pe.core.investment``.

Imports from the T0 kernel module directly (the analysis facade is proven
separately by ``tests/workflows/analysis/test_investment_trigger.py``) and
pins the K-MSR paper's worked multiples plus the analytical certainty limit
— spec anchors V1b/V1c of ``docs/invest-feedback-spec.md``. The functions
under test are called, never re-derived.
"""

from __future__ import annotations

import numpy as np

from pe.core.investment import credible_floor_multiple, trigger_multiple

R, Y = 0.055, 0.03  # paper's r = 5.5 %, y = 3 %


def test_v1c_paper_multiples() -> None:
    """V1c: σ ∈ {0.20, 0.30, 0.48} → multiples ≈ {2.86, 3.86, 6.4} (rtol 5e-3)."""
    for sigma, expected in ((0.20, 2.86), (0.30, 3.86), (0.48, 6.4)):
        np.testing.assert_allclose(trigger_multiple(sigma, R, Y), expected, rtol=5e-3)


def test_v1b_certainty_limit_is_timing_wedge() -> None:
    """V1b: σ = 0, r = .055, y = .03 → multiple == r/y == credible_floor_multiple."""
    np.testing.assert_allclose(trigger_multiple(0.0, R, Y), R / Y, rtol=1e-12)
    np.testing.assert_allclose(credible_floor_multiple(R, Y), R / Y, rtol=1e-12)
