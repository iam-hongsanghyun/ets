# Binding specification: Phase 2 (D0+D1) — general PE platform

Authored by ets-lead-economist (design gate, 2026-07-11). Binds the D0/D1
architecture (docs/platform-plan-d0-d1.md). Sign-off additionally requires
equivalence-verifier green on anchors A1–A6 and the inertness obligations.

## 1. D0 reinterpretation validity (per mechanism)

- **penalty_price is an obligation-EXTINGUISHING buyout, not the EU fine.**
  compliance.py:105-117 settles shortage via `penalty_emissions`
  (extinguishes the obligation); clearing brackets at max penalty ×
  multiplier. That is exactly the RPS Alternative Compliance Payment and
  the NZ ITQ deemed value. Validity condition: the market's non-compliance
  instrument must be an obligation-extinguishing per-unit charge. Where
  enforcement is injunctive (most water abstraction, nutrient permits):
  prohibitive buyout + a diagnostic assertion that penalty_emissions ≡ 0.
  Rename to `buyout_price` is semantically overdue (alias, §5).
- **Banking at carry g = r+ρ**: valid for perpetual, costless-to-store,
  vintage-homogeneous certificates. NAMED GAP G-D0-1: banking lifetime
  (REC 3-5yr validity, water carryover caps, ITQ ~10% carry) — future
  vintage-tracked bank with expiry T and carryover cap κ; do NOT fake with
  hoarding_inflow (opposite friction).
- **No-borrowing (Rubin)** is the banking-approach default; static path
  already supports borrowing_allowed/limit (NZ deemed-value maps natively).
  Rubin-with-borrowing = separate future work order, new equilibrium object.
- **MSR/CCR family confirmed general** (RGGI CCR / CA APCR are the same
  family but PRICE-triggered at the contemporaneous auction — implement via
  the FloorRule dedicated-slot semantics, not lagged Observables; needs its
  own worked anchor when built). Water allocation-vs-storage rules: supply
  rules on an exogenous observable, trivially in-family.
- **Hotelling**: valid iff exhaustible stock (carbon budgets, groundwater
  MINING); invalid for flow-supplied markets (RECs, annual TAC).
- **Investment trigger**: broadest validity (any irreversible lumpy
  capacity, payoff monotone in permit price). Per-market obligation:
  justify payout_yield y; never defaulted.
- **NAMED GAP G-D0-2**: trading ratios between participant classes
  (nutrient 2:1, biodiversity like-for-like) — a units wedge WITHIN one
  market; not a D1 link. Deferred.

Validity table summary: RPS/RECs — buyout EXACT, investment canonical,
banking partial (lifetime); water — buyout partial, Hotelling valid for
groundwater mining, elastic baseline valid; ITQ — deemed value EXACT via
borrowing_limit (static); nutrient — mostly blocked by G-D0-2.

**Showcase verdict: RPS/REC buyout market first** — exercises static
clearing, buyout bit-for-bit, banking within-lifetime, investment trigger
(renewable entry), optional OBA-style output-indexed obligation, zero new
code; pre-stages the D1 link showcase.

## 2. D1 link semantics — the PriceLink object

- **(a) Additive linear ONLY in v1**: x_B(t) = x_B_base(t) + φ·P_A(t),
  φ ∈ ℝ sign-free, units [units_B per units_A]. Exactly the K-MSR pattern
  θ_steel = φ + 30·H. NO link_function selector (a defaulted functional
  form is an economic constant in a fallback). Rejected: multiplicative/
  CES, capped pass-through (policy instrument in disguise), lag functions.
- **(b) Channels ranked**: v1 = (1) mac_cost — additive on
  mac_blocks[*].marginal_cost and the threshold MAC level; the linear
  cost_slope is DIMENSIONALLY EXCLUDED (units [currency/t per Mt]) and the
  unit check must reject it mechanically; (2) invest_break_even — compiles
  scalar θ base to {year: base + φ·P_A(t)}; closes the K-MSR
  input-price-endogenous threshold loop. TRAPS (v2): baseline requirement
  (fourth writer to the pinned sector→trajectory→OBA chain), penalty level
  (moves the clearing bracket). FORBIDDEN permanently: elastic-baseline
  P_ref (changes the meaning of ε — a different demand system).
- **(c) Timing: contemporaneous, BINDING, not configurable.** Topological
  order makes P_A(t) known data when B solves; a lag toggle would change
  the information structure (same doctrine as Phase 1's non-configurable
  price signal). Do not confuse with SupplyRule lagged observables — that
  lag resolves within-market simultaneity which does not exist across a
  one-way link.
