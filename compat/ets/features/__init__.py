"""Deprecated mirror of ``pe.features`` — import ``pe.features`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features import *  # noqa

warnings.warn(
    "ets.features is deprecated; import pe.features instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
