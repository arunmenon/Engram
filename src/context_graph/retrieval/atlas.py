"""Atlas response helpers for the retrieval engine (ADR-0006, ADR-0019).

Pure functions: graph property dicts in, Atlas models out.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from context_graph.domain.models import AtlasEdge, AtlasNode, NodeScores, Provenance

_PROVENANCE_KEYS = {"event_id", "global_position", "session_id", "agent_id", "trace_id"}


def build_atlas_node(
    record_props: dict[str, Any],
    scores: NodeScores,
    retrieval_reason: str = "direct",
    provenance_source: str = "redis",
) -> AtlasNode:
    """Convert event node properties to an AtlasNode with provenance.

    ``provenance_source`` names the event log backend the event came from.
    """
    event_id = record_props.get("event_id", "")
    occurred_at_raw = record_props.get("occurred_at")
    if isinstance(occurred_at_raw, str):
        occurred_at = datetime.fromisoformat(occurred_at_raw)
    else:
        occurred_at = datetime.now(UTC)

    provenance = Provenance(
        event_id=event_id,
        global_position=record_props.get("global_position", ""),
        source=provenance_source,
        occurred_at=occurred_at,
        session_id=record_props.get("session_id", ""),
        agent_id=record_props.get("agent_id", ""),
        trace_id=record_props.get("trace_id", ""),
    )

    attributes = {k: v for k, v in record_props.items() if k not in _PROVENANCE_KEYS}

    return AtlasNode(
        node_id=event_id,
        node_type="Event",
        attributes=attributes,
        provenance=provenance,
        scores=scores,
        retrieval_reason=retrieval_reason,
    )


def build_adjacency(
    nodes: dict[str, AtlasNode],
    edges: list[AtlasEdge],
    edge_weights: dict[str, float],
) -> dict[str, list[tuple[str, float]]]:
    """Build a bidirectional weighted adjacency list from nodes and edges (for PPR)."""
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for node_id in nodes:
        adjacency[node_id] = []
    for edge in edges:
        weight = edge_weights.get(edge.edge_type, 1.0)
        if edge.source in adjacency:
            adjacency[edge.source].append((edge.target, weight))
        if edge.target in adjacency:
            adjacency[edge.target].append((edge.source, weight))
    return adjacency
