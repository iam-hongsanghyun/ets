"""Data-only block catalogue: every block in ``docs/blocks-graph-plan.md`` §1.

Each :class:`~ets.blocks.registry.BlockSpec`'s ``ParamSpec.config_key``\\ s are
verified against ``ets.config_io`` (``normalize_scenario``/``normalize_year``/
``normalize_participant``, defaults from ``templates.blank_*``) —
``tests/test_blocks_catalogue.py`` asserts every scenario/year/participant
scope config_key actually appears in the corresponding normalised blank
document, so this file can never silently drift from the engine.

Deliberately omitted from the palette:

* ``compare_all`` (price-formation "all" branch) — plan §1 calls this out as
  a comparison action, not a drawable block.
* ``international_offset_cost/limit/band`` — "known-inert" config keys per
  ``docs/blocks-graph-plan.md`` (read by no code in ``src/``).
* A dedicated ``oba`` config-owning param — ``production_output`` and
  ``benchmark_emission_intensity`` already live on the ``participant`` block
  (they are participant-scope fields in ``config_io``); the ``oba`` block
  below is a documentation/validation marker with no ParamSpecs of its own,
  so it cannot collide with the participant's own fields.

Dependency law: this module imports only :mod:`ets.blocks.registry` and
stdlib.
"""

from __future__ import annotations

from .registry import BlockRegistry, BlockSpec, ParamSpec, PortSpec

# ── shared enums (mirrors config_io / solvers, duplicated here only as
#    strings so this module never imports solvers/config_io at runtime) ────
_ABATEMENT_TYPES = ("linear", "threshold", "piecewise")
_MODEL_APPROACHES = ("competitive", "hotelling", "banking", "nash_cournot", "all")
_MSR_MODES = ("bank_threshold", "price_band", "surplus_rule", "hybrid")
_EXPECTATION_RULES = ("myopic", "next_year_baseline", "perfect_foresight", "manual")
_UNSOLD_TREATMENTS = ("reserve", "cancel", "carry_forward")
_AUCTION_MODES = ("explicit", "derive_from_cap")
# Mirrors modules/market_links/backend/plugin.py:ALLOWED_LINK_CHANNELS —
# duplicated here only as strings, per this module's own dependency law (see
# module docstring). D1 shipped ``mac_cost``/``invest_break_even`` (spec §2b);
# D3-4/D3-7 add the two steel↔carbon shared-agent coupling channels
# (``carbon_input_price``/``output_ref_price``, docs/multi-commodity-spec.md §7):
# they stamp the sibling PRICE onto the shared producer (not a MAC shift, not a
# quantity). Golden-inert: no existing graph uses the two new keys, so widening
# the enum leaves every committed scenario byte-identical.
_LINK_CHANNELS = ("mac_cost", "invest_break_even", "carbon_input_price", "output_ref_price")
# The product-market OBA design lever (spec §7 ruling #4): ``output_based`` is
# the cap-RELAXING marginal φ·q allocation, ``fixed_cap`` the distributional
# design. Mirrors modules/product_market/backend/plugin.py:_ALLOWED_OBA_MODES.
_PRODUCT_OBA_MODES = ("output_based", "fixed_cap")
# Mirrors config_io/builder.py:_JOINT_SOLVER_ALLOWED_SWEEPS / _..._ALLOWED_SEEDS
# (D2 joint-equilibrium schema, docs/joint-equilibrium-plan.md §4) — duplicated
# here only as strings, per this module's dependency law. config_io is the
# single source of truth for the runtime DEFAULTS; the joint_solver block below
# declares NONE of them (every param defaults to None ⇒ "user did not set this"
# ⇒ config_io.normalize_joint_solver fills its own default), so a bare dropped
# node compiles to an empty joint_solver block that normalizes exactly as the
# engine would — no joint-solver default is ever hardcoded here.
_JOINT_SWEEP_SCHEMES = ("gauss_seidel",)
_JOINT_INITIAL_GUESSES = ("one_way_seed", "cold")

# ── generic per-price-formation scenario fields ─────────────────────────
# These scenario-level keys are ALWAYS present in a normalised scenario dict
# regardless of model_approach (config_io/builder.py:normalize_scenario), so
# every price-formation BlockSpec declares them — whichever single
# price-formation block a market uses is the guaranteed home for them.
_COMMON_PRICE_FORMATION_PARAMS = (
    ParamSpec("discount_rate", "discount_rate", "scenario", "float", 0.04, unit="1/yr"),
    ParamSpec("risk_premium", "risk_premium", "scenario", "float", 0.0, unit="1/yr"),
    ParamSpec(
        "solver_penalty_price_multiplier",
        "solver_penalty_price_multiplier",
        "scenario",
        "float",
        1.25,
    ),
    ParamSpec(
        "solver_price_bracket_expand_factor",
        "solver_price_bracket_expand_factor",
        "scenario",
        "float",
        2.0,
    ),
    ParamSpec(
        "solver_price_bracket_max_expansions",
        "solver_price_bracket_max_expansions",
        "scenario",
        "int",
        10,
    ),
    ParamSpec("solver_slsqp_max_iters", "solver_slsqp_max_iters", "scenario", "int", 400),
    ParamSpec("solver_slsqp_ftol", "solver_slsqp_ftol", "scenario", "float", 1e-9),
    ParamSpec(
        "solver_calibration_xatol", "solver_calibration_xatol", "scenario", "float", 0.1
    ),
    ParamSpec(
        "solver_calibration_fatol", "solver_calibration_fatol", "scenario", "float", 0.01
    ),
)

_PRICE_FORMATION_OUT_PORT = PortSpec("price_formation", "out", "price_formation")

# Every policy/expectations block carries an optional ``announced`` year
# label (plan §1 "Policy timing"): when later than the market's first year it
# routes the block's changes through a ``policy_events[]`` entry instead of
# the base config. The value always lands in the scenario-level
# ``policy_events`` list, so config_key points there regardless of which
# block declares it.
_ANNOUNCED_PARAM = ParamSpec(
    "announced", "policy_events", "scenario", "str", "", label="Announced year"
)

_POLICY_OUT_PORT = PortSpec("policy", "out", "policy")


