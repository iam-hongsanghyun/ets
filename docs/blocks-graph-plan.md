# GUI-composability implementation plan (blocks + graph compiler)

Authored by lead-modeller (architecture co-lead, modularization programme).
Companion economic spec: `docs/blocks-composition-rules.md` (validator rules
R1–R32 and engine findings F1–F6).

Principle: **a drawn graph compiles to the existing scenario-config dict**;
the only runtime is `ets.solvers.simulation.run_simulation_from_config`. No
block executes math. Blocks are metadata + a deterministic compiler.

Baseline reference: `PYTHONPATH=src python3 -m pytest -q` → 73 passed,
4 xfailed. Golden baselines live in `tests/baselines/` (see `_capture.py` and
`MANIFEST.json`).

Known-inert config keys: `examples/k_msr_paper_reproduction.json` carries
`international_offset_cost/limit/band` keys read by no code in `src/` —
deliberately excluded from the catalogue.

## 1. Block catalogue

`config_key` names verified against `config_io/builder.py:normalize_scenario`
(scenario scope), `config_io/normalize.py:normalize_year` (year scope) and
`normalize_participant` (participant scope). Defaults from
`config_io/templates.py:blank_*`.

### market

| block id | wraps | params → config keys | ports |
|---|---|---|---|
| `carbon_market` | `market/core.py:CarbonMarket` via `config_io/builder.py:build_market_from_year`; one node = one scenario in `{"scenarios":[...]}` | `name`→`scenarios[].name`; `order`; per-year grid `years[]`: `year`, `total_cap`, `auction_mode` (`explicit`\|`derive_from_cap`), `auction_offered`, `reserved_allowances`, `carbon_budget`, `banking_allowed`, `borrowing_allowed`, `borrowing_limit` | in: `participants` (1..n), `sectors` (0..n), `price_formation` (exactly 1), `policies` (0..n), `expectations` (0..1); out: `results` → analysis blocks |

### price-formation (exactly one per market; all set `model_approach`)

| block id | wraps | params → config keys |
|---|---|---|
| `competitive_clearing` | `solvers/simulation.py:solve_scenario_path`, `market/equilibrium.py:solve_equilibrium` | `model_approach="competitive"`; `solver_competitive_max_iters`, `solver_competitive_tolerance`, `solver_penalty_price_multiplier`, `solver_price_bracket_expand_factor`, `solver_price_bracket_max_expansions`, `solver_slsqp_max_iters`, `solver_slsqp_ftol` |
| `rubin_schennach_banking` | `solvers/banking.py:solve_banking_path` | `model_approach="banking"`; `discount_rate`, `risk_premium`, `banking_initial_bank`, `banking_strict_no_arbitrage`, `banking_bank_tolerance`, `banking_supply_rule_max_iters`, `banking_supply_rule_tolerance` |
| `hotelling` | `solvers/hotelling.py:solve_hotelling_path` | `model_approach="hotelling"`; `discount_rate`, `risk_premium`, `solver_hotelling_*` (bisection/λ-expansion settings) |
| `nash_cournot` | `solvers/nash.py:solve_nash_path` | `model_approach="nash_cournot"`; `solver_nash_*`; `nash_strategic_participants` populated from participant→block edges (port `strategic`) |
| `forward_transmission` | `solvers/transmission.py:solve_transmission_path`, `blend_prices` | `model_approach="competitive"` + `forward_transmission_lambda` ∈ [0,1]; hotelling params for the blend |
| `compare_all` | `solvers/simulation.py:run_simulation` "all" branch | `model_approach="all"` (expose as compare action, not a block) |

### policy (0..n per market; one per family)

