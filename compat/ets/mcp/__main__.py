"""Deprecated entry point for ``python -m ets.mcp`` — use ``python -m pe.mcp``.

Delegates to the ``pe`` composer MCP server. The deprecation warning is emitted
on STDERR only (``warnings.warn`` writes to stderr); the MCP protocol owns
STDOUT, which stays byte-clean. Removed at 0.4.0.
"""

from __future__ import annotations

import warnings

from pe.mcp.server import main

# stacklevel=1 so the warning is attributed to this __main__ frame and shows on
# stderr under the default filter (a `python -m ets.mcp` entry point, not an
# import shim); stdout stays protocol-clean.
warnings.warn(
    "ets.mcp is deprecated; run `python -m pe.mcp` instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=1,
)

if __name__ == "__main__":
    main()
