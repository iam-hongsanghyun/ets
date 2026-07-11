"""Deprecated mirror of ``pe.features.sectors`` — import ``pe.features.sectors`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.sectors import *  # noqa

warnings.warn(
    "ets.features.sectors is deprecated; import pe.features.sectors instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
