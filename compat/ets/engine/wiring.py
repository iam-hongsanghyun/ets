"""Deprecated mirror of ``pe.engine.wiring`` — import ``pe.engine.wiring`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine.wiring import *  # noqa

warnings.warn(
    "ets.engine.wiring is deprecated; import pe.engine.wiring instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