def _market_block() -> BlockSpec:
    return BlockSpec(
        id="carbon_market",
        label="Carbon Market",
        category="market",
        doc=(
            "One node = one scenario in {'scenarios': [...]} "
            "(config_io/builder.py:build_market_from_year)."
        ),
        feature="core",
        params=(
            ParamSpec("name", "name", "scenario", "str", "New Scenario"),
            ParamSpec(
                "years",
                "years",
                "scenario",
                "list",
                default=(),
                label="Per-year grid (year, total_cap, auction_mode, "
                "auction_offered, reserved_allowances, carbon_budget, "
                "banking_allowed, borrowing_allowed, borrowing_limit)",
            ),
            # Opaque pass-through escape hatches — used by decompile.py so a
            # round-tripped graph never loses information that structurally
            # belongs to the market rather than to any one policy block.
            ParamSpec(
                "sectors", "sectors", "scenario", "list", default=(),
                label="Sector pool table (raw pass-through; sector nodes "
                "are the graph-authoring alternative)",
            ),
            ParamSpec(
                "policy_events", "policy_events", "scenario", "list", default=(),
                label="Policy-event timeline (raw pass-through)",
            ),
            # D1 graph disentanglement (docs/platform-plan-d0-d1.md D1 "GRAPH
            # DISENTANGLEMENT"; spec §6). price_unit is REQUIRED iff this
            # market participates in a link; absent = "today's carbon labels"
            # (D1 COMPAT RULE, no injected default, byte-identical for every
            # existing example).
            ParamSpec(
                "price_unit", "price_unit", "scenario", "str", None,
                label="Price unit (REQUIRED iff this market is linked)",
            ),
            # scope="edge": compile.py-only bookkeeping that selects the
            # wrapping scenario's "name" for a >1-market linked component.
            # Must agree across a linked component; defaults to the
            # order-first market's "name" (compile.py:_compile_linked_scenario).
            ParamSpec(
                "scenario_name", "scenario_name", "edge", "str", None,
                label="Linked-scenario display name (multi-market only; "
                "must agree across the component)",
            ),
            # D0-R2 flow vocabulary (spec §5, display only — the kernel never
            # branches on either key). Default None (absent), NOT
            # "carbon"/"tCO2e": config_io writes these only when the raw
            # config carries them (D1 COMPAT RULE, byte-identical to today).
            # Display callers fall back to "carbon"/"tCO2e" when absent.
            ParamSpec(
                "flow_label", "flow_label", "scenario", "str", None,
                label="Flow label (display only; falls back to 'carbon' when absent)",
            ),
            ParamSpec(
                "flow_unit", "flow_unit", "scenario", "str", None,
                label="Flow unit (display only; falls back to 'tCO2e' when absent)",
            ),
        ),
        ports=(
            PortSpec("participants", "in", "compliance", cardinality="1..n"),
            PortSpec("sectors", "in", "sector_pool", cardinality="0..n"),
            PortSpec("price_formation", "in", "price_formation", cardinality="1"),
            PortSpec("policies", "in", "policy", cardinality="0..n"),
            PortSpec("expectations", "in", "expectations", cardinality="0..1"),
            PortSpec("baseline", "in", "baseline", cardinality="0..1"),
            PortSpec("results", "out", "results"),
            # D1 market links (docs/platform-spec-d0-d1.md §2): "signal" is
            # this market's SOLVED delivered price, read by a market_link's
            # "from" port; "links" receives inbound market_link edges — a
            # market may have 0..n inbound links (spec §3 "multiple distinct
            # sources sum order-invariantly"). A market_link edge on either
            # port is what makes this carbon_market node join a >1-market
            # connected component at compile time (compile.py
            # _connected_components) — a market with NEITHER port connected
            # compiles exactly as today (component of size one).
            PortSpec("signal", "out", "market_signal"),
            PortSpec("links", "in", "market_link", cardinality="0..n"),
            # D2 joint-equilibrium (docs/joint-equilibrium-plan.md §4): an
            # optional ``joint_solver`` node attaches to ANY one market of a
            # cyclic (joint fixed-point) component through this port — it
            # configures the whole component's outer loop, not this market
            # alone (compile.py:_compile_joint_solver reads it once per
            # component). Absent for every single-market / acyclic graph, so a
            # graph without a joint_solver node compiles byte-identically to
            # today. Mirrors how a policy/baseline metadata block attaches to a
            # market via a dedicated in-port.
            PortSpec("joint_solver", "in", "joint_solver", cardinality="0..1"),
            # D3-7 producer_ref (docs/multi-commodity-spec.md §6/§7 V-D3-3): a
            # carbon market may READ its emitters from a sibling product market's
            # producers rather than authoring its own ``participant`` nodes — the
            # shared-agent coupling (a producer contributes e_i to Σe=Cap here and
            # q_i to Σq+M=D on the product side). A ``product_market``'s
            # ``producer_ref`` out-port feeds this in-port; compile.py then stamps
            # ``producer_ref: {market: <product id>}`` on this carbon body
            # (config_io resolves the per-year emitter view). 0..1: at most one
            # product market supplies a carbon market's emitters. Golden-inert: no
            # committed carbon graph draws this edge, so a carbon market WITHOUT it
            # compiles byte-identically to today.
            PortSpec("producer_ref", "in", "producer_ref", cardinality="0..1"),
        ),
    )


