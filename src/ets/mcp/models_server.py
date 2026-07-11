"""Deprecated mirror of ``pe.mcp.models_server`` — import ``pe.mcp.models_server`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.models_server import *  # noqa

warnings.warn(
    "ets.mcp.models_server is deprecated; import pe.mcp.models_server instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
