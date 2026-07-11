"""Deprecated mirror of ``pe.features.msr.decree`` — import ``pe.features.msr.decree`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.msr.decree import *  # noqa

warnings.warn(
    "ets.features.msr.decree is deprecated; import pe.features.msr.decree instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