def _product_market_block() -> BlockSpec:
    r"""The multi-commodity product market (steel↔carbon, docs/multi-commodity-spec.md).

    A goods market that clears on a behavioural demand curve against optimising
    producer supply (``Σ q_i(P_s, P_c) + M(P_s) = D(P_s)``) — distinct in KIND
    from a ``carbon_market`` (which clears a compliance-obligation flow). It is
    NOT a price-formation variant: the ``"product"`` model_approach is selected
    structurally by the node's own block id, so it declares no price-formation
    port and carries NO competitive/banking scenario keys.

    Every param is ``scope="edge"``: a product body is normalised by
    ``config_io``'s dedicated ``normalize_product_body`` (NOT ``normalize_
    scenario``), so these config_keys never appear in ``normalize_scenario(blank_
    scenario())`` — ``compile.py`` reads them directly into a ``model_approach:
    "product"`` body rather than through the scope-driven ``_merge_block_params``
    machinery, and the catalogue drift-guard exempts ``edge`` scope by design.
    """
    return BlockSpec(
        id="product_market",
        label="Product Market",
        category="market",
        doc=(
            "One node = one product (goods) market body "
            "(config_io/builder.py:_build_product_market_from_year); clears "
            "Σ q_i(P_s, P_c) + M(P_s) = D(P_s) on a demand curve "
            "(features/product_market/solver.py:solve_product_path)."
        ),
        feature="product_market",
        params=(
            ParamSpec("name", "name", "edge", "str", "New Product Market", label="Market id"),
            # Exogenous P_c at which the market is solvable STANDALONE (D3-3); a
            # steel↔carbon link replaces it with the coupled carbon price (D3-4).
            ParamSpec(
                "carbon_price", "carbon_price", "edge", "float", 0.0,
                unit="currency/tCO2", label="Exogenous carbon price P_c (standalone)",
            ),
            # The behavioural demand curve (spec §1 [JC1]): linear
            # {form, intercept (A_d), slope (b_d)} closed-form anchor, or
            # {form: "isoelastic", kappa, eta} numeric option.
            ParamSpec(
                "product_demand", "product_demand", "edge", "dict", default={},
                label="Demand curve {form: linear|isoelastic, intercept/slope or kappa/eta}",
            ),
            # Carbon-free elastic imports M = world_price(M_0) + slope(m)·P_s, with
            # an optional price-active CBAM sub-dict {enabled, coverage, sigma_foreign}.
            ParamSpec(
                "import_supply", "import_supply", "edge", "dict", default={},
                label="Import supply {world_price, slope, sigma_foreign, cbam:{enabled, coverage}}",
            ),
            ParamSpec(
                "oba_mode", "oba_mode", "edge", "enum", "output_based",
                enum=_PRODUCT_OBA_MODES,
                label="OBA design (output_based=cap-relaxing φ·q vs fixed_cap)",
            ),
            ParamSpec(
                "years", "years", "edge", "list", default=(),
                label="Per-year grid (year labels; producers attach via the "
                "'producers' port and broadcast across every year)",
            ),
            # D1 link vocabulary (spec §2e/§6): REQUIRED iff this market joins a
            # steel↔carbon link; absent = unlinked standalone product market.
            ParamSpec(
                "price_unit", "price_unit", "edge", "str", None,
                label="Price unit (REQUIRED iff this market is linked)",
            ),
            ParamSpec(
                "scenario_name", "scenario_name", "edge", "str", None,
                label="Linked-scenario display name (multi-market only; "
                "must agree across the component)",
            ),
            ParamSpec("flow_label", "flow_label", "edge", "str", None, label="Flow label (display)"),
            ParamSpec("flow_unit", "flow_unit", "edge", "str", None, label="Flow unit (display)"),
        ),
        ports=(
            PortSpec("producers", "in", "producer", cardinality="1..n"),
            # producer_ref -> a carbon_market's producer_ref in-port: the shared
            # producers ALSO emit into the linked carbon market (spec §6).
            PortSpec("producer_ref", "out", "producer_ref"),
            PortSpec("results", "out", "results"),
            # The steel↔carbon coupling rides the same market_link idiom as carbon
            # markets: 'signal' is this market's SOLVED delivered price, 'links'
            # receives inbound market_link edges — a link on either makes this node
            # join a >1-market joint component (compile._connected_components).
            PortSpec("signal", "out", "market_signal"),
            PortSpec("links", "in", "market_link", cardinality="0..n"),
            PortSpec("joint_solver", "in", "joint_solver", cardinality="0..1"),
        ),
    )


def _producer_block() -> BlockSpec:
    r"""The two-margin multi-commodity producer (steel firm, spec §2).

    Chooses output ``q_i`` AND intensity abatement ``a_i`` to maximise profit;
    ``a_i^* = clip(P_c/β, 0, a_max)`` (intensity margin) and
    ``q_i^*(P_s, P_c)`` (output margin) are its two FOCs. Authored on the
    product-market side (attaches to a ``product_market``'s ``producers`` port);
    the sibling carbon market reads the same producers through a ``producer_ref``.

    Every param is ``scope="edge"``: a producer is validated by
    ``normalize_product_body._normalize_producer`` (mapping to
    :class:`pe.core.participant.producer.ProducerParams`), not by
    ``normalize_participant``; ``compile.py`` reads these directly into a
    product-body ``participants[]`` entry.
    """
    return BlockSpec(
        id="producer",
        label="Producer",
        category="participants",
        doc="core/participant/producer.py:MultiCommodityProducer via normalize_product_body._normalize_producer",
        feature="product_market",
        params=(
            ParamSpec("name", "name", "edge", "str", "New Producer"),
            # Quadratic production cost γ q + ½ δ q² ⇒ MC = γ + δ q (δ > 0 REQUIRED,
            # spec §2 [JC3]); the config-door normaliser rejects δ ≤ 0 / β ≤ 0.
            ParamSpec(
                "output_cost", "output_cost", "edge", "dict", default={},
                label="Output cost {gamma (γ), delta (δ > 0)}",
            ),
            ParamSpec(
                "intensity", "intensity", "edge", "float", 0.0,
                unit="tCO2/t", label="Baseline emission intensity σ",
            ),
            ParamSpec(
                "abatement", "abatement", "edge", "dict", default={},
                label="Intensity abatement {beta (β > 0), a_max}",
            ),
            ParamSpec(
                "oba_benchmark", "oba_benchmark", "edge", "float", 0.0,
                unit="tCO2/t", label="OBA benchmark φ (marginal output subsidy P_c·φ)",
            ),
            ParamSpec(
                "F_lump", "F_lump", "edge", "float", 0.0,
                unit="tCO2/yr", label="Lump-sum free allocation (infra-marginal transfer)",
            ),
            ParamSpec(
                "capacity", "capacity", "edge", "float", None, label="Output capacity (optional)",
            ),
            # Cleaner-tech options (spec §4g): each drops σ→σ' once P_c crosses the
            # Dixit-Pindyck trigger P* = M·θ (trigger_mode ∈ {break_even, option_value}).
            ParamSpec(
                "technology_options", "technology_options", "edge", "list", default=(),
                label="Clean-tech options [{name, sigma_prime, theta, trigger_mode}]",
            ),
        ),
        ports=(PortSpec("product", "out", "producer"),),
    )


