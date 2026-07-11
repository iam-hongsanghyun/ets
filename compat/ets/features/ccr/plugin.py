"""Deprecated mirror of ``pe.features.ccr.plugin`` — import ``pe.features.ccr.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.ccr.plugin import *  # noqa

warnings.warn(
    "ets.features.ccr.plugin is deprecated; import pe.features.ccr.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
