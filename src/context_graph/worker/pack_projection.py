"""Apply pack projection plans through the PackGraph port (ADR-0018).

``domain/pack_projection.py`` plans the writes for an event; this applies
them in order: nodes (with stubs for referenced artifacts), lifecycle
transitions, lookups for matched targets, then edges, so every edge finds
both endpoints.

Backend-neutral: uses only ``PackGraph`` operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from context_graph.ports.pack_graph import EdgeWrite
from context_graph.ports.pack_graph import NodeRef as GraphRef

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import EdgeLookup, ProjectionPlan
    from context_graph.ports.pack_graph import PackGraph

log = structlog.get_logger(__name__)

# Fields that order matches for ``to_latest``, most specific first
LATEST_ORDER = ("started_at", "occurred_at", "updated_at")


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


def _latest(nodes: list[dict[str, Any]], key_property: str) -> list[dict[str, Any]]:
    """The most recent node, by the first ordering field any match has; ties by key."""
    if not nodes:
        return []
    for order_field in LATEST_ORDER:
        dated = [n for n in nodes if n.get(order_field)]
        if dated:
            return [max(dated, key=lambda n: (str(n[order_field]), str(n.get(key_property))))]
    return [max(nodes, key=lambda n: str(n.get(key_property)))]


async def resolve_lookups(
    graph: PackGraph, lookups: list[EdgeLookup], limit: int
) -> list[EdgeWrite]:
    edges: list[EdgeWrite] = []
    for lookup in lookups:
        found = await graph.find_nodes(lookup.label, lookup.equals, limit)
        if len(found) >= limit:
            log.warning(
                "pack_lookup_limit_reached",
                label=lookup.label,
                edge_type=lookup.edge_type,
                limit=limit,
            )
        matched = [node for node in found if _matches_prefix(node, lookup)]
        if lookup.latest:
            matched = _latest(matched, lookup.key_property)
        for node in matched:
            key = node.get(lookup.key_property)
            if key is None:
                continue
            target = GraphRef(lookup.label, str(key), lookup.key_property)
            edges.append(EdgeWrite(lookup.edge_type, lookup.source, target, lookup.properties))
    return edges


async def apply_plan(graph: PackGraph, plan: ProjectionPlan, lookup_limit: int) -> int:
    """Write a plan; returns the number of edges written."""
    if plan.empty:
        return 0
    await graph.upsert_nodes(plan.nodes)
    await graph.change_states(plan.states)
    edges = [*plan.edges, *await resolve_lookups(graph, plan.lookups, lookup_limit)]
    written = await graph.upsert_edges(edges)
    log.debug(
        "pack_plan_applied",
        nodes=len(plan.nodes),
        states=len(plan.states),
        edges=written,
    )
    return written
