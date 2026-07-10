# ETS Model TODO

Items are grouped by theme. Checked items are complete. Unchecked items are pending.

---

## Infrastructure

- [x] Backend modular sub-package restructuring: split `src/ets/` into `participant/`, `market/`, `config_io/`, `solvers/`, `web/` sub-packages; backward-compat shims kept at old flat paths
- [x] Solver settings UX: each solver's convergence settings shown inline within its approach panel; removed separate accordion
- [x] Nash participant list grouped by `sector_group` with per-sector Select all / Deselect all toggle
- [x] Sector-participants level: optional `sectors[]` in scenario config; each sector has `cap_trajectory`, `auction_share_trajectory`, `carbon_budget`; participants get `sector_allocation_share`; `total_cap` and `auction_offered` derived from sector sums; backward-compatible with per-participant mode
- [x] Import workflow: CSV → ETS config JSON conversion (`/api/import-csv`); `src/ets/analysis/csv_import.py`

---

## Core economic modelling

- [x] Replace reduced-form abatement with firm-level compliance optimisation
- [x] Separate compliance into three channels: abate, buy allowances, pay penalty
- [x] Add richer per-participant result outputs (abatement cost, allowance cost, penalty cost, total)
- [x] Replace `cost_slope`-only linear MAC with explicit piecewise MAC blocks
- [x] Support discrete technology-switch decisions (blast furnace → hydrogen DRI, etc.)
- [x] Add banking and borrowing of allowances across years
- [x] Add configurable expectation-formation rules (myopic, next_year_baseline, perfect_foresight, manual)
- [x] Add Hotelling Rule solver (shadow price bisection over carbon budget)
- [x] Add Nash-Cournot strategic equilibrium (best-response iteration)
- [x] Add Market Stability Reserve (MSR) — withhold/release based on aggregate bank
- [x] Add CBAM liability calculation (post-equilibrium, export-share weighted)
- [x] Hotelling risk premium (`risk_premium` param ρ): price path `P(t) = λ·(1+r+ρ)^t`
- [x] Output-based allocation (OBA): `production_output × benchmark_emission_intensity` overrides ratio-based free allocation; frontend inputs + builder support; example `k_ets_oba_benchmark.json`
- [x] Participant-specific BAU emissions trajectory: `initial_emissions_trajectory` per participant with linear interpolation; example `k_ets_bau_trajectory.json`

---

## Policy mechanisms

- [x] Price floor, price ceiling, reserve price, minimum bid coverage, unsold treatment
- [x] Free-allocation phase-out auto-calculator: scenario-level `free_allocation_trajectories`; linearly interpolates `free_allocation_ratio` per participant per year
- [x] Policy trajectory constraints: `cap_trajectory`, `price_floor_trajectory`, `price_ceiling_trajectory` — linearly interpolated scenario-level overrides
- [x] Multi-jurisdiction CBAM: `cbam_jurisdictions` array on participant; `eua_prices` dict per year; per-jurisdiction liability columns
- [x] Sector grouping: `sector_group` on participants; sector-level aggregated rows in scenario summary
- [x] Sector-level auction revenue attribution: proportional by allowance buys (`{sg} Auction Revenue Share`)
- [x] Benchmark-based free allocation: OBA path (`production_output × benchmark_emission_intensity`) implemented in builder; example `k_ets_oba_benchmark.json`
- [x] Additional trade policy jurisdictions as built-in sensitivity: UK CBAM (2026), US CBAM (draft), Japan GX-ETS — example `k_ets_multi_jurisdiction_cbam.json`; jurisdiction-specific params via `cbam_jurisdictions`
- [x] KAU–EUA price convergence scenario helper: `convergence_scenario_template()` in templates.py; `price_floor_trajectory` ramps KAU → EUA; example `k_ets_kau_eua_convergence.json`
- [x] Auction revenue reinvestment tracker: `Domestic Retained Revenue`, `CBAM Foregone Revenue`, `Potential Revenue if KAU=EUA` columns in `scenario_summary()`

---

## Multi-year dynamics

- [x] Policy trajectory constraints across years: `cap_trajectory`, `price_floor_trajectory`, `price_ceiling_trajectory`
- [x] BAU trajectory auto-generation: `initial_emissions_trajectory` per participant (year-keyed dict, linearly interpolated); builder applies per-year override; example `k_ets_bau_trajectory.json`
- [x] Grid emission factor trajectory: `grid_emission_factor_trajectory` per participant; same interpolation pattern as `cap_trajectory`; affects Scope 2 emissions and CBAM exposure year by year
- [ ] Expected future price logic — replace the `next_year_baseline` heuristic with a proper dynamic expectations module (e.g. adaptive/learning expectations)

---

## Calibration and data

