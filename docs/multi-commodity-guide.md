# Compose a multi-commodity model

A practical guide to building, running, and reading a **multi-commodity
partial-equilibrium model** on the PE platform — a product market (steel)
coupled to a compliance market (carbon), solved as a joint equilibrium.

This is the "how do I build one" guide. For the economics and the proofs — the
product-market clearing primitive, the two-margin producer FOCs, existence and
loop gain, the closed OBA/CBAM cap-integrity rulings — see
[`docs/multi-commodity-spec.md`](multi-commodity-spec.md) and the architecture
in [`docs/multi-commodity-plan.md`](multi-commodity-plan.md). This page never
restates that math; it links to it.

The worked example throughout is the shipped flagship
[`examples/steel_carbon_joint.json`](../examples/steel_carbon_joint.json). Every
number in this guide is real output from running it with `uv run`.

---

## 1. What a multi-commodity model is, and how it differs from the joint model

A **joint model** ([`docs/joint-model-guide.md`](joint-model-guide.md)) couples
two markets that trade the *same kind of flow* — two carbon markets whose prices
feed each other through abatement costs. Both markets clear a
compliance-obligation flow; both prices are shadow prices of a cap.

A **multi-commodity model** couples two markets of *different kinds*:

- A **product market** (steel) clears a **goods market** on a behavioral
  **demand curve** against optimizing supply. Its price is a Walrasian goods
  price — both blades slope (supply up, demand down).
- A **compliance market** (carbon) clears an obligation flow against an
  exogenous cap. Its price is the shadow price of the cap.

The link between them is a **single producer that lives in both markets**. Its
steel output drives its emissions (`steel → carbon`); the carbon price raises
its output cost (`carbon → steel`). That two-way dependence is a cycle, so the
prices are mutually endogenous and must be found together:

```
   carbon price  ──▶  raises the steel producer's per-tonne output cost
        ▲                              │
        │                              ▼
   its output drives  ◀──  a lower steel output means fewer emissions
     its emissions
```

This is the **steel↔carbon cycle**, and it is solved by the **same joint engine**
as the same-flow joint model — the damped Gauss-Seidel outer loop over the price
pair `(P_steel, P_carbon)`, unchanged. What is new is only the product market
type and the two-margin producer inside it. If you have read the joint-model
guide, the outer-loop mechanics, the four `Joint *` diagnostics, and the damping
advice all carry over verbatim; this guide covers only what is different.

> A subtlety worth stating: the `steel → carbon` direction *looks* like a
> quantity channel (output drives emissions), but no quantity is threaded across
> markets. The producer re-derives its output and emissions from *both prices*
> inside each market's clearing, so the price norm suffices and the joint engine
> is reused byte-for-byte. See [`docs/multi-commodity-plan.md`](multi-commodity-plan.md) §0.

---

## 2. Build one — the config shape

A multi-commodity scenario reuses the joint `markets` / `links` /
`joint_solver` envelope. The two markets are a `carbon` market and a `steel`
market carrying `model_approach: "product"`, wired into a cycle by two coupling
links. Here is the base scenario of the flagship, annotated:

```jsonc
{
  "scenarios": [
    {
      "name": "steel-carbon base (finite-beta cycle)",
      "markets": [
        {
          "market_id": "carbon",
          "price_unit": "USD/tCO2",          // REQUIRED on every linked market
          "model_approach": "competitive",
          "producer_ref": { "market": "steel" },   // pull the steel producer in as an emitter view
          "years": [
            { "year": "2030",
              "total_cap": 40.0, "auction_offered": 40.0, "auction_mode": "explicit",
              "price_upper_bound": 200.0,
              "participants": [] }              // the producer is referenced, not re-declared here
          ]
        },
        {
          "market_id": "steel",
          "price_unit": "USD/t-steel",
          "model_approach": "product",         // <- the new market type
          "carbon_price": 0.0,                  // seed; overwritten by the link each sweep
          "product_demand": { "form": "linear", "intercept": 40.0, "slope": 0.3 },
          "import_supply": { "world_price": 0.0, "slope": 0.2, "sigma_foreign": 5.0 },
          "years": [
            { "year": "2030",
              "participants": [
                { "name": "SteelCo A", "kind": "producer",
                  "output_cost": { "gamma": 5.0, "delta": 2.0 },   // MC = gamma + delta*q
                  "intensity": 5.0,                                 // baseline tCO2/t
                  "abatement": { "beta": 10.0, "a_max": 5.0} },     // MAC = beta*a, a* = P_c/beta
                { "name": "SteelCo B", "kind": "producer",
                  "output_cost": { "gamma": 5.0, "delta": 2.0 },
                  "intensity": 5.0,
                  "abatement": { "beta": 10.0, "a_max": 5.0} }
              ] }
          ]
        }
      ],
      "links": [
        { "from_market": "carbon", "to_market": "steel",
          "channel": "carbon_input_price", "phi": 1.0, "phi_unit": "1/1",
          "target_participants": ["*"] },
        { "from_market": "steel", "to_market": "carbon",
          "channel": "output_ref_price", "phi": 1.0, "phi_unit": "1/1",
          "target_participants": ["*"] }
      ],
      "joint_solver": { "relaxation": 0.5, "tolerance": 1e-12, "max_iterations": 400 }
    }
  ]
}
```

