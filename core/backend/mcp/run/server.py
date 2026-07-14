"""FastMCP server: the pe-run app (operation + analysis) over stdio.

Wires the governor tools (``pe.mcp.models_tools``) and the analysis tools
(``pe.mcp.analysis_tools``) into one server. The governor half is the same
operate-time surface the legacy ``pe.mcp.models_server`` (pe-models) exposed;
the analysis half is new (``pe.analysis`` post-processing). See
:mod:`pe.mcp.run`'s package docstring for the role split.

Run: ``python -m pe.mcp.run`` (stdio transport — the shape the repo-root
``.mcp.json`` registers as ``pe-run``).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .. import analysis_tools, models_tools

SERVER_NAME = "pe-run"

INSTRUCTIONS = """\
You RUN and ANALYSE the ETS (emissions-trading-system) model registry: the \
bundled examples under examples/ and every model saved to the shared registry \
(the same registry the pe-config server's save_model writes to, and the web \
composer's "Save model" too).

Role boundary: this server OPERATES already-configured models -- it never \
edits a model's internals. If the user wants to change what a model contains \
(add a block, tweak a parameter), send them to the pe-config server \
(new_graph(template_id=<model_id>) loads the model onto its canvas), or to \
the pe-modules server for a single feature.

Workflow (operation):
1. Call list_models() first -- never guess a model id.
2. Call describe_model(model_id) before running anything unfamiliar: it \
reports scenarios, year span, participants, and configured mechanisms without \
solving. Use model_manifest(model_id) for the raw per-scenario breakdown.
3. run_model(model_id, scenario=...) solves one model into a compact per-year \
summary. compare_models(model_ids, scenario=...) aligns up to 4 models by \
year. sweep_model(model_id, parameter_path, values) explores one parameter.
4. rename_model / delete_model only work on saved "user_" entries; bundled \
examples are immutable. Confirm before deleting -- it is not reversible.

Workflow (analysis):
- run_batch(model_id, sweeps) sweeps several parameter axes at once (the \
multi-axis generalisation of sweep_model), reporting per-combination \
headlines.
- narrate_model(model_id) returns a plain-language summary of the solved \
price/abatement path.
- import_csv(csv_text) turns a per-year CSV into a runnable config (hand it \
to pe-config to save).
- compute_investment_trigger(sigma, r, y) gives the Dixit–Pindyck real- \
options trigger multiple and break-even dating.
- calibrate_slopes(model_id, observed_prices, participant_names) inverse-fits \
MAC slopes to observed prices; calibrate_from_elasticity / \
calibrate_abatement_from_reference forward-build a demand/supply/abatement \
block from one anchor.

Do not fabricate a model's configuration or results -- everything you say \
must come from this server's own tool output, never guessed or remembered \
from a previous turn.
"""


def build_server() -> FastMCP:
    """Construct the FastMCP server with every run/analysis tool registered."""
    server = FastMCP(name=SERVER_NAME, instructions=INSTRUCTIONS)
    for fn in (
        # operation (governor)
        models_tools.list_models,
        models_tools.describe_model,
        models_tools.run_model,
        models_tools.compare_models,
        models_tools.sweep_model,
        models_tools.rename_model,
        models_tools.delete_model,
        models_tools.model_manifest,
        models_tools.list_sessions,
        models_tools.run_session,
        # analysis (post-processing)
        analysis_tools.run_batch,
        analysis_tools.narrate_model,
        analysis_tools.import_csv,
        analysis_tools.compute_investment_trigger,
        analysis_tools.calibrate_slopes,
        analysis_tools.calibrate_from_elasticity,
        analysis_tools.calibrate_abatement_from_reference,
    ):
        server.tool()(fn)
    return server


mcp = build_server()


def main() -> None:
    """Entry point for ``python -m pe.mcp.run`` — serve over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
