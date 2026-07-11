"""Deprecated mirror of ``pe.core.defaults`` — import ``pe.core.defaults`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.defaults import *  # noqa

warnings.warn(
    "ets.core.defaults is deprecated; import pe.core.defaults instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