- **(d) Placement/composition**: link application is an ENGINE-TIER step —
  after the full build pipeline, BEFORE the path solver, applied ONCE
  (never inside any fixed point — F4 purity), copy-on-write. Order:
  link-apply → adoption outer loop → inner path solve. Banking verified
  compatible (year-varying MACs are native). Events: B's segments re-read
  the same solved P_A; A resolves completely first.
- **(e) Units**: every linked market declares price_unit; every link
  declares its coefficient unit; pint dimensional check AT THE CONFIG/
  VALIDATOR TIER ONLY (stripped to floats before the kernel; solver stays
  float; goldens untouched). Missing declarations on a linked market =
  ERROR (silent dimensionless fallback is an economic constant hiding in a
  default). Unlinked markets need no declarations.

## 3. DAG equilibrium concept

**Recursive (block-recursive) partial equilibrium**: for topological order
m1..mK, the solution is (E1..EK) where Ek is market k's OWN approach
equilibrium with link-target inputs evaluated at solved ancestor paths as
exogenous parameters. Downstream never feeds back; each market's ceteris
paribus set = its non-ancestors. Maintained assumption (document wherever
a link exists): B is atomistic in A. Where that fails, D1 is a first-order
approximation and the diagnostics must quantify the ignored feedback; the
joint fixed point is D2.

Validator: **R34** link graph must be a DAG (self-links rejected);
**R35** demand-side whitelist only (mac_cost targets + invest_break_even;
ALL supply-side targets forbidden — a price-indexed supply instrument is a
SupplyRule inside its own market's fixed point, never a link; duplicate
(source,target,field) rejected; multiple distinct sources sum
order-invariantly); **R36** unit declarations per 2(e).

Diagnostics: per-link per-year guarded summary columns "Link <A→B> Price
In" / "Link <A→B> Input Shift" (key-presence-guarded, never attach-always);
one solve-time WARNING per link stating the recursive-PE reading; optional
back_demand_estimate ψ → "Feedback Ignored (A units)" column (diagnostic
only, NEVER fed back). Solve topological; REPORT in declaration order.

## 4. Invariants and anchors

I1 per-market conservation unchanged with links on. I2 links are
demand-side information, never supply creation (config-diff check against
the R35 whitelist). I3 upstream invariance: A bit-identical with/without
outgoing links. I4 φ=0 and links-absent inertness. I5 unit discipline at
every boundary. I6 multi-source summation commutativity.

MASTER ANCHOR PATTERN: link-compiled config ≡ hand-edited config,
bit-identically, for every channel.

| ID | Anchor | Tolerance |
|---|---|---|
| A1 | Two-market linear chain hand-solved (P_A = σ_A(E0−Q_A); P_B = c_B + φ·P_A), competitive AND banking variants | price atol 1e-6; budget 1e-3 Mt |
| A2 | φ=0 == unlinked exact; all existing goldens bit-identical with links absent | exact |
| A3 | Declaration-order invariance | exact |
| A4 | K-MSR θ_steel: hydrogen market, φ=30 kgH2/tCO2 → compiled break_even == hand-entered mapping; run bit-identical; adoption year identical | exact |
| A5 | Units mismatch / missing declaration / cost_slope target → validator ERROR | raises |
| A6 | Upstream invariance (I3) | exact |

## 5. D0 naming (verdicts)

`permit` (alias allowance — Montgomery/Rubin/Schennach conventions) ·
`baseline_requirement` (alias initial_emissions; rejected gross_demand,
obligation) · `self_supply` (alias abatement — survives RECs where the
action CREATES certificates) · `buyout_price` (alias penalty_price — makes
the code honest, §1). flow_label/flow_unit/price_unit are presentation/
validation-tier; the kernel never branches on them. **Old spellings remain
the canonical keys in normalized output** (golden discipline); neutral
names are accepted input aliases from D0; flipping canonical spelling is a
separate 0.4.0 migration with golden regeneration under
equivalence-verifier.

## 6. Parameters (all defaults inert)

PriceLink: source_market, target_market (REQUIRED) · channel ∈ {mac_cost,
invest_break_even} (REQUIRED, no default) · target_participants (explicit,
no implicit all) · target_technologies (REQUIRED for mac_cost) · phi
(REQUIRED, sign-free, 0 legal) · phi_unit (REQUIRED) ·
back_demand_estimate (None, diagnostic only). Market: price_unit REQUIRED
iff linked; flow_label/flow_unit default absent = today's carbon labels.
Graph: links: [] default. Inertness obligation: links absent + no aliases
→ zero solver code paths change, all goldens bit-identical.

Carried gaps: G-D0-1 banking lifetime/vintages; G-D0-2 trading ratios;
Rubin-with-borrowing.

