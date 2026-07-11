"""Deprecated mirror of ``pe.core.market.model`` — import ``pe.core.market.model`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.market.model import *  # noqa

warnings.warn(
    "ets.core.market.model is deprecated; import pe.core.market.model instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
