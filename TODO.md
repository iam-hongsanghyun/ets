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
- [ ] Hotelling risk premium (`risk_premium` param ρ): price path `P(t) = λ·(1+r+ρ)^t` — policy uncertainty premium on top of discount rate; needed to calibrate theoretical path against observed market prices
- [ ] Allow participant-specific production or output assumptions (needed for output-based allocation)

---

## Policy mechanisms

- [x] Price floor, price ceiling, reserve price, minimum bid coverage, unsold treatment
- [ ] Benchmark-based free allocation (move beyond simple `free_allocation_ratio`)
- [ ] Output-based allocation (requires production/output decision above)
- [ ] Auction design variants: full auction, reserve price bands, limited release schedules
- [ ] Free-allocation phase-out auto-calculator: given `(sector_type, scenario, start_year, end_year)` compute `free_allocation_ratio` per year per participant — currently requires manual entry per year
- [ ] Multi-jurisdiction CBAM: replace single `cbam_export_share` with a `cbam_jurisdictions` array `[(jurisdiction, export_share, coverage_ratio, reference_price)]`; output per-jurisdiction liability columns (EU, UK, US, Japan GX-ETS)
- [ ] Sector grouping: `sector_group` label on participants so output tables can aggregate Steel sub-sectors (general / special / electric arc) and Petrochemical sub-sectors (NCC / BTX / polymers) into sector-level rows

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
- [ ] EUA ensemble / fan chart: run same K-ETS scenario with multiple external EUA trajectories (EC / Enerdata / BNEF), return price uncertainty bands as a native output format (not just duplicated scenarios)
- [ ] Sector-level auction revenue breakdown (currently aggregated; needs per-participant/per-sector split)
- [ ] Indirect emissions (Scope 2): `electricity_consumption` + `grid_emission_factor` per participant; post-equilibrium indirect CBAM exposure block analogous to direct CBAM

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

| Item | Requires code? | Status | What's needed |
|---|---|---|---|
| Hotelling risk premium `ρ` | ✅ Yes | Missing | Add `risk_premium` param to Hotelling solver; `P(t) = λ·(1+r+ρ)^t` |
| Sector-level auction revenue | ✅ Yes | Aggregate only | Attribute auction proceeds per participant in summary output |
| Free-allocation phase-out calculator | ✅ Yes | Manual only | Auto-compute `free_allocation_ratio` trajectory from scenario type + timeline |
| Multi-jurisdiction CBAM | ✅ Yes | Missing | `cbam_jurisdictions` array; per-jurisdiction liability columns |
| Sector grouping / sub-sector aggregation | ✅ Yes | Missing | `sector_group` label; grouped summary rows in output |
| EUA ensemble / fan chart | ✅ Yes | Missing | Multiple EUA inputs → price uncertainty bands as native output |
| Indirect emissions (Scope 2) | ✅ Yes | Missing | `electricity_consumption` + `grid_emission_factor`; indirect CBAM block |
| Batch/Sensitivity runner | ✅ Yes | Missing | Run N parameter combinations automatically, output distributions |
| BAU trajectory | Data only | Manual only | Per-sector BAU emissions path (11th Power Plan / NDC) |
| Model calibration | Data only | Missing | Fit MACC params to observed KAU prices |
| Benchmark-based free allocation | ✅ Yes | Missing | Replace ratio-based with product benchmark/output-based rules |
| Output-based allocation | ✅ Yes | Blocked | Requires production/output decision module |
| CSV import | ✅ Yes | Missing | Import participant and year data from structured tables |
