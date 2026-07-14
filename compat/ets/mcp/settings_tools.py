"""Deprecated mirror of ``pe.mcp.settings_tools`` — import ``pe.mcp.settings_tools`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.settings_tools import *  # noqa

warnings.warn(
    "ets.mcp.settings_tools is deprecated; import pe.mcp.settings_tools instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
