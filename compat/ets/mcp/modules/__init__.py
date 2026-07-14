"""Deprecated mirror of ``pe.mcp.modules`` — import ``pe.mcp.modules`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.modules import *  # noqa

warnings.warn(
    "ets.mcp.modules is deprecated; import pe.mcp.modules instead. Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
