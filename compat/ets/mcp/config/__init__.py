"""Deprecated mirror of ``pe.mcp.config`` — import ``pe.mcp.config`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.config import *  # noqa

warnings.warn(
    "ets.mcp.config is deprecated; import pe.mcp.config instead. Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
