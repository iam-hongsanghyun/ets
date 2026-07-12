r"""D3-7 gate: the block composer can DRAW the steel↔carbon multi-commodity model.

Covers ``docs/multi-commodity-spec.md`` §6/§7 (the composer half of D3): a user
DRAWS a ``carbon_market`` + a ``product_market`` + ``producer`` nodes + the two
shared-agent coupling links (``carbon_input_price`` / ``output_ref_price``) + a
``producer_ref`` (the carbon side reads the product market's producers) + a
``joint_solver``, and it compiles to EXACTLY the ``steel_carbon_joint`` base
scenario config shape, decompiles back, and round-trips.

Assertions, end to end:

(a) compile   — the drawn graph compiles bit-identically to
    ``normalize_config`` of the committed ``examples/steel_carbon_joint.json``
    base scenario (the config the graph must author).
(b) validate  — the cycle is LEGAL (no error): the empty-participant carbon
    market is carved out of R2 (it reads emitters via producer_ref), the new
    channels pass R35, and no product-market rule (R38/R39/R40) fires.
(c) solve     — the compiled config runs to the hand-verified finite-β fixed
    point ``P_s* = 60``, ``P_c* = 10`` with ``Joint Converged == 1``.
(d) round-trip — ``compile(decompile(compiled)) == compiled``, and the decompiled
    graph carries a ``product_market`` node, two ``producer`` nodes, and the
    ``producer_ref`` edge wired product-market -> carbon-market.
(e) rules     — a product market with no producer is an R38 error; an unattached
    producer is an R39 error (the well-formedness rails).

Hand anchor (V-D3-5b, ``docs/multi-commodity-spec.md`` §7): two identical
producers γ=5, δ=2, σ=5, β=10, a_max=5; linear demand A_d=40, b_d=0.3;
carbon-free imports m=0.2, σ_foreign=5; fixed cap=40 ⇒ P_s*=60, P_c*=10.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from pe import run_simulation_from_config
from pe.blocks import Edge, Graph, Node, compile_graph, graph_from_config, validate_graph
from pe.config_io import normalize_config

# The committed flagship config the drawn graph must author (base scenario).
_EXAMPLE = Path(__file__).resolve().parents[3] / "examples" / "steel_carbon_joint.json"
_SCENARIO_NAME = "steel-carbon base (finite-beta cycle)"

P_STEEL_STAR = 60.0
P_CARBON_STAR = 10.0
PRICE_ATOL = 1e-6


def _golden_base_scenario() -> dict[str, Any]:
    """``normalize_config`` of the flagship's FIRST scenario — the round-trip target."""
    example = json.loads(_EXAMPLE.read_text())
    return normalize_config({"scenarios": [example["scenarios"][0]]})


def _steel_carbon_graph() -> Graph:
    """The drawn steel↔carbon graph: carbon + product markets, producers, coupling."""
    nodes: list[Node] = []
    edges: list[Edge] = []

    # ── carbon compliance market (competitive; emitters come from producer_ref) ──
    nodes.append(
        Node(
            "carbon",
            "carbon_market",
            {
                "name": "carbon",
                "order": 0,
                "price_unit": "USD/tCO2",
                "scenario_name": _SCENARIO_NAME,
                "years": [
                    {
                        "year": "2030",
                        "total_cap": 40.0,
                        "auction_mode": "explicit",
                        "auction_offered": 40.0,
                    }
                ],
            },
        )
    )
    nodes.append(Node("carbon_pf", "competitive_clearing", {}))
    edges.append(Edge("carbon_pf", "price_formation", "carbon", "price_formation"))
    nodes.append(Node("carbon_ceil", "price_ceiling", {"price_upper_bound": 200.0}))
    edges.append(Edge("carbon_ceil", "policy", "carbon", "policies"))

    # ── steel product (goods) market + its two producers ──
    nodes.append(
        Node(
            "steel",
            "product_market",
            {
                "name": "steel",
                "order": 1,
                "price_unit": "USD/t-steel",
                "carbon_price": 0.0,
                "product_demand": {"form": "linear", "intercept": 40.0, "slope": 0.3},
                "import_supply": {"world_price": 0.0, "slope": 0.2, "sigma_foreign": 5.0},
                "years": [{"year": "2030"}],
            },
        )
    )
    for index, producer_name in enumerate(("SteelCo A", "SteelCo B")):
        pid = f"steel_p{index}"
        nodes.append(
            Node(
                pid,
                "producer",
                {
                    "name": producer_name,
                    "order": index,
                    "output_cost": {"gamma": 5.0, "delta": 2.0},
                    "intensity": 5.0,
                    "abatement": {"beta": 10.0, "a_max": 5.0},
                },
            )
        )
        edges.append(Edge(pid, "product", "steel", "producers"))

    # ── the carbon side reads the steel producers (producer_ref) ──
    edges.append(Edge("steel", "producer_ref", "carbon", "producer_ref"))

    # ── the two shared-agent coupling links (the joint SCC's back-edges) ──
    nodes.append(
        Node(
            "l_carbon_steel",
            "market_link",
            {
                "channel": "carbon_input_price",
                "phi": 1.0,
                "phi_unit": "1/1",
                "target_participants": ["*"],
            },
        )
    )
    edges.append(Edge("carbon", "signal", "l_carbon_steel", "from"))
    edges.append(Edge("l_carbon_steel", "link", "steel", "links"))
    nodes.append(
        Node(
            "l_steel_carbon",
            "market_link",
            {
                "channel": "output_ref_price",
                "phi": 1.0,
                "phi_unit": "1/1",
                "target_participants": ["*"],
            },
        )
    )
    edges.append(Edge("steel", "signal", "l_steel_carbon", "from"))
    edges.append(Edge("l_steel_carbon", "link", "carbon", "links"))

    # ── the joint outer loop (damped Gauss-Seidel) ──
    nodes.append(
        Node(
            "js",
            "joint_solver",
            {"relaxation": 0.5, "tolerance": 1e-12, "max_iterations": 400},
        )
    )
    edges.append(Edge("js", "joint_solver", "carbon", "joint_solver"))
    return Graph(nodes=nodes, edges=edges)