| block id | wraps | params → config keys | constraints |
|---|---|---|---|
| `msr_bank_threshold` | `solvers/msr.py:MSRState.apply` | `msr_enabled=true`, `msr_mode="bank_threshold"`, `msr_upper_threshold`, `msr_lower_threshold`, `msr_withhold_rate`, `msr_release_rate`, `msr_cancel_excess`, `msr_cancel_threshold`, `msr_initial_reserve_mt`, `msr_start_year` | exclusive with `kmsr_decree` |
| `kmsr_decree` | `solvers/banking.py:_decree_msr_action` inside the supply-rule fixed point | `msr_enabled=true`, `msr_mode`∈{`price_band`,`surplus_rule`,`hybrid`}, `msr_price_band_high/_low`, `msr_surplus_upper_ratio/_lower_ratio`, `msr_max_intake_mt`, `msr_max_release_mt`, `msr_initial_reserve_mt`, `msr_start_year` | requires `rubin_schennach_banking` |
| `ccr` | `solvers/ccr.py:CCRState.cap_adjustment` | `ccr_enabled=true`, `ccr_phi_emissions`, `ccr_phi_abatement_cost`, `ccr_reference_emissions`, `ccr_reference_abatement_cost`, `ccr_start_year` | requires competitive |
| `price_floor` | bound clamping in `market/equilibrium.py` | year `price_lower_bound` and/or `price_floor_trajectory` | |
| `price_ceiling` | same | `price_upper_bound` / `price_ceiling_trajectory` | |
| `auction_reserve` | auction mechanics in `equilibrium.py:solve_equilibrium` (+ reserve-price cancellation in banking supply rule) | year `auction_reserve_price`, `minimum_bid_coverage`, `unsold_treatment`∈{`reserve`,`cancel`,`carry_forward`} | |
| `cancellation` | year-level cap removal | schedule `[{year, amount}]` → `years[].cancelled_allowances` | |
| `cap_path` | `builder.py:_interp_value` | `cap_trajectory` {start_year, end_year, start_value, end_value} | |
| `free_allocation_phaseout` | `builder.py:_interp_ratio` | `free_allocation_trajectories[]` | participant names must resolve |
| `oba` | OBA override in `builder.py:build_market_from_year` | table `[{participant, benchmark_emission_intensity}]`; `production_output` stays a participant param | |
| `cbam` | CBAM liability in `market/results.py` | year `eua_price`, `eua_prices`, `eua_price_ensemble`; exposure params stay on participants | diagnostics-only |
| `hoarding` | `solvers/banking.py:_hoarding_inflow` | schedule `[{year, amount}]` → `years[].hoarding_inflow` | requires banking |

Policy timing: every policy block carries optional `announced` (year label).
If later than the first market year, the compiler emits a `policy_events[]`
entry (`{"announced", "changes", "year_overrides"}`) instead of base config —
executed by `solvers/events.py:solve_scenario_with_events`. Reproduces
`examples/k_msr_event_timing_2x2.json` from the canvas.

### expectations

| block id | wraps | params |
|---|---|---|
| `expectations` | `solvers/expectations.py:ExpectationSpec`, `derive_expected_prices` | year `expectation_rule` ∈ {myopic, next_year_baseline, perfect_foresight, manual}, `manual_expected_price`; meaningful only with competitive / forward_transmission |
| `price_elastic_baseline` | Feedback Option A: `participant/models.py:MarketParticipant.activity_multiplier` | scenario `reference_carbon_price`; per-participant `output_price_elasticity` stays on participants |

### participants

| block id | wraps | params | ports |
|---|---|---|---|
| `participant` | `participant/models.py:MarketParticipant` via `build_participant` | `name`, `order`, `sector`, `initial_emissions(_trajectory)`, `free_allocation_ratio`, `penalty_price`, `abatement_type`∈{linear,threshold,piecewise}, `max_abatement`, `cost_slope`, `threshold_cost`, `mac_blocks[]`, `sector_allocation_share`, `production_output`, `output_price_elasticity`, `electricity_consumption`, `grid_emission_factor(_trajectory)`, `scope2_cbam_coverage`, `cbam_export_share`, `cbam_coverage_ratio`, `cbam_jurisdictions[]` | out: `compliance` → market; `member_of` → sector; `strategic` → `nash_cournot` |
| `technology_option` | `participant/models.py:TechnologyOption` via `build_technology_option` | `name`, `initial_emissions`, `free_allocation_ratio`, `penalty_price`, abatement params, `fixed_cost`, `max_activity_share` | out: `option` → participant `technologies` |
| `sector` | sector pool derivation in `builder.py:build_market_from_year` | `name`, `cap_trajectory`, `auction_share_trajectory`, `carbon_budget` → `scenarios[].sectors[]`; participant→sector edge sets `sector_group` | in: `members`; out: `pool` → market |

