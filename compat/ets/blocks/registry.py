"""Deprecated mirror of ``pe.blocks.registry`` — import ``pe.blocks.registry`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.registry import *  # noqa

warnings.warn(
    "ets.blocks.registry is deprecated; import pe.blocks.registry instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
