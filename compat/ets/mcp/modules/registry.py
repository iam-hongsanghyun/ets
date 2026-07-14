"""Deprecated mirror of ``pe.mcp.modules.registry`` — import ``pe.mcp.modules.registry`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.modules.registry import *  # noqa

warnings.warn(
    "ets.mcp.modules.registry is deprecated; import pe.mcp.modules.registry instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
