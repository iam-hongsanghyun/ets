"""Deprecated mirror of ``pe.blocks`` — import ``pe.blocks`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks import *  # noqa

warnings.warn(
    "ets.blocks is deprecated; import pe.blocks instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
