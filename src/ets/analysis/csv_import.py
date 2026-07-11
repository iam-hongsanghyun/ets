"""Deprecated mirror of ``pe.analysis.csv_import`` — import ``pe.analysis.csv_import`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis.csv_import import *  # noqa

warnings.warn(
    "ets.analysis.csv_import is deprecated; import pe.analysis.csv_import instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
