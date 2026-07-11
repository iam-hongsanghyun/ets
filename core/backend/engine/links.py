r"""One-way market links (T3): DAG ordering + pure inbound-link application.

The engine-tier half of D1's PriceLink (``docs/platform-plan-d0-d1.md`` D1
"engine"; binding economic spec ``docs/platform-spec-d0-d1.md`` §2d, §3, §7).
Three pure functions the multi-market dispatch (``engine/dispatch.py``) calls
ONCE per scenario, in this order:

1. :func:`build_link_specs` — construct the immutable ``core.protocols.LinkSpec``
   objects from a multi-market scenario's ``links: [...]`` records, validated
   through the ``market_links`` plugin door (the config-tier field/structural
   validator, D1-1).
2. :func:`topological_market_order` — Kahn's algorithm over the link DAG with
   a deterministic tie-break (declared market order, then market id); a cycle
   is R34's engine-side enforcement — a loud ``ValueError`` naming the cycle
   and citing D2.
3. :func:`check_horizon_alignment` — the E8 strict-subset horizon guard,
   surfaced at solve entry as a clean config-level error (the channel's
   per-year lookup would otherwise raise mid-solve).
4. :func:`apply_inbound_links` — pure copy-on-write application of every
   inbound link, reading each already-solved upstream market's FINAL
   converged DELIVERED price path (the E4 pin; the same
   ``item["equilibrium"]["price"]`` signal ``engine/feedback.py`` reads).

Link application is an ENGINE-TIER step applied ONCE, BEFORE the path solver,
never inside any fixed point (spec §2d, F4 purity); the shift math itself lives
in the channel implementations (``features/market_links/channels.py``), which
are already pure copy-on-write.

Tier note (``tests/test_module_isolation.py``): this module is T3 (``pe.engine``).
Its ``pe.core.protocols`` (T0) and ``pe.config_io`` (T1) imports are eager;
the ``pe.features.market_links.*`` (T2) imports — the plugin-door validator and
the channel registry — are FUNCTION-LOCAL, so importing ``pe.engine`` loads no
channel runtime (activation scoping; the ``engine.wiring.link_channels``
precedent). Both are the legal T3 -> T2 edge the AST ratchet permits.

References:
    docs/platform-spec-d0-d1.md §2d (placement/purity), §3 (DAG equilibrium,
    R34/R35), §7 E4 (final delivered path), E8 (horizon strict-subset).
    docs/platform-plan-d0-d1.md D1 ("engine": topological_market_order,
    apply_links).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..config_io import iter_market_bodies
from ..core.protocols import LinkSpec

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

    from ..core.market.model import CarbonMarket

logger = logging.getLogger(__name__)

__all__ = [
    "apply_inbound_links",
    "build_link_specs",
    "check_horizon_alignment",
    "topological_market_order",
]


def build_link_specs(scenario: Mapping[str, Any]) -> tuple[LinkSpec, ...]:
    """Construct the ``LinkSpec`` tuple from a multi-market scenario's ``links``.

    Reads the scenario's ``links: [...]`` records and runs them through the
    ``market_links`` plugin door (``validate_links`` — the config-tier
    field/structural validator, D1-1: required fields, channel whitelist,
    endpoint existence, the ``mac_cost`` linear-target dimensional exclusion,
    and the price_unit-on-linked-market check), then materialises each
    normalized record as an immutable ``core.protocols.LinkSpec`` (the kernel
    parameter object whose ``__post_init__`` re-validates the bounds a second
    time — belt and braces).

    The market bodies passed to ``validate_links`` are the normalized bodies
    ``iter_market_bodies`` derives (endpoint existence and the linear-target
    check need them); a scenario with no ``markets`` key yields no bodies and
    an empty ``links`` list, so this returns ``()`` — the inertness default
    (spec §6).

    Args:
        scenario: A raw (not yet normalized) scenario dict — the multi-market
            ``markets``/``links`` shape (``docs/platform-spec-d0-d1.md`` §6).

    Returns:
        The scenario's links as ``LinkSpec`` objects, in declaration order
        (``validate_links`` does not reorder — topological ordering is
        :func:`topological_market_order`, and reporting stays in declaration
        order, spec §3).

    Raises:
        ValueError: Any plugin-door validation failure, or any ``LinkSpec``
            bound violation.
    """
    # Lazy T3 -> T2 plugin-door edge (activation scoping; the door is a
    # config-tier validator that imports only stdlib, already eagerly loaded
    # transitively via config_io — importing it here loads no channel runtime).
    from ..features.market_links.plugin import validate_links

    bodies = {market_id: body for market_id, body in iter_market_bodies(scenario) if market_id is not None}
    normalized_links = validate_links(scenario.get("links") or [], bodies)
    return tuple(
        LinkSpec(
            from_market=link["from_market"],
            to_market=link["to_market"],
            channel=link["channel"],
            phi=link["phi"],
            phi_unit=link["phi_unit"],
            target_participants=tuple(link["target_participants"]),
            target_technologies=tuple(link["target_technologies"]),
            back_demand_estimate=link["back_demand_estimate"],
        )
        for link in normalized_links
    )


def topological_market_order(
    market_ids: Sequence[str], links: Sequence[LinkSpec]
) -> list[str]:
    r"""Order markets so every link's source precedes its target (Kahn, deterministic).

    Recursive (block-recursive) partial equilibrium (spec §3): for the returned
    order ``m1..mK``, market ``k`` solves with its link-target inputs evaluated
    at already-solved ancestor paths as exogenous parameters. Each link
    ``A -> B`` is a DAG edge (``A`` before ``B``); a cycle is not a DAG and is
    D2's joint fixed point, rejected here (R34's engine-side enforcement).

    Algorithm:
        Kahn's topological sort with a deterministic ready-set tie-break.

        LaTeX:
        $$ \text{in-deg}(v) = \big|\{(u,v) : u \to v \in E\}\big|, \qquad
           R_0 = \{v : \text{in-deg}(v) = 0\}, $$
        $$ \text{pop } v \in R \text{ minimising } (\text{decl}(v),\, v);
           \;\; \text{in-deg}(w) \mathrel{-}= 1 \;\forall (v,w) \in E;
           \;\; |result| \ne |V| \Rightarrow \text{cycle}. $$

        ASCII fallback:
            E = { (from, to) } deduped per (from, to) pair
            in_deg[v] = number of distinct edges into v
            ready = { v : in_deg[v] == 0 }, sorted by (declared_index[v], v)
            while ready:
                pop v = min(ready) by (declared_index, id); emit v
                for each edge (v, w): in_deg[w] -= 1; add w when it hits 0
            if emitted != all markets: a cycle remains -> ValueError

        Symbols:
            V            : the market ids [-]
            E            : link edges, deduped per (from, to) pair (two links
                           on one pair with distinct channels are one DAG edge)
            decl(v)      : v's index in ``market_ids`` (declared order) [-]

    Args:
        market_ids: Every market id, in DECLARED order (the
            ``iter_market_bodies`` order — the primary tie-break key).
        links: The scenario's links; only ``(from_market, to_market)`` edges
            are read (channel/phi are irrelevant to ordering), deduped per
            pair.

    Returns:
        The market ids in a valid topological order; ties broken by declared
        order, then id (so the order is a deterministic function of the graph
        alone, invariant to link declaration order — anchor A3).

    Raises:
        ValueError: The link graph has a cycle (some markets never reach
            in-degree 0); the message names the residual markets and cites D2.
    """
    order_index = {market_id: index for index, market_id in enumerate(market_ids)}
    successors: dict[str, list[str]] = {market_id: [] for market_id in market_ids}
    in_degree: dict[str, int] = {market_id: 0 for market_id in market_ids}

    seen_edges: set[tuple[str, str]] = set()
    for link in links:
        edge = (link.from_market, link.to_market)
        if edge in seen_edges:
            continue  # two links on one (from, to) pair are ONE DAG edge (R35)
        seen_edges.add(edge)
        successors[link.from_market].append(link.to_market)
        in_degree[link.to_market] += 1

    def _key(market_id: str) -> tuple[int, str]:
        return (order_index[market_id], market_id)

    ready = sorted((m for m in market_ids if in_degree[m] == 0), key=_key)
    result: list[str] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        newly_ready: list[str] = []
        for successor in successors[node]:
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                newly_ready.append(successor)
        if newly_ready:
            ready.extend(newly_ready)
            ready.sort(key=_key)

    if len(result) != len(market_ids):
        cyclic = sorted(m for m in market_ids if in_degree[m] > 0)
        raise ValueError(
            f"Cyclic market links among {cyclic}: cyclic links are the joint "
            "fixed point, D2; D1 solves DAGs only (R34 engine-side enforcement). "
            "Break the cycle or defer to the D2 joint-solve."
        )
    return result


def check_horizon_alignment(
    links: Sequence[LinkSpec], market_bodies: Mapping[str, Any]
) -> None:
    r"""Enforce the E8 strict-subset horizon rule per link, at solve entry.

    Spec §7 E8: every link ``L(A -> B)`` requires ``label-set(B) ⊆
    label-set(A)`` — each target year must exist in the source's solved path,
    since ``P_A(t)`` is read contemporaneously at ``B``'s own year ``t``
    (the source ``A`` may carry extra years). The channel's per-year lookup
    (``channels._source_price``) already raises on a missing year, but that
    error would surface MID-SOLVE; this hoists the same check to a clean
    config-level ``ValueError`` before any market is solved (precedent: the
    D2.1 missing-year error).

    Rejected fillers (spec §7 E8): hold-last (a hidden random walk), zero-shift
    (a spurious boundary cliff at the trigger), interpolation (an unstated
    intra-gap price process) — the only sanctioned fix is adding the missing
    years to the source.

    Args:
        links: The scenario's links.
        market_bodies: Normalized market bodies keyed by market id; only each
            body's ``years[*]["year"]`` labels are read.

    Raises:
        ValueError: A link whose target declares a year absent from its
            source; the message names the missing years and the source market.
    """
    for link in links:
        source_years = {str(year["year"]) for year in market_bodies[link.from_market]["years"]}
        target_years = {str(year["year"]) for year in market_bodies[link.to_market]["years"]}
        missing = sorted(target_years - source_years)
        if missing:
            raise ValueError(
                f"Link {link.from_market}->{link.to_market}: target market "
                f"'{link.to_market}' declares year(s) {missing} absent from source "
                f"market '{link.from_market}' (spec §7 E8 strict-subset — every "
                f"target year must exist in the source's solved path). Add the "
                f"missing year(s) to '{link.from_market}'."
            )


def apply_inbound_links(
    target_market_id: str,
    target_markets: list[CarbonMarket],
    inbound_links: Sequence[LinkSpec],
    solved_delivered_paths: Mapping[str, Mapping[str, float]],
) -> list[CarbonMarket]:
    r"""Apply every inbound link to a target market, pure copy-on-write.

    For each link ``A -> target``, look up the channel factory in the reviewed
    ``engine.wiring.link_channels()`` registry, instantiate a fresh channel,
    and apply it to the (running) target markets reading ``A``'s FINAL
    converged DELIVERED price path (the E4 pin: never an intermediate iterate).
    Multiple inbound links compose by threading the copy-on-write output of one
    into the next; the additive-linear channels sum order-invariantly, so the
    result is independent of ``inbound_links`` order (invariant I6). Applied
    ONCE, BEFORE the path solve, never inside a fixed point (spec §2d).

    Algorithm:
        ASCII: markets := target_markets
               for link in inbound_links:
                   P_A := solved_delivered_paths[link.from_market]  # {year: price}
                   markets := link_channels()[link.channel]().apply(link, P_A, markets)
               return markets   # target_markets itself when nothing shifted

    Args:
        target_market_id: The market being shifted (error attribution / clarity;
            every ``inbound_links`` entry has ``to_market == target_market_id``).
        target_markets: The target market's per-year ``CarbonMarket`` list
            (never mutated — the channels are copy-on-write).
        inbound_links: The links whose ``to_market`` is ``target_market_id``.
        solved_delivered_paths: ``{market_id: {year_label: delivered_price}}``
            for every already-solved upstream market — the delivered price is
            ``item["equilibrium"]["price"]`` (post-overlay, floor-clipped; the
            same signal ``engine/feedback.py`` reads).

    Returns:
        The shifted markets (a new list), or ``target_markets`` itself when
        there are no inbound links or nothing matched (copy-on-write identity).
    """
    if not inbound_links:
        return target_markets

    # Lazy T3 -> T2: the channel registry (and thus the channel runtime) loads
    # only when a linked scenario actually applies a link (the wiring
    # link_channels precedent; import pe.engine loads no channel runtime).
    from .wiring import link_channels

    channels = link_channels()
    markets = target_markets
    for link in inbound_links:
        source_delivered_path = solved_delivered_paths[link.from_market]
        channel = channels[link.channel]()
        markets = channel.apply(link, source_delivered_path, markets)
    return markets
