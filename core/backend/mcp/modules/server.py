"""FastMCP server: wires ``pe.mcp.modules.tools`` up as the pe-modules server.

The factory server (see :mod:`pe.mcp.modules`'s package docstring). It
registers the four uniform per-module tools plus one templated doc resource,
``pe-module://{module}/reference``, that serves each module's
``doc/reference.md`` — so a client can pull a module's full mechanism text as
a resource instead of a tool result when it prefers to.

Run: ``python -m pe.mcp.modules`` (stdio transport — the shape the repo-root
``.mcp.json`` registers as ``pe-modules``).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import tools
from .registry import get_module
from .tools import _read_reference

SERVER_NAME = "pe-modules"

INSTRUCTIONS = """\
You are a per-feature expert for the ETS (emissions-trading-system) modelling \
platform. Each "module" is one policy/market feature (banking, MSR, CCR, \
CBAM, price controls, hotelling, nash_cournot, sectors, transmission, ...). \
This server gives every module the same four-tool surface; you pick the \
module by name.

Workflow:
1. Call list_modules() first to see which features exist, what blocks each \
owns, and whether it has a mechanism doc -- never guess a module name.
2. Call describe_module(module) before proposing values: it returns that \
module's block descriptors (every param with its declared default, unit, \
bounds, and allowed values) plus its reference.md mechanism doc. Propose \
economically meaningful values from the doc and the declared defaults -- do \
not invent thresholds, reference prices, or budgets.
3. To add a feature to a model the user is composing, call \
configure_module(graph, module, params=...) -- it adds and wires that \
module's block onto the graph exactly as the pe-config server would, and \
returns the updated graph plus any validation issues. Pass block_id=... only \
when the module owns more than one block. Then hand the graph back to \
pe-config (check/save) to continue composing.
4. To see just this feature's effect on an already-saved model, call \
run_module_scoped(model_id, module) -- it runs the model and reports only \
this module's own output columns (the bank path, the MSR reserve pool, the \
CCR adjustment, ...). If it reports active=false, the feature was disabled or \
produced only neutral values in that model; use the pe-run server's \
run_model for the overall price/abatement path.

Only report numbers and defaults that came back from this server's own tool \
output; never fabricate a param default or a scoped result.
"""


def module_reference(module: str) -> str:
    """Resource body for ``pe-module://{module}/reference`` — the mechanism doc.

    Args:
        module: A feature-module name (see ``list_modules``).

    Returns:
        The module's ``doc/reference.md`` text, or a short placeholder line
        when the module ships no reference doc.

    Raises:
        ValueError: ``module`` is not a known module.
    """
    try:
        info = get_module(module)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    text = _read_reference(info)
    return text if text is not None else f"Module '{module}' ships no reference doc."


def build_server() -> FastMCP:
    """Construct the FastMCP server with every module tool + doc resource registered."""
    server = FastMCP(name=SERVER_NAME, instructions=INSTRUCTIONS)
    for fn in (
        tools.list_modules,
        tools.describe_module,
        tools.configure_module,
        tools.run_module_scoped,
    ):
        server.tool()(fn)
    server.resource(
        "pe-module://{module}/reference",
        name="module-reference",
        description="A feature module's doc/reference.md mechanism text.",
        mime_type="text/markdown",
    )(module_reference)
    return server


mcp = build_server()


def main() -> None:
    """Entry point for ``python -m pe.mcp.modules`` — serve over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
