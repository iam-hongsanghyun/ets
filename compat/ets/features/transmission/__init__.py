"""Deprecated mirror of ``pe.features.transmission`` — import ``pe.features.transmission`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.transmission import *  # noqa

warnings.warn(
    "ets.features.transmission is deprecated; import pe.features.transmission instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
