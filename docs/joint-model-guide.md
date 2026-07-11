# Compose a joint-equilibrium model

A practical guide to building, running, and reading a **multi-market cyclic
(joint) partial-equilibrium model** on the PE platform — in the canvas, as a
config file, or through the MCP composer.

This is the "how do I build one" guide. For the economics and the proofs —
existence, the contraction condition, the cycle-detection predicate, the
investment nesting — see [`docs/joint-equilibrium.md`](joint-equilibrium.md).
This page never restates that math; it links to it.

---

## 1. What a joint model is, and when you need one

Most PE models are a single market, or several markets wired in one direction
only: market A's solved price feeds market B, B never feeds back. That is a
**one-way link** — a directed acyclic graph. The platform solves it market by
market in topological order (solve A, apply A's price to B, solve B). No
iteration, one pass.

A **joint model** is what you draw when the markets feed each *other* — a
**cycle**:

```
   carbon price  ──▶  raises a power generator's abatement cost
        ▲                              │
        │                              ▼
   feeds back into  ◀──  power price shifts carbon abatement
```

`A → B` **and** `B → A`. Now there is no valid "solve first" order: A's answer
depends on B's, which depends on A's. The two markets are **mutually
endogenous**, and you have to find both prices at once.

The object you are solving for is the **joint fixed point**: the one price
vector `(P_A, P_B)` where *every* market clears given the *others'* prices — a
mutually consistent equilibrium in which no market wants to move once all the
others have settled. The engine finds it by iterating: solve each market
against the latest neighbour prices, feed the new prices back, repeat, until
nothing moves. When the loop stops moving, you have the joint equilibrium.

**When you need one:** any time a price you compute in one market changes a cost
or a threshold in another market that, in turn, changes the first market's
price. A carbon price raising power-sector marginal costs whose power price
feeds back into carbon abatement is the canonical case. If the feedback only
runs one way, you do **not** need a joint model — a one-way link
(`link_oneway.json`) is solved directly, no outer loop, and stays byte-identical
to a single-market run.

> The math of the fixed point `P* = T(P*)`, why it exists, and when it is unique
> lives in [`docs/joint-equilibrium.md`](joint-equilibrium.md) §1–2. Read it if
> you want the theory; you do not need it to build a model.

---

## 2. Compose it in the canvas (GUI)

Open the Model Composer (`./configure.command`, port 8801). Building a joint
model is the same drag-drop-connect flow as any model, plus three link-specific
moves: **the back-edge, the channel, and the joint-solver node.**

### 2.1 Draw two markets

Drag two **Carbon Market** blocks onto the canvas. Give each the usual minimum:
a **price-formation** block (e.g. Competitive Clearing), at least one
**Participant**, and a year grid. Name them so you can tell them apart
(`power`, `carbon`).

Because these two markets will be linked, each one **must declare a
`price_unit`** (e.g. `USD/tCO2`, `USD/MWh`). This is required the moment a
market touches a link — the engine rejects a linked market with no
`price_unit`. An unlinked market needs none.

### 2.2 Connect them into a cycle with `market_link` edges

Drop a **Market Link** block. It has a `from` input (kind `market_signal`) and a
`link` output (kind `market_link`). Wire the forward direction `A → B`:

- `power.signal` (the market's solved-price out-port) → `market_link.from`
- `market_link.link` → `carbon.links` (the market's inbound-links in-port)

Now drop a **second Market Link** and wire the **back-edge** `B → A` the same
way (`carbon.signal → link2.from`, `link2.link → power.links`). Those two edges
together are the cycle — the thing that makes this a joint model rather than a
one-way chain. Without the back-edge you have an acyclic link and the outer loop
never runs.

**Self-links are forbidden.** A `market_link` whose `from` and `to` are the same
market is rejected at validation — own-price feedback is intra-market demand
response (the price-elastic-baseline overlay), not an outer iteration.

### 2.3 Set each link's channel and φ

Select each `market_link` node and set, in the parameter panel:

| Param | What to set | Notes |
|---|---|---|
| `channel` | `mac_cost` | The demand-side channel. `mac_cost` adds `φ·P` to a target technology's MAC level. (`invest_break_even` shifts an investment break-even threshold instead.) Required — there is no default. |
| `phi` | the coupling coefficient | Sign-free; `0` is legal (an inert edge). This is the `φ` in the loop. |
| `phi_unit` | e.g. `USD/MWh per USD/tCO2` | **Required.** The units of `φ` as `[units_of_target per units_of_source]`. A silent dimensionless fallback would be an economic constant hiding in a default, so the engine refuses to guess it. |
| `target_participants` | explicit names, or `["*"]` | No implicit "all". |
| `target_technologies` | the technology-option name(s) | **Required for `mac_cost`.** A `mac_cost` link may not target a `linear`-abatement option (its `cost_slope` is a slope, dimensionally excluded from a price-level shift). |

### 2.4 Drop a `joint_solver` node (optional but recommended)

Drag one **Joint Solver** block and connect its `joint_solver` output to *any
one* market's `joint_solver` in-port. One node configures the **whole cycle's**
outer loop — you do not attach one per market.

It is **config-driven**: you only set what you want to change. Every param you
leave blank falls back to the engine default. The five settings:

| Param | Default | Meaning |
|---|---|---|
| `relaxation` | `0.5` | `w` — the damping weight in `(0, 1]`. `w < 1` damps; `w = 1` is undamped. See §5. |
| `tolerance` | `1e-4` | Per-market relative convergence tolerance (dimensionless). `atol` is accepted as an alias. |
| `max_iterations` | `50` | Hard cap on outer sweeps. |
| `sweep` | `gauss_seidel` | The only scheme in v1 (Jacobi is deferred). |
| `initial_guess` | `one_way_seed` | Warm-start from the one-way solve (back-edges cut). `cold` starts flat. |

If you drop no Joint Solver node at all, the cycle still solves — with every
default above. The node exists only to override them.

### 2.5 Validate and run

Click **Validate** (surfaces any structural problem — a missing `price_unit`, a
self-link, a linear `mac_cost` target — as a clickable issue), then **Run**.
Results render below the canvas (§4). **Export config** writes the compiled
`scenario-config.json`; **Save model** puts it in the shared registry.

---

## 3. Compose it as a config file (or via MCP)

### 3.1 The config shape

A linked scenario carries a `markets` array and a `links` array (instead of a
flat single-market body), plus an optional `joint_solver` block. This is the
shape the canvas exports and the engine runs:

```jsonc
{
  "scenarios": [
    {
      "name": "joint_two_market",
      "markets": [
        {
          "market_id": "power",
          "price_unit": "USD/tCO2",        // REQUIRED on every linked market
          "years": [ { "year": "2030", "total_cap": 80.0,
                       "auction_mode": "explicit", "auction_offered": 80.0,
                       "participants": [ /* ... */ ] } ]
        },
        {
          "market_id": "carbon",
          "price_unit": "USD/tCO2",
          "years": [ { "year": "2030", /* ... */ } ]
        }
      ],
      "links": [
        {                                   // forward edge  carbon -> power
          "from_market": "carbon", "to_market": "power",
          "channel": "mac_cost", "phi": 0.4, "phi_unit": "1/1",
          "target_participants": ["power_firm"],
          "target_technologies": ["ccgt"]
        },
        {                                   // BACK edge  power -> carbon  (closes the cycle)
          "from_market": "power", "to_market": "carbon",
          "channel": "mac_cost", "phi": 0.5, "phi_unit": "1/1",
          "target_participants": ["carbon_firm"],
          "target_technologies": ["ccs"]
        }
      ],
      "joint_solver": {                     // OPTIONAL — omit to accept every default
        "relaxation": 0.5,
        "tolerance": 1e-4,
        "max_iterations": 50
      }
    }
  ]
}
```

Notes that match the engine exactly:

- **The two links form the cycle.** One `carbon → power`, one `power → carbon`.
  Drop the second and you have a one-way (acyclic) scenario — solved directly,
  no outer loop, no joint diagnostics.
- **`joint_solver` is scenario-level**, a sibling of `markets`/`links`, not
  inside a market. It is only *emitted* when a cycle is present, so every
  single-market and one-way config stays byte-identical to today.
- **Leave keys out to accept defaults.** `{"joint_solver": {"tolerance": 1e-6}}`
  keeps `relaxation=0.5`, `max_iterations=50`, `sweep=gauss_seidel`,
  `initial_guess=one_way_seed`. Every setting is validated loudly (a bad
  `relaxation` outside `(0, 1]`, a non-positive `tolerance`, an unknown `sweep`)
  — never silently clamped.
- **`atol` is an accepted alias for `tolerance`.**

Run it with:

```bash
uv run python -c "
from pe.engine import run_simulation_from_config
import json
summary, _ = run_simulation_from_config(json.load(open('joint_two_market.json')))
print(summary[['Scenario','Market','Equilibrium Carbon Price','Joint Converged']].to_string(index=False))
"
```

### 3.2 Via the pe-composer MCP server

The MCP path builds the same graph document conversationally. The tools are
stateless — you hold the returned `graph` dict and pass it into the next call:

1. `new_graph()` — a blank, validation-clean skeleton (or
   `new_graph(template_id="joint_two_market")` to start from a saved model).
2. `add_block(...)` for each block — two `carbon_market`s, a price-formation
   block and participant(s) per market, two `market_link`s, one `joint_solver`.
   `add_block` auto-wires each block's one obvious edge into a market; the
   **link back-edge wiring** (a market's `signal` out-port into a `market_link`'s
   `from` in-port) is added by editing the returned graph's `edges` directly,
   since a link's source side is not the "one obvious edge".
3. `set_params(graph, node_id, {...})` — set each link's `channel`, `phi`,
   `phi_unit`, `target_participants`, `target_technologies`; set the
   `joint_solver`'s `relaxation` / `tolerance` / `max_iterations`.
4. `check(graph)` after every mutation. Resolve each `next_steps` entry before
   running. `check` returns `ok: true` when there are no ERROR-level issues.
5. `run_model(graph)` — compiles and solves. The compact summary carries the
   four joint diagnostics on the cyclic market rows (§4).

---

## 4. Run it, and read the results

### 4.1 Per-market results

A linked scenario reports one result block **per market**, keyed by the
composite name `"<scenario> :: <market_id>"`. Solving the flagship config above
gives (real output, default `joint_solver`, `w = 0.5`):

```
                  Scenario Market  Equilibrium Carbon Price  Joint Converged  Joint Outer Iterations  Joint Max Normalized Change  Joint Cycle Detected
 joint_two_market :: power  power                164.996333              1.0                    17.0                     0.000074                   0.0
joint_two_market :: carbon carbon                162.490831              1.0                    17.0                     0.000074                   0.0
```

In the GUI each composite becomes its own scenario pill (`joint_two_market ::
power`, `joint_two_market :: carbon`); click a pill to see that market's price,
supply/demand curve, and participants exactly as for a single-market run.

### 4.2 The four joint diagnostics

Cyclic-SCC market rows — and *only* those rows — carry four extra columns. An
acyclic or single-market run never gains them, so their mere presence tells you
"this market was solved jointly".

| Column | Plain meaning |
|---|---|
| **Joint Converged** | `1` = the outer loop reached a mutually consistent fixed point. `0` = it hit the iteration cap or a confirmed oscillation. **A `0` is never an equilibrium** — it is the last iterate, stamped so you can see it failed. |
| **Joint Outer Iterations** | How many sweeps the loop took. A larger number means slower (more tightly coupled) convergence. |
| **Joint Max Normalized Change** | The final per-market relative price change, maxed across the markets. Below `tolerance` on a converged run; the residual on a failed one. |
| **Joint Cycle Detected** | `0` = no oscillation. `2` = a period-2 (anti-phase) oscillation was detected — the prices are ping-ponging, not crawling. This is only meaningful when `Joint Converged = 0`; a converged run always reads `0` here (a transient wobble during descent is not a reported cycle). v1 detects period-2 only: a higher-period spiral in a ≥3-market cycle reads `Converged = 0` with period `0`. |

**Reading them together:**

- `Converged = 1`, `Cycle = 0` — done. Trust the prices.
- `Converged = 0`, `Cycle = 2` — an oscillation. The remedy is **more damping**
  (lower `relaxation`), not more iterations. See §5.
- `Converged = 0`, `Cycle = 0` — a slow crawl (or a non-period-2 spiral). The
  remedy is **more iterations** (raise `max_iterations`), or the coupling is
  near-critical. See §5.

### 4.3 The UI: banner and per-market card

The composer surfaces these automatically.

**Non-convergence banner.** If any market did not converge (or converged while
still oscillating), a banner appears above the results, one line per market, in
plain language, e.g.:

> Joint equilibrium did not converge for carbon after 50 outer iterations —
> reduce the joint-solver relaxation (more damping) or raise max iterations.
> Cycle detected: period 2.

**Per-market convergence card.** Selecting a market's pill shows a "Joint
equilibrium" card headed *"Converged in N iterations"* or *"Did not converge"*,
with the four diagnostics laid out: Converged (Yes/No), Outer iterations, Max
normalized change (in scientific notation), and Cycle detected (`period 2` or
`none`).

If everything converged cleanly, there is no banner — only the card, reading
`Converged: Yes`.

---

## 5. Convergence and damping

The outer loop is a **damped Gauss-Seidel** iteration. After each sweep it does
not jump straight to the freshly-solved prices; it takes a weighted step:

```
P_next = (1 - w) · P_previous + w · P_swept
```

`w` is the `relaxation` weight. `w = 1` is undamped (take the new prices whole);
`w < 1` damps (move only part way). The default `w = 0.5` is deliberately
conservative — it converges across a much wider band of coupling strengths than
`w = 1` does, at the cost of a few extra sweeps.

**Why damping matters — the intuition.** Whether the loop converges at all is
governed by the **loop gain** `g` — roughly, how much a price change in A comes
back amplified after one full trip around the cycle. If `|g| < 1` the loop is a
contraction and settles; if `|g| ≥ 1` it does not. When `g` is negative the
prices *alternate* (over-shoot, over-correct, over-shoot) — a period-2
oscillation. Damping shrinks the effective gain: under-relaxing turns a
borderline-divergent alternation into a convergent one. The full contraction
condition (`ρ(J) < 1`, and `g = s_A·s_B·φ_AB·φ_BA` for a 2-market cycle) is in
[`docs/joint-equilibrium.md`](joint-equilibrium.md) §2.

### If it does NOT converge

Read `Joint Cycle Detected` first — it tells you *which* remedy:

| Symptom | `Cycle Detected` | Fix |
|---|---|---|
| Prices oscillate (ping-pong) | `2` | **Lower `relaxation`** (more damping). More iterations will *not* help — an oscillation at `w = 1` still oscillates at `w = 1` no matter how long you run it. |
| Slow crawl toward a fixed point | `0` | **Raise `max_iterations`.** The loop is converging, just slowly; give it more sweeps. |
| Neither converges nor cleanly oscillates | `0` | The coupling may be near-critical (`|g|` near or above 1). Check `phi` and the market couplings; no `w ∈ (0, 1]` rescues a genuinely divergent (`g > 1`) loop. |

### The `joint_oscillating.json` demonstrator

The shipped `joint_oscillating.json` example is built to make this concrete. It
is a 2-market cycle tuned to a loop gain of `g = -1.5` — an oscillation:

- **At `w = 1` (undamped):** the loop diverges. The run reports
  `Joint Converged = 0` and `Joint Cycle Detected = 2`, and the banner appears.
  Raising `max_iterations` changes nothing — it is an oscillation, not a crawl.
- **At `w = 0.5` (the default):** the same coupling has an effective eigenvalue
  of `-0.25`, well inside the contraction band, and the loop converges to the
  hand-computable fixed point. `Joint Converged = 1`, `Joint Cycle Detected = 0`.

That is the whole lesson in one example: **when a cycle oscillates, reach for
damping, not iterations.** (This is anchor J2 in
[`docs/joint-equilibrium.md`](joint-equilibrium.md) §7.)

---

## 6. A worked example: `joint_two_market.json`

The `joint_two_market.json` flagship is the converging two-market cycle used
throughout this guide. It is the hand-solvable **J1 anchor** — small enough that
you can check the answer by algebra, so it is the right first joint model to run.

**The two markets.** `power` and `carbon`, each a single firm holding one
threshold-abatement technology option whose MAC level sits at `c` — `c_power =
100`, `c_carbon = 80`. Each market on its own would clear at its own `c`.

**The links.** Two `mac_cost` links close the cycle: `carbon → power` with
`φ = 0.4`, and `power → carbon` with `φ = 0.5`. Each link adds `φ · P_neighbour`
to the target firm's MAC level, so each market clears at
`P = c + φ · P_neighbour`. The loop gain is `g = φ_A · φ_B = 0.4 · 0.5 = 0.2`
— comfortably inside the contraction band, so it converges.

**The joint solver.** With the defaults (`w = 0.5`, `tolerance = 1e-4`), the loop
converges in **17 sweeps** to:

```
 joint_two_market :: power  power   164.996333   Joint Converged 1.0   Outer Iterations 17.0   Cycle Detected 0.0
 joint_two_market :: carbon carbon  162.490831   Joint Converged 1.0   Outer Iterations 17.0   Cycle Detected 0.0
```

**The hand check.** The exact fixed point is

```
P_power  = (c_power  + φ_A · c_carbon) / (1 - g) = (100 + 0.4·80) / 0.8 = 165.0
P_carbon = (c_carbon + φ_B · c_power ) / (1 - g) = ( 80 + 0.5·100) / 0.8 = 162.5
```

The default run lands at `164.996 / 162.491` — within the `1e-4` relative
tolerance of the hand values. Tighten the solver to match the analytic answer to
machine precision:

```jsonc
"joint_solver": { "tolerance": 1e-12, "max_iterations": 200 }
```

and the run converges in **53 sweeps** to `165.0 / 162.5` exactly — the J1 anchor
values. `Joint Max Normalized Change` drops to `~8e-13`, `Joint Cycle Detected`
stays `0`.

**Where to see convergence.** In the config path, the four `Joint *` columns on
the summary frame (above). In the GUI, the per-market "Joint equilibrium" card —
*"Converged in 17 iterations"*, `Converged: Yes`, `Cycle detected: none`.

---

## 7. Investment inside a cycle

If a market in the cycle carries an **investment option** (a technology option
with an `investment_trigger`, under `endogenous_investment`), adoption is decided
*inside* the outer loop, against the **joint** price — not against a
single-market price.

Concretely: every outer sweep re-runs each market's investment-wrapped solve
against the current neighbour prices, and adoptions **accumulate as a floor** —
once an option adopts on some sweep, it stays adopted (capex is sunk;
irreversibility is physical). A price that later dips below the trigger does not
un-adopt it. The floor grows, then freezes, after which the outer loop is a pure
price contraction. The final adoption set is checked against the **converged**
joint price, never an intermediate sweep.

The shipped `joint_investment.json` example demonstrates an adoption decision
resolved jointly with the price loop. If a market's investment solve itself
fails to converge mid-loop, the run stamps `Joint Converged = 0` and surfaces the
inner reason rather than papering over it with outer damping.

The economics of adoption-as-outer-floor — the equilibrium concept, the
termination argument, the ex-post trigger checks — are in
[`docs/joint-equilibrium.md`](joint-equilibrium.md) §4.

---

## See also

- [`docs/joint-equilibrium.md`](joint-equilibrium.md) — the binding economic
  spec: the fixed-point object, existence/contraction, the cycle-detection
  predicate, investment nesting, and the J1–J6 anchors.
- [`docs/platform-spec-d0-d1.md`](platform-spec-d0-d1.md) — the underlying
  multi-market link (PriceLink) semantics: channels, `phi`, targeting.
- [`MANUAL.md`](../MANUAL.md) — launchers, the composer GUI walkthrough, and the
  full output-column reference.
