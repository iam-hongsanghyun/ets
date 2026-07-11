"""Deprecated mirror of ``pe.blocks.validate`` — import ``pe.blocks.validate`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.validate import *  # noqa

warnings.warn(
    "ets.blocks.validate is deprecated; import pe.blocks.validate instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
