"""Deprecated mirror of ``pe.core.investment`` — import ``pe.core.investment`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.investment import *  # noqa

warnings.warn(
    "ets.core.investment is deprecated; import pe.core.investment instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
