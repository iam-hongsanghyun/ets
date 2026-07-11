# Backward-compatibility shim — re-exports from core.market.model.
# New location: src/ets/core/market/model.py.
import warnings

from pe.core.market.model import CarbonMarket

warnings.warn(
    "ets.market.core is deprecated; import from pe.core.market.model "
    "instead. Removal milestone: 0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CarbonMarket"]
