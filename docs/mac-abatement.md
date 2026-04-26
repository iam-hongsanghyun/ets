# Marginal Abatement Cost (MAC) Models

**Files:** `src/ets/costs.py`, `src/ets/participant.py`

A MAC curve defines how expensive it is for a participant to reduce their emissions. It is the core economic input that determines each participant's behaviour at any given carbon price.

---

## What is a MAC curve?

The **Marginal Abatement Cost** at abatement level `a` is the cost of reducing one additional tonne of CO₂ at that point. A rational participant abates up to the point where:

```
MAC(a*) = carbon price P
```

Below this point, abating is cheaper than buying an allowance. Above it, buying is cheaper.

```
$/t
 ↑
 │                         ╱ MAC curve
 │                        ╱
P*├───────────────────────X─────────────────
 │                       ╱│
 │                      ╱ │
 │                     ╱  │
 └─────────────────────────────────────────→ abatement (Mt)
                        a*
           ◄────────────►
             abate this     buy allowances
             (cheaper)      (cheaper)
```

---

## Three MAC models

The simulator supports three abatement models, each suited to different sectors and modelling approaches.

---

### Model 1: Linear

**Config:** `abatement_type: "linear"`, `cost_slope`, `max_abatement`

**Factory:** `linear_abatement_factory(max_abatement, cost_slope)` in `costs.py`

The marginal cost rises linearly with abatement:

```
MAC(a) = cost_slope × a
```

**Total abatement cost** (area under MAC curve):

```
C(a) = ∫₀ᵃ slope·x dx = ½ × slope × a²
```

**Optimal abatement** at price P:

```
a* = min(max_abatement,  P / cost_slope)
```

**Code (cost calculation in participant.py):**

```python
if cost_model == "linear":
    cost_slope = technology.marginal_abatement_cost.cost_slope
    return 0.5 * cost_slope * abatement**2 / activity_share
```

The `/ activity_share` term scales the cost when a participant is only partially active (mixed technology portfolios).

**Visual:**

```
$/t
 ↑            ╱
 │           ╱  slope = rise/run
 │          ╱
P*├─────────X
 │         ╱│
 │        ╱ │
 └────────────→ abatement
          a*  max_abatement
```

**When to use:** Simple sectors, early-stage modelling, when only rough abatement potential is known.

**Example:** A generic industrial facility with `max_abatement = 20 Mt`, `cost_slope = 5`:
- At P = $50: abates `50/5 = 10 Mt`
- At P = $100: abates `100/5 = 20 Mt` (hits ceiling)
- At P = $200: still abates `20 Mt` (ceiling binds)

---

### Model 2: Piecewise (MAC blocks)

**Config:** `abatement_type: "piecewise"`, `mac_blocks: [{amount, marginal_cost}, …]`

**Factory:** `piecewise_abatement_factory(mac_blocks)` in `costs.py`

The most realistic model. Emission reductions are grouped into discrete "blocks", each with a fixed marginal cost. Blocks must be ordered by **non-decreasing** marginal cost (cheapest first).

```
mac_blocks = [
    {"amount": 6,  "marginal_cost": 20},
    {"amount": 8,  "marginal_cost": 55},
    {"amount": 8,  "marginal_cost": 110},
]
```

**Abatement decision:**

```python
def abatement_rule(carbon_price):
    abatement = 0.0
    for block in blocks:
        if carbon_price >= block["marginal_cost"]:
            abatement += block["amount"]   # take the whole block
        else:
            break                          # too expensive, stop
    return abatement
```

Each block is **fully taken or fully skipped** — there is no partial block in the piecewise rule (the cost function is piecewise constant, creating discrete jumps in abatement).

**Total abatement cost** for amount `a`:

```python
remaining = a
total_cost = 0.0
for block in blocks:
    used = min(remaining, block["amount"] * activity_share)
    total_cost += used * block["marginal_cost"]
    remaining -= used
    if remaining <= 0: break
```

**Visual (steel blast furnace example):**

```
$/t
 ↑
 110 ├──────────────────┤  Block 3: 8 Mt @ $110
     │                  │
  55 ├──────────┤       │  Block 2: 8 Mt @ $55
     │          │       │
  20 ├──┤       │       │  Block 1: 6 Mt @ $20
     │  │       │       │
   0 └──┴───────┴───────┴──→ cumulative abatement (Mt)
        6      14      22
```

At carbon price P:
- P < $20 → 0 Mt abated
- $20 ≤ P < $55 → 6 Mt abated (cost = 6 × 20 = $120M)
- $55 ≤ P < $110 → 14 Mt abated (cost = 6×20 + 8×55 = $560M)
- P ≥ $110 → 22 Mt abated (cost = 6×20 + 8×55 + 8×110 = $1,440M)

