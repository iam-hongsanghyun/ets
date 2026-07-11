"""Deterministic graph -> scenario-config dict compiler.

Implements the compile step of ``docs/blocks-graph-plan.md`` §2:

1. Each ``carbon_market`` node becomes one entry in ``{"scenarios": [...]}``,
   sorted by ``params["order"]`` then node id.
2. The market's ``price_formation`` edge (cardinality exactly 1) merges its
   scenario-level keys.
3. Each attached policy/expectations block merges its keys.
4. Participants attach via ``compliance`` edges into ``years[].participants``,
   ordered by ``params["order"]`` then node id; ``technology_option`` edges
   append ``technology_options``; ``strategic`` edges populate
   ``nash_strategic_participants`` (sorted by participant name).
5. The assembled dict passes through ``config_io.normalize_config`` — the
   single value validator — before being returned.

Ambiguity resolution (plan §2): edge array order carries no meaning; all
ordering comes from explicit ``order`` params with node-id tiebreak. Two
blocks writing the same config key on one market is a compile error, never
last-write-wins.

Per-year values: any ``ParamSpec`` (year-scope, or participant-scope inside
a market with varying yearly data) may be given either a plain value
(broadcast to every year of the market) or a per-year override map
``{"__per_year__": {year_label: value}}`` — see :func:`per_year_value` /
:func:`resolve_year_value`. This is the one generic mechanism the compiler
uses everywhere a field can vary by year; it applies uniformly to any
config_key, not just the ones the plan calls out by name.

Deliberate scope reduction: policy blocks carry an optional ``announced``
param (plan §1 "Policy timing") for validation (``validate.py`` R30), but
this compiler does not yet synthesise ``policy_events[]`` from it — that is
plan §2 step 3's generative direction and is deferred. ``policy_events`` is
instead round-tripped verbatim as an opaque pass-through param on the
``carbon_market`` node (see ``decompile.py``), which is sufficient for every
current example.

Dependency law: this module imports only ``ets.blocks`` siblings,
``ets.config_io``, and stdlib.
"""

from __future__ import annotations

from typing import Any

from ..config_io import normalize_config
from .catalogue import BLOCK_CATALOGUE
from .graph import Graph, Node
from .registry import BlockSpec

PER_YEAR_KEY = "__per_year__"

_MARKET_YEAR_GRID_KEYS = (
    "year",
    "total_cap",
    "auction_mode",
    "auction_offered",
    "reserved_allowances",
    "carbon_budget",
    "banking_allowed",
    "borrowing_allowed",
    "borrowing_limit",
)

# Every config_key the catalogue declares for each scope, plus the market's
# own structural grid keys. Anything a normalised config carries OUTSIDE
# these sets is a key no block owns — config_io tolerates unknown keys
# (normalize_* does ``blank.update(raw)``) for forward-compatible fields
# such as the documented-inert ``international_offset_*`` triad or a stray
# ``_comment``. Rather than silently dropping them (breaking round-trip) or
# hand-listing every such key, decompile.py stores them verbatim as opaque
# "_extra" params and compile.py replays them verbatim — a single generic
# mechanism, not a per-field special case.
KNOWN_SCENARIO_KEYS = frozenset(
    {p.config_key for block in BLOCK_CATALOGUE for p in block.params if p.scope == "scenario"}
)
KNOWN_YEAR_KEYS = frozenset(
    set(_MARKET_YEAR_GRID_KEYS)
    | {"participants"}
    | {p.config_key for block in BLOCK_CATALOGUE for p in block.params if p.scope == "year"}
)
KNOWN_PARTICIPANT_KEYS = frozenset(
    {p.config_key for block in BLOCK_CATALOGUE for p in block.params if p.scope == "participant"}
)


class CompileError(ValueError):
    """Raised when a graph cannot be compiled to a scenario-config dict."""


def per_year_value(values: dict[str, Any]) -> dict[str, Any]:
    """Wrap a ``{year_label: value}`` map as a per-year override."""
    return {PER_YEAR_KEY: dict(values)}


def is_per_year_value(raw: Any) -> bool:
    return isinstance(raw, dict) and set(raw.keys()) == {PER_YEAR_KEY}


