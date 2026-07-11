"""Deprecated mirror of ``pe.core.market.reporting`` — import ``pe.core.market.reporting`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.market.reporting import *  # noqa

warnings.warn(
    "ets.core.market.reporting is deprecated; import pe.core.market.reporting instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
