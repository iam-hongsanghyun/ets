"""Deprecated mirror of ``pe.mcp.tools`` — import ``pe.mcp.tools`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.tools import *  # noqa

warnings.warn(
    "ets.mcp.tools is deprecated; import pe.mcp.tools instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
