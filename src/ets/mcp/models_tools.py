"""Deprecated mirror of ``pe.mcp.models_tools`` — import ``pe.mcp.models_tools`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.models_tools import *  # noqa

warnings.warn(
    "ets.mcp.models_tools is deprecated; import pe.mcp.models_tools instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
