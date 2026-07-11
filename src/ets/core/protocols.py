"""Deprecated mirror of ``pe.core.protocols`` — import ``pe.core.protocols`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.protocols import *  # noqa

warnings.warn(
    "ets.core.protocols is deprecated; import pe.core.protocols instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
