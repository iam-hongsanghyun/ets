"""Deprecated mirror of ``pe.mcp.models`` — import ``pe.mcp.models`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.models import *  # noqa

warnings.warn(
    "ets.mcp.models is deprecated; import pe.mcp.models instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
