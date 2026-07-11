"""Deprecated mirror of ``pe.blocks.graph`` — import ``pe.blocks.graph`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.graph import *  # noqa

warnings.warn(
    "ets.blocks.graph is deprecated; import pe.blocks.graph instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
