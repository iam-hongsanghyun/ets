"""Deprecated mirror of ``pe.blocks.serialize`` — import ``pe.blocks.serialize`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.serialize import *  # noqa

warnings.warn(
    "ets.blocks.serialize is deprecated; import pe.blocks.serialize instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
