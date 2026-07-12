# Nash-Cournot strategic equilibrium — spec

Authored by ets-lead-economist (design gate, 2026-07-12). Fixes the degenerate
Nash-Cournot approach (TODO.md): the solver runs a best-response iteration over
strategic abatements, then `market.solve_equilibrium(...)` overwrites it with an
all-price-taker competitive clear — so Nash prices come out bit-identical to
competitive. **The defect is a REPORTING bug, not an iteration bug.**

## 1. The strategic FOC

Allowance market. Participant $i$ chooses abatement $a_i$; net allowance demand
$d_i = e_{0,i} - a_i - F_i$ ($d_i>0$ buyer, $<0$ seller). Market clears
$\sum_i d_i = Q$ (auction supply). $\mathrm{MAC}_i = C_i'(a_i)$.

- **Fringe (price-taker):** minimizes $C_i(a_i)+P d_i$ ⇒ $\mathrm{MAC}_i = P$.
- **Strategic:** internalizes its price impact along the inverse residual demand
  $P(d_i)$ (clearing $d_i + D_{-i}(P) = Q$):

$$ \mathrm{MAC}_i = P + d_i\cdot\frac{\partial P}{\partial d_i}, \qquad \frac{\partial P}{\partial d_i} = \frac{1}{S_{-i}}>0,\quad S_{-i} = \sum_{j\neq i}\Big|\frac{\partial d_j}{\partial P}\Big| = \sum_{j\neq i}\frac1{\varphi_j} + b_{\text{fringe}}. $$

Linear MAC ($\mathrm{MAC}_i=\varphi_i a_i$, $d_i^{\text{PT}}(P)=g_i-P/\varphi_i$,
$g_i=e_{0,i}-F_i$): strategic demand
$d_i^\ast = \frac{\varphi_i g_i - P}{\varphi_i + 1/S_{-i}}$ (vs price-taker
$\frac{\varphi_i g_i - P}{\varphi_i}$) — the larger denominator **damps the net
position toward zero** (withholds trade).

**[JC1 — the central call] The markup is SIGNED by the strategic firm's NET
POSITION (Hahn 1984), not automatically "higher":**
- **Net SELLER ($d_i<0$): $\mathrm{MAC}_i < P$** — under-abates to withhold supply
  ⇒ **monopoly ⇒ Nash price ABOVE competitive.**
- **Net BUYER ($d_i>0$): $\mathrm{MAC}_i > P$** — over-abates to withhold demand
  ⇒ **monopsony ⇒ Nash price BELOW competitive.**

Magnitude: wedge $\mathrm{MAC}_i-P = d_i/S_{-i}$ — net position × residual-inverse
slope. Fringe grows ($S_{-i}\to\infty$) ⇒ wedge $\to 0$, Nash $\to$ competitive.

**[JC2]** Compute $\partial P/\partial d_i = 1/S_{-i}$ **analytically** for linear
MACs (exact); keep the codebase's finite-difference $dP/dQ$ as the general fallback
for nonlinear MACs.

## 2. The reported equilibrium — the fix

Clear on the **strategic best responses**: fringe at $\mathrm{MAC}=P$, each
strategic firm at $\mathrm{MAC}_i = P + d_i/S_{-i}$, simultaneously. Fixed point
$(d_1^\ast,\dots,d_k^\ast)$; $P^{\text{Nash}}$ clears
$\sum_i d_i^\ast + D_{\text{fringe}}(P) = Q$.

**Existence/uniqueness:** linear net-demand ($\varphi_i>0$) + positive residual
slope ($S_{-i}>0$ for every strategic firm) ⇒ unique (standard linear Cournot;
best-response slopes sum to <1, diagonally dominant). **[JC4]** Guard $S_{-i}=0$
(single strategic firm + perfectly inelastic residual = infinite price impact,
ill-posed): require an elastic residual (a fringe, or ≥2 strategic firms).

