"""Deprecated mirror of ``pe.engine.dispatch`` — import ``pe.engine.dispatch`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine.dispatch import *  # noqa

warnings.warn(
    "ets.engine.dispatch is deprecated; import pe.engine.dispatch instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