def _coerce_json_shape(value: Any) -> Any:
    """Tuples are a convenient immutable ParamSpec default but config_io's
    normalisers require actual ``list`` instances (``isinstance(x, list)``
    checks) — coerce here, once, at the point every resolved value exits the
    compiler."""
    if isinstance(value, tuple):
        return list(value)
    return value


def resolve_year_value(raw: Any, year_label: str, default: Any) -> Any:
    """Resolve a param's raw value for one market year.

    ``raw`` is either a plain value (broadcast to every year) or a per-year
    override map produced by :func:`per_year_value`.
    """
    if raw is None:
        return _coerce_json_shape(default)
    if is_per_year_value(raw):
        table = raw[PER_YEAR_KEY]
        value = table[year_label] if year_label in table else default
        return _coerce_json_shape(value)
    return _coerce_json_shape(raw)


def _order_key(node: Node) -> tuple[float, str]:
    raw_order = node.params.get("order", 0)
    try:
        order = float(raw_order or 0)
    except (TypeError, ValueError):
        order = 0.0
    return (order, node.id)


def _require_node(graph: Graph, node_id: str, context: str) -> Node:
    node = graph.node(node_id)
    if node is None:
        raise CompileError(f"{context}: dangling reference to unknown node '{node_id}'.")
    return node


def _require_spec(node: Node) -> BlockSpec:
    if node.block not in BLOCK_CATALOGUE:
        raise CompileError(f"Node '{node.id}': unknown block id '{node.block}'.")
    return BLOCK_CATALOGUE.get(node.block)


class _FieldOwners:
    """Tracks which node "wrote" a scenario/year config key, for collision detection."""

    def __init__(self, market_id: str) -> None:
        self._market_id = market_id
        self._scenario: dict[str, str] = {}
        self._year: dict[tuple[str, str], str] = {}

    def set_scenario(self, fields: dict[str, Any], key: str, value: Any, owner: str) -> None:
        if key in self._scenario and self._scenario[key] != owner:
            raise CompileError(
                f"Market '{self._market_id}': both '{self._scenario[key]}' and "
                f"'{owner}' set scenario field '{key}'."
            )
        fields[key] = value
        self._scenario[key] = owner

    def set_year(
        self, year_entries: dict[str, dict[str, Any]], year_label: str, key: str, value: Any, owner: str
    ) -> None:
        marker = (year_label, key)
        if marker in self._year and self._year[marker] != owner:
            raise CompileError(
                f"Market '{self._market_id}' year '{year_label}': both "
                f"'{self._year[marker]}' and '{owner}' set '{key}'."
            )
        year_entries[year_label][key] = value
        self._year[marker] = owner


def compile_graph(graph: Graph) -> dict[str, Any]:
    """Compile a :class:`Graph` into a normalised scenario-config dict.

    Args:
        graph: The drawn block graph.

    Returns:
        ``{"scenarios": [...]}`` after passing through
        ``config_io.normalize_config``.

    Raises:
        CompileError: On structural problems the compiler cannot route
            around (dangling edges, wrong price-formation cardinality, a
            key written by two different blocks, an unknown block id).
        ValueError: Propagated from ``config_io`` value validation.
    """
    market_nodes = [n for n in graph.nodes if n.block == "carbon_market"]
    if not market_nodes:
        raise CompileError("Graph has no 'carbon_market' node.")
    market_nodes.sort(key=_order_key)
    scenarios = [_compile_market(graph, market_node) for market_node in market_nodes]
    return normalize_config({"scenarios": scenarios})