# ── (a) compile: the drawn graph authors the committed flagship config ──


def test_steel_carbon_graph_compiles_to_golden_base_scenario() -> None:
    compiled = compile_graph(_steel_carbon_graph())
    assert compiled == {"scenarios": [_golden_base_scenario()["scenarios"][0]]}


def test_compiled_scenario_carries_the_coupling_shape() -> None:
    scenario = compile_graph(_steel_carbon_graph())["scenarios"][0]
    assert scenario["name"] == _SCENARIO_NAME
    assert [m["market_id"] for m in scenario["markets"]] == ["carbon", "steel"]

    carbon = next(m for m in scenario["markets"] if m["market_id"] == "carbon")
    steel = next(m for m in scenario["markets"] if m["market_id"] == "steel")
    # producer_ref: the carbon body reads the steel producers (config_io resolves
    # the per-year emitter view).
    assert carbon["producer_ref"]["market"] == "steel"
    assert [p["name"] for p in carbon["producer_ref"]["producers_by_year"]["2030"]] == [
        "SteelCo A",
        "SteelCo B",
    ]
    assert steel["model_approach"] == "product"
    assert steel["product_demand"] == {"form": "linear", "a_d": 40.0, "b_d": 0.3}

    channels = {
        (link["from_market"], link["to_market"]): link["channel"] for link in scenario["links"]
    }
    assert channels == {
        ("carbon", "steel"): "carbon_input_price",
        ("steel", "carbon"): "output_ref_price",
    }
    assert scenario["joint_solver"]["relaxation"] == 0.5


# ── (b) validate: the joint SCC is legal; no product-market rule fires ──


def test_steel_carbon_graph_validates_clean() -> None:
    issues = validate_graph(_steel_carbon_graph())
    errors = [i.to_dict() for i in issues if i.level == "error"]
    assert not errors, errors
    # R2 is carved out for the producer_ref carbon market; R38/R39/R40 stay silent.
    fired = {i.rule for i in issues}
    assert fired.isdisjoint({"R2", "R38", "R39", "R40"}), fired


# ── (c) solve: the hand-verified finite-β fixed point ──


def test_compiled_steel_carbon_solves_to_the_hand_anchor() -> None:
    compiled = compile_graph(_steel_carbon_graph())
    summary, _participants = run_simulation_from_config(compiled)

    assert all(summary["Joint Converged"] == 1.0)
    prices = dict(zip(summary["Scenario"], summary["Equilibrium Carbon Price"], strict=True))
    np.testing.assert_allclose(
        prices[f"{_SCENARIO_NAME} :: carbon"], P_CARBON_STAR, rtol=0.0, atol=PRICE_ATOL
    )
    np.testing.assert_allclose(
        prices[f"{_SCENARIO_NAME} :: steel"], P_STEEL_STAR, rtol=0.0, atol=PRICE_ATOL
    )


# ── (d) round-trip: compile -> decompile -> compile is idempotent ──


def test_steel_carbon_graph_round_trips_through_decompile() -> None:
    compiled = compile_graph(_steel_carbon_graph())
    recompiled = compile_graph(graph_from_config(compiled))
    assert recompiled == compiled


def test_decompiled_graph_has_product_market_producers_and_producer_ref() -> None:
    decompiled = graph_from_config(compile_graph(_steel_carbon_graph()))

    product_markets = [n for n in decompiled.nodes if n.block == "product_market"]
    assert len(product_markets) == 1
    producers = [n for n in decompiled.nodes if n.block == "producer"]
    assert [n.params["name"] for n in producers] == ["SteelCo A", "SteelCo B"]

    # The producer_ref edge is wired product-market 'producer_ref' -> carbon 'producer_ref'.
    ref_edges = [e for e in decompiled.edges if e.target_port == "producer_ref"]
    assert len(ref_edges) == 1
    source = decompiled.node(ref_edges[0].source)
    target = decompiled.node(ref_edges[0].target)
    assert source is not None and source.block == "product_market"
    assert target is not None and target.block == "carbon_market"

    # Both coupling links round-trip as market_link nodes on the two D3 channels.
    channels = {n.params["channel"] for n in decompiled.nodes if n.block == "market_link"}
    assert channels == {"carbon_input_price", "output_ref_price"}


# ── (e) well-formedness rails: R38 (product needs producer), R39 (producer needs market) ──


def test_product_market_without_producer_is_r38_error() -> None:
    graph = _steel_carbon_graph()
    graph.nodes = [n for n in graph.nodes if n.block != "producer"]
    graph.edges = [e for e in graph.edges if e.target_port != "producers"]
    rules = {i.rule for i in validate_graph(graph) if i.level == "error"}
    assert "R38" in rules


def test_unattached_producer_is_r39_error() -> None:
    graph = _steel_carbon_graph()
    # Drop the 'product' edges so the producers dangle off their product market.
    graph.edges = [e for e in graph.edges if e.target_port != "producers"]
    rules = {i.rule for i in validate_graph(graph) if i.level == "error"}
    assert "R39" in rules
