"""Deprecated mirror of ``pe.features.oba.plugin`` — import ``pe.features.oba.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.oba.plugin import *  # noqa

warnings.warn(
    "ets.features.oba.plugin is deprecated; import pe.features.oba.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
