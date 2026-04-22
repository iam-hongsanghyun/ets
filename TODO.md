# ETS Model TODO

This roadmap is ordered by modeling value and implementation dependency. The early items improve the economic validity of the simulator; later items extend realism, usability, and diagnostics.

## Phase 1: Core Economic Upgrade

- [x] Replace the reduced-form abatement rule with explicit firm-level compliance optimization.
  - Goal: each participant minimizes compliance cost by choosing among abatement, allowance purchases, and penalty payment.
  - Why first: this is the biggest conceptual improvement in the current model.
  - Deliverables:
    - participant optimization method
    - revised allowance demand logic
    - updated equilibrium solver using optimized firm responses
    - tests for boundary cases

- [x] Separate compliance decisions into three explicit channels.
  - Channels:
    - abate emissions
    - buy allowances
    - pay penalty for uncovered emissions
  - Goal: make the cost comparison transparent and inspectable in outputs.

- [x] Add richer participant result outputs.
  - Show, per participant:
    - abatement cost
    - allowance purchase cost
    - penalty cost
    - total compliance cost
  - Goal: make model outputs economically interpretable.

## Phase 2: Better Abatement Representation

- [x] Replace `cost_slope`-only linear response with explicit marginal abatement cost curves.
  - Options:
    - piecewise linear blocks
    - nonlinear curves
    - technology-step curves
  - Goal: better represent industrial decarbonization and threshold behavior.

- [x] Support technology-switch decisions.
  - Examples:
    - blast furnace vs hydrogen DRI
    - coal vs cleaner generation pathways
  - Goal: model structural transition, not just incremental abatement.

- [ ] Allow participant-specific production or output assumptions.
  - Goal: prepare for output-based free allocation and intensity-style benchmarking.

## Phase 3: Multi-Year Strategic Design

- [x] Add banking and borrowing of allowances across years.
  - Goal: let firms shift compliance across time.
  - Impact: makes annual price paths economically meaningful.

- [ ] Add expected future price logic.
  - Goal: allow current decisions to depend on future scarcity.

- [ ] Add policy trajectory constraints across years.
  - Examples:
    - declining caps
    - changing free allocation
    - tightening penalty rules

## Phase 4: Policy Mechanism Realism

- [ ] Add price floor, price ceiling, and reserve mechanisms.
  - Goal: reflect real ETS design options.

- [ ] Add benchmark-based free allocation.
  - Goal: move beyond simple free-allocation ratios.

- [ ] Add auction design variants.
  - Examples:
    - full auction
    - reserve price
    - limited release schedules

## Phase 5: Sector Calibration and Data

- [ ] Create a calibration layer for participant parameters.
  - Goal: fit model inputs to real data instead of purely illustrative assumptions.

- [ ] Add import workflow for participant/year data from CSV or Excel-like tables.
  - Goal: make empirical setup practical.

- [ ] Add validation rules for inconsistent scenarios.
  - Examples:
    - cap inconsistent with allocation
    - negative implied auction supply
    - unrealistic penalty/cost combinations

## Phase 6: Analysis and UX

- [ ] Add side-by-side scenario comparison charts.
  - Show:
    - annual equilibrium price
    - abatement
    - auction revenue
    - compliance burden

- [ ] Add spreadsheet conveniences to the GUI.
  - Features:
    - duplicate row
    - paste rows from Excel
    - CSV import/export per table
    - inline validation highlighting

- [ ] Add automatic narrative summaries for policy interpretation.
  - Goal: produce decision-oriented summaries from model outputs.

## Recommended Order

1. Firm-level compliance optimization
2. Explicit cost decomposition in outputs
3. Better abatement/MAC curves
4. Technology switching
5. Banking/borrowing across years
6. Policy mechanism realism
7. Calibration and import workflows
8. Advanced comparison UX

## Immediate Next Step

- [ ] Add expected future price logic.
  - Proposed approach:
    - replace the current next-year baseline-price heuristic
    - allow configurable expectation rules
    - support perfect foresight or user-defined expected prices
    - expose the expectation assumption in scenario outputs
