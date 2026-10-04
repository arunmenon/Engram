"""Builders shared by the graph conformance suites."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from context_graph.domain.models import Edge, EdgeType, EntityNode, EntityType, EventNode

# The Neo4j vector index is declared with 384 dimensions.
EMBEDDING_DIMENSIONS = 384


def event_node(
    event_id: str | None = None,
    *,
    session_id: str = "s1",
    minutes_ago: float = 0,
    event_type: str = "tool.execute",
    importance_score: int | None = None,
    access_count: int = 0,
    tool_name: str | None = None,
    agent_id: str = "agent-1",
) -> EventNode:
    return EventNode(
        event_id=event_id or f"evt-{uuid4().hex[:8]}",
        event_type=event_type,
        occurred_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        session_id=session_id,
        agent_id=agent_id,
        trace_id="trace-1",
        tool_name=tool_name,
        global_position=f"{int(datetime.now(UTC).timestamp() * 1000)}-0",
        importance_score=importance_score,
        access_count=access_count,
    )


def entity_node(
    entity_id: str, *, name: str | None = None, embedding: list[float] | None = None
) -> EntityNode:
    now = datetime.now(UTC)
    return EntityNode(
        entity_id=entity_id,
        name=name or entity_id,
        entity_type=EntityType.CONCEPT,
        first_seen=now,
        last_seen=now,
        embedding=embedding or [],
    )


def edge(source: str, target: str, edge_type: EdgeType, **properties: object) -> Edge:
    return Edge(source=source, target=target, edge_type=edge_type, properties=dict(properties))


def unit_vector(axis: int, *, tilt: float = 0.0, tilt_axis: int = 1) -> list[float]:
    """A 384-d vector along ``axis``, optionally tilted toward ``tilt_axis``."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[axis] = 1.0
    if tilt:
        vector[tilt_axis] = tilt
    return vector
