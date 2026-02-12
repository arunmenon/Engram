"""Event-to-graph projection logic.

Pure domain module — ZERO framework imports. Only depends on domain models.

Transforms immutable ``Event`` records into graph nodes and edges suitable
for MERGE into Neo4j. Consumer 1 (graph-projection) calls these functions
for every event received from the Redis Stream.

Source: ADR-0005, ADR-0009
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC

from context_graph.domain.models import CausalMechanism, Edge, EdgeType, Event, EventNode


@dataclass
class ProjectionResult:
    """Result of projecting a single event into graph primitives."""

    node: EventNode
    edges: list[Edge] = field(default_factory=list)


def event_to_node(event: Event) -> EventNode:
    """Transform an Event into an EventNode for Neo4j projection.

    Maps the required Event fields onto the EventNode schema. The
    ``global_position`` must already be set on the event (assigned
    during Redis ingestion).
    """
    if event.global_position is None:
        msg = "Event must have global_position set before projection"
        raise ValueError(msg)

    return EventNode(
        event_id=str(event.event_id),
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        session_id=event.session_id,
        agent_id=event.agent_id,
        trace_id=event.trace_id,
        tool_name=event.tool_name,
        global_position=event.global_position,
        importance_score=event.importance_hint,
    )


def _compute_delta_ms(earlier: Event, later: Event) -> int:
    """Compute elapsed milliseconds between two events' occurred_at timestamps."""
    earlier_ts = earlier.occurred_at
    later_ts = later.occurred_at

    # Ensure both timestamps are timezone-aware for subtraction
    if earlier_ts.tzinfo is None:
        earlier_ts = earlier_ts.replace(tzinfo=UTC)
    if later_ts.tzinfo is None:
        later_ts = later_ts.replace(tzinfo=UTC)

    delta = later_ts - earlier_ts
    return int(delta.total_seconds() * 1000)


def compute_follows_edge(prev_event: Event, curr_event: Event) -> Edge:
    """Create a FOLLOWS edge between consecutive session events.

    The FOLLOWS edge captures temporal ordering within a session.
    ``delta_ms`` records the elapsed time between the two events.
    """
    delta_ms = _compute_delta_ms(prev_event, curr_event)
    return Edge(
        source=str(curr_event.event_id),
        target=str(prev_event.event_id),
        edge_type=EdgeType.FOLLOWS,
        properties={
            "session_id": curr_event.session_id,
            "delta_ms": delta_ms,
        },
    )


def compute_caused_by_edge(event: Event) -> Edge | None:
    """Create a CAUSED_BY edge if the event has a parent_event_id.

    Returns ``None`` when there is no causal parent.
    """
    if event.parent_event_id is None:
        return None

    return Edge(
        source=str(event.event_id),
        target=str(event.parent_event_id),
        edge_type=EdgeType.CAUSED_BY,
        properties={"mechanism": CausalMechanism.DIRECT},
    )


def project_event(event: Event, prev_event: Event | None) -> ProjectionResult:
    """Full projection pipeline for a single event.

    1. Create an EventNode from the event.
    2. If ``prev_event`` exists and belongs to the same session, create a
       FOLLOWS edge.
    3. If the event has a ``parent_event_id``, create a CAUSED_BY edge.

    Returns a ``ProjectionResult`` containing the node and all computed edges.
    """
    node = event_to_node(event)
    edges: list[Edge] = []

    # FOLLOWS edge — only within the same session
    if prev_event is not None and prev_event.session_id == event.session_id:
        edges.append(compute_follows_edge(prev_event, event))

    # CAUSED_BY edge — if causal parent is declared
    caused_by = compute_caused_by_edge(event)
    if caused_by is not None:
        edges.append(caused_by)

    return ProjectionResult(node=node, edges=edges)
