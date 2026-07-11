# D2 architecture: the joint equilibrium model (cyclic PriceLinks)

Authored by lead-modeller. Layered on docs/platform-plan-d0-d1.md and
docs/platform-spec-d0-d1.md. Binding economic spec pending:
docs/joint-equilibrium.md (economist, V-D2-1..8). Does NOT block D0/D1;
lands the moment D1 merges.

D2 removes D1's DAG restriction: a backlink makes the vector of all market
price paths a genuine joint fixed point, solved by an OUTER fixed-point
iteration over the strongly-connected components (SCCs) of the market
graph. Reuses D1's apply_links + per-approach _path_solver_for closures
UNTOUCHED inside the loop; every single-market and one-way config takes
the byte-identical D0/D1 path (the golden gate proves it — no number moves
until a scenario draws a cycle).

## 1. Solve structure — SCC condensation + outer loop

- `engine/scc.py` (new, T3, pure/stdlib): Tarjan over the market digraph
  (edge A→B iff a link carries A's signal into B); returns SCCs +
  topologically-ordered condensation DAG. Deterministic tie-break:
  declared market order, then market_id.
- Size-1 SCC, no self-edge → solved exactly as D1 (byte-identical).
- Cyclic SCC (size ≥ 2) → `engine/joint.py:solve_joint_scc` outer loop:
  the coupling-loop Gauss-Seidel + relaxation pattern lifted to a
  price-PATH vector over the SCC's markets.
  - Initial guess: D1 one-way seed (forward links normal, back-links via
    D1 back_demand_estimate) — warm start, ~halves outer iterations
    [V-D2-1].
  - One outer iteration = one Gauss-Seidel sweep (deterministic order,
    each market reads most-recent delivered paths of already-swept SCC
    siblings) [V-D2-2 GS vs Jacobi].
  - Relaxation on prices AFTER each sweep: P_next = (1-w)P_guess +
    w·P_swept (core/relaxation.py). w<1 damps; w=1 undamped.
  - Convergence: max over SCC markets of a PER-MARKET normalized change
    (markets can differ in flow_unit — a bare max|ΔP| in mixed units is
    meaningless) [V-D2-3].

## 2. Nesting (economist to bless)

OUTER = SCC price fixed point (D2, cyclic SCCs only) · MIDDLE = per-market
investment adoption loop (Phase 1, untouched) · INNER = approach solve
(banking window / competitive PF, untouched).

LOAD-BEARING: a backlink breaks D1's block-triangular separability —
inside a cyclic SCC, A's adoption depends on B. Recommendation: MIDDLE
nests INSIDE OUTER for cyclic SCCs (each sweep re-runs each market's
investment-wrapped solve against current neighbor prices); acyclic SCCs
stay exactly D1. Sub-question [V-D2-4]: adoption-as-outer-floor
(recommended — reuse the splice-carrier FLOOR + monotone-one-flip host
check; kills discrete-flip oscillation, bounds iterations, keeps
irreversibility honest) vs re-derive-fresh (cleaner ex-ante concept, but
reintroduces flips as an oscillation source). This changes the
equilibrium concept — economist's call.

## 3. Termination & damping (tied to the known finding)

- Relaxation is the primary damping (economist sets contraction theory
  [V-D2-5/6]); architecture exposes relaxation ∈ (0,1] per SCC, damped
  default.
- Hard cap → WARNING → last iterate stamped `Joint Converged = 0.0`
  (banking/investment/coupling precedent). A non-converged SCC is NEVER
  reported as an equilibrium.
- Cycle detection: track ‖P_k − P_{k-2}‖ alongside ‖P_k − P_{k-1}‖; report
  `Joint Cycle Detected = <period>` (oscillating ≠ slowly crawling — a
  different remedy: more damping vs more iterations).
- SEPARATION from TODO.md:91: the floor-cancellation 2-cycle lives INSIDE
  one market's banking supply-rule fixed point, BELOW D2's outer loop. D2
  relaxation acts on the SCC price vector BETWEEN market solves; it does
  NOT damp the inner 2-cycle. The single-market floor-cancellation damping
  is a sibling prerequisite, economist-designed, tracked separately — D2
  must not paper over an inner pathology with outer relaxation.
- Reported (guarded, cyclic-SCC markets only): Joint Converged, Joint
  Outer Iterations, Joint Max Normalized Change, Joint Cycle Detected.

## 4. Config & validator delta (minimal)

`links[]` UNCHANGED (a backlink is just an edge D1 rejected). Delta:
- R34 REPLACED: cycles LEGAL; a cyclic SCC must resolve outer-loop
  settings. New text asserts settings-resolvable, not acyclic.
- New optional scenario `joint_solver` block (the ONLY schema addition):
  {relaxation, atol/tolerance, max_iterations, sweep, initial_guess}, all
  defaulted; not emitted unless a cycle is present → single-market/D1
  configs byte-identical.
- New R37: cyclic SCC with relaxation=1.0 + banking/discrete-adoption →
  WARNING (the floor-cancellation lesson generalized).
- Self-link stays forbidden (R36 unchanged) — self-feedback is intra-market
  demand response, already the elastic-baseline overlay [V-D2-7].
- R35 unchanged; mixed-unit convergence norm enforced at solve time.

## 5. Engine placement

`engine/scc.py` (Tarjan), `engine/joint.py` (outer loop; imports
core.relaxation, engine.links, the per-market solver closure; never T4
coupling), `core/relaxation.py` (D2-1: lift coupling's _relax/
_max_price_change to T0, pure; coupling switches to it with zero
behaviour change). `dispatch.py` grows ONE guarded branch: all SCCs size 1
→ D1 path unchanged; any cyclic → joint path. Four `Joint *` columns
stamped only on cyclic-SCC markets (key-presence guard).

## 6. Work orders (layered on D1)

D2-0 economist spec (blocking) · D2-1 core/relaxation lift (S) · D2-2
scc.py + joint.py outer loop (L) · D2-3 dispatch cyclic branch + R34
flip/R37 + joint_solver (M, G-full) · D2-4 blocks cycles-legal +
round-trip (M) · D2-5 investment-inside-cyclic-SCC per V-D2-4 (M, G-full)
· D2-6 two goldens: converging hand-verifiable 2-market SCC + deliberately
oscillating (damping recovers; at w=1 the non-convergence + cycle-detected
flags fire) (S-M, G-full) · D2-7 frontend back-edges + joint settings +
non-convergence banner (L) · D2-8 MCP cycles-legal-with-settings +
convergence reporting (M) · D2-9 docs (S). D2-1 lands the moment D1
merges; D2-0 gates D2-2/3/5.

## 7. Risks

Non-convergence is the headline (mitigation = economist-designed damping,
NOT an ad-hoc weight; architecture guarantees the REPORTING discipline,
not convergence). Runtime: outer × middle × inner nesting — banking-cyclic
SCC is the worst case; bound max_iterations, runtime WARNING on cost
budget, keep D2-6 goldens small/non-banking [V-D2-8]. Investment-in-cycle
(§2) is the load-bearing economic call. Mixed-unit norm (§1). Determinism
(SCC + sweep order fully deterministic or numbers go env-dependent —
ULP-amplification lesson). Deferred to D3: convergence acceleration
(Aitken/Anderson), SCC-parallel Jacobi, multi-commodity agents, pint
through solve, auto damping selection.

## Pending economist verdicts

V-D2-1 seed · V-D2-2 sweep scheme · V-D2-3 mixed-unit convergence norm ·
V-D2-4 investment nesting + adoption monotonicity (the load-bearing call)
· V-D2-5 default relaxation/schedule · V-D2-6 existence/uniqueness/
contraction + inner-non-convergence handling · V-D2-7 self-link ·
V-D2-8 banking-cyclic outer cap.