The pieces that are specific to a multi-commodity model:

- **`model_approach: "product"`** turns the market into a product market. It
  clears `Σ q_i(P_s, P_c) + M(P_s) = D(P_s)` by root-finding on the steel price,
  instead of clearing an allowance obligation.
- **`product_demand`** is the downward-sloping demand curve. `form: "linear"`
  is `D = intercept − slope·P_s`; `form: "isoelastic"` (`D = kappa·P_s^{-eta}`)
  is the numerically-solved option for pass-through studies.
- **`import_supply`** is the carbon-free foreign supply `M = slope·(P_s − …)`
  that makes leakage well-defined. `sigma_foreign` is the emission intensity
  imports carry abroad. Omit the whole block for a closed economy (no leakage).
  A `cbam` sub-block turns on the price-active border charge (§3).
- **`kind: "producer"`** participants are two-margin producers, not compliance
  minimizers. Each carries `output_cost` (`gamma`, `delta` — `delta > 0` is
  required so marginal cost slopes up), `intensity` (baseline `sigma`),
  `abatement` (`beta`, `a_max`), and optionally `oba_benchmark` (§3d) and
  `technology_options` (§5).
- **`producer_ref`** on the carbon market pulls the steel producer in as a
  build-time **emitter view** — the same object, read from the carbon side. You
  declare the producer once, in the steel body; the carbon market never
  re-declares it. Its `participants: []` list is intentionally empty.
- **The two links close the cycle.** `carbon_input_price` stamps `P_carbon` onto
  the producer so its output prices carbon in; `output_ref_price` stamps
  `P_steel` onto the producer so its emissions follow output. These are the two
  new price-parameter channels — not quantity channels.
- **`joint_solver`** is the same block as the same-flow joint model. The
  flagship tightens it (`tolerance: 1e-12`, `max_iterations: 400`) so the run
  lands on the hand-verified anchor to machine precision; the defaults
  (`w = 0.5`, `tolerance = 1e-4`) converge too.

You can build the same graph in the canvas or through the `pe-composer` MCP
server exactly as in [`docs/joint-model-guide.md`](joint-model-guide.md) §2–3;
the product market and producer are additional block types on the same canvas.

Run it and read the joint prices:

```bash
uv run python -c "
from pe.engine import run_simulation_from_config
import json
summary, _ = run_simulation_from_config(json.load(open('examples/steel_carbon_joint.json')))
cols = ['Scenario','Equilibrium Carbon Price','Joint Converged','Leakage Rate','Gross Emissions','OBA Free Allocation']
print(summary[cols].to_string(index=False))
"
```

The base scenario converges to `P_carbon* = 10`, `P_steel* = 60`, per-firm
`q* = 5`, `a* = 1`, residual `Σe* = 40 = Cap`. `Joint Converged = 1`.

---

## 3. The levers

Each lever is a defaulted-inert knob; a config turns on any subset, and they
compose additively in the producer's decision. The flagship's numbers below are
the run output from §2.

### (a) Cap tightness — `total_cap` / `auction_offered`

Tighter cap → higher `P_carbon` → more abatement and more output loss → lower
emissions but a higher steel price. `P_carbon` is endogenous to the cap (its
shadow price). In the flagship the cap is `40`; that pins residual emissions at
`Σe = 40` and produces `P_carbon = 10`.

### (b) Demand elasticity — `product_demand.slope` (or `eta`)

Elastic demand (large slope) means the producer cannot pass the carbon cost
through, so output loss and leakage dominate. Inelastic demand passes the cost
into `P_steel` and consumers bear it. This is the **incidence split**. The
flagship's `slope = 0.3` is fairly inelastic, so the carbon cost passes into the
steel price (`P_steel` rises from the `30` no-policy level to `60`).

