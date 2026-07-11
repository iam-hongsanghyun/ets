"""Deprecated mirror of ``pe.core.baseline`` — import ``pe.core.baseline`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.baseline import *  # noqa

warnings.warn(
    "ets.core.baseline is deprecated; import pe.core.baseline instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
