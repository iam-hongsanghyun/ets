r"""Tarjan condensation of the market digraph (T3, pure/stdlib).

The D2 joint-equilibrium engine's front half (``docs/joint-equilibrium.md`` §1;
``docs/joint-equilibrium-plan.md`` §1, §5, work order D2-2). D1 solves a
one-way DAG in a single topological pass (``engine.links.topological_market_order``);
D2 removes the DAG restriction by first CONDENSING the market graph into its
strongly-connected components (SCCs). Every acyclic (size-1, no self-edge) SCC
is solved exactly as D1 (byte-identical); every cyclic SCC is handed to the
outer Gauss-Seidel fixed point (``engine.joint.solve_joint_scc``).

The market DIGRAPH is defined precisely as::

    V = the market ids (nodes)
    E = { (A, B) : some LinkSpec has from_market == A and to_market == B, A != B }

i.e. a directed edge ``A -> B`` exists iff a link carries market A's solved
delivered price signal into market B (``LinkSpec`` semantics, D1). Multiple
links on one ``(A, B)`` pair (distinct channels) collapse to ONE edge — channel
and ``phi`` are irrelevant to the graph's cycle structure. A self-link (``A ->
A``) is forbidden by R36 (``LinkSpec.__post_init__`` rejects ``from == to``), so
self-edges never arrive through validated links; ``is_cyclic`` still checks for
one defensively so a size-1 SCC with a stray self-edge is reported cyclic rather
than silently treated as acyclic.

DETERMINISM IS LOAD-BEARING (the ULP-amplification lesson,
``docs/joint-equilibrium-plan.md`` §7): the SCC set and the condensation order
must be a pure function of the graph alone, invariant to link declaration order
and free of any dict-/set-iteration-order dependence. Every node scan and every
successor scan is sorted explicitly by the tie-break key ``(declared index in
market_ids, market id)`` — the same tie-break ``topological_market_order`` uses.

References:
    Tarjan, R. E. (1972). "Depth-first search and linear graph algorithms."
    SIAM Journal on Computing 1(2), 146-160. (SCCs in one DFS pass.)
    Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms* (CLRS),
    §22.5 (strongly connected components). (Textbook statement.)
    docs/joint-equilibrium-plan.md §1 (SCC + outer loop), §5 (engine placement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..core.protocols import LinkSpec

logger = logging.getLogger(__name__)

__all__ = [
    "SCC",
    "condensation_order",
    "strongly_connected_components",
]


@dataclass(frozen=True)
class SCC:
    """One strongly-connected component of the market digraph (frozen).

    Attributes:
        members: The component's market ids, in the deterministic tie-break
            order ``(declared index, market id)`` (the same order the sweep
            reads them — the sweep order is part of the equilibrium definition
            in the near-critical regime, ``docs/joint-equilibrium.md`` §6
            V-D2-2). A single-member tuple is the acyclic/D1 case unless
            ``cyclic`` is set.
        cyclic: ``True`` iff the component needs the joint outer loop — size
            >= 2 (a genuine cycle), or size 1 with a self-edge (R36-forbidden,
            handled defensively). ``False`` is the size-1, no-self-edge D1 case
            solved byte-identically to D1.
    """

    members: tuple[str, ...]
    cyclic: bool


def _deduped_edges(
    market_ids: Sequence[str], links: Sequence[LinkSpec]
) -> tuple[dict[str, int], dict[str, list[str]], set[str]]:
    """Build the deterministic successor map and the self-edge set.

    Returns ``(order_index, successors, self_looped)`` where ``order_index``
    maps each market id to its declared position, ``successors[v]`` lists v's
    out-neighbours sorted by ``(declared index, id)`` (deduped per ``(from,
    to)`` pair, distinct-endpoint edges only), and ``self_looped`` holds any
    market carrying a defensive self-edge (empty for validated links).
    """
    order_index = {market_id: index for index, market_id in enumerate(market_ids)}
    successors: dict[str, list[str]] = {market_id: [] for market_id in market_ids}
    self_looped: set[str] = set()

    seen: set[tuple[str, str]] = set()
    for link in links:
        edge = (link.from_market, link.to_market)
        if edge in seen:
            continue
        seen.add(edge)
        if link.from_market == link.to_market:
            self_looped.add(link.from_market)
            continue
        # Ignore edges touching ids absent from ``market_ids`` (defensive: the
        # caller owns the node set; a dangling endpoint is not a graph node).
        if link.from_market in successors and link.to_market in order_index:
            successors[link.from_market].append(link.to_market)

    for node in successors:
        successors[node].sort(key=lambda m: (order_index[m], m))
    return order_index, successors, self_looped


def strongly_connected_components(
    market_ids: Sequence[str], links: Sequence[LinkSpec]
) -> list[frozenset[str]]:
    r"""Tarjan's SCCs of the market digraph (iterative, deterministic).

    Partitions the markets into strongly-connected components: two markets are
    in the same component iff each is reachable from the other along link
    edges. A single DFS pass assigns each node a monotone ``index`` (discovery
    time) and a ``lowlink`` (the least index reachable via the node's subtree
    plus one back/cross edge to a node still on the DFS stack); a node with
    ``lowlink == index`` is an SCC root, and the SCC is exactly the stack
    suffix above it.

    Algorithm:
        Tarjan (1972); CLRS §22.5. Recursion is expressed with an explicit
        work stack (no Python recursion-limit exposure for large graphs).

        LaTeX:
        $$ \mathrm{index}(v) = \text{discovery order of } v, \qquad
           \mathrm{low}(v) = \min\!\Big(\mathrm{index}(v),\;
             \min_{(v,w)\in E,\, w \text{ on stack}} \mathrm{index}(w),\;
             \min_{(v,w)\in E,\, w \text{ tree child}} \mathrm{low}(w)\Big), $$
        $$ \mathrm{low}(v) = \mathrm{index}(v) \;\Rightarrow\; v \text{ roots an
           SCC} = \text{stack suffix down to } v. $$

        ASCII fallback:
            index[v]  = discovery time of v (monotone counter)
            low[v]    = min(index[v],
                            min index[w] over on-stack out-neighbours w,
                            min low[w]   over tree-child out-neighbours w)
            low[v] == index[v]  =>  pop the DFS stack down to v: that suffix
                                    is one SCC.

        Symbols (units): all dimensionless graph bookkeeping —
            V        : market ids [-]
            E        : deduped directed link edges (from, to), from != to [-]
            index(v) : DFS discovery order of v [-]
            low(v)   : v's lowlink [-]

    Determinism: nodes are entered in declared order; each node's
    out-neighbours are visited in ``(declared index, id)`` order, so the
    partition is a pure function of the graph (invariant to link declaration
    order). The returned list order is Tarjan's natural emission order (reverse
    topological); use :func:`condensation_order` when a forward, tie-broken
    condensation order is required.

    Args:
        market_ids: Every market id, in DECLARED order (the primary tie-break
            key; the ``iter_market_bodies`` order in the engine).
        links: The scenario's links; only ``(from_market, to_market)`` is read
            (deduped per pair; channel and ``phi`` are irrelevant to cycle
            structure; self-links are skipped from edges and recorded
            separately for the defensive self-loop check).

    Returns:
        The SCCs as a list of ``frozenset``s partitioning ``market_ids``; every
        market appears in exactly one component.
    """
    order_index, successors, _self = _deduped_edges(market_ids, links)

    index_of: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    dfs_stack: list[str] = []
    counter = 0
    components: list[frozenset[str]] = []

    for start in market_ids:  # declared order — deterministic entry
        if start in index_of:
            continue
        # Work items: [node, next-successor-cursor]; a cursor of 0 means the
        # node has not been initialised yet (pre-visit), matching a recursive
        # call's entry.
        work: list[list] = [[start, 0]]
        while work:
            frame = work[-1]
            node, cursor = frame[0], frame[1]
            if cursor == 0:
                index_of[node] = counter
                lowlink[node] = counter
                counter += 1
                dfs_stack.append(node)
                on_stack[node] = True

            descended = False
            neighbours = successors[node]
            j = cursor
            while j < len(neighbours):
                w = neighbours[j]
                if w not in index_of:
                    frame[1] = j + 1  # resume after this child on return
                    work.append([w, 0])
                    descended = True
                    break
                if on_stack.get(w, False):
                    lowlink[node] = min(lowlink[node], index_of[w])
                j += 1
            if descended:
                continue

            if lowlink[node] == index_of[node]:
                component: list[str] = []
                while True:
                    w = dfs_stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                components.append(frozenset(component))

            work.pop()
            if work:  # propagate lowlink up the tree edge to the parent
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])

    logger.debug("SCC condensation: %d markets -> %d components", len(market_ids), len(components))
    return components


def condensation_order(market_ids: Sequence[str], links: Sequence[LinkSpec]) -> list[SCC]:
    r"""SCCs in a deterministic topological order of the condensation DAG.

    Condenses the market digraph to its SCCs and returns them in a valid
    topological order: for every cross-component edge ``comp_i -> comp_j``,
    ``comp_i`` precedes ``comp_j``. Condensing a digraph by its SCCs always
    yields a DAG, so a topological order exists; ties are broken deterministically
    so the order is a pure function of the graph (the ULP-amplification lesson).

    Algorithm:
        Kahn's topological sort over the condensation DAG with a deterministic
        ready-set tie-break — the same discipline as
        ``engine.links.topological_market_order``, lifted from market nodes to
        component nodes.

        ASCII fallback:
            comps      = strongly_connected_components(...)
            key(comp)  = min over members of (declared index, id)   # rep node
            E'         = { (comp(u), comp(v)) : (u, v) in E, comp(u) != comp(v) }
            in_deg'[c] = number of distinct condensation edges into c
            ready      = { c : in_deg'[c] == 0 }, sorted by key(c)
            while ready:
                pop c = min(ready) by key; emit c
                for each edge (c, d): in_deg'[d] -= 1; add d when it hits 0

        Symbols (units): dimensionless graph bookkeeping —
            key(comp) : the component's tie-break key = its lexicographically
                        least ``(declared index, id)`` member [-]
            E'        : condensation edges (cross-component only) [-]

    Args:
        market_ids: Every market id, in DECLARED order (the tie-break's primary
            key).
        links: The scenario's links (see :func:`strongly_connected_components`).

    Returns:
        The SCCs as ``SCC`` objects (``members`` in ``(declared index, id)``
        order; ``cyclic`` set per :func:`is_cyclic`), the list itself in a
        deterministic topological order of the condensation DAG. A three-market
        chain ``A -> B -> C`` yields ``[{A}, {B}, {C}]``; a back-edge ``C -> A``
        collapses the three into a single cyclic ``{A, B, C}``.
    """
    order_index, successors, self_looped = _deduped_edges(market_ids, links)
    components = strongly_connected_components(market_ids, links)

    component_of: dict[str, int] = {}
    for comp_id, component in enumerate(components):
        for node in component:
            component_of[node] = comp_id

    def _member_key(market_id: str) -> tuple[int, str]:
        return (order_index[market_id], market_id)

    # Deterministic ordered member tuples + each component's tie-break key.
    ordered_members: list[tuple[str, ...]] = []
    component_key: list[tuple[int, str]] = []
    for component in components:
        members = tuple(sorted(component, key=_member_key))
        ordered_members.append(members)
        component_key.append(_member_key(members[0]))

    # Condensation DAG edges (cross-component only), deduped.
    comp_successors: dict[int, set[int]] = {c: set() for c in range(len(components))}
    comp_in_degree: dict[int, int] = {c: 0 for c in range(len(components))}
    comp_edges: set[tuple[int, int]] = set()
    for u in market_ids:
        cu = component_of[u]
        for v in successors[u]:
            cv = component_of[v]
            if cu == cv:
                continue
            if (cu, cv) in comp_edges:
                continue
            comp_edges.add((cu, cv))
            comp_successors[cu].add(cv)
            comp_in_degree[cv] += 1

    def _comp_sort_key(comp_id: int) -> tuple[int, str]:
        return component_key[comp_id]

    ready = sorted(
        (c for c in range(len(components)) if comp_in_degree[c] == 0), key=_comp_sort_key
    )
    topo: list[int] = []
    while ready:
        comp_id = ready.pop(0)
        topo.append(comp_id)
        newly_ready: list[int] = []
        for succ in comp_successors[comp_id]:
            comp_in_degree[succ] -= 1
            if comp_in_degree[succ] == 0:
                newly_ready.append(succ)
        if newly_ready:
            ready.extend(newly_ready)
            ready.sort(key=_comp_sort_key)

    # A condensation is always a DAG; a leftover node would signal a bug in the
    # SCC partition, not a legal cyclic condensation.
    if len(topo) != len(components):
        raise AssertionError(
            "condensation is not a DAG — the SCC partition is inconsistent "
            "(internal invariant violation, not a user-facing cycle)."
        )

    result = [
        SCC(
            members=ordered_members[comp_id],
            cyclic=is_cyclic(ordered_members[comp_id], self_looped),
        )
        for comp_id in topo
    ]
    logger.debug(
        "condensation order: %d components, %d cyclic",
        len(result),
        sum(1 for scc in result if scc.cyclic),
    )
    return result


def is_cyclic(members: tuple[str, ...], self_looped: set[str]) -> bool:
    """Whether an SCC needs the joint outer loop.

    A component is cyclic iff it has more than one member (a genuine mutual
    dependency) or a single member carrying a self-edge (R36-forbidden through
    validated links, checked defensively). The size-1, no-self-edge case is the
    acyclic/D1 component solved byte-identically to D1.

    Args:
        members: The component's market ids (any order).
        self_looped: Market ids observed to carry a self-edge.

    Returns:
        ``True`` if the component must be handed to ``solve_joint_scc``.
    """
    if len(members) > 1:
        return True
    return members[0] in self_looped
