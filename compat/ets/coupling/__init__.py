"""Deprecated mirror of ``pe.coupling`` — import ``pe.coupling`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.coupling import *  # noqa

warnings.warn(
    "ets.coupling is deprecated; import pe.coupling instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
