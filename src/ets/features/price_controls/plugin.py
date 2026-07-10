r"""price_controls plugin door — trajectory arms and the delivered-floor overlay (T2).

Two-door feature (``docs/feature-modules-plan.md`` PLAN v2 §"Two-door
features"): this module is the ONLY thing ``config_io`` may import from
``ets.features.price_controls``. It carries the feature's config-facing
pieces (work order O10):

* ``apply_price_bound_trajectories`` — the ``price_floor_trajectory`` /
  ``price_ceiling_trajectory`` arms lifted verbatim from
  ``config_io/builder.py:build_market_from_year`` (the ``cap_trajectory``
  arm stays host: it is the cap's, not a price control's).
* ``DeliveredFloor`` — the ``core.protocols.PriceOverlay`` implementation of
  the reserve-price clip on delivered prices, lifted verbatim from the
  banking solver's epilogue (clip-LAST; F3).

The in-clearing floor branch (``core/market/clearing.py``) is NOT here and
never will be: with floor = 0 it is the oversupply boundary condition
P = 0, sold = e(0) of static clearing — an equilibrium concept the kernel
owns (PLAN v2 §3 REMAINDER; permanent property test
``tests/test_price_boundary_property.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ...core.market.model import CarbonMarket


def apply_price_bound_trajectories(
    year_num: float,
    meta: Mapping[str, Any],
    price_lower_bound: float | None,
    price_upper_bound: float | None,
    *,
    interp_value: Callable[[float, dict], float | None],
) -> tuple[float | None, float | None]:
    """Apply the scenario price-floor/ceiling trajectories to one year's bounds.

    Lifted verbatim from the builder's trajectory arm (O10): a configured
    trajectory OVERRIDES the per-year bound; an absent/disabled trajectory
    (``interp_value`` returns ``None``) leaves the per-year value untouched,
    so attaching this step to every scenario is exact.

    Algorithm:
        ASCII: F_t = interp(price_floor_trajectory, t)   if configured
               C_t = interp(price_ceiling_trajectory, t) if configured
               (linear interpolation between the trajectory's start/end
               year-value pairs, clamped at the endpoints — the host's
               ``_interp_value``)

        Symbols (units):
            F_t : year price_lower_bound override   [currency/tCO2]
            C_t : year price_upper_bound override   [currency/tCO2]
            t   : numeric year (e.g. 2031.0)        [calendar year]

    Declared fields (read): ``meta["price_floor_trajectory"]``,
    ``meta["price_ceiling_trajectory"]``. Writes: none (pure — returns the
    new bounds).

    Args:
        year_num: Numeric year used by trajectory interpolation.
        meta: Scenario-level config mapping (read-only).
        price_lower_bound: The year's configured lower bound
            [currency/tCO2], or ``None``.
        price_upper_bound: The year's configured upper bound
            [currency/tCO2], or ``None``.
        interp_value: The HOST's trajectory interpolator (kept host-owned so
            trajectory semantics are defined exactly once;
            ``config_io/builder.py:_interp_value``).

    Returns:
        ``(price_lower_bound, price_upper_bound)`` with any configured
        trajectory overrides applied.
    """
    floor_override = interp_value(year_num, meta.get("price_floor_trajectory") or {})
    ceiling_override = interp_value(year_num, meta.get("price_ceiling_trajectory") or {})
    if floor_override is not None:
        price_lower_bound = floor_override
    if ceiling_override is not None:
        price_upper_bound = ceiling_override
    return price_lower_bound, price_upper_bound


class DeliveredFloor:
    r"""Reserve-price clip on delivered prices (``core.protocols.PriceOverlay``).

    Lifted verbatim from the banking solver's epilogue (work order O10): the
    solved path is clipped to each year's ``auction_reserve_price`` ONCE,
    LAST — after the fixed point has converged, never inside it (the
    in-window shadow price may sit below the floor; what the floor pins is
    the DELIVERED auction price). Clip-last is the same operation-order
    doctrine as the λ overlay's blend-then-clip (F3,
    ``docs/forward-transmission.md``).

    Algorithm:
        LaTeX:
        $$ P_t^{\mathrm{delivered}} = \max\big(P_t,\; F_t\big) $$

        ASCII fallback:
            delivered = max(price, auction_reserve_price or 0)

        Symbols (units):
            P_t : solved price of year t                   [currency/tCO2]
            F_t : the year's auction reserve price; 0 unset [currency/tCO2]

    Attach-always is EXACT: with no floor configured the overlay computes
    ``max(p, 0.0) = p`` for every solved price ``p >= 0`` (Arbitration
    outcomes, O10), so unconfigured scenarios are bit-identical with or
    without the overlay.
    """

    def delivered(self, price: float, market: CarbonMarket) -> float:
        """Clip the solved price to the year's auction reserve price.

        Args:
            price: Solved price after price formation [currency/tCO2].
            market: The year's market (``auction_reserve_price``).

        Returns:
            Delivered price ``max(price, floor)`` [currency/tCO2].
        """
        return max(price, float(getattr(market, "auction_reserve_price", 0.0) or 0.0))
