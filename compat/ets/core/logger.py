"""Deprecated mirror of ``pe.core.logger`` — import ``pe.core.logger`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.logger import *  # noqa

warnings.warn(
    "ets.core.logger is deprecated; import pe.core.logger instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