## 7. Arbitration outcomes (binding, economist PROCEED 2026-07-11)

- **E2 domain taxonomy — THREE tiers, not two**: `general` (any administered
  flow) / `carbon` (any carbon market) / `kets` (Korea pack). cbam + scope-2
  params → `carbon` (used by generic examples; `kets` misclassifies;
  `trade` rejected — CBAM is F6 post-clearing reporting, no price edge).
  kmsr_decree BLOCK → `kets` (the feature stays engine-general; the block
  carries the tag). K-* examples: derived block tags are the DEFAULT, PLUS
  an optional per-example `domain` override for calibration-defined
  membership — seed it for k_msr_P0_no_reserve, k_msr_A_reserve_price,
  k_msr_lambda_regimes, k_ets_hoarding_basic, k_ets_lambda_msr (general
  blocks, Korean calibration). No filename inference.
- **E4 investment × links — per-market wrapping CONFIRMED exact** (block-
  triangular: both v1 channels write downstream only; back_demand_estimate
  never fed back; sequential per-market trigger-consistent equilibria =
  the chain equilibrium by induction; D1.4 termination applies verbatim per
  market at cost Σ(Ni+1)). PINS: (1) a link reads the upstream market's
  FINAL converged delivered path, never an intermediate iterate; (2) links
  compile into the target's markets AND its AdoptionSpecs BEFORE spec
  gathering, so both the InvestmentRule factory and the independent ex-post
  checker read the link-shifted θ_B(t).
- **E7 events × multi-market — deferral SIGNED OFF.** Error text names D2 and
  the natural first relaxation: events permitted only on SINK markets (no
  outgoing links) — there the existing splice machinery is already correct.
- **E8 horizon alignment — STRICT SUBSET**: ERROR unless label-set(B) ⊆
  label-set(A) per link L(A→B) (A may carry extra years; every target year
  must exist in the source's solved path). Rejected all partial-overlap
  fillers (hold-last = hidden random walk; zero-shift = spurious boundary
  cliff at the trigger; interpolation = an unstated intra-gap price
  process). Precedent: D2.1 missing-year ValueError. Error suggests adding
  the missing years to the source.
- **Schema names**: phi/phi_unit govern (φ mirrors the paper — single-letter
  equation convention); market-level price_unit required iff linked, kept
  distinct from flow_unit; channel keys mac_cost/invest_break_even;
  from_market/to_market endpoint spelling is the architect's choice.
- **E6 diagnostic columns (golden-pinned, ASCII arrows, channel-qualified)**:
  `Link {from}->{to} Price In` (per (from,to) pair, deduped) ·
  `Link {from}->{to} {channel} Input Shift` (channel key verbatim — two
  links on one pair with different channels must not collide) ·
  `Link {from}->{to} Feedback Ignored` (only when back_demand_estimate
  declared; source-market quantity units documented in MANUAL, not the
  column name). All key-presence-guarded, multi-market scenarios only.

## 8. E1b — RPS/REC showcase calibration (stylized, not a jurisdiction repro)

One obligated aggregate retailer; flow_label "REC", flow_unit "TWh",
price_unit "USD/MWh" (revenue columns read as $M since $1/MWh ≡ $1M/TWh);
years 2026-2030 (inside REC lifetime; G-D0-1 non-binding). Obligation =
RPS%×500 TWh = 50/70/90/120/150. auction_offered 0 (OTC clearing at net
demand 0). Self-supply blocks: B1 60 TWh @ 8, B2 50 @ 22; offshore B3 40 @
38 as the flagged option, θ=40 flat, trigger_mode break_even, L=0; buyout
(ACP) 45. Anchors:
1. ACP-binding: pre-adoption prices [8, 22, 22, 45, 45]; buyout binds 2029
   (obligation 120 crosses capacity-below-ACP 110); assert P=buyout,
   settlement 10 TWh (atol 1e-6).
2. Buyout-triggers-entry: first θ=40 crossing 2029 → τ=2029; final path
   [8, 22, 22, 38, 38] (2029's 38<40 exercises the D1.1 ex-post-regret INFO
   path); D-P variant σ=0.3 y=0.03 r=0.055 ⇒ M≈3.86 P*≈154 > path sup ⇒
   never adopts, == B3-deleted config exactly (V3 semantics).
3. Banking variant: the 22→45 jump violates no-arbitrage at g=0.055 ⇒ a
   window forms; assert in-window carry P_{t+1}/P_t = 1.055 (rtol 1e-9),
   cumulative self-supply identity to 1e-3 TWh, and the discrete-MAC
   terminal-bank WARNING. Golden ships with the hand-derivation note.
