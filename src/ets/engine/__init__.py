"""Deprecated mirror of ``pe.engine`` — import ``pe.engine`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine import *  # noqa

warnings.warn(
    "ets.engine is deprecated; import pe.engine instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
