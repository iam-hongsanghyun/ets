r"""price_controls runtime — the floor-cancellation supply rule (T2, engine/host-facing).

Runtime door of the two-door feature (``docs/feature-modules-plan.md`` PLAN
v2): imported by the banking host (transitionally; the wiring literal moves
to ``engine/wiring.py`` in the engine order), never by ``config_io``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.market.clearing import total_net_demand

if TYPE_CHECKING:
    from ...core.market.model import CarbonMarket


def _free_allocation_total(market: CarbonMarket) -> float:
    """Total free allocation of a year [Mt CO2e] (as in the banking host)."""
    return float(sum(p.free_allocation for p in market.participants))


class FloorCancellationRule:
    r"""Rule A: cancel auction volume unsold at the reserve-price floor.

    Lifted VERBATIM from the floor-cancellation block of
    ``solvers/banking.py:_supply_schedule`` (work order O10). Where the floor
    exceeds the year's solved price, the auction sells only the demand at the
    floor; the unsold volume is REMOVED from circulating supply when
    ``unsold_treatment == "cancel"`` — the K-MSR paper's Rule A, the one
    floor design that defeats the waterbed under banking
    (``docs/blocks-composition-rules.md`` §1 Cancellation row).

    Algorithm:
        LaTeX:
        $$ u_t = \max\!\big(0,\; S_t - e_t(F_t)\big)
           \quad\text{if } F_t > P_t^{(k)} \text{ and cancel},\qquad
           S_t' = S_t - u_t $$

        ASCII fallback:
            if floor > solved_price and unsold_treatment == "cancel":
                unsold = max(0, supply - demand_at(floor)); supply -= unsold

        Symbols (units):
            F_t      : year's auction_reserve_price          [currency/tCO2]
            P_t^(k)  : year t price from the PREVIOUS fixed-point iterate
                                                             [currency/tCO2]
            e_t(p)   : residual emissions at price p (net auction demand
                       plus free allocation)                 [Mt CO2e]
            S_t      : circulating supply entering the slot (already
                       MSR-adjusted)                         [Mt CO2e]
            u_t      : cancelled unsold volume               [Mt CO2e]

    CONTRACT (explicit, deliberately NOT ``core.protocols.SupplyRule`` —
    economist verdict 1c on PLAN v2): this rule reads the CONTEMPORANEOUS
    year's solved price from the previous fixed-point iterate and composes
    on the post-MSR replacement supply — an inner-loop lagged read, not the
    year-lagged ``Observables`` a ``SupplyRule`` is limited to. Forcing it
    into that protocol would either fake a lagged observable or invite the
    reordering the composition rules forbid. Instead the banking host calls
    it from a DEDICATED slot, in its fixed position:

    * inside the supply-schedule fixed point (F4) — cancellation feeds back
      into the window budget;
    * AFTER the injected MSR supply rules, on the MSR-adjusted supply
      (MSR-then-floor, ``docs/blocks-composition-rules.md`` §2 item 3);
    * per year, receiving ``(market, solved_price, supply)`` and returning
      the replacement supply plus the cancelled volume.

    The rule is stateless across years; the host still constructs it fresh
    per schedule evaluation (via a factory slot) so the lifecycle is uniform
    with the ``SupplyRule`` family (``ets.core.protocols`` doctrine).

    The demand-at-floor call is the same expression as the banking host's
    ``_residual_emissions`` (net auction demand at a pinned price plus free
    allocation), computed here from kernel primitives so the feature imports
    only ``ets.core`` (tier contract).
    """

    def apply_to_year(
        self, market: CarbonMarket, solved_price: float, supply: float
    ) -> tuple[float, float]:
        """Cancel the volume unsold at the floor, if the floor binds.

        Args:
            market: The year's market (``auction_reserve_price``,
                ``unsold_treatment``, demand-side fields).
            solved_price: The year's price from the previous fixed-point
                iterate [currency/tCO2].
            supply: The year's circulating supply entering this slot
                (already MSR-adjusted) [Mt CO2e].

        Returns:
            ``(supply, cancelled)`` — the replacement circulating supply
            after cancellation and the cancelled volume [Mt CO2e]
            (``(supply, 0.0)`` unchanged when the floor does not bind or
            ``unsold_treatment != "cancel"``).
        """
        floor = float(getattr(market, "auction_reserve_price", 0.0) or 0.0)
        if floor > solved_price and market.unsold_treatment == "cancel":
            demand_at_floor = total_net_demand(market, floor) + _free_allocation_total(market)
            unsold = max(0.0, supply - demand_at_floor)
            return supply - unsold, unsold
        return supply, 0.0
