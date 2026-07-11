"""SCC condensation (D2-2): correctness + load-bearing determinism.

Covers ``pe.engine.scc``: Tarjan's SCCs, the deterministic topological
condensation order, and the acyclic-vs-cyclic classification. Determinism is a
correctness property here (the ULP-amplification lesson,
``docs/joint-equilibrium-plan.md`` §7), so it is asserted directly.
"""

from __future__ import annotations

from pe.core.protocols import LinkSpec
from pe.engine.scc import (
    SCC,
    condensation_order,
    strongly_connected_components,
)


def _link(from_market: str, to_market: str, phi: float = 1.0) -> LinkSpec:
    """A minimal valid link ``from_market -> to_market`` (mac_cost channel)."""
    return LinkSpec(
        from_market=from_market,
        to_market=to_market,
        channel="mac_cost",
        phi=phi,
        phi_unit="KRW/tCO2 per KRW/tCO2",
        target_participants=("*",),
        target_technologies=("t",),
    )


def _members(order: list[SCC]) -> list[tuple[str, ...]]:
    return [scc.members for scc in order]


def test_chain_three_size_one_sccs_in_order() -> None:
    """A -> B -> C: three size-1 SCCs, condensation order [A, B, C]."""
    markets = ["A", "B", "C"]
    links = [_link("A", "B"), _link("B", "C")]

    comps = strongly_connected_components(markets, links)
    assert {frozenset({"A"}), frozenset({"B"}), frozenset({"C"})} == set(comps)
    assert len(comps) == 3

    order = condensation_order(markets, links)
    assert _members(order) == [("A",), ("B",), ("C",)]
    # A size-1 SCC with no self-edge is the acyclic/D1 case.
    assert all(not scc.cyclic for scc in order)


def test_back_edge_collapses_chain_into_one_scc() -> None:
    """Adding C -> A collapses {A, B, C} into a single cyclic SCC."""
    markets = ["A", "B", "C"]
    links = [_link("A", "B"), _link("B", "C"), _link("C", "A")]

    comps = strongly_connected_components(markets, links)
    assert comps == [frozenset({"A", "B", "C"})]

    order = condensation_order(markets, links)
    assert _members(order) == [("A", "B", "C")]
    assert order[0].cyclic is True
    # members are in (declared index, id) order, not set-iteration order.
    assert order[0].members == ("A", "B", "C")


def test_two_cycle_plus_downstream_sink() -> None:
    """{A<->B} feeding a size-1 sink C: cyclic SCC precedes the acyclic one."""
    markets = ["A", "B", "C"]
    links = [_link("A", "B"), _link("B", "A"), _link("B", "C")]

    order = condensation_order(markets, links)
    assert _members(order) == [("A", "B"), ("C",)]
    assert order[0].cyclic is True
    assert order[1].cyclic is False


def test_upstream_source_precedes_cycle() -> None:
    """An acyclic source C -> A feeding {A<->B}: C first (condensation-upstream)."""
    markets = ["A", "B", "C"]
    links = [_link("C", "A"), _link("A", "B"), _link("B", "A")]

    order = condensation_order(markets, links)
    assert _members(order) == [("C",), ("A", "B")]
    assert order[0].cyclic is False
    assert order[1].cyclic is True


def test_determinism_invariant_to_link_declaration_order() -> None:
    """Same graph, links declared in any order -> byte-identical condensation."""
    markets = ["A", "B", "C", "D"]
    forward = [_link("A", "B"), _link("B", "C"), _link("C", "B"), _link("C", "D")]
    shuffled = [_link("C", "D"), _link("C", "B"), _link("A", "B"), _link("B", "C")]

    order_a = condensation_order(markets, forward)
    order_b = condensation_order(markets, shuffled)
    assert order_a == order_b
    # {B, C} is the cycle; A upstream, D downstream.
    assert _members(order_a) == [("A",), ("B", "C"), ("D",)]
    assert [scc.cyclic for scc in order_a] == [False, True, False]


def test_determinism_repeated_calls_identical() -> None:
    """Determinism: repeated calls on the same input give identical results."""
    markets = ["m3", "m1", "m2"]  # declared order != sorted order
    links = [_link("m1", "m2"), _link("m2", "m1"), _link("m3", "m1")]

    runs = [condensation_order(markets, links) for _ in range(5)]
    assert all(run == runs[0] for run in runs)
    # Tie-break is (declared index, id): m3 declared first, then the {m1,m2}
    # cycle whose representative is m1 (declared before m2).
    assert _members(runs[0]) == [("m3",), ("m1", "m2")]
    assert runs[0][1].members == ("m1", "m2")


def test_multiple_channels_one_edge() -> None:
    """Two links on one (from, to) pair are ONE graph edge (no double-count)."""
    markets = ["A", "B"]
    links = [
        _link("A", "B"),
        LinkSpec(
            from_market="A",
            to_market="B",
            channel="invest_break_even",
            phi=0.3,
            phi_unit="KRW/tCO2 per KRW/tCO2",
            target_participants=("*",),
            target_technologies=(),
        ),
    ]
    comps = strongly_connected_components(markets, links)
    assert {frozenset({"A"}), frozenset({"B"})} == set(comps)
    order = condensation_order(markets, links)
    assert _members(order) == [("A",), ("B",)]


def test_isolated_markets_no_links() -> None:
    """No links: every market is its own acyclic SCC, in declared order."""
    markets = ["B", "A", "C"]
    order = condensation_order(markets, [])
    assert _members(order) == [("B",), ("A",), ("C",)]
    assert all(not scc.cyclic for scc in order)
