"""Deprecated mirror of ``pe.core.paths`` — import ``pe.core.paths`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.paths import *  # noqa

warnings.warn(
    "ets.core.paths is deprecated; import pe.core.paths instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
