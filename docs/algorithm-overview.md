# Algorithm Overview

The simulator is organised as **three nested layers**. Each layer has a single, well-defined responsibility. Understanding how they compose is the key to understanding the whole system.

---

## The three layers at a glance

```
┌────────────────────────────────────────────────────────────────────┐
│  Layer 3 — Multi-Year Path  (simulation.py, expectations.py)       │
│                                                                    │
│  For each year t = 2030, 2035, 2040 …                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Layer 2 — Market Equilibrium  (market.py)                   │  │
│  │                                                              │  │
│  │  Find P* such that  Σ demand_i(P*) = auction supply Q        │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Layer 1 — Participant Optimisation  (participant.py)  │  │  │
│  │  │                                                        │  │  │
│  │  │  min_a  Cost(a, P)  for each participant i             │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

The layers call each other in sequence:

- **Layer 3** iterates over years and manages state (bank balances, carry-forward allowances) between them.
- **Layer 2** is called once per year. It needs to evaluate total market demand many times at different trial prices; it does this by calling Layer 1.
- **Layer 1** is called once per participant per trial price evaluation. It solves a bounded scalar optimisation to find the cost-minimising abatement level.

---

## Full execution flow

```
run_simulation(config)
│
├─ build_markets_from_config(config)           # scenarios.py
│   └─ For each scenario × year:
│       ├─ Normalise & validate JSON config
│       └─ Build CarbonMarket + MarketParticipant objects
│
└─ For each scenario (grouped markets):
    │
    ├─ Sort years chronologically
    │
    ├─ Compute baseline_prices                 # independent equilibrium, no banking
    │   └─ market.find_equilibrium_price()  ×  n_years
    │
    ├─ Build expectation_specs                 # one rule per year
    │
    ├─ Derive initial expected_prices
    │   (from baseline or manual values)
    │
    ├─ [IF perfect_foresight rule present]
    │   Fixed-point iteration  (≤ 25 rounds):
    │   ├─ Simulate full path  →  realised_prices
    │   ├─ Update expected_prices to realised_prices
    │   └─ Stop when  max|Δprice| ≤ 1e-3
    │
    └─ Final path simulation:
        For each year t (chronological):
        ├─ market.solve_equilibrium(bank_t, P_future_t, carry_t)
        │   └─ _solve_for_supply(Q, P_low, P_high, …)
        │       └─ scipy.root_scalar("brentq")
        │           └─ market.total_net_demand(P)
        │               └─ participant.optimize_compliance(P)  × n_participants
        │                   ├─ _optimize_for_technology(tech, P)
        │                   │   └─ scipy.minimize_scalar  (if callable MAC)
        │                   └─ [if mixed] _optimize_mixed_technology_portfolio
        │                       └─ scipy.minimize (SLSQP)
        ├─ market.participant_results(P*)
        ├─ carry_{t+1} = unsold  if carry_forward policy
        └─ bank_{t+1}  = { ending_bank_balance per participant }
```

---

## Layer 1 — Participant optimisation

**File:** `src/ets/participant.py`  
**Detailed doc:** [mac-abatement.md](mac-abatement.md), [technology-transition.md](technology-transition.md)

Each participant minimises their total compliance cost over a scalar variable — the amount of abatement taken:

```
min_{a}  fixed_cost  +  abatement_cost(a)  +  allowance_cost(a, P)  +  penalty(a, P)
       -  sales_revenue(a, P)  -  P_future × banking_balance(a, P)
```

The optimisation is bounded: `0 ≤ a ≤ max_abatement`.

Key outputs per participant:
- `abatement` — tonnes reduced
- `residual_emissions` — remaining obligations
- `net_allowances_traded` — positive = buyer, negative = seller
- `ending_bank_balance` — allowances carried to next year

---

## Layer 2 — Market equilibrium

**File:** `src/ets/market.py`  
**Detailed doc:** [market-equilibrium.md](market-equilibrium.md)

The equilibrium condition is:

```
D(P*) = Q       where  D(P) = Σ_i net_allowances_traded_i(P)
```

`D(P)` is a monotonically non-increasing function of price (higher price → more abatement → less demand). The solver brackets a root using the penalty price as an upper bound, then applies **Brent's method** for guaranteed, fast convergence.

Auction-specific rules (reserve price, minimum bid coverage, unsold treatment) are evaluated before the root-finding step.

---

## Layer 3 — Multi-year simulation

**File:** `src/ets/simulation.py`, `src/ets/expectations.py`  
**Detailed doc:** [multi-year-simulation.md](multi-year-simulation.md)

State carried between years:
- **Bank balances** per participant (allowances saved from previous years)
- **Carry-forward allowances** (unsold auction volume, when `unsold_treatment = "carry_forward"`)

Four expectation-formation rules govern how participants predict future carbon prices, which affects their banking and borrowing decisions today. Under `perfect_foresight`, the simulation loops until expected and realised prices converge — implementing a **rational expectations equilibrium**.

---

## Computational complexity

| Step | Operations per call | Typical count |
|---|---|---|
| `minimize_scalar` (per participant, per price evaluation) | ~50–100 function evaluations | n_participants × n_brent_evals |
| Brent's method convergence | ~10–20 price evaluations | 1 per year |
| Perfect foresight iterations | 1 full path per iteration | ≤ 25 |
| Total function evaluations | ~50 × n_participants × 15 × 25 | ~18,750 for 1 scenario, 5 participants, 5 years |

In practice, simulations complete in under 1 second for typical configurations.

---

## Monotonicity guarantee

Brent's method requires that `D(P) - Q` changes sign over the bracketed interval. This is guaranteed because:

1. At `P = 0`: participants do not abate, residual emissions are high, demand exceeds any finite supply → `D(0) - Q > 0`
2. At `P = penalty_price`: it becomes cheaper to pay the fine than to buy allowances, so demand collapses to zero → `D(penalty_price) - Q < 0`

If the upper bound is somehow still not enough (unusual edge cases with very high penalty prices), the solver expands the upper bound by doubling up to 10 times before raising an error.

---

## Related documents

- [MAC & Abatement Models](mac-abatement.md)
- [Technology Transition](technology-transition.md)
- [Market Equilibrium Solver](market-equilibrium.md)
- [Multi-Year Simulation](multi-year-simulation.md)
- [Data Model & Config Schema](data-model.md)
