# D3 multi-commodity (steel↔carbon) — architecture / implementation plan

Authored by lead-modeller (2026-07-12). Companion economics: `docs/multi-commodity-spec.md`
(economist). Tiers are path-enforced by `tests/test_module_isolation.py`: T0 `pe.core.*`
→ T1 `pe.config_io.*` → T2 `pe.features.<X>.*` (`modules/<X>/backend/`, two-door) → T3
`pe.engine.*` → T4 workflows → T5 apps. Math-bearing work orders carry a `[V-D3-x]`
economist verdict slot.

## 0. The load-bearing decision — price-driven coupling ⇒ joint engine reused verbatim

The steel↔carbon coupling runs both ways: carbon→steel (P_carbon raises the producer's
steel-output marginal cost → shifts steel supply) and steel→carbon (output q drives
emissions → allowance demand). The second *looks* like a QUANTITY channel — which
joint-equilibrium.md §5 deferred to D3 behind a new quantity-norm. **We do NOT thread q.**
Instead thread only the sibling PRICE and re-derive q\* inside each market's clearing from
BOTH prices: the producer program pins (q\*, a\*) as a deterministic function of
(P_steel, P_carbon), so both markets evaluated at the same price pair recover the identical
q\*. The coupling stays price-driven, and — per joint-equilibrium.md §5 — *quantities are
deterministic functions of converged prices → the price norm SUFFICES*.

**Consequence:** `engine/scc.py` and `engine/joint.py` are reused BYTE-FOR-BYTE; the
{carbon, steel} 2-cycle is the same SCC object as the carbon↔carbon cycle. `[V-D3-1]`
economist must confirm the producer program is strictly convex in q (a linear c(q) gives
bang-bang supply → discontinuous → Kakutani-ε non-existence, to be reported honestly via
`Joint Converged=0`, never faked).

## 1. The minimal new primitive — product-market clearing on a demand curve

New T0 primitive `core/backend/core/market/product_clearing.py` (pure numerics, imports
only `pe.core.*` + scipy), sibling of `clearing.py`. `solve_product_equilibrium(market,
P_carbon, ...)` Brent root-finds `excess(P_steel) = Σ producer.product_supply(P_steel;
P_carbon) + import_supply(P_steel[, CBAM(P_carbon)]) − D(P_steel)` on `[0, P_max]`. Monotone
(supply↑, demand↓) → unique root, mirroring `solve_equilibrium`'s bracket-then-Brent
discipline. **Why T0:** the *algorithm* is a pure root-finder of the same kind already in
T0; the *economic content* (demand/import/CBAM params) is feature-parsed.

**Market "type" without perturbing carbon (golden-inert):** reuse the existing
discriminator `model_approach`. A product market is a body with `model_approach: "product"`;
`engine/dispatch.py:_path_solver_for` gains one `"product"` branch before the competitive
default (fires only for the new string). `ALLOWED_MODEL_APPROACHES` (`config_io/normalize.py`)
gains `"product"` (REQUIRED — unknown approaches silently clamp to competitive). The product
market stays a `CarbonMarket` object with product data `setattr`'d (as `msr_*`/`eua_price`
already are); cap buckets inert (`total_cap=auction_offered=0`). **Strain:** `CarbonMarket`
is now semantically overloaded; a dedicated `ProductMarket` dataclass is DEFERRED until a
second product good justifies it.

## 2. The multi-commodity agent

New T0 participant kind `MultiCommodityProducer` (`core/backend/core/participant/producer.py`).
NOT a reuse of `MarketParticipant` (which *minimises compliance cost at fixed output* — a
producer *maximises profit over (q, a)*). It imports the existing abatement-cost helpers
(`core/costs.py`) and the OBA benchmark relationship. Off-by-default, golden-inert.

One object, two faces, both delegating to one core optimiser:

