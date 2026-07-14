"""Deprecated mirror of ``pe.mcp.run`` — import ``pe.mcp.run`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.run import *  # noqa

warnings.warn(
    "ets.mcp.run is deprecated; import pe.mcp.run instead. Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
