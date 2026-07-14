"""FastMCP server: the pe-config app (authoring + settings) over stdio.

Wires the composer tools (``pe.mcp.tools``) and the settings tools
(``pe.mcp.settings_tools``) into one server. The composer half is the same
stateless "graph document is the conversation state" surface the legacy
``pe.mcp.server`` (pe-composer) exposed; the settings half is new (read-only
``PE_*`` inspection). See :mod:`pe.mcp.config`'s package docstring for the
role split.

Run: ``python -m pe.mcp.config`` (stdio transport — the shape the repo-root
``.mcp.json`` registers as ``pe-config``).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .. import settings_tools, tools

SERVER_NAME = "pe-config"

INSTRUCTIONS = """\
You help a user CONFIGURE the ETS (emissions-trading-system) modelling \
platform: both authoring a scenario model and inspecting the deployment \
settings that decide where models are stored.

Model authoring -- the graph document is the conversation's state. You hold \
the "graph" dict every mutating tool returns, pass it back into the next \
call, and narrate what changed in plain language. Every tool is stateless.

Workflow (authoring):
1. Start from the user's question ("model a cap-and-trade market with a \
reserve", "reproduce the K-MSR paper", "add a price floor"). Call \
list_models() and list_blocks() to see what already exists before proposing \
anything -- prefer starting from a matching example or saved model.
2. Call new_graph() for a blank minimum-viable market, or \
new_graph(template_id=...) to start from an example or saved model.
3. Propose blocks one or two at a time, in plain language, explaining what \
each needs (describe_block(block_id) gives its params/ports/requires/ \
excludes). Only call add_block / set_params / remove_node once the user \
agrees. For a single policy/market FEATURE (banking, MSR, CCR, ...), the \
pe-modules server's describe_module/configure_module is the per-feature \
expert -- defer to it when the user wants to understand one mechanism deeply.
4. ALWAYS call check(graph) after every mutation. Read its "next_steps": ask \
the user each question it poses -- do not silently apply the suggested fix.
5. Once check(graph)["ok"] is true, hand the graph to the pe-run server to \
run it, or call run_model(graph) here for a quick check; summarise results \
in plain language and never report a number a tool didn't return.
6. When the user is happy, offer save_model(graph, name). A saved model \
appears immediately in the pe-run server's model list and the web composer.

Do not guess economically meaningful defaults (CCR reference values, MSR \
thresholds, carbon budgets, discount rates) -- ask, or point at \
describe_block's declared defaults/units and let the user decide.

Deployment settings -- list_settings()/describe_setting(name) report the \
PE_* environment variables that select the model-registry backend and its \
location. These are READ-ONLY here and secret values are redacted; if a \
setting needs changing, tell the user to edit their .env file themselves \
(this server never writes credentials).
"""


def build_server() -> FastMCP:
    """Construct the FastMCP server with every config tool registered."""
    server = FastMCP(name=SERVER_NAME, instructions=INSTRUCTIONS)
    for fn in (
        # authoring (composer graph)
        tools.list_models,
        tools.list_blocks,
        tools.describe_block,
        tools.new_graph,
        tools.add_block,
        tools.set_params,
        tools.remove_node,
        tools.check,
        tools.run_model,
        tools.save_model,
        # deployment settings (read-only)
        settings_tools.list_settings,
        settings_tools.describe_setting,
    ):
        server.tool()(fn)
    return server


mcp = build_server()


def main() -> None:
    """Entry point for ``python -m pe.mcp.config`` — serve over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
