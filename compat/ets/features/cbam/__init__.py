"""Deprecated mirror of ``pe.features.cbam`` — import ``pe.features.cbam`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.cbam import *  # noqa

warnings.warn(
    "ets.features.cbam is deprecated; import pe.features.cbam instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
