"""Deprecated mirror of ``pe.engine.feedback`` — import ``pe.engine.feedback`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine.feedback import *  # noqa

warnings.warn(
    "ets.engine.feedback is deprecated; import pe.engine.feedback instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
