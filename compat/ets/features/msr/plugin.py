"""Deprecated mirror of ``pe.features.msr.plugin`` — import ``pe.features.msr.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.msr.plugin import *  # noqa

warnings.warn(
    "ets.features.msr.plugin is deprecated; import pe.features.msr.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
