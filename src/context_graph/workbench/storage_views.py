"""Bounded observed rows for workbench evidence; never substitute projected writes."""

from __future__ import annotations

import asyncio
import copy
from typing import TYPE_CHECKING, Any

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.subscription import MemorySubscription

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend


def memory_snapshot(graph: MemoryGraphStore) -> dict[str, Any]:
    return {
        "nodes": [
            {"type": k[0], "id": k[1], "properties": copy.deepcopy(v)}
            for k, v in graph.nodes.items()
        ],
        "edges": [
            {"source": a[1], "type": kind, "target": b[1], "properties": copy.deepcopy(props)}
            for (a, kind, b), props in graph.edges.items()
        ],
    }


def spanner_snapshot(database: Any, fence: Any) -> dict[str, Any]:
    from context_graph.adapters.spanner.log import json_value
    from context_graph.adapters.spanner.tenant_control import tenant_snapshot

    if fence is None:
        raise ValueError("Workbench Spanner evidence requires an owned sandbox binding")
    # Read graph and owner in one consistent snapshot. One extra row detects a
    # budget violation instead of silently presenting a truncated graph as proof.
    with tenant_snapshot(database, fence, operation="read") as snapshot:
        nodes = list(snapshot.execute_sql("SELECT label, node_id, props FROM GraphNodes LIMIT 501"))
        edges = list(
            snapshot.execute_sql(
                "SELECT src_id, edge_type, dst_id, props FROM GraphEdges LIMIT 2001"
            )
        )
    return {
        "nodes": [
            {"type": label, "id": ident, "properties": json_value(props)}
            for label, ident, props in nodes
        ],
        "edges": [
            {"source": src, "type": kind, "target": dst, "properties": json_value(props)}
            for src, kind, dst, props in edges
        ],
    }


async def observed_graph(graph: GraphBackend) -> dict[str, Any]:
    from context_graph.adapters.spanner.graph import SpannerGraphStore

    if isinstance(graph, MemoryGraphStore):
        result = memory_snapshot(graph)
    elif isinstance(graph, SpannerGraphStore):
        result = await asyncio.to_thread(spanner_snapshot, graph._database, graph._tenant_fence)
    else:
        raise ValueError("Unsupported workbench evidence backend")
    if len(result["nodes"]) > 500 or len(result["edges"]) > 2000:
        raise ValueError("Sandbox exceeded its 500-node / 2000-edge budget")
    return result


async def observed_dead_letters(subscription: Any) -> list[Any]:
    from context_graph.adapters.spanner.subscription import SpannerSubscription

    if isinstance(subscription, MemorySubscription):
        return copy.deepcopy(subscription.dead_letters)
    if isinstance(subscription, SpannerSubscription):
        return await subscription.dead_letters()
    raise ValueError("Unsupported workbench subscription backend")
