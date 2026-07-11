"""Deprecated mirror of ``pe.analysis.calibration`` — import ``pe.analysis.calibration`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis.calibration import *  # noqa

warnings.warn(
    "ets.analysis.calibration is deprecated; import pe.analysis.calibration instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
