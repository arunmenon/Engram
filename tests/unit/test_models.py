"""Unit tests for domain models (src/context_graph/domain/models.py).

Validates Pydantic model construction, field constraints, enum completeness,
and default values.  No external dependencies required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from context_graph.domain.models import (
    AtlasResponse,
    BeliefCategory,
    BeliefNode,
    EdgeType,
    EntityType,
    EpisodeNode,
    EpisodeType,
    Event,
    EventQuery,
    EventStatus,
    EventType,
    GoalNode,
    GoalStatus,
    IntentType,
    LineageQuery,
    NodeScores,
    NodeType,
    Provenance,
    SubgraphQuery,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _required_event_kwargs() -> dict:
    """Minimal keyword arguments that satisfy all required Event fields."""
    return {
        "event_id": uuid4(),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(UTC),
        "session_id": "test-session",
        "agent_id": "test-agent",
        "trace_id": "test-trace",
        "payload_ref": "payload:test",
    }


# ---------------------------------------------------------------------------
# Event — required fields
# ---------------------------------------------------------------------------


class TestEventCreation:
    """Tests for valid and invalid Event construction."""

    def test_valid_event_with_required_fields(self) -> None:
        """An Event built with all required fields should be accepted."""
        event = Event(**_required_event_kwargs())
        assert event.event_type == "tool.execute"
        assert event.session_id == "test-session"
        assert event.global_position is None

    def test_valid_event_with_all_optional_fields(self) -> None:
        """An Event with every optional field populated should be accepted."""
        kwargs = _required_event_kwargs()
        kwargs.update(
            {
                "tool_name": "web_search",
                "parent_event_id": uuid4(),
                "ended_at": datetime.now(UTC),
                "status": EventStatus.COMPLETED,
                "schema_version": 2,
                "importance_hint": 7,
                "global_position": "1700000000000-0",
            }
        )
        event = Event(**kwargs)
        assert event.tool_name == "web_search"
        assert event.status == EventStatus.COMPLETED
        assert event.schema_version == 2
        assert event.importance_hint == 7

    @pytest.mark.parametrize(
        "missing_field",
        [
            "event_id",
            "event_type",
            "occurred_at",
            "session_id",
            "agent_id",
            "trace_id",
            "payload_ref",
        ],
    )
    def test_event_rejects_missing_required_field(self, missing_field: str) -> None:
        """Omitting any single required field must raise ValidationError."""
        kwargs = _required_event_kwargs()
        del kwargs[missing_field]
        with pytest.raises(ValidationError):
            Event(**kwargs)


# ---------------------------------------------------------------------------
# Event — field-level constraints
# ---------------------------------------------------------------------------


class TestEventFieldConstraints:
    """Tests for individual field validators and constraints."""

    @pytest.mark.parametrize(
        "bad_type",
        [
            "noperiod",
            "Capital.letters",
            ".leading.dot",
            "trailing.",
            "double..dot",
            "has spaces.ok",
            "123.numeric_start",
        ],
    )
    def test_event_type_pattern_rejects_invalid(self, bad_type: str) -> None:
        """event_type must match ^[a-z][a-z0-9]*(\\.[a-z][a-z0-9_]*)+$."""
        kwargs = _required_event_kwargs()
        kwargs["event_type"] = bad_type
        with pytest.raises(ValidationError):
            Event(**kwargs)

    @pytest.mark.parametrize(
        "good_type",
        [
            "agent.invoke",
            "tool.execute",
            "llm.chat",
            "system.session_start",
            "observation.input",
            "user.preference.stated",
        ],
    )
    def test_event_type_pattern_accepts_valid(self, good_type: str) -> None:
        """Known good dot-namespaced event types must be accepted."""
        kwargs = _required_event_kwargs()
        kwargs["event_type"] = good_type
        event = Event(**kwargs)
        assert event.event_type == good_type

    def test_importance_hint_none_is_ok(self) -> None:
        """importance_hint defaults to None and that is valid."""
        event = Event(**_required_event_kwargs())
        assert event.importance_hint is None

    @pytest.mark.parametrize("value", [1, 5, 10])
    def test_importance_hint_valid_range(self, value: int) -> None:
        """importance_hint values 1-10 are accepted."""
        kwargs = _required_event_kwargs()
        kwargs["importance_hint"] = value
        event = Event(**kwargs)
        assert event.importance_hint == value

    @pytest.mark.parametrize("value", [0, -1, 11, 100])
    def test_importance_hint_invalid_range(self, value: int) -> None:
        """importance_hint outside 1-10 must be rejected."""
        kwargs = _required_event_kwargs()
        kwargs["importance_hint"] = value
        with pytest.raises(ValidationError):
            Event(**kwargs)

    def test_schema_version_defaults_to_one(self) -> None:
        """schema_version should default to 1."""
        event = Event(**_required_event_kwargs())
        assert event.schema_version == 1

    def test_schema_version_rejects_zero(self) -> None:
        """schema_version must be >= 1."""
        kwargs = _required_event_kwargs()
        kwargs["schema_version"] = 0
        with pytest.raises(ValidationError):
            Event(**kwargs)


# ---------------------------------------------------------------------------
# Enum completeness checks
# ---------------------------------------------------------------------------


class TestEnumCompleteness:
    """Verify enum members match the documented domain model."""

    def test_event_type_enum_values_are_dot_namespaced(self) -> None:
        """Every EventType value must contain at least one dot."""
        for member in EventType:
            assert "." in member.value, f"{member.name} value '{member.value}' has no dot"

    def test_entity_type_has_six_members(self) -> None:
        """EntityType must have exactly 6 members per ADR-0011."""
        assert len(EntityType) == 6
        expected = {"AGENT", "USER", "SERVICE", "TOOL", "RESOURCE", "CONCEPT"}
        assert {m.name for m in EntityType} == expected

    def test_edge_type_has_twenty_members(self) -> None:
        """EdgeType: 5 core + 4 new + 2 entity + 9 personalization = 20."""
        assert len(EdgeType) == 20

    def test_intent_type_has_eight_members(self) -> None:
        """IntentType must have all 8 intent categories."""
        assert len(IntentType) == 8
        expected = {
            "WHY",
            "WHEN",
            "WHAT",
            "RELATED",
            "GENERAL",
            "WHO_IS",
            "HOW_DOES",
            "PERSONALIZE",
        }
        assert {m.name for m in IntentType} == expected

    def test_node_type_has_eleven_members(self) -> None:
        """NodeType must have 3 core + 5 personalization + 3 episodic/belief/goal types."""
        assert len(NodeType) == 11

    def test_event_status_values(self) -> None:
        """EventStatus must have the five lifecycle states."""
        expected = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "TIMEOUT"}
        assert {m.name for m in EventStatus} == expected

    def test_retention_tier_order(self) -> None:
        """RetentionTier values should be hot, warm, cold, archive."""
        from context_graph.domain.models import RetentionTier

        values = [t.value for t in RetentionTier]
        assert values == ["hot", "warm", "cold", "archive"]


# ---------------------------------------------------------------------------
# SubgraphQuery
# ---------------------------------------------------------------------------


class TestSubgraphQuery:
    """Tests for SubgraphQuery model constraints."""

    def test_requires_query_session_agent(self) -> None:
        """SubgraphQuery must require query, session_id, and agent_id."""
        with pytest.raises(ValidationError):
            SubgraphQuery()  # type: ignore[call-arg]

    def test_valid_subgraph_query(self) -> None:
        """A properly constructed SubgraphQuery should be accepted."""
        sq = SubgraphQuery(query="what happened?", session_id="s1", agent_id="a1")
        assert sq.max_nodes == 100
        assert sq.max_depth == 3

    @pytest.mark.parametrize("value", [0, -1, 501, 1000])
    def test_max_nodes_out_of_bounds(self, value: int) -> None:
        """max_nodes must be between 1 and 500."""
        with pytest.raises(ValidationError):
            SubgraphQuery(query="q", session_id="s", agent_id="a", max_nodes=value)

    @pytest.mark.parametrize("value", [1, 250, 500])
    def test_max_nodes_in_bounds(self, value: int) -> None:
        """max_nodes values 1-500 should be accepted."""
        sq = SubgraphQuery(query="q", session_id="s", agent_id="a", max_nodes=value)
        assert sq.max_nodes == value

    @pytest.mark.parametrize("value", [0, -1, 11, 100])
    def test_max_depth_out_of_bounds(self, value: int) -> None:
        """max_depth must be between 1 and 10."""
        with pytest.raises(ValidationError):
            SubgraphQuery(query="q", session_id="s", agent_id="a", max_depth=value)

    @pytest.mark.parametrize("value", [1, 5, 10])
    def test_max_depth_in_bounds(self, value: int) -> None:
        """max_depth values 1-10 should be accepted."""
        sq = SubgraphQuery(query="q", session_id="s", agent_id="a", max_depth=value)
        assert sq.max_depth == value


# ---------------------------------------------------------------------------
# LineageQuery
# ---------------------------------------------------------------------------


class TestLineageQuery:
    """Tests for LineageQuery model constraints."""

    def test_requires_node_id(self) -> None:
        """LineageQuery must require node_id."""
        with pytest.raises(ValidationError):
            LineageQuery()  # type: ignore[call-arg]

    def test_valid_lineage_query_defaults(self) -> None:
        """A valid LineageQuery should have max_depth=3, max_nodes=100."""
        lq = LineageQuery(node_id="n1")
        assert lq.max_depth == 3
        assert lq.max_nodes == 100

    @pytest.mark.parametrize("value", [0, -1, 11])
    def test_max_depth_out_of_bounds(self, value: int) -> None:
        """max_depth must be between 1 and 10."""
        with pytest.raises(ValidationError):
            LineageQuery(node_id="n1", max_depth=value)


# ---------------------------------------------------------------------------
# EventQuery
# ---------------------------------------------------------------------------


class TestEventQuery:
    """Tests for EventQuery model defaults and constraints."""

    def test_defaults(self) -> None:
        """EventQuery with no arguments should use limit=100 and offset=0."""
        eq = EventQuery()
        assert eq.limit == 100
        assert eq.offset == 0

    def test_limit_bounds(self) -> None:
        """limit must be between 1 and 1000."""
        with pytest.raises(ValidationError):
            EventQuery(limit=0)
        with pytest.raises(ValidationError):
            EventQuery(limit=1001)

    def test_offset_non_negative(self) -> None:
        """offset must be >= 0."""
        with pytest.raises(ValidationError):
            EventQuery(offset=-1)


# ---------------------------------------------------------------------------
# AtlasResponse
# ---------------------------------------------------------------------------


class TestAtlasResponse:
    """Tests for the Atlas response envelope model."""

    def test_default_structure(self) -> None:
        """An AtlasResponse with no arguments should have empty nodes/edges."""
        resp = AtlasResponse()
        assert resp.nodes == {}
        assert resp.edges == []
        assert resp.pagination.cursor is None
        assert resp.pagination.has_more is False
        assert resp.meta.query_ms == 0
        assert resp.meta.nodes_returned == 0
        assert resp.meta.truncated is False


# ---------------------------------------------------------------------------
# NodeScores
# ---------------------------------------------------------------------------


class TestNodeScores:
    """Tests for NodeScores default values."""

    def test_defaults(self) -> None:
        """NodeScores should default all scores to zero."""
        scores = NodeScores()
        assert scores.decay_score == 0.0
        assert scores.relevance_score == 0.0
        assert scores.importance_score == 0


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    """Tests for Provenance model."""

    def test_requires_all_fields(self) -> None:
        """Provenance must require all core fields."""
        with pytest.raises(ValidationError):
            Provenance()  # type: ignore[call-arg]

    def test_valid_provenance(self) -> None:
        """A fully-populated Provenance should be accepted."""
        prov = Provenance(
            event_id="evt-123",
            global_position="1700000000000-0",
            occurred_at=datetime.now(UTC),
            session_id="s1",
            agent_id="a1",
            trace_id="t1",
        )
        assert prov.source == "redis"
        assert prov.event_id == "evt-123"


# ---------------------------------------------------------------------------
# New enum completeness
# ---------------------------------------------------------------------------


class TestNewEnums:
    """Tests for BeliefCategory, GoalStatus, EpisodeType enums."""

    def test_belief_category_has_three_members(self) -> None:
        assert len(BeliefCategory) == 3
        expected = {"USER_MODEL", "WORLD_MODEL", "CAPABILITY"}
        assert {m.name for m in BeliefCategory} == expected

    def test_goal_status_has_four_members(self) -> None:
        assert len(GoalStatus) == 4
        expected = {"ACTIVE", "COMPLETED", "ABANDONED", "SUPERSEDED"}
        assert {m.name for m in GoalStatus} == expected

    def test_episode_type_has_three_members(self) -> None:
        assert len(EpisodeType) == 3
        expected = {"TEMPORAL", "CAUSAL", "THEMATIC"}
        assert {m.name for m in EpisodeType} == expected

    def test_new_node_types_exist(self) -> None:
        assert NodeType.BELIEF == "Belief"
        assert NodeType.GOAL == "Goal"
        assert NodeType.EPISODE == "Episode"

    def test_new_edge_types_exist(self) -> None:
        assert EdgeType.CONTAINS == "CONTAINS"
        assert EdgeType.CONTRADICTS == "CONTRADICTS"
        assert EdgeType.PURSUES == "PURSUES"
        assert EdgeType.SUPERSEDES == "SUPERSEDES"


# ---------------------------------------------------------------------------
# New node models
# ---------------------------------------------------------------------------


class TestBeliefNode:
    """Tests for BeliefNode model."""

    def test_valid_belief_node(self) -> None:
        now = datetime.now(UTC)
        node = BeliefNode(
            belief_id="belief-1",
            belief_text="User prefers dark mode",
            confidence=0.85,
            category=BeliefCategory.USER_MODEL,
            created_at=now,
            last_confirmed_at=now,
        )
        assert node.belief_id == "belief-1"
        assert node.confidence == 0.85
        assert node.confirmation_count == 1
        assert node.superseded_by is None

    def test_belief_node_confidence_bounds(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            BeliefNode(
                belief_id="b1",
                belief_text="text",
                confidence=1.5,
                category=BeliefCategory.WORLD_MODEL,
                created_at=now,
                last_confirmed_at=now,
            )

    def test_belief_node_with_superseded_by(self) -> None:
        now = datetime.now(UTC)
        node = BeliefNode(
            belief_id="belief-old",
            belief_text="User likes light mode",
            confidence=0.3,
            category=BeliefCategory.USER_MODEL,
            created_at=now,
            last_confirmed_at=now,
            superseded_by="belief-new",
        )
        assert node.superseded_by == "belief-new"


class TestGoalNode:
    """Tests for GoalNode model."""

    def test_valid_goal_node(self) -> None:
        now = datetime.now(UTC)
        node = GoalNode(
            goal_id="goal-1",
            description="Complete project setup",
            status=GoalStatus.ACTIVE,
            created_at=now,
            last_active_at=now,
        )
        assert node.goal_id == "goal-1"
        assert node.status == GoalStatus.ACTIVE
        assert node.priority is None
        assert node.evidence_count == 1

    def test_goal_node_priority_bounds(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            GoalNode(
                goal_id="g1",
                description="test",
                status=GoalStatus.ACTIVE,
                created_at=now,
                last_active_at=now,
                priority=0,
            )
        with pytest.raises(ValidationError):
            GoalNode(
                goal_id="g1",
                description="test",
                status=GoalStatus.ACTIVE,
                created_at=now,
                last_active_at=now,
                priority=11,
            )

    def test_goal_node_valid_priority(self) -> None:
        now = datetime.now(UTC)
        node = GoalNode(
            goal_id="g1",
            description="test",
            status=GoalStatus.COMPLETED,
            created_at=now,
            last_active_at=now,
            priority=5,
        )
        assert node.priority == 5


class TestEpisodeNode:
    """Tests for EpisodeNode model."""

    def test_valid_episode_node(self) -> None:
        now = datetime.now(UTC)
        node = EpisodeNode(
            episode_id="ep-1",
            session_id="session-1",
            start_time=now,
            end_time=now,
            episode_type=EpisodeType.TEMPORAL,
        )
        assert node.episode_id == "ep-1"
        assert node.event_count == 0
        assert node.summary_id is None

    def test_episode_node_with_summary(self) -> None:
        now = datetime.now(UTC)
        node = EpisodeNode(
            episode_id="ep-2",
            session_id="session-1",
            start_time=now,
            end_time=now,
            event_count=15,
            episode_type=EpisodeType.CAUSAL,
            summary_id="summary-abc",
        )
        assert node.event_count == 15
        assert node.summary_id == "summary-abc"
        assert node.episode_type == EpisodeType.CAUSAL
