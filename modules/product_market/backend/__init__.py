"""product_market feature (T2) — a goods market clearing on a demand curve (D3).

The steel↔carbon flagship's product-market feature (``docs/multi-commodity-plan.md``
§1/§6 D3-3, ``docs/multi-commodity-spec.md`` §1/§6/§7). Two-door layout
(``docs/feature-modules-plan.md`` PLAN v2 §"Two-door features"):

* config door — ``plugin.py`` (``normalize_product_body``): the ONLY thing
  ``config_io`` may import from ``pe.features.product_market``. It validates
  and normalises a ``model_approach: "product"`` market body (product demand,
  import supply, the exogenous ``carbon_price``, and the ``kind: "producer"``
  participants). Imports stdlib only.
* runtime door — ``solver.py`` (``solve_product_path``): builds the three
  injected clearing curves from the normalised body and calls the T0 primitive
  ``pe.core.market.product_clearing.solve_product_equilibrium``. Wired
  EXCLUSIVELY by the engine (``engine/wiring.py:solve_product_path``, routed by
  ``engine/dispatch.py``'s one ``"product"`` branch); imports ``pe.core.*``
  only.

This ``__init__`` is deliberately import-free — importing any submodule runs
the package ``__init__`` first, so an eager ``solver`` import here would
force-load the product RUNTIME whenever the ``plugin`` door is read
(``config_io``), breaking lazy activation (a carbon-only scenario must never
import ``product_market.solver``). The engine imports the solver directly from
the ``solver`` submodule, function-locally.
"""
