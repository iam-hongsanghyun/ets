"""Deprecated mirror of ``pe.features.oba`` — import ``pe.features.oba`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.oba import *  # noqa

warnings.warn(
    "ets.features.oba is deprecated; import pe.features.oba instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
