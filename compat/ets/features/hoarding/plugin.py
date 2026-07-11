"""Deprecated mirror of ``pe.features.hoarding.plugin`` — import ``pe.features.hoarding.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.hoarding.plugin import *  # noqa

warnings.warn(
    "ets.features.hoarding.plugin is deprecated; import pe.features.hoarding.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
