# Floor-cancellation 2-cycle fix (D2 banking-cyclic prerequisite)

Authored by ets-lead-economist (design gate, 2026-07-11). Binds the executor
(banking-equilibrium-modeller). Companion: docs/joint-equilibrium.md §3 (the
binding separation). Blocks D2-5 (banking markets in cyclic SCCs).

## 1. The equilibrium object — a complementarity/boundary equilibrium (crisp,
closed-form); the current iteration MIS-FRAMES it as a search

Unlike the discrete-MAC cyclic SCC of joint-equilibrium.md §2 (genuine
ε-equilibrium / non-existence), the floor-cancellation equilibrium is
well-defined. It is the reserve-price complementarity, per year:

  0 ≤ (P_t − F_t) ⊥ u_t ≥ 0

— either the floor is SLACK (P_t > F_t, cancellation u_t = 0, full supply
sold) or it BINDS (P_t = F_t exactly, u_t = S_t − e_t(F_t) ≥ 0 cancelled).
This is the identical boundary the competitive kernel already solves
DIRECTLY without iterating (core/market/clearing.py:214-233:
demand_floor < offered ⇒ price = floor, sold = demand_floor).

Why the current code manufactures the 2-cycle:
FloorCancellationRule.apply_to_year (modules/price_controls/backend/rules.py
:100) tests `floor > solved_price` using the PREVIOUS iterate's price with a
STRICT inequality — a discontinuous proxy for "the floor binds," wrong
exactly at the equilibrium. Cancel supply → next solve prices AT F_t →
`F_t > F_t` flips False → cancellation withdrawn → base supply returns →
price collapses below floor → cancel again. Period-2 orbit; the supply gap =
the cancelled volume (~16.9 Mt). The true boundary point (S = e(F), P = F) is
a DISCONTINUITY of the current map, so the map cannot fix it — the map is
wrong, not the equilibrium.

## 2. The fix — ranked

**PRIMARY — direct complementarity solve (contemporaneous boundary test).**
Replace the discontinuous lagged predicate `floor > solved_price` with the
contemporaneous binding condition on fixed quantities: **the floor binds in
year t iff e_t(F_t) < S_t** (demand-at-floor below supply) — identically
equivalent to "the unconstrained price would fall below F_t" by monotonicity
of e_t(·), but with NO dependence on the oscillating previous-iterate price
and NO discontinuity. When it binds: cancel u_t = S_t − e_t(F_t), the year
contributes e_t(F_t) to circulating supply (price pinned to F_t); else no
cancellation. e_t(F_t) and base S_t are FIXED across schedule iterations, so
the schedule reaches its fixed point in ≤2 evaluations with zero oscillation,
landing on the §1 boundary equilibrium. This is clearing.py:214-233 imported
into the banking supply loop — PRESERVES THE MEANING (Rule A) exactly.

Binding refinement — **gate to static-regime years**. Cancellation applies
only to STATIC-regime years; window-regime years hold P_t ≥ F_t by
intertemporal arbitrage (auction clears fully, nothing unsold) and must NOT
cancel even when static demand-at-floor < base supply. The host computes the
window (a,b) immediately before the schedule step (solver.py:293 then :300);
pass `window` into `_supply_schedule`, cancel only for t outside [a,b]
(window None ⇒ all years static). Static-year cancellation depends only on
(S_t^base, F_t, e_t(F_t)) — all fixed — so the window↔cancellation coupling
is MONOTONE (a contraction, never an orbit).

**SECONDARY — cycle-detection guard (subordinate safety net).** Keep a
period-2 detector (‖S_k − S_{k−2}‖ vs ‖S_k − S_{k−1}‖) for any residual
multi-year window-boundary orbit the direct solve doesn't linearize; on
detection take the complementarity solution (P=F, u=base−e(F)), not an
arbitrary last iterate. A guard, not the mechanism.

**REJECTED as primary — damping the cancelled-volume delta.** A relaxed
u^{k+1}=(1−w)u^k + w·u_target lands on an INTERIOR supply whose clearing price
sits strictly between the low price and F_t — where the floor STILL binds, so
the correct cancellation there is FULL, not partial. The damped limit is NOT
on the complementarity set {P=F, u=full} ∪ {P>F, u=0} — it stops the
oscillation at a non-equilibrium. Damping is the right tool for a smooth
high-gain feedback (the D2 OUTER loop); wrong for a discontinuous
complementarity, which must be solved on its boundary, not averaged across
it. (This is the ad-hoc treatment TODO.md warns against.)

**Deferred (D3, optional).** Fold P_t ≥ F_t into solve_banking_window as an
explicit complementarity constraint, eliminating the outer floor iteration.
Cleaner but larger; not required for the D2 gate.

## 3. Golden impact — golden-inert; ships off current behaviour + a new anchor

