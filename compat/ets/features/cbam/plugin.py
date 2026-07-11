"""Deprecated mirror of ``pe.features.cbam.plugin`` — import ``pe.features.cbam.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.cbam.plugin import *  # noqa

warnings.warn(
    "ets.features.cbam.plugin is deprecated; import pe.features.cbam.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
