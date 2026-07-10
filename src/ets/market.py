# Backward-compatibility shim — re-exports from the market sub-package.
# New location: src/ets/market/ (the sub-package).
# Note: Python resolves 'market' to the market/ package when both exist,
# so this module is shadowed and never imported; the warning below is
# kept for the removal milestone bookkeeping.
import warnings

from .market import CarbonMarket

warnings.warn(
    "the flat ets/market.py shim is deprecated; import from the ets.market "
    "sub-package instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CarbonMarket"]
