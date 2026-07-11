"""Deprecated mirror of ``pe.blocks.compile`` — import ``pe.blocks.compile`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.compile import *  # noqa

warnings.warn(
    "ets.blocks.compile is deprecated; import pe.blocks.compile instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
