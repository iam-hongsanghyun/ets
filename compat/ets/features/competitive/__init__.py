"""Deprecated mirror of ``pe.features.competitive`` — import ``pe.features.competitive`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.competitive import *  # noqa

warnings.warn(
    "ets.features.competitive is deprecated; import pe.features.competitive instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
