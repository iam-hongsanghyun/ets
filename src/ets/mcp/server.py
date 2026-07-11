"""Deprecated mirror of ``pe.mcp.server`` — import ``pe.mcp.server`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.server import *  # noqa

warnings.warn(
    "ets.mcp.server is deprecated; import pe.mcp.server instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
