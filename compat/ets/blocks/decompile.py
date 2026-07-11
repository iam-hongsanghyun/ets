"""Deprecated mirror of ``pe.blocks.decompile`` — import ``pe.blocks.decompile`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.decompile import *  # noqa

warnings.warn(
    "ets.blocks.decompile is deprecated; import pe.blocks.decompile instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
