"""Deprecated mirror of ``pe.core.costs`` — import ``pe.core.costs`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.costs import *  # noqa

warnings.warn(
    "ets.core.costs is deprecated; import pe.core.costs instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
