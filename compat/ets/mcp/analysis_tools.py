"""Deprecated mirror of ``pe.mcp.analysis_tools`` — import ``pe.mcp.analysis_tools`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.analysis_tools import *  # noqa

warnings.warn(
    "ets.mcp.analysis_tools is deprecated; import pe.mcp.analysis_tools instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
