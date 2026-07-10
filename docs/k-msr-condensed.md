# Leading Carbon Prices to an Irreversible Industrial Transition — condensed

*Compressed working-paper version. Same argument, numbers, and caveats as the
full draft; repetition, over-hedging, and decorative formalism removed.*

## Abstract

Korea's carbon price sits far below the level that makes heavy-industry
decarbonization bankable, and the investments that matter — hydrogen steel
(H₂-DRI) and electrified naphtha cracking (e-NCC) — are decided this decade,
before the price signal arrives. Can a market stability reserve (K-MSR) raise
the price enough, and credibly enough, to trigger them? Using a
partial-equilibrium model of the K-ETS (2026–2040), we show three things. (1) A
reserve that absorbs and later releases allowances cannot move the price level
(the waterbed theorem); only permanent cancellation can — but Korea's cancellable
stock (~155 Mt, 0.31 cap-years) is too small to lead, closing only ~26% of the
required 2035 price rise. The leading instrument must therefore act on the
auction *flow*. (2) A pre-announced **auction reserve price** guarantees a floor
that is enforced at the primary market and so is immune to Korea's weak forward
transmission (λ ≈ 0), whereas a quantity rule works only through secondary-market
anticipation that low λ erodes. (3) A credible floor lowers the Dixit–Pindyck
irreversibility hurdle from ~3.86× to ~1.83× break-even — not to 1 — so the floor
schedule must escalate somewhat above bare break-even. The policy implication is
a specific rule: an escalating, pre-announced, automatically executed auction
reserve price, with unsold volume cancelled and keyed to the circulating surplus.

## 1. The gap

At 2026 input prices the H₂-DRI break-even is ~210,000 KRW/tCO₂ and e-NCC ~280,000;
the KAU trades near 24,000–30,000. On the government's input-cost path the steel
threshold falls to ~97,500 by 2035 — still ~4× today's price, and under no new
policy the KAU reaches only ~67,500 by 2040. The investment decisions precede the
price, and the market barely prices the future. That is the problem.

## 2. Model

Annual partial equilibrium, six sectors, 2026–2040. A marginal-abatement-cost
(MAC) curve stacks sector-by-technology options; the steel and petrochemical
thresholds are endogenous to input prices (θ_steel = φ + 30·H, θ_NCC = φ + 2.9·E).
Banking is solved under no-arbitrage (discounted price constant while the bank is
positive). Forward transmission is a coefficient λ ∈ [0,1] weighting the
inter-temporal (Hotelling) price against the static clearing price; from KRX data
the realized forward carry is ~0%/yr against a 5.5% benchmark, i.e. λ ≈ 0. We
compare four scenarios: **P0** (no reserve), **P1** (draft decree: absorb, then
release 20 Mt/yr, no cancellation), **A** (reserve price rising 22,750 → 97,500 by
2035, unsold cancelled), **B** (quantity rule: cancel from 2035).

## 3. Result 1 — the waterbed and the scale wall

Under P1 the price adds ~1,300 KRW by 2030, then falls 18% in 2031 as the release
activates, and rejoins the no-policy path exactly by 2040 (both 67,461). Absorb-
and-release moves *when* allowances arrive, not *how many* exist, so it cannot
shift the level. Only cancellation can — but the cancellable stock is ~155 Mt
(0.31 cap-years). Re-solving for cancellations of 16–155 Mt, retiring the full
stock raises the 2035 price by ~11,200 KRW, just 26% of the ~43,000 required. The
constraint is scale, not diminishing returns: scarcity cannot lead. The leading
instrument must reach the auction flow year on year.

## 4. Result 2 — why a price floor beats a quantity rule under low λ

Separate three claims a reserve "guarantees the price" conflates.

- **Auction price (mechanical).** Bids below the reserve price cannot clear, so any
  year with cleared volume satisfies P ≥ F_t — independent of banking, liquidity,
  or λ. This is why the reserve price is the recommended instrument.
- **Spot price (conditional).** The floor reaches the secondary market either once
  compliance demand at the floor exceeds the bank (not until the 2030s, given the
  bank grows to 114 Mt before drawing down) or via a standing buyback-and-cancel
  facility (immediate, at fiscal cost).
- **Investment (credibility).** A guaranteed price is not a guaranteed investment;
  that turns on the floor's credibility over the asset's life (Result 3).

The robust, policy-relevant statement is the narrow one: a primary-market floor
delivers a λ-independent *lower bound* on the price and hence on activation dates,
which a quantity commitment working through anticipation cannot. Re-solving A
under three λ regimes leaves the delivered path and both activation dates
(H₂-DRI 2035, e-NCC 2039) identical from 2030; only the counterfactual lift over
no-policy varies. A quantity rule enjoys no such immunity — its early price is
anticipation that evaporates as λ falls, exactly when the steel investment must be
financed. This adds a dimension Weitzman's cost-curvature criterion omits: in a
weak-transmission market, enforcement point matters.

## 5. Result 3 — the floor and the irreversibility hurdle

Under irreversibility a firm invests not at break-even P_NPV but at
[β/(β−1)]·P_NPV, with the multiple rising in volatility σ: 3.86× at σ=0.30, ~6.4×
at the observed σ≈0.48. On its face this is fatal — the firm waits for ~2.7×97,500
≈ 260,000 KRW, so a floor topping out at break-even is short by a factor of ~3.

The answer is credibility. The multiple is large partly because the future price
is uncertain; a credible floor removes the lower-tail uncertainty in the binding
region, cutting the multiple toward r/y ≈ 1.83× — more than half the excess, but
not to 1. The residual 1.83× is a pure timing wedge (the price drifts up at r−y,
so deferring a sunk outlay still pays). A quantity rule raises the mean but leaves
the lower tail intact, so it earns none of this reduction. Two honest corollaries:
break-even activation is not quite optimal even under full credibility, and the
schedule should escalate somewhat above break-even so the scheduled price reaches
the investor's trigger on time. Credibility — not the price level alone — is the
binding constraint.

## 6. Policy rule and robustness

The reserve should be an **escalating, pre-announced, automatically executed
auction reserve price, with unsold volume cancelled in full and keyed to the total
circulating surplus**, plus a published surplus indicator. Supporting points: the
cancellation base must be the surplus (reached via the auction), not the small
EU-style auctioned share, and the rate should be 100%. A price anchor avoids the
green-paradox exposure of stock-triggered quantity rules; indexed to the input-
price-driven thresholds, it also tracks permanent cost shifts a fixed quantity
cannot. Of nine quantity-rule variants, only pre-announced full-cancellation
absorption reaches the thresholds, and it fails the cost-sensitivity test.

## 7. Limits (stated plainly)

The model is deterministic; uncertainty enters only through the Dixit–Pindyck
step. λ is a reduced-form weight, not identified structurally — the paper's main
open problem — and λ ≈ 0 is inferred from ~0 forward carry, which is also
consistent with rational pricing of flat expectations. The waterbed result uses
perfect-foresight banking, in some tension with the low-λ (hoarding) premise. The
firm's investment is post-processing on an exogenous price path, not a two-way
equilibrium, and the A-path enforces the floor as a period-by-period lower bound
without solving the fixed point with its own cancellation feedback. The e-NCC
threshold moves only as far as the regulated KEPCO tariff is allowed to reflect
cost, so that transition is jointly governed by K-ETS and tariff policy. The
priority extension is the investment decision as optimal stopping against a
partially credible, escalating price barrier.
