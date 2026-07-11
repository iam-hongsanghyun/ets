"""market_links feature (T2) — one-way price links between markets (D1).

Schema-only in this build (``docs/platform-plan-d0-d1.md`` D1-1): this
feature currently ships ONE door, ``plugin.py`` (field/structural validation
of ``links: [...]`` records, spec ``docs/platform-spec-d0-d1.md`` §2/§6). It
is the ONLY thing ``config_io`` may import from ``pe.features.market_links``
(the two-door plugin contract; ``config_io.markets.iter_market_bodies`` is
the caller). The runtime pieces named by the D1 plan —
``core.protocols.LinkChannel``, ``channels.py`` (per-channel application),
``engine/links.py`` (topological order + copy-on-write apply) — land in
D1-2/D1-3; nothing here solves or mutates a market yet.
"""
