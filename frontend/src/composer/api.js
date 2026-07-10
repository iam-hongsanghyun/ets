// Fetch wrapper for the graph-composer backend contract
// (docs/blocks-graph-plan.md §5). The live endpoints are being built
// concurrently (Order 8) — every call here degrades gracefully instead of
// throwing, so the Composer view stays usable while the backend lands.

import { BLOCKS_FIXTURE } from "./blocksFixture.js";

async function safeFetchJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    return { ok: false, unavailable: true, status: null, data: null, error: String(error) };
  }
  if (response.status === 404) {
    return { ok: false, unavailable: true, status: 404, data: null, error: "not found" };
  }
  // The Vite dev server (no backend attached) answers unknown paths with a
  // 200 + the SPA's index.html rather than a 404. Treat "not actually JSON"
  // the same as "not found" so the fixture fallback still kicks in.
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("json")) {
    return { ok: false, unavailable: true, status: response.status, data: null, error: "endpoint did not return JSON" };
  }
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    return { ok: false, unavailable: false, status: response.status, data: null, error: "invalid JSON response" };
  }
  if (!response.ok) {
    return { ok: false, unavailable: false, status: response.status, data, error: data?.error || `HTTP ${response.status}` };
  }
  return { ok: true, unavailable: false, status: response.status, data, error: null };
}

// GET /api/blocks -> { blocks: [...] }. Falls back to the hand-authored dev
// fixture only when the live endpoint is unavailable (network error or 404).
// Always prefers the live endpoint.
async function fetchBlockCatalogue() {
  const result = await safeFetchJson("/api/blocks");
  if (result.ok) {
    return { blocks: result.data.blocks || [], source: "live" };
  }
  if (result.unavailable) {
    return { blocks: BLOCKS_FIXTURE, source: "fixture" };
  }
  // Endpoint exists but returned an error — surface it rather than silently
  // falling back, so a real backend bug isn't masked as "not built yet".
  throw new Error(result.error || "Failed to load block catalogue.");
}

// GET /api/templates -> { templates: [...] } (existing endpoint, already
// used by the rest of the app).
async function fetchTemplates() {
  const result = await safeFetchJson("/api/templates");
  if (result.ok) return result.data.templates || [];
  return [];
}

// GET /api/graph/from-template?id=<id> -> { graph }
async function fetchGraphFromTemplate(templateId) {
  return safeFetchJson(`/api/graph/from-template?id=${encodeURIComponent(templateId)}`);
}

// POST /api/graph/validate {graph} -> { ok, issues }
async function validateGraph(graph) {
  return safeFetchJson("/api/graph/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph }),
  });
}

// POST /api/graph/compile {graph} -> { config }
async function compileGraph(graph) {
  return safeFetchJson("/api/graph/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph }),
  });
}

// POST /api/graph/run {graph} -> today's /api/run payload plus a "graph" echo
async function runGraph(graph) {
  return safeFetchJson("/api/graph/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph }),
  });
}

export {
  fetchBlockCatalogue,
  fetchTemplates,
  fetchGraphFromTemplate,
  validateGraph,
  compileGraph,
  runGraph,
};
