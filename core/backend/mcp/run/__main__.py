"""Entry point for ``python -m pe.mcp.run`` — starts the pe-run server on stdio."""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()