### analysis (consume a market's results / compiled config)

| block id | wraps | params |
|---|---|---|
| `batch_sweep` | `analysis/batch.py:run_batch` | `sweeps[]` {path, values[]} |
| `calibration` | `analysis/calibration.py:calibrate_slopes` | `observed_prices`, `participant_names[]`, `initial_slopes`, `max_iter` |
| `narrative` | `analysis/narrative.py:generate_narrative` | `scenario_name` |
| `investment_trigger` | `analysis/investment_trigger.py` | `sigma`, `r`, `y`, `credibility` |
| `external_feedback` | `coupling/loop.py:run_coupled_simulation` + `coupling/adapters.py` | adapter, elasticity, reference price, relaxation weight, tolerance, max iterations |

## 2. Graph schema

Frontend POSTs:

```json
{
  "version": 1,
  "nodes": [
    {"id": "steel", "block": "participant", "params": {"name": "Steel", "order": 1, "initial_emissions": 106.26}},
    {"id": "mkt",   "block": "carbon_market", "params": {"name": "P1", "years": [{"year": "2026", "total_cap": 507.0, "auction_mode": "derive_from_cap"}]}},
    {"id": "pf",    "block": "rubin_schennach_banking", "params": {"discount_rate": 0.055, "banking_initial_bank": 89.0}},
    {"id": "msr",   "block": "kmsr_decree", "params": {"msr_mode": "hybrid", "msr_initial_reserve_mt": 85.28, "announced": "2031"}}
  ],
  "edges": [
    {"source": "steel", "sourcePort": "compliance",      "target": "mkt", "targetPort": "participants"},
    {"source": "pf",    "sourcePort": "price_formation", "target": "mkt", "targetPort": "price_formation"},
    {"source": "msr",   "sourcePort": "policy",          "target": "mkt", "targetPort": "policies"}
  ],
  "meta": {"canvas": {}}
}
```

`meta.canvas` (positions, zoom) is opaque to the backend, persisted verbatim.

Compile step (`blocks/compile.py:compile_graph`) — deterministic, pure:

1. Each `carbon_market` node → one entry in `{"scenarios": [...]}`; sorted by
   `params.order` then node id.
2. The market's `price_formation` edge (cardinality exactly 1) merges its
   scenario-level keys.
3. Each attached policy/expectations block merges its keys. Blocks with
   `announced` > first year emit `policy_events[]` entries, sorted by
   (`announced`, node id).
4. Participants via `compliance` edges → `years[].participants[]`, ordered by
   `params.order` then node id; `technology_option` edges append
   `technology_options`; `member_of` sets `sector_group`; `strategic` edges
   populate `nash_strategic_participants` (sorted by name).
5. The dict passes through `config_io.builder:normalize_config` — the single
   value validator — before being returned or run.

Ambiguity resolution: edge array order carries no meaning; all ordering comes
from explicit `order` params with node-id tiebreak. Two blocks writing the
same config key on one market is a **validation error**, never
last-write-wins. Unconnected nodes are warnings; dangling edges, port-type
mismatches, cardinality violations, decree-without-banking are errors with
node/edge attribution.

## 3. Target package tree