**Verified: ZERO baseline scenarios pair model_approach:banking with
unsold_treatment:"cancel".** k_msr_paper_reproduction's banking scenarios
(P0,P1) carry no reserve/cancel; its cancel scenarios (A,B) are COMPETITIVE.
Every other cancel config is competitive (cancellation already direct via
clearing.py:214-233, untouched). The banking floor-cancellation loop is
reachable ONLY by banking+cancel+binding-floor, which no golden exercises.
**The fix is math-inert against all 39 goldens** (equivalence-verifier
confirms bit-identity via the non-binding path, V2) and ships against a NEW
anchor (V1), no recapture. BINDING on the executor: the e_t(F_t) < S_t test +
window gating must leave the competitive path and every non-binding banking
path byte-identical; ANY golden move means the change leaked beyond the
binding-floor+banking cell → rework before sign-off.

## 4. Anchors

Single participant, linear MAC slope σ, free-alloc 0, penalty high; residual
e(p) = E0 − p/σ, static clearing P(S) = σ(E0 − S); unsold_treatment "cancel".

| ID | Config | Current (undamped) | Correct (fix) | Tol |
|----|--------|--------------------|--------------|-----|
| V1 (binding, hand) | σ=1, E0=100, S⁰=90, F=30 → base P⁰=10<F binds; e(F)=70; unsold=20 | supplies 2-cycle 90↔70, prices 10↔30, max_iters WARNING + arbitrary iterate | ≤2 iters → P=F=30, sold=70, cancelled u=20, cum supply −20; banking_floor_cancelled=20 | price/vol atol 1e-6; iters ≤2 exact |
| V2 (non-binding inertness) | same, S⁰=50 → base P⁰=50>F=30 slack; e(F)=70≥50 | no cancel | P=50, cancelled=0 — bit-identical to current | exact (old==new) |
| V3 (window gating) | 2-yr: y1 static-oversupplied (binds per V1); y2 in-window arbitrage price>F | y2 would wrongly cancel under naive e(F)<S | cancel y1 ONLY; y2 clears in-window, u₂=0 | price atol 1e-6; y2 cancel==0 exact |
| V4 (boundary regression) | V1 with F=10 (= base price) | strict > edge | no cancel (P=F with u=0, complementary slackness) — stable | exact |

V1 is the captured NEW golden. V2 is the inertness witness.

### 4a. Window-clip refinement — economist-ratified deviation from §2 (2026-07-11)

The executor deviated from §2's literal "cancel only for t OUTSIDE [a,b]"
because the blanket static-only gate SUPPRESSES cancellation for a WINDOW
year whose delivered price is dragged DOWN to the floor by an in-window
release valve (MSR intake or investment adoption lowering demand). That
leaves unsold-at-floor volume unaccounted and breaks the V6 supply
partition sum_t e_t = B_0 + sum_t S_t − sum_t u_t − MSR_net − B_T by
22.5–28.8 Mt (two test_anchors.py::test_v6 cases). The ratified gate
(solver.py:270): STATIC years apply the price-free complementarity
e_t(F_t) < S_t UNCONDITIONALLY (kills the orbit); WINDOW years cancel ONLY
where the floor clips the arbitrage price (F_t > P_t). Economist verdict
(2026-07-11): CONFIRMED — window-clip cancellation is Rule A at the
delivered clip (D2 §3 delivered-floor family), nets the residual once
against the re-solved post-cancellation window budget, no double-count;
the identity is the correct waterbed partition with window-year u_t
included. Two standing conditions, both satisfied in the merge:
1. The subordinate period-2 guard (§2 SECONDARY) stays LIVE on the
   window-clip branch — it operates at the outer supply fixed point
   (solver.py:417) over both regimes; on detection it takes the
   complementarity solution (min circulating supply = P=F, u=base−e(F)),
   never an arbitrary iterate.
2. **Residual (D3, approximation NOT leak):** the window is solved
   UNCONSTRAINED at shadow prices then floor-CLIPPED, rather than solved
   with P_t ≥ F_t as an intertemporal boundary constraint (the §2
   "fold the floor into solve_banking_window" item). This is a modelling
   approximation, not a conservation violation — **V6 conservation pinned
   green is the standing witness that it is an approximation, not a leak.**
   Single-market property, unchanged by cycles, orthogonal to D2-5.

## 5. Relation to D2 — separate loops, this GATES D2-5

The inner fix lives INSIDE one market's supply-schedule fixed point
(solver.py:292-316) and makes a single banking market self-converge to its
boundary equilibrium — by DIRECT SOLVE, using NO relaxation, the sharpest
statement of the separation. The D2 outer loop (engine/joint.py) relaxes the
SCC PRICE VECTOR between whole-market solves; it never reaches inside
solve_banking_path. An outer w tuned to suppress residual inner oscillation
would conceal a single-market pathology present with ZERO links — forbidden.

**GATE (binding): D2-5 (wiring banking markets into cyclic SCCs) is BLOCKED
until this fix lands and V1 is green.** Until then D2 cyclic SCCs may contain
competitive markets (cancellation already direct) but not banking-with-cancel
markets. R37's WARNING is necessary but not sufficient — V1 green is the hard
gate.
