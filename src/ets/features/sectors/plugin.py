"""Deprecated mirror of ``pe.features.sectors.plugin`` — import ``pe.features.sectors.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.sectors.plugin import *  # noqa

warnings.warn(
    "ets.features.sectors.plugin is deprecated; import pe.features.sectors.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