```
src/ets/blocks/
  __init__.py      surface: BLOCK_CATALOGUE, compile_graph, validate_graph,
                   graph_from_config, Graph, Node, Edge (no underscore exports)
  registry.py      BlockSpec / ParamSpec / PortSpec dataclasses; registry
  catalogue.py     data-only block definitions of §1 (ParamSpec carries
                   config_key + scope)
  graph.py         Graph/Node/Edge dataclasses, JSON (de)serialisation
  validate.py      structural graph validation (rules R1–R32); value
                   validation delegated to config_io normalisation
  compile.py       graph → existing scenario-config dict
  decompile.py     scenario config → graph (loads examples/*.json on canvas)
```

Dependency law: `blocks/` imports **only** `config_io` (templates for
defaults, normalisation for validation) — never `web/`, never `solvers/`
(running a compiled config is the caller's job). `web/` imports `blocks/`,
`analysis/`, `solvers/`, `config_io`. Nothing imports `web/`. `config_io/`
remains the only scenario-JSON authority; `blocks/graph.py` parses graph JSON
only (a distinct document type).

## 4. Work orders

Full gate after every order:
`PYTHONPATH=src python3 -m pytest -q` (includes Appendix B anchors and, after
Order 1, golden replay). Reference: 73 passed, 4 xfailed.

- **Order 1 — NEW (gate hardening): golden-baseline replay test.**
  `tests/test_golden_baselines.py`: parametrised over `tests/baselines/*.json`
  (skip `MANIFEST.json`, `_capture.py`), re-run
  `ets.run_simulation_from_file(examples/<stem>.json)`, compare every numeric
  cell `assert_allclose(rtol=0, atol=0)`, strings exactly. If any mismatch at
  HEAD: stop, escalate to ets-lead-economist before any move.
- **Order 1b — FIX (economics, pre-compiler): F1 MSR/CCR composition.**
  `solvers/simulation.py:173` must add, not overwrite:
  `effective_carry = carry_forward_allowances + ccr_adjustment + msr_net`.
  Regression test with analytical expectation; economist sign-off on the
  equation. Behaviour change is deliberate and isolated (no example enables
  both MSR and CCR). Downgrades R10 afterwards.
- **Order 2 — NEW (chore): `pyproject.toml` single source of truth.**
  Project `ets`, src layout, deps pinned from requirements.txt,
  `[tool.pytest.ini_options] pythonpath=["src"]`, ruff/mypy config per
  CLAUDE.md. requirements.txt becomes a pointer (Vercel deploy retest before
  deleting pinned lines).
- **Order 3 — MOVE: split `web/handlers.py` — transport-free API out.**
  Move `{_predefined_templates, _decorate_frontend_config, _WarningCollector,
  _build_dashboard_payload, _slugify_filename, _save_user_scenario,
  _lookup_sector, _json_safe, _handle_calibrate, _handle_batch_run,
  _handle_narrative, _handle_csv_import, build_analysis}` → `web/api.py`
  verbatim. `handlers.py` keeps `ASSET_CONTENT_TYPES`, `ETSRequestHandler`,
  `launch_web_app`, re-imports moved names (webapp.py shim stays
  byte-compatible). Rewrite `web/server.py` imports. Gate: full pytest + WSGI
  smoke diff (capture /api/templates and /api/run responses before/after).
- **Order 4 — MOVE: single route table for both servers.**
  New `web/routes.py` with `ROUTES: dict[(method, path) → handler]` covering
  the 7 existing endpoints; `ETSRequestHandler` and `web/server.py:app` both
  dispatch through it; static serving stays server-specific. Gate: exact
  response equality on every endpoint incl. a malformed-JSON 400.
- **Order 5 — NEW: `blocks/registry.py` + `blocks/catalogue.py`.**
  Test `tests/test_blocks_catalogue.py`: every ParamSpec.config_key appears in
  the corresponding `blank_*()` normalised output — catalogue can never drift
  from the engine silently.
- **Order 6 — NEW: `blocks/graph.py`, `blocks/validate.py`,
  `blocks/compile.py`.** Validator implements R1–R32. Tests: four canonical
  drawings (basic linear, MSR-on-competitive, K-MSR P1 decree, CCR) compile
  to configs whose run output equals `run_simulation_from_file` on the
  matching example, cell-for-cell; plus rejection tests (two MSR blocks,
  decree-without-banking, zero/two price-formation edges, dangling edge).
- **Order 7 — NEW: `blocks/decompile.py:graph_from_config`.** Round-trip test:
  for all runnable examples,
  `normalize(compile(graph_from_config(cfg))) == normalize(cfg)`.
- **Order 8 — NEW: graph endpoints** in `web/api.py` + `web/routes.py`:
  `GET /api/blocks`, `POST /api/graph/validate`, `POST /api/graph/compile`,
  `POST /api/graph/run` (reuses `_build_dashboard_payload` so the response
  shape is what the frontend already renders), `GET /api/graph/from-template`.
  WSGI tests: `/api/graph/run` equals `/api/run` on the equivalent config.
- **Order 9 — MOVE (hygiene, last): deprecation-warn the flat shims**
  (`market.py, msr.py, ccr.py, hotelling.py, nash.py, simulation.py,
  scenarios.py, participant.py, expectations.py, server.py, webapp.py`, root
  `ets_framework.py`/`app.py`): module-level DeprecationWarning + removal
  milestone ("after frontend migrates to graph API"). `import ets` itself must
  stay warning-clean (`python3 -W error::DeprecationWarning -c "import ets"`).
  Recorded API leakage to retire at removal: `simulation.py` / `webapp.py`
  re-export `_underscore` names; new code must never import them.

## 5. API contract (frontend)

Existing endpoints unchanged. New:

- `GET /api/blocks` → `{"blocks": [{"id","label","category","doc",
  "params":[{"name","type","default","unit","min","max","enum","config_key","scope"}],
  "ports":{"inputs":[{"name","accepts","cardinality"}],"outputs":[{"name","type"}]},
  "constraints":[{"kind":"requires|excludes","block":"..."}]}]}` — palette and
  param forms render entirely from this; no block knowledge hardcoded
  client-side.
- `POST /api/graph/validate` `{graph}` → `200 {"ok": bool, "issues":
  [{"level":"error|warning","node":"id?","edge":i?,"message"}]}` (HTTP 200
  either way; 400 only for unparseable JSON).
- `POST /api/graph/compile` `{graph}` → `{"config": {…scenario schema…}}` —
  exportable, runnable via CLI `--config`.
- `POST /api/graph/run` `{graph}` → today's `/api/run` payload plus `"graph"`
  echo. Errors: `400 {"error": "<message>"}`.
- `GET /api/graph/from-template?id=<template_id>` → `{"graph"}` via
  `blocks/decompile.py`, same ids `/api/templates` serves.

## 6. End-state dependency diagram

```
 frontend/ (React + React Flow)          examples/*.json     tests/ (pytest, Appendix B,
      │ HTTP (graph JSON / config JSON)        │              golden baselines)
      ▼                                        │
 api/index.py ── ets.web.server (WSGI) ──┐     │
 app.py ─────── ets.cli ── ets.web.handlers    │
                                (http.server)  │
                                     │         │
                              ets.web.routes ──┴─ ets.web.api
                                     │               │
                 ┌───────────────────┼───────────────┼──────────────┐
                 ▼                   ▼               ▼              ▼
            ets.blocks         ets.analysis    ets.coupling   ets.solvers
                 │                   │            │                 │
                 └────────────┬──────┴────────────┴─────────────────┤
                              ▼                                     ▼
                        ets.config_io  ─────────────────▶  ets.market ── ets.participant
                              │                                     │
                              └───────────────▶ ets.config, ets.costs ◀────┘
 Arrows point in the import direction. Nothing imports ets.web;
 ets.blocks imports config_io only; pure math packages import no I/O.
```
