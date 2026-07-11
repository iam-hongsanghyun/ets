"""Deprecated mirror of ``pe.core.participant.compliance`` — import ``pe.core.participant.compliance`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.participant.compliance import *  # noqa

warnings.warn(
    "ets.core.participant.compliance is deprecated; import pe.core.participant.compliance instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
