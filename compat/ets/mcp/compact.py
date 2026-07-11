"""Deprecated mirror of ``pe.mcp.compact`` — import ``pe.mcp.compact`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.compact import *  # noqa

warnings.warn(
    "ets.mcp.compact is deprecated; import pe.mcp.compact instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
