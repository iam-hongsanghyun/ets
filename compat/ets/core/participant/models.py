"""Deprecated mirror of ``pe.core.participant.models`` — import ``pe.core.participant.models`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.participant.models import *  # noqa

warnings.warn(
    "ets.core.participant.models is deprecated; import pe.core.participant.models instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
