"""Entry point for ``python -m pe.mcp.config`` — starts the pe-config server on stdio."""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()
