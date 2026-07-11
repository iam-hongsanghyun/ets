"""Deprecated mirror of ``pe.features.msr.state`` — import ``pe.features.msr.state`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.msr.state import *  # noqa

warnings.warn(
    "ets.features.msr.state is deprecated; import pe.features.msr.state instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
