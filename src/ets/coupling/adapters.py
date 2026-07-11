"""Deprecated mirror of ``pe.coupling.adapters`` — import ``pe.coupling.adapters`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.coupling.adapters import *  # noqa

warnings.warn(
    "ets.coupling.adapters is deprecated; import pe.coupling.adapters instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