### (c) Intensity and abatement — `intensity`, `abatement.beta`, `abatement.a_max`

Baseline `intensity` (`sigma`) sets exposure; `beta` sets how cheap intensity
abatement is. A low-`beta` (cheap-abatement) firm leans on the **intensity
margin** and preserves output; a high-`beta` firm sheds **output** instead and
leaks more. In the flagship `beta = 10`, `sigma = 5`, so each firm abates
`a* = P_c/beta = 1` and still sheds output — both margins are active (§5).

### (d) Free allocation / OBA — `oba_mode: "output_based"`, `oba_benchmark`

Output-based allocation grants each firm `phi·q` free allowances, where `phi` is
its `oba_benchmark`. Because it scales with output it is a **marginal output
subsidy** of `P_carbon·phi` per tonne — it raises `q*` (fighting leakage on the
output margin) while leaving `a*` untouched. Crucially it is **cap-relaxing**;
see §4. Set `oba_mode: "output_based"` on the steel market and `oba_benchmark`
on each producer.

### (e) CBAM (price-active) — `import_supply.cbam`

A border charge `coverage·P_carbon·sigma_foreign` per imported tonne levels the
domestic and imported carbon cost, so imports rise less and leakage falls. Turn
it on inside `import_supply`:

```jsonc
"import_supply": { "world_price": 0.0, "slope": 0.2, "sigma_foreign": 5.0,
                   "cbam": { "enabled": true, "coverage": 0.5 } }
```

This CBAM feeds **into** steel clearing — it is price-active, distinct from the
platform's post-clearing reporting CBAM (`CBAM Gap` / `CBAM Liability`). In the
flagship, `coverage = 0.5` cuts leakage `0.353 → 0.111` and raises `P_carbon`
to `12.73` (blocking the import escape valve makes the cap bind harder).

### (f) Imports / leakage — `import_supply`

The presence of `import_supply` is itself the leakage channel: a domestic carbon
price pushes output abroad. The **leakage rate** `L = sigma_foreign·ΔM /
(−Δe_dom)` is foreign emissions gained per unit of domestic emissions cut. It is
reported (§4). Remove `import_supply` and there is no leakage to report.

### (g) Investment (long-run margin) — `technology_options`

A cleaner technology option (lower `sigma_prime`) that adopts when the carbon
price clears its trigger. This is the third decarbonization margin — a durable
downward shift of the intensity curve. See §5.

---

## 4. Read the results — leakage and the cap-integrity contrast

Multi-commodity scenarios add columns to the **steel** market row (the carbon
row carries the usual joint diagnostics). The load-bearing ones:

| Column | Plain meaning |
|---|---|
| **Equilibrium Carbon Price** (carbon row) | `P_carbon*`. On the steel row this column carries `P_steel*`. |
| **Leakage Rate** | Headline `L` against the no-policy (`P_c = 0`) counterfactual at the **un-adopted** technology — it scores the whole-policy effect, including any induced tech switch. |
| **Conditional Leakage** | The secondary diagnostic at the post-adoption intensity `sigma'`. Equals Leakage Rate when nothing adopts. |
| **Gross Emissions** | Total emissions actually released, `Σe`. |
| **OBA Free Allocation** | Free allowances issued by OBA, `phi·Σq`. Zero unless `oba_mode: "output_based"` is on. |

### The punchline: CBAM preserves the cap, OBA relaxes it

This is the guide's key story. Both CBAM and OBA fight leakage, but on
**different margins** and with **different consequences for cap integrity**:

- **CBAM is cap-PRESERVING.** It works on the import margin. No free allowances
  are issued, so `Σe = Cap` — gross emissions stay at the cap.
- **OBA is cap-RELAXING.** It works on the output margin by issuing `phi·Σq`
  free allowances **on top of** the auctioned cap, so `Σe = Cap + phi·Σq`. Gross
  emissions float up with output. OBA is **not** emissions-neutral.

The flagship makes this concrete (real run output):

| Scenario | `P_carbon` | `P_steel` | Leakage Rate | Gross Emissions | OBA Free Allocation |
|---|---|---|---|---|---|
| base (cap only) | 10.00 | 60.00 | 0.353 | 40.00 | 0.00 |
| CBAM `c = 0.5` | 12.73 | 71.26 | **0.111** | **40.00** | 0.00 |
| OBA `output_based` | 10.00 | 53.33 | 0.326 | **53.33** | **13.33** |

