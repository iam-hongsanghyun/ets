"""Deprecated mirror of ``pe.features.ccr`` — import ``pe.features.ccr`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.ccr import *  # noqa

warnings.warn(
    "ets.features.ccr is deprecated; import pe.features.ccr instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