def _market_link_block() -> BlockSpec:
    return BlockSpec(
        id="market_link",
        label="Market Link",
        category="links",
        doc=(
            "One-way price link A -> B (docs/platform-spec-d0-d1.md §2); "
            "compiles into the linked scenario's 'links' array "
            "(core/backend/blocks/compile.py:_compile_links)."
        ),
        feature="market_links",
        params=(
            # REQUIRED, no default (spec §6: "a defaulted functional form/
            # channel is an economic constant hiding in a fallback").
            ParamSpec(
                "channel", "channel", "edge", "enum", None, enum=_LINK_CHANNELS,
                label="Channel (demand-side only)",
            ),
            ParamSpec(
                "phi", "phi", "edge", "float", None,
                label="phi — link coefficient (sign-free, 0 legal)",
            ),
            ParamSpec(
                "phi_unit", "phi_unit", "edge", "str", None,
                label="phi unit [units_B per units_A] (REQUIRED)",
            ),
            ParamSpec(
                "target_participants", "target_participants", "edge", "list", default=(),
                label="Target participants (explicit names, or ['*'] for all — "
                "no implicit 'all')",
            ),
            ParamSpec(
                "target_technologies", "target_technologies", "edge", "list", default=(),
                label="Target technologies (REQUIRED for channel=mac_cost)",
            ),
            ParamSpec(
                "back_demand_estimate", "back_demand_estimate", "edge", "float", None,
                label="psi — diagnostic-only feedback estimate, never fed back",
            ),
        ),
        ports=(
            PortSpec("from", "in", "market_signal", cardinality="1"),
            PortSpec("link", "out", "market_link"),
        ),
    )


def _joint_solver_block() -> BlockSpec:
    return BlockSpec(
        id="joint_solver",
        label="Joint Solver",
        category="links",
        doc=(
            "Outer-loop settings for a cyclic (joint fixed-point) market SCC "
            "(engine/joint.py:solve_joint_scc); compiles into the linked "
            "scenario's optional 'joint_solver' block "
            "(config_io/builder.py:normalize_joint_solver via "
            "core/backend/blocks/compile.py:_compile_joint_solver)."
        ),
        feature="market_links",
        params=(
            # Every config_key matches a normalize_joint_solver normalized key
            # EXACTLY (plan §4). Every default is None — "the user did not set
            # this" — NOT the engine's runtime default: config_io owns those
            # (see _JOINT_SWEEP_SCHEMES comment above). compile.py emits only
            # the keys the user actually set; the block appears at all only when
            # the user drops a joint_solver node, so a graph WITHOUT one stays
            # byte-identical to today (the D1 COMPAT RULE).
            ParamSpec(
                "relaxation", "relaxation", "edge", "float", None, bounds=(0.0, 1.0),
                label="w — relaxation weight in (0, 1]; < 1 damps (config_io default 0.5)",
            ),
            ParamSpec(
                "tolerance", "tolerance", "edge", "float", None,
                label="Per-market convergence tolerance (config_io accepts 'atol' "
                "as an alias; default 1e-4)",
            ),
            ParamSpec(
                "max_iterations", "max_iterations", "edge", "int", None,
                label="Outer-sweep cap (config_io default 50)",
            ),
            ParamSpec(
                "sweep", "sweep", "edge", "enum", None, enum=_JOINT_SWEEP_SCHEMES,
                label="Sweep scheme (Gauss-Seidel only in v1; Jacobi is D3)",
            ),
            ParamSpec(
                "initial_guess", "initial_guess", "edge", "enum", None,
                enum=_JOINT_INITIAL_GUESSES,
                label="Warm-start seed (config_io default one_way_seed)",
            ),
        ),
        ports=(PortSpec("joint_solver", "out", "joint_solver"),),
    )


