"""Deprecated mirror of ``pe.features.hoarding`` — import ``pe.features.hoarding`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.hoarding import *  # noqa

warnings.warn(
    "ets.features.hoarding is deprecated; import pe.features.hoarding instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
