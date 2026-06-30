# Feedback Option B — Soft-Link Coupling

**Files:** `src/ets/coupling/loop.py`, `src/ets/coupling/adapters.py`
**API:** `from ets.coupling import run_coupled_simulation, ExternalModel, ElasticityExternalModel, NullExternalModel`
**Demo:** [`examples/feedback_b_coupling_demo.py`](../examples/feedback_b_coupling_demo.py)

## What it adds

Option A adds an *own-price* activity response inside the allowance market. Option
B goes further: it couples the ETS engine to a **separate, purpose-built model**
(energy-system, CGE, DSGE, …) and iterates the two to a joint equilibrium. This
is how you get general-equilibrium feedback — cross-sector reallocation, energy
prices, income effects, welfare — **without** embedding a CGE/DSGE in this
codebase. The ETS engine stays the specialist allowance-market component; the
economics lives behind a thin adapter.

## The fixed-point loop

$$
p_{k+1} \;=\; \mathrm{ETS}\!\left(\,\text{model.respond}(\text{config}_0,\; p_k)\,\right)
$$

solving the fixed point `p* = ETS(respond(config_0, p*))`:

1. Run the ETS → carbon-price path `p_k` (one price per scenario-year).
2. Hand `p_k` to the external model; it returns revised activity (updated
   per-participant `initial_emissions`).
3. Re-run the ETS on the revised config → new prices.
4. Repeat until the price path stops moving (`max |Δprice| ≤ tolerance`).

This is the **outer-loop sibling of Option A**: A solves the activity↔price
interaction *within* each period's market clearing; B solves it *between* full
ETS runs, with the activity response supplied by a pluggable model. With matching
parameters the two converge to a similar fixed point (the demo lands at ≈78→100
vs Option A's ≈74→88 — close, the small gap being constant-elasticity vs the
linearised form).

### Under-relaxation

A naive Gauss–Seidel step (`relaxation=1.0`) can oscillate: a high price collapses
activity, which crashes the price, which over-expands activity, … The loop
**under-relaxes** the price signal fed back to the model,

```
signal ← (1 − w)·signal + w·realised_price        # w = relaxation ∈ (0, 1]
```

which damps the oscillation without changing the fixed point. Default `w = 0.5`
converges the demo in ~4 iterations. Lower `w` for a stubbornly oscillating
coupling; `w = 1.0` recovers the undamped step.

## The adapter contract

```python
from typing import Protocol

class ExternalModel(Protocol):
    def respond(self, baseline_config: dict, prices: dict[tuple[str, str], float],
                iteration: int) -> dict:
        """Map the latest carbon-price path to a revised scenario config."""
```

- `baseline_config` is the **original** (iteration-0) config — always derive from
  it so the mapping is *price → activity*, not a compounding tweak.
- `prices` is keyed by `(scenario_name, year_label)`.
- Return a config of identical shape with revised activity.

### Bundled adapters

| adapter | purpose |
|---------|---------|
| `NullExternalModel` | identity — no feedback; converges in one iteration. A control that must reproduce a plain `run_simulation_from_config`. |
| `ElasticityExternalModel(elasticity, reference_price, …)` | reference stand-in: `E ← E0·(max(P, floor)/P_ref)^(−ε)`, clamped for safety. Runs with no extra dependencies so the loop works out of the box. |

### Writing your own

Wrap any model — a PyPSA dispatch, a CGE, the Benmir et al. DSGE — in a class with
a `respond` method. For example, a sketch around an energy-system model:

```python
class EnergySystemModel:
    def respond(self, baseline_config, prices, iteration):
        cfg = copy.deepcopy(baseline_config)
        for scenario in cfg["scenarios"]:
            for year in scenario["years"]:
                p = prices[(scenario["name"], year["year"])]
                dispatch = my_energy_model.solve(co2_price=p)      # your model
                for participant in year["participants"]:
                    participant["initial_emissions"] = dispatch.emissions[participant["name"]]
        return cfg
```

## Usage

```python
from ets.coupling import run_coupled_simulation, ElasticityExternalModel

result = run_coupled_simulation(
    config,                                   # baseline scenario dict
    ElasticityExternalModel(elasticity=0.5, reference_price=55.0),
    max_iterations=40,
    tolerance=0.25,                           # price units
    relaxation=0.5,
)

result.summary            # final ETS scenario summary (DataFrame)
result.participants       # final ETS participant results (DataFrame)
result.price_history      # list of {(scenario, year): price} per iteration
result.converged          # bool
result.iterations         # iterations run
result.max_price_change   # final max |Δprice|
```

## Scope and honesty

Coupling is only as good as the external model you plug in. The bundled
`ElasticityExternalModel` is a transparent stand-in, not a real economy — it
demonstrates the mechanics and converges to roughly Option A's answer. Real
general-equilibrium closure (welfare, the social cost of carbon, energy-market
prices) requires a real CGE/DSGE/energy model behind the adapter; that is exactly
the point of keeping the boundary explicit rather than embedding one here.
Assumptions of the reference adapter: it rewrites per-year `initial_emissions`
and assumes no `initial_emissions_trajectory` override is set on coupled
participants.
