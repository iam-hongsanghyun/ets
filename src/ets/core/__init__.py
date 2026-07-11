"""Deprecated mirror of ``pe.core`` — import ``pe.core`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core import *  # noqa

warnings.warn(
    "ets.core is deprecated; import pe.core instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
