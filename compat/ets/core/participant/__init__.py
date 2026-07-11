"""Deprecated mirror of ``pe.core.participant`` — import ``pe.core.participant`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.participant import *  # noqa

warnings.warn(
    "ets.core.participant is deprecated; import pe.core.participant instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
