"""Deprecated mirror of ``pe.features.ccr.state`` — import ``pe.features.ccr.state`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.ccr.state import *  # noqa

warnings.warn(
    "ets.features.ccr.state is deprecated; import pe.features.ccr.state instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
