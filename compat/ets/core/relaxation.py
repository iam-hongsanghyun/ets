"""Deprecated mirror of ``pe.core.relaxation`` — import ``pe.core.relaxation`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.relaxation import *  # noqa

warnings.warn(
    "ets.core.relaxation is deprecated; import pe.core.relaxation instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
