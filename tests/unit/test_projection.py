"""Unit tests for the domain projection logic.

Pure unit tests — no infrastructure required. Tests verify the
event-to-graph transformation produces correct nodes and edges.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context_graph.domain.models import CausalMechanism, EdgeType
from context_graph.domain.projection import (
    ProjectionResult,
    compute_caused_by_edge,
    compute_follows_edge,
    event_to_node,
    project_event,
)
from tests.fixtures.events import make_event, make_session_events

# ---------------------------------------------------------------------------
# event_to_node
# ---------------------------------------------------------------------------


class TestEventToNode:
    """Tests for event_to_node()."""

    def test_maps_all_required_fields(self) -> None:
        event = make_event(global_position="1707644400000-0")
        node = event_to_node(event)

        assert node.event_id == str(event.event_id)
        assert node.event_type == event.event_type
        assert node.occurred_at == event.occurred_at
        assert node.session_id == event.session_id
        assert node.agent_id == event.agent_id
        assert node.trace_id == event.trace_id
        assert node.global_position == "1707644400000-0"

    def test_maps_tool_name_when_present(self) -> None:
        event = make_event(
            tool_name="search-api",
            global_position="1707644400000-1",
        )
        node = event_to_node(event)
        assert node.tool_name == "search-api"

    def test_tool_name_none_when_absent(self) -> None:
        event = make_event(global_position="1707644400000-2")
        node = event_to_node(event)
        assert node.tool_name is None

    def test_maps_importance_hint_to_importance_score(self) -> None:
        event = make_event(
            importance_hint=8,
            global_position="1707644400000-3",
        )
        node = event_to_node(event)
        assert node.importance_score == 8

    def test_importance_score_none_when_no_hint(self) -> None:
        event = make_event(global_position="1707644400000-4")
        node = event_to_node(event)
        assert node.importance_score is None

    def test_raises_when_global_position_missing(self) -> None:
        event = make_event()  # global_position defaults to None
        import pytest

        with pytest.raises(ValueError, match="global_position"):
            event_to_node(event)

    def test_default_enrichment_fields_are_empty(self) -> None:
        event = make_event(global_position="1707644400000-5")
        node = event_to_node(event)
        assert node.keywords == []
        assert node.summary is None
        assert node.embedding == []
        assert node.access_count == 0
        assert node.last_accessed_at is None


# ---------------------------------------------------------------------------
# compute_follows_edge
# ---------------------------------------------------------------------------


class TestComputeFollowsEdge:
    """Tests for compute_follows_edge()."""

    def test_creates_follows_edge(self) -> None:
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        prev = make_event(
            occurred_at=base_time,
            session_id="sess-1",
            global_position="100-0",
        )
        curr = make_event(
            occurred_at=base_time + timedelta(seconds=5),
            session_id="sess-1",
            global_position="100-1",
        )

        edge = compute_follows_edge(prev, curr)

        assert edge.edge_type == EdgeType.FOLLOWS
        assert edge.source == str(curr.event_id)
        assert edge.target == str(prev.event_id)

    def test_delta_ms_calculated_correctly(self) -> None:
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        prev = make_event(
            occurred_at=base_time,
            global_position="100-0",
        )
        curr = make_event(
            occurred_at=base_time + timedelta(milliseconds=1500),
            global_position="100-1",
        )

        edge = compute_follows_edge(prev, curr)

        assert edge.properties["delta_ms"] == 1500

    def test_session_id_in_properties(self) -> None:
        prev = make_event(
            session_id="sess-abc",
            global_position="100-0",
        )
        curr = make_event(
            session_id="sess-abc",
            global_position="100-1",
        )

        edge = compute_follows_edge(prev, curr)

        assert edge.properties["session_id"] == "sess-abc"

    def test_zero_delta_for_simultaneous_events(self) -> None:
        timestamp = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        prev = make_event(occurred_at=timestamp, global_position="100-0")
        curr = make_event(occurred_at=timestamp, global_position="100-1")

        edge = compute_follows_edge(prev, curr)

        assert edge.properties["delta_ms"] == 0


# ---------------------------------------------------------------------------
# compute_caused_by_edge
# ---------------------------------------------------------------------------


class TestComputeCausedByEdge:
    """Tests for compute_caused_by_edge()."""

    def test_creates_caused_by_edge_with_parent(self) -> None:
        from uuid import uuid4

        parent_id = uuid4()
        event = make_event(
            parent_event_id=parent_id,
            global_position="100-0",
        )

        edge = compute_caused_by_edge(event)

        assert edge is not None
        assert edge.edge_type == EdgeType.CAUSED_BY
        assert edge.source == str(event.event_id)
        assert edge.target == str(parent_id)

    def test_mechanism_is_direct(self) -> None:
        from uuid import uuid4

        event = make_event(
            parent_event_id=uuid4(),
            global_position="100-0",
        )

        edge = compute_caused_by_edge(event)

        assert edge is not None
        assert edge.properties["mechanism"] == CausalMechanism.DIRECT

    def test_returns_none_without_parent(self) -> None:
        event = make_event(global_position="100-0")

        edge = compute_caused_by_edge(event)

        assert edge is None


# ---------------------------------------------------------------------------
# project_event
# ---------------------------------------------------------------------------


class TestProjectEvent:
    """Tests for project_event()."""

    def test_first_event_in_session_has_no_follows(self) -> None:
        event = make_event(global_position="100-0")

        result = project_event(event, prev_event=None)

        assert isinstance(result, ProjectionResult)
        assert result.node.event_id == str(event.event_id)
        follows_edges = [e for e in result.edges if e.edge_type == EdgeType.FOLLOWS]
        assert len(follows_edges) == 0

    def test_second_event_in_session_has_follows(self) -> None:
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        prev = make_event(
            session_id="sess-1",
            occurred_at=base_time,
            global_position="100-0",
        )
        curr = make_event(
            session_id="sess-1",
            occurred_at=base_time + timedelta(seconds=2),
            global_position="100-1",
        )

        result = project_event(curr, prev_event=prev)

        follows_edges = [e for e in result.edges if e.edge_type == EdgeType.FOLLOWS]
        assert len(follows_edges) == 1
        assert follows_edges[0].source == str(curr.event_id)
        assert follows_edges[0].target == str(prev.event_id)

    def test_no_follows_edge_across_different_sessions(self) -> None:
        prev = make_event(session_id="sess-1", global_position="100-0")
        curr = make_event(session_id="sess-2", global_position="100-1")

        result = project_event(curr, prev_event=prev)

        follows_edges = [e for e in result.edges if e.edge_type == EdgeType.FOLLOWS]
        assert len(follows_edges) == 0

    def test_caused_by_edge_when_parent_exists(self) -> None:
        from uuid import uuid4

        parent_id = uuid4()
        event = make_event(
            parent_event_id=parent_id,
            global_position="100-0",
        )

        result = project_event(event, prev_event=None)

        caused_by_edges = [e for e in result.edges if e.edge_type == EdgeType.CAUSED_BY]
        assert len(caused_by_edges) == 1
        assert caused_by_edges[0].target == str(parent_id)

    def test_no_caused_by_edge_without_parent(self) -> None:
        event = make_event(global_position="100-0")

        result = project_event(event, prev_event=None)

        caused_by_edges = [e for e in result.edges if e.edge_type == EdgeType.CAUSED_BY]
        assert len(caused_by_edges) == 0

    def test_both_follows_and_caused_by(self) -> None:
        from uuid import uuid4

        parent_id = uuid4()
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)

        prev = make_event(
            session_id="sess-1",
            occurred_at=base_time,
            global_position="100-0",
        )
        curr = make_event(
            session_id="sess-1",
            occurred_at=base_time + timedelta(seconds=1),
            parent_event_id=parent_id,
            global_position="100-1",
        )

        result = project_event(curr, prev_event=prev)

        edge_types = {e.edge_type for e in result.edges}
        assert EdgeType.FOLLOWS in edge_types
        assert EdgeType.CAUSED_BY in edge_types
        assert len(result.edges) == 2

    def test_session_events_produce_correct_follows_chain(self) -> None:
        """Verify a sequence of session events produces FOLLOWS edges."""
        events = make_session_events(n=3, session_id="chain-test")
        # Assign global_positions
        for idx, event in enumerate(events):
            events[idx] = event.model_copy(update={"global_position": f"100-{idx}"})

        results: list[ProjectionResult] = []
        prev = None
        for event in events:
            result = project_event(event, prev_event=prev)
            results.append(result)
            prev = event

        # First event: no FOLLOWS
        assert len([e for e in results[0].edges if e.edge_type == EdgeType.FOLLOWS]) == 0

        # Second event: FOLLOWS first
        follows_1 = [e for e in results[1].edges if e.edge_type == EdgeType.FOLLOWS]
        assert len(follows_1) == 1
        assert follows_1[0].source == str(events[1].event_id)
        assert follows_1[0].target == str(events[0].event_id)

        # Third event: FOLLOWS second
        follows_2 = [e for e in results[2].edges if e.edge_type == EdgeType.FOLLOWS]
        assert len(follows_2) == 1
        assert follows_2[0].source == str(events[2].event_id)
        assert follows_2[0].target == str(events[1].event_id)
