"""Deprecated mirror of ``pe.blocks.catalogue`` — import ``pe.blocks.catalogue`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.catalogue import *  # noqa

warnings.warn(
    "ets.blocks.catalogue is deprecated; import pe.blocks.catalogue instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
