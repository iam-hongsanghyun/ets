# Nash-Cournot — Reference

## What this module implements

`pe.features.nash_cournot` (`modules/nash_cournot/backend/solver.py`,
`solve_nash_path`) replaces the competitive module's price-taking
assumption with strategic behaviour for a configurable subset of
participants: instead of every participant treating the carbon price as
given, `strategic_participants` internalise their own price impact along
the residual (inverse) demand curve. The equilibrium concept is a
Cournot-Nash equilibrium in net allowance positions `{d_i}`: no strategic
firm can lower its compliance cost by unilaterally changing its net
position, given the others' positions and the price-taking fringe's
response.

Each strategic firm `i` sets `MAC_i = P + d_i / S_-i`, where
`d_i = e0_i - a_i - F_i` is its net allowance demand and
`S_-i = sum_{j != i} 1/phi_j + b_fringe` is the residual-demand price-slope
it faces. The wedge `MAC_i - P = d_i / S_-i` is **signed by the firm's net
position** (Hahn 1984): a net SELLER (`d_i < 0`) under-abates to withhold
supply → Nash price *above* competitive (monopoly); a net BUYER (`d_i > 0`)
over-abates to withhold demand → Nash price *below* competitive
(monopsony). For a linear MAC the FOC closes as
`d_i*(P) = (phi_i g_i - P) / (phi_i + 1/S_-i)` (`phi_i`, `g_i = e0_i - F_i`
read analytically; a finite-difference linearisation is the non-linear
fallback).

**The reported equilibrium (the fix):** hold each strategic firm at its
Cournot position `d_i*(P)` and clear the residual for `P^Nash` via
`sum_i d_i*(P) + D_fringe(P) = Q` (monotone; geometric-bracket + Brent). The
all-price-taker `market.solve_equilibrium` is used ONLY for the competitive
starting point / loud fallback — never for the report (reporting the
competitive clear was the pre-fix defect that made Nash prices come out
bit-identical to competitive). Uniqueness requires an elastic residual for
every strategic firm (`S_-i > 0`: a fringe, or ≥ 2 strategic firms); a
single strategic firm facing a perfectly inelastic residual raises (JC4).

MSR: the injected duck-typed `MSRState` (never a CCR) applies its
`Q`-adjustment BEFORE the strategic clearing (strategic firms compete over
the MSR-adjusted `Q`), gated on `msr_enabled` / `msr_start_year` exactly as
the competitive path. CCR is deferred to v1.1. Banking / intertemporal
strategy is out of scope for v1 — the Nash path clears statically per year
and flags (never silently runs) a banking-enabled market. See
`examples/nash_cournot_strategic.json` for the hand-anchored net-seller
golden (`P^c = 7` vs `P^Nash = 9`).

## Reference papers

- Cournot, A. (1838). *Recherches sur les Principes Mathématiques de la
  Théorie des Richesses.* Paris: Hachette.

  The founding oligopoly-quantity-competition model this module's
  best-response iteration computes a numerical fixed point of: each
  strategic agent chooses a quantity (here, abatement, which maps
  one-to-one to net allowance demand) taking rivals' quantities as given,
  and the market price is the residual-demand function of the sum of all
  quantities. Cournot's original good is a homogeneous product; this
  module's "quantity" is abatement, with the allowance market's inverse
  demand curve playing Cournot's price function.

- Hahn, R.W. (1984). "Market Power and Transferable Property Rights."
  *Quarterly Journal of Economics*, 99(4), 753–765.

  The tradeable-permit-specific extension of Cournot competition this
  module operationalizes: Hahn shows that when permits are initially
  over-allocated to a dominant firm, that firm's strategic behaviour
  (restricting its own permit purchases, or over-holding sold permits) can
  move the equilibrium price and abatement pattern away from the
  cost-minimizing competitive outcome that Montgomery (1972) guarantees
  under price-taking — i.e. Montgomery's allocation-neutrality result
  (`modules/competitive/doc/reference.md`) does *not* survive strategic
  behaviour, which is exactly the gap this module exists to model. Hahn's
  result that the *initial allocation* of permits determines the direction
  and magnitude of the price distortion (not just who holds them) is the
  reason `strategic_participants` and `free_allocation_ratio` interact
  meaningfully here, unlike in the competitive module.
