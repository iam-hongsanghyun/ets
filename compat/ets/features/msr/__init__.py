"""Deprecated mirror of ``pe.features.msr`` — import ``pe.features.msr`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.msr import *  # noqa

warnings.warn(
    "ets.features.msr is deprecated; import pe.features.msr instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
