"""Permanent re-export facade for the Dixit–Pindyck investment-trigger math.

The machinery lives in :mod:`ets.core.investment` (T0 kernel, stdlib-only)
so that feature/engine code can reach it under the tier contract; this
module REMAINS the T4 analysis surface for post-processing workflows — the
blocks catalogue's ``investment_trigger`` block references
``analysis/investment_trigger.py`` as its documentation anchor. This is not
a deprecation shim: no warning is emitted and the import path is supported
indefinitely. An analysis module reading downward into ``ets.core`` is a
legal edge under ``tests/test_module_isolation.py``.

See :mod:`ets.core.investment` for the algorithm, references, and the
paper's worked values.
"""

from __future__ import annotations

from pe.core.investment import (
    activation_year,
    beta_positive_root,
    credible_floor_multiple,
    effective_volatility,
    trigger_multiple,
)

__all__ = [
    "beta_positive_root",
    "trigger_multiple",
    "credible_floor_multiple",
    "effective_volatility",
    "activation_year",
]
