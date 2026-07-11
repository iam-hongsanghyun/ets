"""Deprecated mirror of ``pe.engine.links`` — import ``pe.engine.links`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.engine.links import *  # noqa

warnings.warn(
    "ets.engine.links is deprecated; import pe.engine.links instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
