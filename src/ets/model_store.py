"""Deprecated mirror of ``pe.model_store`` — import ``pe.model_store`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.model_store import *  # noqa

warnings.warn(
    "ets.model_store is deprecated; import pe.model_store instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
