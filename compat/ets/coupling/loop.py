"""Deprecated mirror of ``pe.coupling.loop`` — import ``pe.coupling.loop`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.coupling.loop import *  # noqa

warnings.warn(
    "ets.coupling.loop is deprecated; import pe.coupling.loop instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
