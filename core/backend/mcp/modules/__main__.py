"""Entry point for ``python -m pe.mcp.modules`` — starts the pe-modules server on stdio."""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()
