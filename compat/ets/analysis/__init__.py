"""Deprecated mirror of ``pe.analysis`` — import ``pe.analysis`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis import *  # noqa

warnings.warn(
    "ets.analysis is deprecated; import pe.analysis instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