**Solver handling:** Because the abatement function is piecewise constant (not smooth), `minimize_scalar` is used on the total compliance cost — which is smooth even though MAC is not, because the cost is the integral of MAC.

**When to use:** Most realistic for industrial sectors. Use when you have sector-specific abatement options (fuel switching, efficiency retrofits, CCS) with known cost and potential.

**Real-world basis:** Each block typically represents a specific technology or measure:
- Block 1 ($20): Energy efficiency improvements (low-hanging fruit)
- Block 2 ($55): Fuel switching, process optimisation
- Block 3 ($110): CCS, deep structural change

---

### Model 3: Threshold

**Config:** `abatement_type: "threshold"`, `threshold_cost`, `max_abatement`

The simplest on/off model. The participant does nothing until the carbon price reaches a threshold, then immediately abates the maximum possible amount.

```
a*(P) = {  0              if P < threshold_cost
          {  max_abatement  if P ≥ threshold_cost
```

**Total cost:** `threshold_cost × abatement`

**Code (scenarios.py — stored as a plain float, not a callable):**

```python
marginal_abatement_cost = participant["threshold_cost"]   # float, not a function

# In participant.py:
threshold_cost = float(technology.marginal_abatement_cost)   # it's just a number
return threshold_cost * abatement
```

When `marginal_abatement_cost` is a float (not callable), the participant only considers `a = 0` or `a = max_abatement` — there is no middle ground.

**Visual:**

```
$/t
 ↑
 │  threshold_cost ─────────────────────────────
 │                 ↑
 │                 │ at this price, instantly switch
 │                 │ from 0 to max_abatement
 └──────────────────────────────────────────────→ abatement
                   0      max_abatement
```

**When to use:** Models breakthrough technologies that only become viable above a specific price point (e.g. green hydrogen, direct air capture). Below the threshold, the technology is uneconomic; above it, it fully deploys.

---

## How the solver chooses abatement level

In `participant.py`, `_optimize_for_technology()` handles both callable and threshold MACs:

```python
if callable(technology.marginal_abatement_cost):
    # Linear or Piecewise: smooth cost function, use scalar minimiser
    result = minimize_scalar(
        lambda a: self._total_compliance_cost(technology, a, P, ...),
        bounds=(0.0, technology.max_abatement),
        method="bounded",
    )
    abatement = result.x

else:
    # Threshold: only two candidates — 0 or max
    abatement = min(
        [0.0, technology.max_abatement],
        key=lambda a: self._total_compliance_cost(technology, a, P, ...)
    )
```

`minimize_scalar` with `method="bounded"` uses Brent's method on the scalar cost function — it is guaranteed to converge for unimodal functions on a bounded interval. The total compliance cost is always unimodal in abatement because:
1. Abatement cost is convex (linear or piecewise increasing in `a`)
2. Allowance cost is linearly decreasing in `a` (more abatement = fewer allowances to buy)
3. Their sum has a single minimum

---

## The full compliance cost objective

```python
def _total_compliance_cost(technology, abatement, carbon_price,
                            starting_bank_balance, expected_future_price,
                            banking_allowed, borrowing_allowed, borrowing_limit):

    residual_emissions = technology.initial_emissions - abatement
    free_allocation    = technology.free_allocation          # = emissions × ratio

    inventory = _finalize_inventory(
        residual_emissions, free_allocation, carbon_price,
        penalty_price, starting_bank_balance, expected_future_price,
        banking_allowed, borrowing_allowed, borrowing_limit
    )

    return (
        technology.fixed_cost
        + abatement_cost(technology, abatement)
        + inventory["allowance_cost"]        # P × allowances purchased
        + inventory["penalty_cost"]          # penalty_price × uncovered tonnes
        - inventory["sales_revenue"]         # P × surplus allowances sold
        - expected_future_price × inventory["ending_bank_balance"]  # banking value
    )
```

The last term prices the option to bank: if a participant ends up with surplus allowances and banking is allowed, those allowances are worth `expected_future_price` each — so the current cost is reduced by that amount.

---

## MAC in the chart (frontend)

The Analysis tab renders participant MAC curves using the block data directly from `SERIES_FIELD_META` in `AppShared.jsx`. The SVG chart draws:
1. Horizontal bars for each block (width = amount, height = marginal cost)
2. A vertical line at the equilibrium price
3. Shading: blocks to the left of the price line are taken; blocks to the right are not

---

## See also

- [Technology Transition](technology-transition.md) — MAC curves per technology option, mixed portfolios
- [Algorithm Overview](algorithm-overview.md) — how the MAC feeds into the market equilibrium solver
