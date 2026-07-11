"""Deprecated mirror of ``pe.analysis.batch`` — import ``pe.analysis.batch`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis.batch import *  # noqa

warnings.warn(
    "ets.analysis.batch is deprecated; import pe.analysis.batch instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
