"""Deprecated mirror of ``pe.features.ccr.rules`` — import ``pe.features.ccr.rules`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.ccr.rules import *  # noqa

warnings.warn(
    "ets.features.ccr.rules is deprecated; import pe.features.ccr.rules instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
