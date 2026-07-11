"""Deprecated mirror of ``pe.features.banking.window`` — import ``pe.features.banking.window`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.banking.window import *  # noqa

warnings.warn(
    "ets.features.banking.window is deprecated; import pe.features.banking.window instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