```
core (T0):   optimize_producer(params, P_steel, P_carbon) -> (q*, a*, emissions, supply, profit)
  carbon face:  optimize_compliance(P_carbon, ...) -> ComplianceOutcome   # duck-types participant protocol
  steel  face:  product_supply(P_steel, ...)       -> q*                  # consumed by solve_product_equilibrium
```

The carbon market's `solve_equilibrium` calls `participant.optimize_compliance(P)` on every
participant — the producer IMPLEMENTS that method (delivered P_steel stamped before the
carbon leg solves), so `solve_equilibrium` is UNTOUCHED. The producer's output response to
P_carbon is an own-market response inside the single carbon Brent solve (like the
elastic-baseline overlay, V-D2-7 — not an outer loop). At the joint fixed point both faces
evaluate at (P_steel\*, P_carbon\*) → identical q\* → price norm suffices. `[V-D3-2]`
economist owns the objective/FOCs/OBA-as-marginal-output-subsidy term.

## 3. Reuse vs new — the ledger

| Component | Disposition |
|---|---|
| `engine/joint.py` `solve_joint_scc`, `engine/scc.py`, `core.relaxation` mixed-unit norm | **REUSED VERBATIM** |
| OBA output→intensity (`modules/oba`) | **GENERALIZED** — benchmark moves from build-time free-alloc override into the producer's marginal profit (q now endogenous); build-time OBA for exogenous-output carbon participants stays as-is (golden-inert) |
| investment-in-cycle (`endogenous_investment`, `_solve_scc_member` adoption floor) | **REUSED** — producer cleaner-tech = an AdoptionSpec; MIDDLE-inside-OUTER monotone floor already runs in cyclic SCCs |
| `market_links` channels | **EXTENDED** — two new sibling channels (§4), not edits |
| `config_io` builder/markets/normalize | **EXTENDED** additively — product body, `"product"` approach, `kind:"producer"`, ref-expansion |
| `engine/dispatch.py` | **ONE branch** in `_path_solver_for`; `_solve_market_leg`/`_solve_scc_member`/`_solve_cyclic_scc`/collect-stamp all UNTOUCHED |
| `engine/wiring.py` | **EXTENDED** — `solve_product_path` entry + 2 channel-registry entries |

The joint machinery routes the product market with no change because SCC condensation, sweep
threading (`{market_id:{year:price}}`), inbound links, adoption-floor carry, and result
collection are all keyed on `market_id` + the injected per-market closure — never on the
market's class.

## 4. The coupling — two price-parameter link channels

The producer is declared ONCE (owner = the product market body) and REFERENCED into the
carbon market. Two `LinkSpec` edges + two new channels in
`modules/product_market/backend/channels.py` (T2 runtime, pure copy-on-write):
- **carbon→steel, `carbon_input_price`:** stamps P_carbon(t) on the steel-side producer so
  `product_supply` prices carbon into output cost.
- **steel→carbon, `output_ref_price`:** stamps P_steel(t) on the carbon-side producer so
  `optimize_compliance` computes output-driven emissions.

Both register in `wiring.py:link_channels()` and mirror into `ALLOWED_LINK_CHANNELS`. New
keys → existing `mac_cost`/`invest_break_even` unaffected (golden-inert). NOT quantity
channels — nothing writes a solved quantity across markets (§0 holds). `[V-D3-3]` economist
confirms φ/incidence and price-driven coupling. Producer params live in the steel body; the
carbon body carries a lightweight `{"producer_ref": {...}}` the multi-market normalizer
expands into a `kind:"producer"` emitter view (single source of truth; rejects solve-time
participant injection).

## 5. Config schema (additive, off-by-default → every existing example bit-identical)

