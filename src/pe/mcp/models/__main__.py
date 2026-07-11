"""Entry point for ``python -m ets.mcp.models`` — starts the governor MCP server on stdio."""

from __future__ import annotations

from ..models_server import main

if __name__ == "__main__":
    main()
