"""Deprecated mirror of ``pe.mcp`` — import ``pe.mcp`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp import *  # noqa

warnings.warn(
    "ets.mcp is deprecated; import pe.mcp instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
