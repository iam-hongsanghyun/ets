# Phase 2 architecture: D0 (rename + vocabulary + domain packs) and D1 (one-way market links)

Authored by lead-modeller. Binding economic spec: docs/platform-spec-d0-d1.md.
Verified against main @ 4e30068. All solved numbers preserved by construction
at every rung; the 39-golden replay is the arbiter throughout.

## Pre-flight facts (verified)

- Frontend↔backend couples only via /api/* — the rename does not touch the
  HTTP contract (gate keeps a grep to keep it true).
- TWO RENAME LANDMINES: (1) web/api.py attaches the dashboard warning
  collector to logging.getLogger("ets") — post-rename all loggers are pe.*;
  fix = dual attach ("pe" and "ets"), drop "ets" at 0.4.0. (2) baselines'
  entry_point strings ("ets.run_simulation_from_file", batch, calibration)
  are provenance pins asserted byte-for-byte by the replay — FROZEN, never
  renamed; migrate only on a legitimate future recapture.
- `import ets` warning-clean inverts INTENTIONALLY in D0: ets.* becomes the
  warning tier, pe.* the clean tier (Order-9 precedent, audit-logged).
- Launchers still exec ets_framework.py — retarget to python -m pe.cli.
- Composer today: one carbon_market node = one scenario (compile groups
  market nodes into scenarios) — D1's disentanglement builds on this.
- validate.py rules end at R33; next free R34+.

## D0-R1 — THE RENAME (one mechanical order; executor module-extractor; full gate)

1. `git mv src/ets src/pe` (history follows); rewrite ~25 absolute
   self-references; relative imports untouched (the proof it is imports-only).
2. Extract the legacy flat shims OUT of src/pe into the new src/ets compat
   package, retargeted one hop to pe.* (O17 style; recorded milestones kept;
   messages name pe.engine / pe.features.msr / ...). src/pe is born shim-free.
3. Generate the src/ets MIRROR: for every module pe.X, a shim ets/X.py =
   star-reexport + DeprecationWarning ("import pe.X instead. Removal: 0.4.0",
   stacklevel=2). ets/__init__ re-exports the public surface and warns.
   Underscore names NOT re-exported by mirror modules; the legacy flat shims
   keep their exact recorded leakage surface (0.4.0 ledger unchanged).
   ets/mcp/__main__ delegates to pe.mcp (warning on stderr only — MCP stdout
   stays protocol-clean).
4. pyproject: name = "pe", version = 0.2.0 (D1 = 0.3.0, shims retire 0.4.0);
   both packages ship for the window; uv.lock regenerated and committed.
5. Infra: api/index.py → pe.web.server; vercel.json includeFiles += src/pe/**
   (keep src/ets/**); .mcp.json → python -m pe.mcp / pe.mcp.models (keys
   pe-composer/pe-models); launchers exec python -m pe.cli; ets_framework.py
   retargets and stays a warning shim; web/api.py dual logger attach.
6. Tests: mass rewrite ets.→pe. (39 files); test_module_isolation classifies
   pe.* (SHIM_MODULES now empty — machinery reserved), PENDING_VIOLATIONS
   stays empty (the ratchet does not reopen for a rename);
   test_shim_deprecations: CLEAN_IMPORTS = pe.* surface, SHIM_WARNINGS
   regenerated, NEW mirror-completeness test (every pe module has an ets
   counterpart; AST-walk asserts src/ets modules import only pe.* + stdlib +
   warnings; exactly one own warning each). _capture.py imports pe but
   entry_point literals FROZEN with a pinning comment. MANIFEST: one
   audit_log entry. Golden JSONs: zero bytes.
7. Frontend: no code change; gate = npm build + grep for module coupling.

Gate: uv sync; FULL pytest (39/39 replays bit-identical); -W error clean
import of the pe surface; shim+isolation suites; ruff no new findings;
Vercel import smoke; pe.cli smoke + headless GUI curl; MCP handshakes for
pe.mcp AND ets.mcp (shim); frontend build+grep.

PRECONDITIONS: prune stale worktrees; merge/close branches touching
src/ets; announce a rename freeze window. Repo names on GitHub are out of
scope (owner decision: one repo).

## D0-R2..R6

- R2 backend flow vocabulary: scenario flow_label (default "carbon") /
  flow_unit (default "tCO2e") in normalize+templates; ParamSpecs on
  carbon_market (keys enter KNOWN_SCENARIO_KEYS — load-bearing for
  decompile); MCP compact header gains "flow: label [unit]" only when
  non-default. Display only; zero new columns; goldens prove it.
- R3 frontend display reads: MarketChart axis title, headings, PeApp chips
  read flow_label/flow_unit with carbon defaults (carbon models render
  byte-identically).
- R4 non-carbon showcase: RPS/REC buyout market (spec §1 verdict) —
  existing mechanisms only + flow labels; surgical golden capture +
  audit_log; proves the platform claim.
- R5 domain packs REAL: BlockSpec.domain (default "general"); cbam(+scope-2
  params) tagged domain kets [economist E2 confirms; also kmsr_decree];
  manifest gains "domains" (derived — K-* examples classify automatically);
  /api/blocks serializes domain; composer palette filter; pe.command
  grouping; MCP domain= filters. NO packaging split (declared deferral).
- R6 docs pointer pass (rename + flow + domain + Desktop MCP config note).

## D1 — multi-market schema

Scenario MAY carry markets: [{market_id, flow_label/unit, model_approach,
mechanism flags, years[], participants...}] and links: [{from_market,
to_market, channel, phi, phi_unit, target_participants,
target_technologies, back_demand_estimate}]. A market body = today's
scenario body minus name/policy_events; normalize_scenario internals
reused per market. COMPAT RULE (bit-identity by construction): scenarios
WITHOUT markets normalize down the byte-identical legacy path; the flat
shape REMAINS the canonical normalized form for single-market scenarios
(markets view is derived via config_io.iter_market_bodies(scenario) →
[(None, scenario)] degenerate). Interim loud ValueError in decompile for
markets-shaped configs until D1-4 (never let _scenario_extra swallow one).

GRAPH DISENTANGLEMENT: a scenario = a connected component of market nodes
under link edges; a linkless market node = component of size one = today's
semantics exactly (every existing graph compiles bit-identically). New
block market_link (category links) with ports market signal → link → market
links port; compile: size-1 components verbatim today's path; larger →
one scenario with markets+links (market node name = market_id; order
deterministic; scenario_name param must agree across the component).
Decompile inverse; round-trip property-tested both directions. Validation:
R34 DAG (loud cycle error naming D2), R35 channel/units whitelist, R36
declarations; "::" forbidden in ids of multi-market scenarios (composite
grouping key); policy_events + markets → loud error (deferred, E7);
model_approach "all" inside markets → loud error.

## D1 — engine

- engine/links.py (T3): topological_market_order (Kahn, deterministic
  tie-break, cycle → ValueError citing D2); apply_links pure copy-on-write
  (vintage.apply precedent) reading the DELIVERED per-year price of
  upstream (same object feedback.py reads). LinkChannel protocol in
  core/protocols.py; implementations features/market_links/channels.py
  (T2); config door features/market_links/plugin.py; reviewed
  LINK_CHANNELS literal in engine/wiring.py.
- dispatch: single-market → byte-identical legacy branch (goldens prove);
  multi-market → topo order; per-market _path_solver_for closures REUSED
  UNTOUCHED (approaches may differ per market); composite grouping key
  "scenario :: market_id" (the _rename_markets precedent) so ledger/summary
  machinery is unmodified; guarded "Market" column + link diagnostics
  columns ONLY on multi-market scenarios (key-presence-guard precedent).
- INVESTMENT COMPOSITION — recommendation PER-MARKET wrapping in topo
  order (block-triangular: one-way links make sequential per-market fixed
  points compose EXACTLY to the chain equilibrium at cost Σ(N_i+1) solves
  vs (ΣN_i+1) for chain-level; reuses solve_with_investment_feedback and
  the D1.4 termination proof verbatim). [Economist E4 verdict pending.]
- Events × multi-market: EXPLICITLY DEFERRED to D2 (loud error) — splicing
  re-invokes dispatch per segment with carried state; per-market carriers ×
  link re-application × cross-market announcement semantics is a real
  design problem. [E7 sign-off pending.]

## D1 — units

Explicit unit-string checks primary (R36 string equality vs both
endpoints' declarations); pint as validator-only dimensional lint behind
an extra (import-guarded) — honours the CLAUDE.md mandate exactly at the
boundary where bare floats would cross with units mattering. Full pint
through the solve path = declared D3-candidate programme (repo-wide float
perturbation risk + golden recapture); never smuggled into D1.

## Work orders

D0-R1 (L, extractor, FULL gate + smokes) → R2 (M) ∥ R5 (M) → R3 (S) ∥ R4
(S) → R6 (S). D1-0 economist channel/anchor doc [E-slots] gates D1-2/3/4.
D1-1 schema+accessor+normalize-snapshot regression (M) → D1-2 protocols+
feature channels+anchor units tests (M) → D1-3 engine links+dispatch+
investment wrap+guarded columns (L, FULL gate) → D1-4 blocks ports+
market_link+component compile/decompile+R34-36 (L, FULL gate + round-trip
property tests) → D1-5 units validation (S) → D1-6 two-market linked
golden, small (S-M, FULL gate) → D1-7 frontend composer link edges +
pe-shell multi-market tabs (L) ∥ D1-8 MCP link-awareness (M) → D1-9 docs
(S). Versions: D0 = 0.2.0, D1 = 0.3.0, ets mirror retires 0.4.0 (own
removal order with import census).

## Risks

Rename blast radius (worktree prune + branch freeze preconditions; GitHub
repo names untouched); the two landmines pre-neutralized; _scenario_extra
passthrough vs the markets key (interim loud guard); composite key
collisions ("::" ban); runtime multiplication (small linked goldens; slow
marks; per-market investment wrap); composer mental-model shift (the link
edge is the ONLY semantic change, drawn and narrated); deferrals recorded:
D2 cyclic links + events×multi-market + chain-level feedback if E4 rules
so; D3 pint-through-solve, domain packaging split, frontend isolation
test, 0.4.0 mirror retirement.

## Pending economist verdicts

E1 flow vocabulary defaults · E1b showcase calibration + qualitative
anchors · E2 domain tags (cbam/scope-2, kmsr_decree, K-* set) · E4
per-market vs chain-level investment wrapping (block-triangular argument
above) · E5 two-market golden design · E6 guarded diagnostic column names ·
E7 events×multi-market deferral sign-off · E8 R34-R36 rule texts + horizon
alignment when linked markets' year grids differ.
