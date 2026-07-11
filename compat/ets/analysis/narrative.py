"""Deprecated mirror of ``pe.analysis.narrative`` — import ``pe.analysis.narrative`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis.narrative import *  # noqa

warnings.warn(
    "ets.analysis.narrative is deprecated; import pe.analysis.narrative instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
