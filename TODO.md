# ETS Model TODO

Items are grouped by theme. Checked items are complete. Unchecked items are pending.

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
- [ ] Allow participant-specific production or output assumptions (needed for output-based allocation)

---

## Policy mechanisms

- [x] Price floor, price ceiling, reserve price, minimum bid coverage, unsold treatment
- [ ] Benchmark-based free allocation (move beyond simple `free_allocation_ratio`)
- [ ] Output-based allocation (requires production/output decision above)
- [ ] Auction design variants: full auction, reserve price bands, limited release schedules
- [ ] Free-allocation phase-out trajectory: auto linear/step-down of `free_allocation_ratio` across years (currently must be set manually per year)

---

## Multi-year dynamics

- [ ] Expected future price logic — replace the `next_year_baseline` heuristic with a proper dynamic expectations module
- [ ] Policy trajectory constraints across years: auto-declining caps, changing free allocation rules, tightening penalties
- [ ] BAU trajectory: per-sector automatic Business-as-Usual emissions path generation (currently requires manual entry per year)

---

## Calibration and data

- [ ] Model calibration: fit MACC parameters to reproduce historically observed carbon prices
- [ ] Import workflow for participant/year data from CSV or structured tables
- [ ] Validation rules for inconsistent scenarios (cap < free allocation, unrealistic cost combinations, etc.)

---

## Analysis and sensitivity

- [ ] Batch/sensitivity runner: run N parameter combinations automatically, output distributions of prices and outcomes
- [ ] Sector-level auction revenue breakdown (currently aggregated; needs per-participant/per-sector split)
- [ ] Indirect emissions (Scope 2): electricity-price linkage module for covered indirect emissions

---

## UX and outputs

- [x] Side-by-side scenario comparison charts
- [x] Visual MAC block editor
- [x] Technology transition wizard with archetypes
- [ ] Spreadsheet conveniences: duplicate row, paste from clipboard, CSV import/export per table, inline validation highlighting
- [ ] Automatic narrative summaries for policy interpretation
- [ ] Indirect emissions (Scope 2) display in participant outputs

---

## Remaining work — summary table

| Item | Status | What's needed |
|---|---|---|
| Batch/Sensitivity runner | Missing | Run N parameter combinations automatically, output price and outcome distributions |
| BAU trajectory | Manual only | Per-sector automatic BAU emissions path generation |
| Free-allocation phase-out | Manual only | Auto linear/step-down trajectory for `free_allocation_ratio` across years |
| Model calibration | Missing | Fit MACC parameters to reproduce historically observed prices |
| Sector-level auction revenue | Aggregate only | Break auction revenue down by participant/sector |
| Indirect emissions (Scope 2) | Missing | Electricity price linkage module for covered indirect emissions |
| Benchmark-based free allocation | Missing | Replace ratio-based allocation with benchmark/output-based rules |
| Output-based allocation | Blocked | Requires production/output decision module |
| CSV import | Missing | Import participant and year data from structured tables |