Read it left to right. **CBAM cuts leakage hard — `0.353 → 0.111` — while
holding `Σe = Cap = 40`.** **OBA barely dents leakage — `0.353 → 0.326` — and
inflates gross emissions +33% (`40 → 53.33`)**, exactly the `Cap + phi·Σq = 40 +
13.33` identity. The `Gross Emissions` and `OBA Free Allocation` columns are how
you *see* the cap relaxing.

So in this calibration CBAM dominates: more leakage protection *and* it keeps the
cap intact. The ranking is calibration-dependent — a different demand elasticity
or abatement cost can reorder the leakage numbers — but the structural fact,
**CBAM cap-preserving vs OBA cap-relaxing**, is general
([`docs/multi-commodity-spec.md`](multi-commodity-spec.md) §7 ruling #4).

> The single-market [`examples/oba_output_allocation.json`](../examples/oba_output_allocation.json)
> shows a *different* OBA design — `fixed_cap` / exogenous-output — where output
> does not respond, allocation is purely distributional, the price is flat, and
> `Σe = Cap`. That is not a contradiction: OBA becomes a marginal output subsidy
> that relaxes the cap only once output responds endogenously, which is exactly
> what the `output_based` design in the multi-commodity model captures.

---

## 5. The two decarbonization margins (and investment as the third)

A carbon price makes a producer cut emissions on two margins at once:

- **The intensity margin** — abate `a* = P_carbon/beta` (clipped to `a_max`).
  This responds first and linearly to the carbon price, independent of output.
- **The output margin** — shed output in response to the residual carbon burden
  after abatement. Cheap-abatement firms preserve output; expensive-abatement
  firms shed it (and leak more).

In the flagship base scenario the total emission cut of `85` (from the no-policy
`e0 = 125` down to `40`) splits into an **intensity margin of 25** and an
**output margin of 60** — both active. This two-way split is *why the cycle is
born*: because `beta` is finite, output `q = Cap/(sigma − P_c/beta)` varies with
the carbon price at a fixed cap, closing the steel↔carbon loop. With
`beta → ∞` (no intensity abatement) output would be pinned by the cap and the
model would collapse to a one-way chain.

**Investment is the long-run third margin.** A `technology_options` entry offers
a cleaner technology (lower `sigma_prime`) that adopts when the carbon price
clears its trigger. Adoption is decided *inside* the joint loop against the
joint price, accumulating as a monotone floor (irreversibility is physical) —
the same investment-in-cycle machinery as the same-flow joint model
([`docs/joint-model-guide.md`](joint-model-guide.md) §7). The flagship's
investment scenario offers an H2-DRI option (`sigma_prime = 3`) with
`trigger_mode: "break_even"` (so the reported `Clean Tech Trigger Price` is
`theta = 9`). At the base `P_carbon = 10 ≥ 9` the switch fires: intensity drops
`5 → 3`, the cap loosens, `P_carbon` falls to `7.93` (ex-post regret is
permitted), and domestic output recovers. Headline `Leakage Rate` drops to
`0.162` because it holds the un-adopted-`sigma` counterfactual and so scores the
induced tech switch; `Conditional Leakage` (`0.393`) is the post-adoption-`sigma'`
diagnostic.

The FOCs, the loop-gain algebra, and the adoption nesting are in
[`docs/multi-commodity-spec.md`](multi-commodity-spec.md) §2–3 and §7.

---

## See also

- [`docs/multi-commodity-spec.md`](multi-commodity-spec.md) — the binding
  economics: the product-market primitive, the two-margin producer FOCs,
  existence and loop gain, the finite-β cyclic anchor, the closed V-D3 rulings
  (including the OBA/CBAM cap-integrity contrast).
- [`docs/multi-commodity-plan.md`](multi-commodity-plan.md) — the architecture:
  the reused joint engine, the one new clearing primitive, the two coupling
  channels, the producer-ref expansion.
- [`docs/joint-model-guide.md`](joint-model-guide.md) — the sibling guide for a
  same-flow joint model: the outer loop, the four `Joint *` diagnostics,
  convergence and damping. The multi-commodity model reuses all of it.
- [`examples/steel_carbon_joint.json`](../examples/steel_carbon_joint.json) —
  the flagship worked through this guide (base, CBAM, OBA, investment).
- [`MANUAL.md`](../MANUAL.md) — launchers, the composer GUI, and the full
  output-column reference.
</content>