def _compile_market(graph: Graph, market_node: Node) -> dict[str, Any]:
    owners = _FieldOwners(market_node.id)
    scenario_fields: dict[str, Any] = {}
    year_entries: dict[str, dict[str, Any]] = {}

    years_raw = market_node.params.get("years") or []
    for raw_year in years_raw:
        label = str(raw_year.get("year"))
        entry = {k: v for k, v in raw_year.items() if k in _MARKET_YEAR_GRID_KEYS}
        entry["year"] = label
        year_entries[label] = entry
    if not year_entries:
        raise CompileError(f"Market '{market_node.id}' has no years in its 'years' grid.")

    owners.set_scenario(scenario_fields, "name", market_node.params.get("name", "New Scenario"), f"node:{market_node.id}")
    for passthrough_key in ("sectors", "policy_events"):
        raw = market_node.params.get(passthrough_key)
        if raw:
            owners.set_scenario(scenario_fields, passthrough_key, raw, f"node:{market_node.id}")

    # Opaque unknown-key passthrough (see KNOWN_*_KEYS docstring above).
    scenario_extra = market_node.params.get("_scenario_extra")
    if scenario_extra:
        for key, value in scenario_extra.items():
            owners.set_scenario(scenario_fields, key, value, f"node:{market_node.id}:_scenario_extra")
    year_extra_raw = market_node.params.get("_year_extra")
    if year_extra_raw:
        for year_label in year_entries:
            extra = resolve_year_value(year_extra_raw, year_label, {})
            for key, value in (extra or {}).items():
                owners.set_year(year_entries, year_label, key, value, f"node:{market_node.id}:_year_extra")

    _compile_price_formation(graph, market_node, owners, scenario_fields)
    _compile_policies(graph, market_node, owners, scenario_fields, year_entries)
    _compile_expectations(graph, market_node, owners, year_entries)
    _compile_baseline(graph, market_node, owners, scenario_fields)
    _compile_sectors(graph, market_node, owners, scenario_fields)
    _compile_participants(graph, market_node, year_entries)
    _compile_strategic(graph, market_node, owners, scenario_fields)

    return {**scenario_fields, "years": list(year_entries.values())}


def _merge_block_params(
    node: Node,
    spec: BlockSpec,
    owners: _FieldOwners,
    scenario_fields: dict[str, Any],
    year_entries: dict[str, dict[str, Any]] | None,
    owner_label: str,
    *,
    skip: frozenset[str] = frozenset(),
) -> None:
    """Merge every scope=="scenario"/"year" ParamSpec on ``node`` into the draft."""
    for param in spec.params:
        if param.config_key in skip:
            continue
        raw = node.params.get(param.name, param.default)
        if raw is None:
            continue
        if param.scope == "scenario":
            owners.set_scenario(scenario_fields, param.config_key, _coerce_json_shape(raw), owner_label)
        elif param.scope == "year" and year_entries is not None:
            for year_label in year_entries:
                value = resolve_year_value(raw, year_label, param.default)
                if value is None:
                    continue
                owners.set_year(year_entries, year_label, param.config_key, value, owner_label)


def _compile_price_formation(
    graph: Graph, market_node: Node, owners: _FieldOwners, scenario_fields: dict[str, Any]
) -> None:
    edges = graph.edges_into(market_node.id, "price_formation")
    if len(edges) != 1:
        raise CompileError(
            f"Market '{market_node.id}' must have exactly one price-formation edge "
            f"(found {len(edges)})."
        )
    pf_node = _require_node(graph, edges[0].source, f"Market '{market_node.id}' price_formation edge")
    pf_spec = _require_spec(pf_node)
    _merge_block_params(
        pf_node, pf_spec, owners, scenario_fields, None, f"node:{pf_node.id}",
        skip=frozenset({"nash_strategic_participants"}),
    )


def _compile_policies(
    graph: Graph,
    market_node: Node,
    owners: _FieldOwners,
    scenario_fields: dict[str, Any],
    year_entries: dict[str, dict[str, Any]],
) -> None:
    for edge in graph.edges_into(market_node.id, "policies"):
        policy_node = _require_node(graph, edge.source, f"Market '{market_node.id}' policy edge")
        policy_spec = _require_spec(policy_node)
        _merge_block_params(
            policy_node, policy_spec, owners, scenario_fields, year_entries,
            f"node:{policy_node.id}", skip=frozenset({"policy_events"}),
        )


def _compile_expectations(
    graph: Graph, market_node: Node, owners: _FieldOwners, year_entries: dict[str, dict[str, Any]]
) -> None:
    edges = graph.edges_into(market_node.id, "expectations")
    if len(edges) > 1:
        raise CompileError(f"Market '{market_node.id}' has more than one expectations edge.")
    if not edges:
        return
    node = _require_node(graph, edges[0].source, f"Market '{market_node.id}' expectations edge")
    spec = _require_spec(node)
    _merge_block_params(node, spec, owners, {}, year_entries, f"node:{node.id}")


