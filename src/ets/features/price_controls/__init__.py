"""price_controls feature (T2) — floor/ceiling trajectories, floor-cancellation, delivered floor.

Two-door layout (``docs/feature-modules-plan.md`` PLAN v2): ``plugin.py`` is
the config door (price-bound trajectory arms + the ``DeliveredFloor`` price
overlay); ``rules.py`` is runtime (``FloorCancellationRule``, evaluated inside
the banking fixed point by the host's dedicated slot). The in-clearing floor
branch of ``core/market/clearing.py`` deliberately STAYS KERNEL — it is the
oversupply boundary condition of static clearing, not a policy instrument
(PLAN v2 §3 REMAINDER; Arbitration outcomes item 6).
"""