- [x] Model calibration tool: `calibrate_slopes()` in `src/ets/analysis/calibration.py`; scipy Nelder-Mead fits `abatement_cost_slope` per participant to minimise MSE vs observed KAU prices; `/api/calibrate` endpoint; example `k_ets_calibration_request.json`
- [x] Import workflow: `csv_to_config()` in `src/ets/analysis/csv_import.py`; CSV rows → participant/year config; `/api/import-csv` endpoint
- [x] Facility-level cost distribution analysis: per-sector P10/P50/P90 compliance cost percentiles + `Cost Std Dev` in `scenario_summary()` when ≥2 participants per sector
- [x] Validation rules: duplicate participant names, penalty < floor, cap < supply (post-trajectory)

---

## Analysis and sensitivity

- [x] Batch/sensitivity runner: `run_batch()` in `src/ets/analysis/batch.py`; JSON-path parameter sweeps, cartesian product execution; `/api/batch-run` endpoint; example `k_ets_batch_eua_sweep.json`
- [x] EUA ensemble / fan chart: `eua_price_ensemble` dict per year (EC / Enerdata / BNEF); per-source CBAM liability columns in participant results
- [x] Indirect emissions (Scope 2): `electricity_consumption` + `grid_emission_factor` + `scope2_cbam_coverage`; `Indirect Emissions` and `Scope 2 CBAM Liability` in results
- [x] Sub-sector decomposition: example `k_ets_subsector_decomposition.json` — steel split into Integrated/EAF/Special with separate MACCs; petrochemical into NCC/BTX/Polymer

---

## UX and outputs

- [x] Side-by-side scenario comparison charts
- [x] Visual MAC block editor
- [x] Technology transition wizard with archetypes
- [x] Scope 2 / indirect emissions display in participant results panel (`ParticipantPanel.jsx` wired to show `Indirect Emissions` and `Scope 2 CBAM Liability`)
- [x] Automatic narrative summaries: `generate_narrative()` in `src/ets/analysis/narrative.py`; rule-based plain-language summary of price path, compliance cost, CBAM exposure; `/api/narrative` endpoint
- [ ] Spreadsheet conveniences: duplicate row, paste from clipboard, CSV import/export per table, inline validation highlighting

---

## Engine defects found during modularization (math changes — need economist sign-off + new baselines)

- [ ] **Nash–Cournot equilibrium is degenerate**: `solvers/nash.py:_solve_nash_year` runs the best-response iteration but returns `market.solve_equilibrium(...)` (plain competitive clearing) — converged strategic abatements never feed the reported equilibrium, so Nash prices are bit-identical to competitive (verified empirically, dP/dQ = 0.526, two strategic gencos). Fix is a math change: report the strategic equilibrium; then add a Nash golden example (deliberately not added while degenerate). Related: F2 wiring inconsistencies (ungated MSR, no CCR in nash path).
- [ ] `climate_solutions_msr_stability` never fires its MSR (bank never crosses the threshold; withheld = 0 in every golden year) — either retune the example so the mechanism demonstrably fires or rename its intent; `k_ets_msr_ccr_combined` now provides firing coverage.

## Modularization / block-composer follow-ups (non-blocking, from economist review 2026-07-10)

- [ ] Validator gaps (W2): R6 misses an all-myopic per-year `expectation_rule` dict; R30 splice warning only fires when the MSR block itself is late-announced (a late-announced *other* policy crossing a bank_threshold MSR also resets the pool); add dedicated rejection tests for R6/R7/R8/R11/R13/R15/R19 (family-level coverage only today)
- [ ] Catalogue default-value drift guard (W3): `tests/test_blocks_catalogue.py` asserts config-key existence but not default values; add a value-level test importing both catalogue and engine defaults (`MSR_DEFAULTS`, `CCR_DEFAULTS`, `banking.py` decree literals). Also reconcile the dead `discount_rate 0.055` fallback in `solvers/simulation.py:344` vs 0.04 everywhere else
- [ ] `announced` param currently compiles to nothing (W4): synthesize `policy_events[]` from late-announced policy blocks per plan §1 "Policy timing"; until then, validator should WARN when `announced` ≠ first market year
- [ ] CBAM canvas presentation (W5): rendered as a policy input to the market; should be styled/categorised as a diagnostics block downstream of price formation (economically inert as compiled, but the drawing implies otherwise)
- [ ] R26 downgrade: emit WARNING instead of ERROR when `oba`/`sector` nodes are present (free-allocation check ignores OBA > sector > per-year ratio precedence; engine re-validates at run anyway)
- [ ] Retire flat shims at v2.0 milestone (after frontend migrates fully to the graph API): delete `src/ets/{market,participant}.py` (already dead — shadowed by same-named packages), remove remaining shims + the `_underscore` re-export leakage in `simulation.py`/`webapp.py`
- [ ] Web server asymmetry: unknown `POST /api/x` returns 404 (http.server) vs 405 (WSGI); unify
- [ ] Vercel deploy retest with `pyproject.toml` present, then slim `requirements.txt` to a pointer

## Summary table — remaining items

| Item | Effort | Criticality | What's needed |
|---|---|---|---|
| Expected price dynamic module | Medium | Low — theoretical improvement | Adaptive/learning expectations as alternative to `next_year_baseline` |
| Spreadsheet conveniences | Medium | Low — UX polish | CSV import/export, duplicate row, clipboard paste |