def _compile_baseline(
    graph: Graph, market_node: Node, owners: _FieldOwners, scenario_fields: dict[str, Any]
) -> None:
    edges = graph.edges_into(market_node.id, "baseline")
    if len(edges) > 1:
        raise CompileError(f"Market '{market_node.id}' has more than one baseline edge.")
    if not edges:
        return
    node = _require_node(graph, edges[0].source, f"Market '{market_node.id}' baseline edge")
    spec = _require_spec(node)
    _merge_block_params(node, spec, owners, scenario_fields, None, f"node:{node.id}")


def _compile_sectors(
    graph: Graph, market_node: Node, owners: _FieldOwners, scenario_fields: dict[str, Any]
) -> None:
    edges = graph.edges_into(market_node.id, "sectors")
    if not edges:
        return
    node_ids = sorted({e.source for e in edges}, key=lambda nid: _order_key(_require_node(graph, nid, "sector edge")))
    sectors = []
    for node_id in node_ids:
        node = _require_node(graph, node_id, f"Market '{market_node.id}' sector edge")
        sectors.append(
            {
                "name": node.params.get("sector_name", "New Sector"),
                "cap_trajectory": node.params.get("cap_trajectory") or {},
                "auction_share_trajectory": node.params.get("auction_share_trajectory") or {},
                "carbon_budget": node.params.get("carbon_budget", 0.0),
            }
        )
    owners.set_scenario(scenario_fields, "sectors", sectors, "edges:sectors")


def _compile_participant_dict(node: Node, spec: BlockSpec, year_label: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for param in spec.params:
        raw = node.params.get(param.name, param.default)
        value = resolve_year_value(raw, year_label, param.default)
        if value is None:
            continue
        out[param.config_key] = value
    extra_raw = node.params.get("_extra")
    if extra_raw:
        extra = resolve_year_value(extra_raw, year_label, {})
        out.update(extra or {})
    return out


def _compile_participants(graph: Graph, market_node: Node, year_entries: dict[str, dict[str, Any]]) -> None:
    edges = graph.edges_into(market_node.id, "participants")
    if not edges:
        raise CompileError(f"Market '{market_node.id}' has no participants attached.")
    participant_ids = sorted(
        {e.source for e in edges},
        key=lambda nid: _order_key(_require_node(graph, nid, "participant edge")),
    )
    for entry in year_entries.values():
        entry["participants"] = []
    for participant_id in participant_ids:
        pnode = _require_node(graph, participant_id, f"Market '{market_node.id}' participant edge")
        pspec = _require_spec(pnode)
        option_edges = [e for e in graph.edges if e.target == participant_id and e.target_port == "options"]
        if option_edges and pnode.params.get("technology_options"):
            raise CompileError(
                f"Participant '{participant_id}' has both a 'technology_options' param "
                "and 'option' edges from technology_option nodes."
            )
        option_ids = sorted(
            {e.source for e in option_edges},
            key=lambda nid: _order_key(_require_node(graph, nid, "technology_option edge")),
        ) if option_edges else []
        for year_label, entry in year_entries.items():
            pdict = _compile_participant_dict(pnode, pspec, year_label)
            if option_ids:
                options = []
                for option_id in option_ids:
                    onode = _require_node(graph, option_id, f"Participant '{participant_id}' option edge")
                    ospec = _require_spec(onode)
                    options.append(_compile_participant_dict(onode, ospec, year_label))
                pdict["technology_options"] = options
            entry["participants"].append(pdict)


def _compile_strategic(
    graph: Graph, market_node: Node, owners: _FieldOwners, scenario_fields: dict[str, Any]
) -> None:
    edges = graph.edges_into(market_node.id, "price_formation")
    if not edges:
        return
    pf_node_id = edges[0].source
    strategic_edges = [e for e in graph.edges if e.target == pf_node_id and e.target_port == "strategic"]
    if not strategic_edges:
        return
    names = []
    for e in strategic_edges:
        node = _require_node(graph, e.source, f"Nash '{pf_node_id}' strategic edge")
        names.append(str(node.params.get("name", "")))
    owners.set_scenario(scenario_fields, "nash_strategic_participants", sorted(names), "edges:strategic")
