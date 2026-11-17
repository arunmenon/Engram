"""Apply pack projection plans through the PackGraph port (ADR-0018).

``domain/pack_projection.py`` plans the writes for an event; this applies
them in order: nodes (with stubs for referenced artifacts), lifecycle
transitions, lookups for matched targets, then edges, so every edge finds
both endpoints.

Backend-neutral: uses only ``PackGraph`` operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.domain.pack_projection import LATEST_FALLBACK
from context_graph.ports.pack_graph import EdgeWrite
from context_graph.ports.pack_graph import NodeRef as GraphRef

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import EdgeLookup, ProjectionPlan
    from context_graph.ports.pack_graph import PackGraph

log = structlog.get_logger(__name__)


def _under(path: str, prefix: str) -> bool:
    """Whether ``path`` is ``prefix`` or inside it (``src`` matches ``src/x``, not ``src2/x``)."""
    if not prefix:
        return False
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/")


def _matches_prefix(node: dict[str, Any], lookup: EdgeLookup) -> bool:
    if lookup.prefix_field is None:
        return True
    declared = node.get(lookup.prefix_field) or []
    if isinstance(declared, str):
        declared = [declared]
    return any(_under(path, prefix) for prefix in declared for path in lookup.prefixes)


def _latest(nodes: list[dict[str, Any]], lookup: EdgeLookup) -> list[dict[str, Any]]:
    """The match ``find_latest`` would pick, among nodes already read."""
    order_by = lookup.order_by or LATEST_FALLBACK
    dated = [
        n
        for n in nodes
        if n.get(order_by) is not None
        and (lookup.not_after is None or str(n[order_by]) <= lookup.not_after)
    ]
    if not dated:
        return []
    return [max(dated, key=lambda n: (str(n[order_by]), str(n.get(lookup.key_property))))]


async def resolve_lookups(
    graph: PackGraph, lookups: list[EdgeLookup], limit: int
) -> list[EdgeWrite]:
    """Edges to the nodes each lookup finds.

    Identical lookups (same type, values, ordering and cutoff) are read
    once: a flush of changes in one repository asks for that repository's
    components once, not once per change.
    """
    edges: list[EdgeWrite] = []
    latest_cache: dict[str, dict[str, Any] | None] = {}
    found_cache = await _prefetch(graph, lookups, limit)
    for lookup in lookups:
        if lookup.latest and lookup.prefix_field is None:
            # The backend orders and limits: right however many nodes match
            order_by = lookup.order_by or LATEST_FALLBACK
            key = _cache_key(lookup.label, lookup.equals, order_by, lookup.not_after)
            if key not in latest_cache:
                latest_cache[key] = await graph.find_latest(
                    lookup.label, lookup.equals, order_by, lookup.not_after
                )
            node = latest_cache[key]
            edges.extend(_edges(lookup, [node] if node is not None else []))
            continue
        key = _cache_key(lookup.label, lookup.equals, limit)
        if key not in found_cache:
            found_cache[key] = await graph.find_nodes(lookup.label, lookup.equals, limit)
            if len(found_cache[key]) >= limit:
                log.warning(
                    "pack_lookup_limit_reached",
                    label=lookup.label,
                    edge_type=lookup.edge_type,
                    limit=limit,
                )
        matched = [node for node in found_cache[key] if _matches_prefix(node, lookup)]
        if lookup.latest:
            matched = _latest(matched, lookup)
        edges.extend(_edges(lookup, matched))
    return edges


async def _prefetch(
    graph: PackGraph, lookups: list[EdgeLookup], limit: int
) -> dict[str, list[dict[str, Any]]]:
    """The matches of every distinct non-latest lookup, one call per type and field set."""
    groups: dict[tuple[str, tuple[str, ...]], dict[str, dict[str, Any]]] = {}
    for lookup in lookups:
        if lookup.latest and lookup.prefix_field is None:
            continue
        group = groups.setdefault((lookup.label, tuple(sorted(lookup.equals))), {})
        group.setdefault(_cache_key(lookup.label, lookup.equals, limit), lookup.equals)
    found: dict[str, list[dict[str, Any]]] = {}
    for (label, _fields), conditions in groups.items():
        answers = await graph.find_nodes_matching(label, list(conditions.values()), limit)
        found.update(zip(conditions, answers, strict=True))
    return found


def _cache_key(label: str, equals: dict[str, Any], *rest: Any) -> str:
    return orjson.dumps([label, equals, *rest], option=orjson.OPT_SORT_KEYS).decode()


def _edges(lookup: EdgeLookup, matched: list[dict[str, Any]]) -> list[EdgeWrite]:
    edges = []
    for node in matched:
        key = node.get(lookup.key_property)
        if key is None:
            continue
        found = GraphRef(lookup.label, str(key), lookup.key_property)
        source, target = (found, lookup.known) if lookup.reverse else (lookup.known, found)
        edges.append(
            EdgeWrite(
                lookup.edge_type,
                source,
                target,
                lookup.properties,
                remove_properties=lookup.remove_properties,
            )
        )
    return edges


async def apply_plan(graph: PackGraph, plan: ProjectionPlan, lookup_limit: int) -> int:
    """Write a plan; returns the number of edges written."""
    return await apply_plans(graph, [plan], lookup_limit)


async def apply_plans(graph: PackGraph, plans: list[ProjectionPlan], lookup_limit: int) -> int:
    """Write several events' plans, in log order, in four stages; returns edges written.

    All nodes, then all lifecycle transitions (in order: a later event's
    transition sees an earlier one's), then the lookups, then all edges.
    That is one call per stage for a whole projection flush instead of one
    per stage per event. Lookups see every node of the flush, and a
    ``to_latest`` lookup still never looks past its own event's time.
    Node writes only set properties and create states on creation, so
    writing a later event's nodes before an earlier event's transitions
    leaves the same graph.
    """
    for plan in plans:
        for reason in plan.rejected:
            log.warning("pack_write_rejected", reason=reason)
    plans = [plan for plan in plans if not plan.empty]
    if not plans:
        return 0
    nodes = [node for plan in plans for node in plan.nodes]
    states = [state for plan in plans for state in plan.states]
    lookups = [lookup for plan in plans for lookup in plan.lookups]
    if nodes:
        await graph.upsert_nodes(nodes)
    if states:
        await graph.change_states(states)
    edges = [edge for plan in plans for edge in plan.edges]
    edges += await resolve_lookups(graph, lookups, lookup_limit)
    written = await graph.upsert_edges(edges) if edges else 0
    log.debug(
        "pack_plans_applied",
        events=len(plans),
        nodes=len(nodes),
        states=len(states),
        edges=written,
    )
    return written
