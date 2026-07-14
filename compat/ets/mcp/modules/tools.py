"""Deprecated mirror of ``pe.mcp.modules.tools`` — import ``pe.mcp.modules.tools`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.modules.tools import *  # noqa

warnings.warn(
    "ets.mcp.modules.tools is deprecated; import pe.mcp.modules.tools instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
