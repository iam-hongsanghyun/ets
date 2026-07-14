"""Deprecated mirror of ``pe.mcp.run.server`` — import ``pe.mcp.run.server`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.run.server import *  # noqa

warnings.warn(
    "ets.mcp.run.server is deprecated; import pe.mcp.run.server instead. Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
