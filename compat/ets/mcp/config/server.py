"""Deprecated mirror of ``pe.mcp.config.server`` — import ``pe.mcp.config.server`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.config.server import *  # noqa

warnings.warn(
    "ets.mcp.config.server is deprecated; import pe.mcp.config.server instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
