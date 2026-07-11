"""Deprecated mirror of ``pe.mcp.suggestions`` — import ``pe.mcp.suggestions`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.mcp.suggestions import *  # noqa

warnings.warn(
    "ets.mcp.suggestions is deprecated; import pe.mcp.suggestions instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
