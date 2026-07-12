// pe.command Canvas tab ONLY: derive a §2 wire-graph document from ONE
// scenario config (the App's live `config` is the single source of truth), so
// the visual editor renders the SAME model the Model (forms) tab edits.
//
// This is the config->graph direction the Canvas needs at mount/rebuild. It is
// deliberately DISPLAY-oriented, not a full round-trip decompiler: it emits the
// data-entity graph the pe-shell canvas can edit — the market, its price-
// formation node, its companies (participants), sectors and technology options
// — and never a compile-faithful mechanism wiring. The Canvas never compiles
// this graph back to config (the reverse direction is a TARGETED field update,
// see CanvasView.jsx), so a missing optional mechanism node only affects what
// is drawn, never config integrity — the backend `graph_from_config`
// (blocks/decompile.py) remains the authority for a full graph.
//
// Node ids mirror decompile.py's scheme (`market0`, `market0_pf`,
// `market0_p<i>`), and `peModelExpand.expandModelGraph` then materialises
// `market0_sector<i>` and `market0_p<i>_opt<j>` from the opaque `sectors` /
// `technology_options` params — so a node id alone locates its config target
// (see parseNodeTarget), no per-node metadata threading required.

import { blockById } from "../composer/graphUtils.js";

const MARKET_ID = "market0";

// Price-formation block per modelling approach (mirrors decompile.py's
// _PF_BLOCK_FOR_APPROACH) — a display node only; falls back to competitive.
const PF_BLOCK_FOR_APPROACH = {
  competitive: "competitive_clearing",
  banking: "rubin_schennach_banking",
  hotelling: "hotelling",
  nash_cournot: "nash_cournot",
};

// A sector config entry keys its name as `name`; the `sector` block spells the
// same field `sector_name` (its other three params are config-key `sectors`
// too). This is the ONLY name divergence between a data entity's node params
// and its config keys — participant/technology_option config keys equal their
// param names, so those round-trip as identity.
const SECTOR_PARAM_TO_KEY = { sector_name: "name" };

function sectorParamToKey(paramName) {
  return SECTOR_PARAM_TO_KEY[paramName] || paramName;
}

// The year grid the carbon_market node displays — every year field except the
// per-year participant list (which becomes participant nodes instead).
function yearGrid(years) {
  return (years || []).map(({ participants, ...rest }) => rest);
}

// Build the §2 wire document for ONE scenario, using `displayYear`'s
// participants as the model's company structure. `sectors` and each
// participant's `technology_options` stay as opaque list params here —
// expandModelGraph turns them into their own nodes downstream.
function graphFromScenario(scenario, catalogue, displayYear) {
  if (!scenario) return { version: 1, nodes: [], edges: [], meta: {} };
  const nodes = [];
  const edges = [];

  const marketParams = { name: scenario.name, years: yearGrid(scenario.years) };
  if ((scenario.sectors || []).length) marketParams.sectors = scenario.sectors;
  nodes.push({ id: MARKET_ID, block: "carbon_market", params: marketParams });

  const pfBlockId = PF_BLOCK_FOR_APPROACH[scenario.model_approach] || "competitive_clearing";
  if (blockById(catalogue, pfBlockId)) {
    nodes.push({ id: `${MARKET_ID}_pf`, block: pfBlockId, params: {} });
    edges.push({ source: `${MARKET_ID}_pf`, sourcePort: "price_formation", target: MARKET_ID, targetPort: "price_formation" });
  }

  const participants = (displayYear?.participants) || (scenario.years?.[0]?.participants) || [];
  participants.forEach((participant, index) => {
    const id = `${MARKET_ID}_p${index}`;
    nodes.push({ id, block: "participant", params: { ...participant, order: index } });
    edges.push({ source: id, sourcePort: "compliance", target: MARKET_ID, targetPort: "participants" });
  });

  return { version: 1, nodes, edges, meta: {} };
}

// Locate the config target a canvas node id maps to. Ids are the decompile.py /
// expandModelGraph scheme, so the id alone is enough — no side table.
function parseNodeTarget(nodeId) {
  let match;
  if ((match = /^market\d+_p(\d+)_opt(\d+)$/.exec(nodeId))) {
    return { kind: "technology_option", participantIndex: Number(match[1]), optionIndex: Number(match[2]) };
  }
  if ((match = /^market\d+_p(\d+)$/.exec(nodeId))) {
    return { kind: "participant", index: Number(match[1]) };
  }
  if ((match = /^market\d+_sector(\d+)$/.exec(nodeId))) {
    return { kind: "sector", index: Number(match[1]) };
  }
  return { kind: "other" };
}

export { graphFromScenario, parseNodeTarget, sectorParamToKey, MARKET_ID };
