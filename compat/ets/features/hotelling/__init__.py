"""Deprecated mirror of ``pe.features.hotelling`` — import ``pe.features.hotelling`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.hotelling import *  # noqa

warnings.warn(
    "ets.features.hotelling is deprecated; import pe.features.hotelling instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
