"""market_links feature (T2) — one-way price links between markets (D1).

Two-door layout (``docs/feature-modules-plan.md`` PLAN v2). The config door
is ``plugin.py`` (field/structural validation of ``links: [...]`` records,
spec ``docs/platform-spec-d0-d1.md`` §2/§6) — the ONLY thing ``config_io``
may import from ``pe.features.market_links`` (``config_io.markets
.iter_market_bodies`` is the caller). The runtime door is ``channels.py``
(``MacCostChannel`` / ``InvestBreakEvenChannel``, the pure copy-on-write
``core.protocols.LinkChannel`` implementations, D1-2), wired EXCLUSIVELY by
the engine's ``LINK_CHANNELS`` registry (``engine/wiring.py``) and applied by
``engine/links.py`` (topological order + one copy-on-write pass, D1-3).

This ``__init__`` is deliberately import-free: importing ANY submodule of a
package always runs the package ``__init__.py`` first, so an eager
``channels`` import here would force-load the link RUNTIME whenever the
always-eager ``plugin`` door is read (``config_io``), breaking the
lazy-activation guarantee (a non-linked scenario must never import
``market_links.channels``). The engine imports the channel classes directly
from the ``channels`` submodule, function-locally.
"""
