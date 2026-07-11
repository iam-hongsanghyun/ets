"""Deprecated mirror of ``pe.core.market`` — import ``pe.core.market`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.market import *  # noqa

warnings.warn(
    "ets.core.market is deprecated; import pe.core.market instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
