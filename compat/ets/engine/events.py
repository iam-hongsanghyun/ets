"""Deprecated mirror of ``pe.engine.events`` — import ``pe.engine.events`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine.events import *  # noqa

warnings.warn(
    "ets.engine.events is deprecated; import pe.engine.events instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
