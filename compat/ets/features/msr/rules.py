"""Deprecated mirror of ``pe.features.msr.rules`` — import ``pe.features.msr.rules`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.msr.rules import *  # noqa

warnings.warn(
    "ets.features.msr.rules is deprecated; import pe.features.msr.rules instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
