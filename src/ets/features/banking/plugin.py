"""Deprecated mirror of ``pe.features.banking.plugin`` — import ``pe.features.banking.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.banking.plugin import *  # noqa

warnings.warn(
    "ets.features.banking.plugin is deprecated; import pe.features.banking.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
