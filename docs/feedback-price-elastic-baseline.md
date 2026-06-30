# Feedback Option A — Price-Elastic Baseline

**Files:** `src/ets/participant/models.py` (`activity_multiplier`), `src/ets/participant/compliance.py` (`_scale_for_activity`)
**Enabled by:** scenario `reference_carbon_price > 0` **and** participant `output_price_elasticity > 0`
**Example:** [`examples/feedback_a_price_elastic_baseline.json`](../examples/feedback_a_price_elastic_baseline.json)

## What it adds

The base tool is a partial-equilibrium model of the **allowance market**: the only
price→quantity response is abatement (firms abate to MAC = P). The BAU baseline
(`initial_emissions`) is a fixed input. Option A adds the missing **own-price
activity response**: carbon-intensive output — and therefore the baseline — falls
as the carbon price rises. This "demand destruction" channel closes a feedback
loop *inside* market clearing:

```
higher price → less activity → lower baseline → fewer permits demanded → price moderates
```

Because the equilibrium solver already roots-finds the price where net demand =
supply, making the baseline price-dependent simply makes the demand curve more
elastic; the price and the activity level are found **jointly**, in the same Brent
solve. No new solver, no outer loop.

## The activity multiplier

$$
m(P) = \max\!\left(0,\; 1 - \varepsilon\,\frac{P - P_\mathrm{ref}}{P_\mathrm{ref}}\right),
\qquad
E_\text{base}(P) = E_0 \cdot m(P)
$$

ASCII: `m(P) = max(0, 1 - eps * (P - P_ref) / P_ref)`, `E_base(P) = E0 * m(P)`

| symbol | meaning | units | config field |
|--------|---------|-------|--------------|
| `P`     | carbon price (solved) | price units | (output) |
| `P_ref` | reference / undistorted price | price units | `reference_carbon_price` (scenario) |
| `eps`   | linearised price elasticity of activity (≥ 0) | dimensionless | `output_price_elasticity` (participant) |
| `E0`    | nominal BAU baseline | Mt CO₂e | `initial_emissions` |

Scaling `initial_emissions` by `m(P)` scales the whole activity envelope
proportionally — baseline emissions, abatement potential (`max_abatement`), and
benchmarked free allocation all move together (the per-unit-of-output
interpretation). `eps = 0` **or** `P_ref = 0` returns `m ≡ 1` → identical to the
inelastic tool.

### Behaviour: a restoring force toward `P_ref`

- `P > P_ref` → `m < 1` → activity contracts → demand falls → **price pulled down**.
- `P < P_ref` → `m > 1` → activity expands → demand rises → **price pulled up**.

So the elastic baseline damps price excursions away from the reference. In the
worked example a tightening cap pushes the inelastic price from ≈123 to ≈172,
while the elastic baseline (`eps = 0.5`, `P_ref = 55`) holds it to ≈74 → ≈88 —
firms cut output instead of paying an ever-higher price.

## Configuration

| field | level | type | default | meaning |
|-------|-------|------|---------|---------|
| `reference_carbon_price` | scenario | float | `0.0` | P_ref anchor; `0` disables the channel for the whole scenario |
| `output_price_elasticity` | participant | float ≥ 0 | `0.0` | ε; `0` leaves that participant's baseline fixed |

Both default to neutral, so **every existing scenario is unchanged**. Reading the
realised activity level back out: the per-participant `Initial Emissions` column
in the participant results reports `E0 · m(P*)` — i.e. the price-scaled baseline.

> **Auction mode.** Use `auction_mode: "explicit"` with the elastic baseline.
> In `derive_from_cap` mode the auction volume is derived from *nominal* free
> allocation at build time, before the price (and thus `m(P)`) is known.

## Scope and honesty

This is a **reduced-form, own-price** activity response — still partial
equilibrium. It does **not** capture cross-sector reallocation, income effects,
or energy-market clearing. For those, couple the tool to a purpose-built model
(see [Feedback Option B — Coupling](feedback-coupling.md)). The linearisation is
first-order: it is accurate for moderate deviations from `P_ref` and is floored
at `m = 0` (activity cannot go negative).
