"""Deprecated mirror of ``pe.core.participant.technology`` — import ``pe.core.participant.technology`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.participant.technology import *  # noqa

warnings.warn(
    "ets.core.participant.technology is deprecated; import pe.core.participant.technology instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