A steel↔carbon model reuses the joint `markets`/`links`/`joint_solver` envelope (cf.
`examples/joint_two_market.json`): a `carbon` market (`model_approach: banking`/competitive,
a cap, pure emitters + a `producer_ref`) and a `steel` market (`model_approach: "product"`,
`product_demand` {linear|isoelastic}, `import_supply` [leakage lever], `cbam` [import-charge
lever], and a `kind:"producer"` participant with `output_cost`/`intensity`/`abatement`/
`oba_benchmark`/`capacity`/`technology_options` [cleaner-tech lever]) + two coupling links +
`joint_solver`. Each lever is a defaulted-inert knob (imports absent → none; `cbam.enabled:
false`; `oba_benchmark:0`; no trigger → static intensity). Any scenario without a `"product"`
market normalizes byte-identically — all 12 curated examples + the joint set stay bit-identical.

## 6. Work orders (mirroring D2)

- **D3-0** economist spec (BLOCKING): producer objective+FOCs+uniqueness (convex c(q)),
  demand/import/CBAM/OBA forms, closed-form 2-market anchors, price-driven ratification →
  `docs/multi-commodity-spec.md`. Gates D3-2/3/4/6.
- **D3-1** product-market clearing primitive `solve_product_equilibrium` (T0). Golden-inert.
- **D3-2** `MultiCommodityProducer` agent + `optimize_producer` + two faces (T0). `[V-D3-2]`.
- **D3-3** dispatch routing + product path solver + `"product"` whitelist + builder product
  body/`kind:"producer"` (T2 `modules/product_market/` + T3 wiring/dispatch + config_io).
  Golden-inert (proves carbon markets unmoved before any coupling).
- **D3-4** coupling: two price-parameter channels + registry + producer-ref expansion.
  Joint engine untouched. `[V-D3-3]`. Lights up the cycle.
- **D3-5** levers: CBAM import charge, imports/leakage, OBA output subsidy, cleaner-tech
  investment-in-cycle. Each off-by-default. `[V-D3-4]`.
- **D3-6** hand-anchored golden example `examples/steel_carbon_joint.json` + baseline +
  closed-form anchor test. `[V-D3-5]`.
- **D3-7** frontend product-market/producer nodes + steel↔carbon result display (two price
  paths, steel quantity, leakage) + MCP describe/run surfaces.
- **D3-8** docs (this + user guide).

Sequencing: D3-0 gates the math orders; D3-1 lands early parallel to D3-0; D3-3 is the
golden-inert routing shell; D3-4 lights the cycle; D3-5 layers levers; D3-6 the closed-form
gate. First cut = one product market + one carbon market + price-taking producers +
price-driven coupling.

## 7. Risks / strains

1. **`CarbonMarket` overloaded as product container** — cap buckets inert; product solver
   emits ledger-compatible detail dicts (output/abatement/profit columns); baseline pins
   whatever shape emerges. Dedicated `ProductMarket` dataclass DEFERRED.
2. **"Participant in two markets"** — resolved by single-declaration + producer-ref expansion
   (each market builds a normal participant list; producer duck-types the protocol on the
   carbon face), NOT solve-time injection.
3. **Non-existence when c(q) linear** (bang-bang → Kakutani-ε only) — economist demands
   strictly convex output cost `[V-D3-1]`; the joint loop's non-convergence reporting surfaces
   it honestly.
4. **Determinism** — `optimize_producer` a deterministic function of the two prices (fixed
   Brent/analytic FOC), same discipline as `optimize_compliance`.
5. **Loop gain** — steel↔carbon 2-cycle g = s_carbon·s_steel·φ·φ; w=0.5 damps |g|<3; strong
   CBAM + inelastic demand → R37 near-critical WARNING already fires. No new damping.
6. **DEFERRED:** full multi-good MPE; genuine quantity channels + the quantity-norm; endogenous
   world price; multiple product markets in one cycle; producer market power in steel (v1 is
   price-taking).

**Open items for the economist:** `[V-D3-1]` convexity/uniqueness of q\*(P_steel,P_carbon);
`[V-D3-2]` producer objective+FOCs+OBA-subsidy term; `[V-D3-3]` price-driven coupling +
producer ownership; `[V-D3-4]` per-lever (CBAM incidence, leakage form, OBA subsidy);
`[V-D3-5]` closed-form 2-market anchor values.
