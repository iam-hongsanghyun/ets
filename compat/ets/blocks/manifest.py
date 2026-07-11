"""Deprecated mirror of ``pe.blocks.manifest`` — import ``pe.blocks.manifest`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.blocks.manifest import *  # noqa

warnings.warn(
    "ets.blocks.manifest is deprecated; import pe.blocks.manifest instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