**The existing Jacobi best-response loop converges to the correct strategic
profile — it is NOT the bug.** **[JC5] THE FIX:** after convergence to
$\{d_i^\ast\}$, hold the strategic firms FIXED at their strategic quantities and
clear the residual — solve $D_{\text{fringe}}(P) = Q - \sum_i d_i^\ast$ for
$P^{\text{Nash}}$ (Brent on the fringe), report $P^{\text{Nash}}$, strategic firms
at $(a_i^\ast, d_i^\ast)$ with $\mathrm{MAC}_i = P^{\text{Nash}} + d_i^\ast/S_{-i}$,
fringe at its price-taking response. **Do NOT call `market.solve_equilibrium`** —
that re-optimizes everyone as price-takers (the discard that makes Nash ==
competitive). **[JC3]** Keep Jacobi (order-independent); optional relaxation
damping via `core/relaxation.py` if near-dominant strategic firms oscillate.

## 3. Hand-anchored 2-genco example (the Nash anchor)

2 symmetric strategic firms ($\varphi_s=1$, $e_{0,s}=10$, $F_s=17$ ⇒ $g_s=-7$,
**net sellers** / over-allocated incumbents); fringe $D_f(P)=35-P$ ($b_f=1$);
auction $Q=0$. $S_{-i}=b_f+1/\varphi_s=2$ ⇒ $\partial P/\partial d_i=1/2$;
$d_i^\ast=\tfrac23(g_s-P)$.

- **Competitive:** $(35-P)+2(-7-P)=0 \Rightarrow 21-3P=0 \Rightarrow \boxed{P^{c}=7}$;
  each strategic sells 14, MAC$_s=7=P$.
- **Nash:** $(35-P)+2\cdot\tfrac23(-7-P)=0 \Rightarrow 77-7P=0 \Rightarrow \boxed{P^{\text{Nash}}=11}$;
  each strategic sells **12** (<14, restricts supply), MAC$_s=11+(-12)/2=\mathbf 5 < P$.

**Markup +57% (11 vs 7)**, driven by net position ($|d_i|=12$) × residual slope
(0.5). The golden pins $P^{\text{Nash}}=11 \neq P^{c}=7$ — a genuinely strategic
price. **Ship the SELLER anchor as the headline "higher-than-competitive" golden;
note in the description that a net-BUYER config yields $P^{\text{Nash}}<P^{c}$
(monopsony)** — the direction is not universal.

## 4. Mechanism composition (the F2 gaps)

- **MSR — IN SCOPE, gate consistently.** MSR adjusts auction $Q$ from the lagged
  bank (supply-side, orthogonal to conduct). Apply the MSR $Q$-adjustment BEFORE
  the strategic clearing; strategic firms compete over the MSR-adjusted $Q$. Gate
  on the same `msr_enabled` flag as competitive (fixes the "ungated in the nash
  path" defect).
- **CCR — COMPOSABLE, defer to v1.1** (same $Q$-adjust-pre-clearing mechanism;
  land MSR first, document the deferral).
- **Free allocation / OBA — AUTOMATIC, in scope.** They set $g_i=e_{0,i}-F_i$,
  which the strategic FOC already reads — and allocation **signs the markup**
  (over-allocation → seller → price up; under → buyer → price down). No new code;
  flag in the description.
- **Reserve-price floor — clip-last** (delivered-floor AFTER strategic clearing).
- **Banking / intertemporal — OUT OF SCOPE (v1).** Strategic banking across
  periods is a distinct, harder object; Nash here is single-period strategic
  clearing. Flag explicitly; do not silently run banking under Nash.

## 5. Golden impact

The fix MOVES all Nash-labelled behavior (currently == competitive). No existing
example/baseline uses `model_approach:"nash_cournot"` with strategic participants
(deliberately not added while degenerate). So the fix is **golden-inert against
the existing library** and ships against a NEW golden (the §3 anchor: $P^c=7$ vs
$P^{\text{Nash}}=11$) — the first baseline to exercise a distinct strategic price.
Retire the "Nash output overstates the equilibrium" docs/UI caveat once merged.

**Build:** the modeller codes the strategic clearing into `_solve_nash_year`
(report Cournot, not competitive), adds the §3 golden, and gates MSR into the Nash
path. Bounded, hand-anchored, golden-inert against the current library.
