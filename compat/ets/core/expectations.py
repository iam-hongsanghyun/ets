"""Deprecated mirror of ``pe.core.expectations`` — import ``pe.core.expectations`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.expectations import *  # noqa

warnings.warn(
    "ets.core.expectations is deprecated; import pe.core.expectations instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
