"""Deprecated top-level ``ets`` package — import ``pe`` instead.

Re-exports the public surface (``CarbonMarket``, ``MarketParticipant``,
``run_simulation*``) from ``pe`` for the ets->pe rename window (D0-R1). The
whole ``ets`` compat package is removed at 0.4.0.
"""

import warnings

from pe import (
    CarbonMarket,
    MarketParticipant,
    run_simulation,
    run_simulation_from_config,
    run_simulation_from_file,
)

warnings.warn(
    "ets is deprecated; import pe instead. Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CarbonMarket",
    "MarketParticipant",
    "run_simulation",
    "run_simulation_from_config",
    "run_simulation_from_file",
]