def _price_formation_blocks() -> tuple[BlockSpec, ...]:
    competitive = BlockSpec(
        id="competitive_clearing",
        label="Competitive Clearing",
        category="price_formation",
        doc="features/competitive/solver.py:solve_scenario_path, core/market/clearing.py:solve_equilibrium",
        feature="competitive",
        params=(
            ParamSpec(
                "model_approach", "model_approach", "scenario", "enum",
                "competitive", enum=_MODEL_APPROACHES,
            ),
            ParamSpec(
                "solver_competitive_max_iters", "solver_competitive_max_iters",
                "scenario", "int", 25,
            ),
            ParamSpec(
                "solver_competitive_tolerance", "solver_competitive_tolerance",
                "scenario", "float", 0.001,
            ),
            *_COMMON_PRICE_FORMATION_PARAMS,
        ),
        ports=(_PRICE_FORMATION_OUT_PORT,),
    )
    banking = BlockSpec(
        id="rubin_schennach_banking",
        label="Rubin/Schennach Banking Equilibrium",
        category="price_formation",
        doc="features/banking/solver.py:solve_banking_path",
        feature="banking",
        params=(
            ParamSpec(
                "model_approach", "model_approach", "scenario", "enum",
                "banking", enum=_MODEL_APPROACHES,
            ),
            ParamSpec("banking_initial_bank", "banking_initial_bank", "scenario", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("banking_strict_no_arbitrage", "banking_strict_no_arbitrage", "scenario", "bool", True),
            ParamSpec("banking_bank_tolerance", "banking_bank_tolerance", "scenario", "float", 1e-6),
            ParamSpec("banking_supply_rule_max_iters", "banking_supply_rule_max_iters", "scenario", "int", 25),
            ParamSpec("banking_supply_rule_tolerance", "banking_supply_rule_tolerance", "scenario", "float", 0.001),
            *_COMMON_PRICE_FORMATION_PARAMS,
        ),
        ports=(_PRICE_FORMATION_OUT_PORT,),
    )
    hotelling = BlockSpec(
        id="hotelling",
        label="Hotelling Exhaustible-Resource Path",
        category="price_formation",
        doc="features/hotelling/solver.py:solve_hotelling_path",
        feature="hotelling",
        params=(
            ParamSpec(
                "model_approach", "model_approach", "scenario", "enum",
                "hotelling", enum=_MODEL_APPROACHES,
            ),
            ParamSpec("solver_hotelling_max_bisection_iters", "solver_hotelling_max_bisection_iters", "scenario", "int", 80),
            ParamSpec("solver_hotelling_max_lambda_expansions", "solver_hotelling_max_lambda_expansions", "scenario", "int", 20),
            ParamSpec("solver_hotelling_convergence_tol", "solver_hotelling_convergence_tol", "scenario", "float", 0.0001),
            ParamSpec("solver_hotelling_lambda_initial_low", "solver_hotelling_lambda_initial_low", "scenario", "float", 0.001),
            ParamSpec("solver_hotelling_lambda_initial_high", "solver_hotelling_lambda_initial_high", "scenario", "float", 20.0),
            ParamSpec("solver_hotelling_lambda_expand_factor", "solver_hotelling_lambda_expand_factor", "scenario", "float", 3.0),
            *_COMMON_PRICE_FORMATION_PARAMS,
        ),
        ports=(_PRICE_FORMATION_OUT_PORT,),
    )
    nash = BlockSpec(
        id="nash_cournot",
        label="Nash–Cournot",
        category="price_formation",
        doc="features/nash_cournot/solver.py:solve_nash_path",
        feature="nash_cournot",
        params=(
            ParamSpec(
                "model_approach", "model_approach", "scenario", "enum",
                "nash_cournot", enum=_MODEL_APPROACHES,
            ),
            ParamSpec("solver_nash_price_step", "solver_nash_price_step", "scenario", "float", 0.5),
            ParamSpec("solver_nash_max_iters", "solver_nash_max_iters", "scenario", "int", 120),
            ParamSpec("solver_nash_convergence_tol", "solver_nash_convergence_tol", "scenario", "float", 0.001),
            ParamSpec("solver_nash_inner_xatol", "solver_nash_inner_xatol", "scenario", "float", 1e-4),
            ParamSpec("nash_strategic_participants", "nash_strategic_participants", "scenario", "list", default=()),
            *_COMMON_PRICE_FORMATION_PARAMS,
        ),
        ports=(
            _PRICE_FORMATION_OUT_PORT,
            PortSpec("strategic", "in", "strategic", cardinality="0..n"),
        ),
    )
    forward_transmission = BlockSpec(
        id="forward_transmission",
        label="Forward Transmission (λ overlay)",
        category="price_formation",
        doc="features/transmission/solver.py:solve_transmission_path, blend_prices",
        feature="transmission",
        params=(
            ParamSpec(
                "model_approach", "model_approach", "scenario", "enum",
                "competitive", enum=_MODEL_APPROACHES,
            ),
            ParamSpec(
                "forward_transmission_lambda", "forward_transmission_lambda",
                "scenario", "float", None, bounds=(0.0, 1.0),
            ),
            ParamSpec("solver_competitive_max_iters", "solver_competitive_max_iters", "scenario", "int", 25),
            ParamSpec("solver_competitive_tolerance", "solver_competitive_tolerance", "scenario", "float", 0.001),
            ParamSpec("solver_hotelling_max_bisection_iters", "solver_hotelling_max_bisection_iters", "scenario", "int", 80),
            ParamSpec("solver_hotelling_max_lambda_expansions", "solver_hotelling_max_lambda_expansions", "scenario", "int", 20),
            ParamSpec("solver_hotelling_convergence_tol", "solver_hotelling_convergence_tol", "scenario", "float", 0.0001),
            ParamSpec("solver_hotelling_lambda_initial_low", "solver_hotelling_lambda_initial_low", "scenario", "float", 0.001),
            ParamSpec("solver_hotelling_lambda_initial_high", "solver_hotelling_lambda_initial_high", "scenario", "float", 20.0),
            ParamSpec("solver_hotelling_lambda_expand_factor", "solver_hotelling_lambda_expand_factor", "scenario", "float", 3.0),
            *_COMMON_PRICE_FORMATION_PARAMS,
        ),
        ports=(_PRICE_FORMATION_OUT_PORT,),
    )
    return (competitive, banking, hotelling, nash, forward_transmission)


def _policy_blocks() -> tuple[BlockSpec, ...]:
    msr_bank_threshold = BlockSpec(
        id="msr_bank_threshold",
        label="MSR (bank threshold)",
        category="policy",
        doc="features/msr/state.py:MSRState.apply",
        feature="msr",
        params=(
            ParamSpec("msr_enabled", "msr_enabled", "scenario", "bool", True),
            ParamSpec("msr_mode", "msr_mode", "scenario", "enum", "bank_threshold", enum=_MSR_MODES),
            ParamSpec("msr_upper_threshold", "msr_upper_threshold", "scenario", "float", 200.0, unit="Mt CO2e"),
            ParamSpec("msr_lower_threshold", "msr_lower_threshold", "scenario", "float", 50.0, unit="Mt CO2e"),
            ParamSpec("msr_withhold_rate", "msr_withhold_rate", "scenario", "float", 0.12, bounds=(0.0, 1.0)),
            ParamSpec("msr_release_rate", "msr_release_rate", "scenario", "float", 50.0, unit="Mt CO2e/yr"),
            ParamSpec("msr_cancel_excess", "msr_cancel_excess", "scenario", "bool", False),
            ParamSpec("msr_cancel_threshold", "msr_cancel_threshold", "scenario", "float", 400.0, unit="Mt CO2e"),
            ParamSpec("msr_initial_reserve_mt", "msr_initial_reserve_mt", "scenario", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("msr_start_year", "msr_start_year", "scenario", "float", 0.0, unit="yr"),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
        excludes=("kmsr_decree",),
    )
    kmsr_decree = BlockSpec(
        id="kmsr_decree",
        label="K-MSR Decree",
        category="policy",
        doc="features/msr/decree.py:decree_msr_action",
        feature="msr",
        params=(
            ParamSpec("msr_enabled", "msr_enabled", "scenario", "bool", True),
            ParamSpec("msr_mode", "msr_mode", "scenario", "enum", "hybrid", enum=("price_band", "surplus_rule", "hybrid")),
            ParamSpec("msr_price_band_high", "msr_price_band_high", "scenario", "float", 25000.0),
            ParamSpec("msr_price_band_low", "msr_price_band_low", "scenario", "float", 15000.0),
            ParamSpec("msr_surplus_upper_ratio", "msr_surplus_upper_ratio", "scenario", "float", 0.18, bounds=(0.0, 1.0)),
            ParamSpec("msr_surplus_lower_ratio", "msr_surplus_lower_ratio", "scenario", "float", 0.05, bounds=(0.0, 1.0)),
            ParamSpec("msr_max_intake_mt", "msr_max_intake_mt", "scenario", "float", 20.0, unit="Mt CO2e/yr"),
            ParamSpec("msr_max_release_mt", "msr_max_release_mt", "scenario", "float", 20.0, unit="Mt CO2e/yr"),
            ParamSpec("msr_initial_reserve_mt", "msr_initial_reserve_mt", "scenario", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("msr_start_year", "msr_start_year", "scenario", "float", 0.0, unit="yr"),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
        requires=("rubin_schennach_banking",),
        excludes=("msr_bank_threshold",),
    )
    ccr = BlockSpec(
        id="ccr",
        label="Carbon Cap Rule (CCR)",
        category="policy",
        doc="features/ccr/state.py:CCRState.cap_adjustment",
        feature="ccr",
        params=(
            ParamSpec("ccr_enabled", "ccr_enabled", "scenario", "bool", True),
            ParamSpec("ccr_phi_emissions", "ccr_phi_emissions", "scenario", "float", 0.0),
            ParamSpec("ccr_phi_abatement_cost", "ccr_phi_abatement_cost", "scenario", "float", 0.0),
            ParamSpec("ccr_reference_emissions", "ccr_reference_emissions", "scenario", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("ccr_reference_abatement_cost", "ccr_reference_abatement_cost", "scenario", "float", 0.0),
            ParamSpec("ccr_start_year", "ccr_start_year", "scenario", "float", 0.0, unit="yr"),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
        requires=("competitive_clearing",),
    )
    price_floor = BlockSpec(
        id="price_floor",
        label="Price Floor",
        category="policy",
        doc="bound clamping in core/market/clearing.py",
        feature="price_controls",
        params=(
            ParamSpec("price_lower_bound", "price_lower_bound", "year", "float", 0.0, unit="currency/tCO2e"),
            ParamSpec("price_floor_trajectory", "price_floor_trajectory", "scenario", "dict", default={}),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    price_ceiling = BlockSpec(
        id="price_ceiling",
        label="Price Ceiling",
        category="policy",
        doc="bound clamping in market/equilibrium.py",
        feature="price_controls",
        params=(
            ParamSpec("price_upper_bound", "price_upper_bound", "year", "float", 100.0, unit="currency/tCO2e"),
            ParamSpec("price_ceiling_trajectory", "price_ceiling_trajectory", "scenario", "dict", default={}),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    auction_reserve = BlockSpec(
        id="auction_reserve",
        label="Auction Reserve",
        category="policy",
        doc="auction mechanics in core/market/clearing.py:solve_equilibrium",
        feature="price_controls",
        params=(
            ParamSpec("auction_reserve_price", "auction_reserve_price", "year", "float", 0.0, unit="currency/tCO2e"),
            ParamSpec("minimum_bid_coverage", "minimum_bid_coverage", "year", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("unsold_treatment", "unsold_treatment", "year", "enum", "reserve", enum=_UNSOLD_TREATMENTS),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    cancellation = BlockSpec(
        id="cancellation",
        label="Cancellation Schedule",
        category="policy",
        doc="year-level cap removal",
        feature="price_controls",
        params=(
            ParamSpec(
                "cancelled_allowances", "cancelled_allowances", "year", "float", 0.0,
                unit="Mt CO2e", label="Cancellation schedule [{year, amount}]",
            ),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    cap_path = BlockSpec(
        id="cap_path",
        label="Cap Trajectory",
        category="policy",
        doc="config_io/builder.py:_interp_value",
        feature="core",
        params=(
            ParamSpec("cap_trajectory", "cap_trajectory", "scenario", "dict", default={}),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    free_allocation_phaseout = BlockSpec(
        id="free_allocation_phaseout",
        label="Free-Allocation Phase-Out",
        category="policy",
        doc="config_io/builder.py:_interp_ratio",
        feature="core",
        params=(
            ParamSpec("free_allocation_trajectories", "free_allocation_trajectories", "scenario", "list", default=()),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    oba = BlockSpec(
        id="oba",
        label="Output-Based Allocation",
        category="policy",
        doc=(
            "OBA override in config_io/builder.py:build_market_from_year — "
            "no owned params: production_output/benchmark_emission_intensity "
            "already live on the participant block."
        ),
        feature="oba",
        params=(_ANNOUNCED_PARAM,),
        ports=(_POLICY_OUT_PORT,),
    )
    cbam = BlockSpec(
        id="cbam",
        label="CBAM",
        category="policy",
        doc="CBAM liability in features/cbam/plugin.py reporters (diagnostics-only, F6)",
        feature="cbam",
        params=(
            ParamSpec("eua_price", "eua_price", "year", "float", 0.0, unit="currency/tCO2e"),
            ParamSpec("eua_prices", "eua_prices", "year", "dict", default={}, label="Per-jurisdiction EUA prices"),
            ParamSpec("eua_price_ensemble", "eua_price_ensemble", "year", "dict", default={}, label="Named EUA price trajectories"),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    hoarding = BlockSpec(
        id="hoarding",
        label="Hoarding Inflow",
        category="policy",
        doc="features/hoarding/plugin.py:HoardingInflow",
        feature="hoarding",
        params=(
            ParamSpec(
                "hoarding_inflow", "hoarding_inflow", "year", "float", 0.0,
                unit="Mt CO2e", label="Hoarding schedule [{year, amount}]",
            ),
            _ANNOUNCED_PARAM,
        ),
        ports=(_POLICY_OUT_PORT,),
        requires=("rubin_schennach_banking",),
    )
    return (
        msr_bank_threshold, kmsr_decree, ccr, price_floor, price_ceiling,
        auction_reserve, cancellation, cap_path, free_allocation_phaseout,
        oba, cbam, hoarding,
    )


def _feedback_blocks() -> tuple[BlockSpec, ...]:
    # New category (docs/invest-feedback-plan.md D4): the outer adoption loop
    # is not a policy mechanism inside one solve — it wraps the whole path
    # solve — but it reuses the "policy" port KIND (not category) into
    # carbon_market.policies, the same in-port every policy block above
    # already targets (see the sibling ``ccr``/``msr_bank_threshold`` blocks).
    endogenous_investment = BlockSpec(
        id="endogenous_investment",
        label="Endogenous Investment Feedback",
        category="feedback",
        doc="engine/feedback.py:solve_with_investment_feedback, features/endogenous_investment/",
        feature="endogenous_investment",
        params=(
            # default=True mirrors msr_enabled/ccr_enabled above (the
            # decompile.py sibling-pattern trick, catalogue.py-local only —
            # config_io's OWN default is False, `blank_scenario`/
            # `normalize_scenario`; a freshly-dragged block or a
            # decompiled node's mere PRESENCE already implies "on" without
            # restating the flag).
            ParamSpec("investment_feedback_enabled", "investment_feedback_enabled", "scenario", "bool", True),
            ParamSpec(
                "investment_max_iterations", "investment_max_iterations", "scenario", "int", None,
                label="Safety-rail outer-iteration cap (default: N_flagged + 1)",
            ),
            ParamSpec(
                "investment_initial_adoptions", "investment_initial_adoptions", "scenario", "list",
                default=(), label="Pre-committed adoptions [{participant, technology, adoption_year}]",
            ),
            ParamSpec(
                "invest_credibility", "invest_credibility", "scenario", "float", None,
                bounds=(0.0, 1.0), label="Scenario-wide credibility override q",
            ),
        ),
        ports=(_POLICY_OUT_PORT,),
    )
    return (endogenous_investment,)


def _expectations_blocks() -> tuple[BlockSpec, ...]:
    expectations = BlockSpec(
        id="expectations",
        label="Expectations Rule",
        category="expectations",
        doc="core/expectations.py:ExpectationSpec, derive_expected_prices",
        feature="core",
        params=(
            ParamSpec("expectation_rule", "expectation_rule", "year", "enum", "next_year_baseline", enum=_EXPECTATION_RULES),
            ParamSpec("manual_expected_price", "manual_expected_price", "year", "float", 0.0, unit="currency/tCO2e"),
        ),
        ports=(PortSpec("expectations", "out", "expectations"),),
    )
    price_elastic_baseline = BlockSpec(
        id="price_elastic_baseline",
        label="Price-Elastic Baseline (Option A)",
        category="expectations",
        doc="core/participant/models.py:MarketParticipant.activity_multiplier",
        feature="elastic_baseline",
        params=(
            ParamSpec("reference_carbon_price", "reference_carbon_price", "scenario", "float", 0.0, unit="currency/tCO2e"),
        ),
        ports=(PortSpec("baseline", "out", "baseline"),),
    )
    return (expectations, price_elastic_baseline)


def _participant_blocks() -> tuple[BlockSpec, ...]:
    participant = BlockSpec(
        id="participant",
        label="Participant",
        category="participants",
        doc="core/participant/models.py:MarketParticipant via build_participant",
        feature="core",
        params=(
            ParamSpec("name", "name", "participant", "str", "New Participant"),
            ParamSpec("sector_group", "sector_group", "participant", "str", "", label="sector"),
            ParamSpec("initial_emissions", "initial_emissions", "participant", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("initial_emissions_trajectory", "initial_emissions_trajectory", "participant", "dict", default={}),
            ParamSpec("free_allocation_ratio", "free_allocation_ratio", "participant", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("penalty_price", "penalty_price", "participant", "float", 0.0, unit="currency/tCO2e"),
            ParamSpec("abatement_type", "abatement_type", "participant", "enum", "linear", enum=_ABATEMENT_TYPES),
            ParamSpec("max_abatement", "max_abatement", "participant", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("cost_slope", "cost_slope", "participant", "float", 1.0),
            ParamSpec("threshold_cost", "threshold_cost", "participant", "float", 0.0),
            ParamSpec("mac_blocks", "mac_blocks", "participant", "list", default=()),
            ParamSpec("technology_options", "technology_options", "participant", "list", default=()),
            ParamSpec("sector_allocation_share", "sector_allocation_share", "participant", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("production_output", "production_output", "participant", "float", 0.0),
            ParamSpec("benchmark_emission_intensity", "benchmark_emission_intensity", "participant", "float", 0.0),
            ParamSpec("output_price_elasticity", "output_price_elasticity", "participant", "float", 0.0),
            ParamSpec("electricity_consumption", "electricity_consumption", "participant", "float", 0.0, unit="MWh"),
            ParamSpec("grid_emission_factor", "grid_emission_factor", "participant", "float", 0.0, unit="tCO2/MWh"),
            ParamSpec("grid_emission_factor_trajectory", "grid_emission_factor_trajectory", "participant", "dict", default={}),
            ParamSpec("scope2_cbam_coverage", "scope2_cbam_coverage", "participant", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("cbam_export_share", "cbam_export_share", "participant", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("cbam_coverage_ratio", "cbam_coverage_ratio", "participant", "float", 1.0, bounds=(0.0, 1.0)),
            ParamSpec("cbam_jurisdictions", "cbam_jurisdictions", "participant", "list", default=()),
        ),
        ports=(
            PortSpec("compliance", "out", "compliance"),
            PortSpec("member_of", "out", "member_of", cardinality="0..1"),
            PortSpec("strategic", "out", "strategic", cardinality="0..1"),
            PortSpec("options", "in", "technology_option", cardinality="0..n"),
        ),
    )
    technology_option = BlockSpec(
        id="technology_option",
        label="Technology Option",
        category="participants",
        doc="core/participant/models.py:TechnologyOption via build_technology_option",
        feature="core",
        params=(
            ParamSpec("name", "name", "participant", "str", "New Technology"),
            ParamSpec("initial_emissions", "initial_emissions", "participant", "float", 0.0, unit="Mt CO2e"),
            ParamSpec("free_allocation_ratio", "free_allocation_ratio", "participant", "float", 0.0, bounds=(0.0, 1.0)),
            ParamSpec("penalty_price", "penalty_price", "participant", "float", 0.0),
            ParamSpec("abatement_type", "abatement_type", "participant", "enum", "linear", enum=_ABATEMENT_TYPES),
            ParamSpec("max_abatement", "max_abatement", "participant", "float", 0.0),
            ParamSpec("cost_slope", "cost_slope", "participant", "float", 1.0),
            ParamSpec("threshold_cost", "threshold_cost", "participant", "float", 0.0),
            ParamSpec("mac_blocks", "mac_blocks", "participant", "list", default=()),
            ParamSpec("fixed_cost", "fixed_cost", "participant", "float", 0.0),
            ParamSpec("max_activity_share", "max_activity_share", "participant", "float", 1.0, bounds=(0.0, 1.0)),
            ParamSpec(
                "investment_trigger", "investment_trigger", "participant", "dict", default={},
                label="Investment trigger (Dixit-Pindyck adoption rule; a "
                "non-empty sub-dict IS the flag, docs/invest-feedback-spec.md D6)",
            ),
        ),
        ports=(PortSpec("option", "out", "technology_option"),),
    )
    sector = BlockSpec(
        id="sector",
        label="Sector",
        category="participants",
        doc="sector pool derivation in config_io/builder.py:build_market_from_year",
        feature="sectors",
        params=(
            ParamSpec("sector_name", "sectors", "scenario", "str", "New Sector", label="name"),
            ParamSpec("cap_trajectory", "sectors", "scenario", "dict", default=None),
            ParamSpec("auction_share_trajectory", "sectors", "scenario", "dict", default=None),
            ParamSpec("carbon_budget", "sectors", "scenario", "float", 0.0, unit="Mt CO2e"),
        ),
        ports=(
            PortSpec("members", "in", "member_of", cardinality="0..n"),
            PortSpec("pool", "out", "sector_pool"),
        ),
    )
    return (participant, technology_option, sector)


def _analysis_blocks() -> tuple[BlockSpec, ...]:
    # Analysis blocks consume a market's solved results / compiled config —
    # they never feed back into a compiled scenario dict, so every param is
    # scope="edge" (never checked against config_io's blank_* documents; see
    # module docstring). blocks/ never imports ets.analysis (dependency law),
    # so these are pure metadata: running them is the caller's job.
    batch_sweep = BlockSpec(
        id="batch_sweep",
        label="Batch Sweep",
        category="analysis",
        doc="analysis/batch.py:run_batch",
        feature="batch_analysis",
        params=(ParamSpec("sweeps", "sweeps", "edge", "list", default=()),),
        ports=(PortSpec("results", "in", "results", cardinality="1"),),
    )
    calibration = BlockSpec(
        id="calibration",
        label="Calibration",
        category="analysis",
        doc="analysis/calibration.py:calibrate_slopes",
        feature="calibration",
        params=(
            ParamSpec("observed_prices", "observed_prices", "edge", "dict", default=None),
            ParamSpec("participant_names", "participant_names", "edge", "list", default=()),
            ParamSpec("initial_slopes", "initial_slopes", "edge", "dict", default=None),
            ParamSpec("max_iter", "max_iter", "edge", "int", 200),
        ),
        ports=(PortSpec("results", "in", "results", cardinality="1"),),
    )
    narrative = BlockSpec(
        id="narrative",
        label="Narrative",
        category="analysis",
        doc="analysis/narrative.py:generate_narrative",
        feature="narrative",
        params=(ParamSpec("scenario_name", "scenario_name", "edge", "str", ""),),
        ports=(PortSpec("results", "in", "results", cardinality="1"),),
    )
    investment_trigger = BlockSpec(
        id="investment_trigger",
        label="Investment Trigger",
        category="analysis",
        doc="analysis/investment_trigger.py",
        feature="investment_trigger",
        params=(
            ParamSpec("sigma", "sigma", "edge", "float", 0.2),
            ParamSpec("r", "r", "edge", "float", 0.04),
            ParamSpec("y", "y", "edge", "float", 1.0),
            ParamSpec("credibility", "credibility", "edge", "float", 1.0, bounds=(0.0, 1.0)),
        ),
        ports=(PortSpec("results", "in", "results", cardinality="1"),),
    )
    external_feedback = BlockSpec(
        id="external_feedback",
        label="External Feedback Loop",
        category="analysis",
        doc="coupling/loop.py:run_coupled_simulation + coupling/adapters.py",
        feature="feedback_coupling",
        params=(
            ParamSpec("adapter", "adapter", "edge", "str", ""),
            ParamSpec("elasticity", "elasticity", "edge", "float", 0.0),
            ParamSpec("reference_price", "reference_price", "edge", "float", 0.0),
            ParamSpec("relaxation_weight", "relaxation_weight", "edge", "float", 0.5, bounds=(0.0, 1.0)),
            ParamSpec("tolerance", "tolerance", "edge", "float", 0.001),
            ParamSpec("max_iterations", "max_iterations", "edge", "int", 25),
        ),
        ports=(PortSpec("results", "in", "results", cardinality="1"),),
    )
    return (batch_sweep, calibration, narrative, investment_trigger, external_feedback)


def _build_catalogue() -> BlockRegistry:
    registry = BlockRegistry()
    for block in (
        _market_block(),
        _product_market_block(),
        _producer_block(),
        _market_link_block(),
        _joint_solver_block(),
        *_price_formation_blocks(),
        *_policy_blocks(),
        *_feedback_blocks(),
        *_expectations_blocks(),
        *_participant_blocks(),
        *_analysis_blocks(),
    ):
        registry.register(block)
    return registry


BLOCK_CATALOGUE = _build_catalogue()
