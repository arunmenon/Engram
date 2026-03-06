from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from engram.models import (
    AtlasNode,
    AtlasResponse,
    BatchResult,
    BehavioralPatternNode,
    DetailedHealthResponse,
    EntityResponse,
    Event,
    GDPRDeleteResponse,
    GDPRExportResponse,
    HealthStatus,
    IngestResult,
    IntentType,
    InterestNode,
    Memory,
    NodeScores,
    Pagination,
    PreferenceNode,
    Provenance,
    PruneResponse,
    ReconsolidateResponse,
    SkillNode,
    SubgraphQuery,
    UserProfile,
)


class TestEvent:
    def test_event_serialization(self):
        event_id = uuid4()
        now = datetime.now(timezone.utc)
        event = Event(
            event_id=event_id,
            event_type="tool.execute",
            occurred_at=now,
            session_id="sess-1",
            agent_id="agent-1",
            trace_id="trace-1",
            payload_ref="test data",
        )
        data = event.model_dump(mode="json")
        restored = Event.model_validate(data)
        assert restored.event_id == event_id
        assert restored.event_type == "tool.execute"
        assert restored.session_id == "sess-1"

    def test_event_optional_fields(self):
        event = Event(
            event_id=uuid4(),
            event_type="agent.invoke",
            occurred_at=datetime.now(timezone.utc),
            session_id="sess-1",
            agent_id="agent-1",
            trace_id="trace-1",
            payload_ref="data",
        )
        assert event.global_position is None
        assert event.tool_name is None
        assert event.parent_event_id is None
        assert event.ended_at is None
        assert event.status is None
        assert event.importance_hint is None
        assert event.payload is None

    def test_event_importance_bounds(self):
        with pytest.raises(PydanticValidationError):
            Event(
                event_id=uuid4(),
                event_type="x",
                occurred_at=datetime.now(timezone.utc),
                session_id="s",
                agent_id="a",
                trace_id="t",
                payload_ref="p",
                importance_hint=0,
            )
        with pytest.raises(PydanticValidationError):
            Event(
                event_id=uuid4(),
                event_type="x",
                occurred_at=datetime.now(timezone.utc),
                session_id="s",
                agent_id="a",
                trace_id="t",
                payload_ref="p",
                importance_hint=11,
            )
        event = Event(
            event_id=uuid4(),
            event_type="x",
            occurred_at=datetime.now(timezone.utc),
            session_id="s",
            agent_id="a",
            trace_id="t",
            payload_ref="p",
            importance_hint=5,
        )
        assert event.importance_hint == 5


class TestAtlasResponse:
    def test_atlas_response_empty(self):
        resp = AtlasResponse()
        assert resp.nodes == {}
        assert resp.edges == []
        assert resp.pagination.has_more is False
        assert resp.pagination.cursor is None
        assert resp.meta.query_ms == 0

    def test_atlas_response_full(self):
        now = datetime.now(timezone.utc)
        data = {
            "nodes": {
                "evt-1": {
                    "node_id": "evt-1",
                    "node_type": "Event",
                    "attributes": {"tool_name": "search"},
                    "provenance": {
                        "event_id": "evt-1",
                        "global_position": "1707644400000-0",
                        "source": "redis",
                        "occurred_at": now.isoformat(),
                        "session_id": "sess-1",
                        "agent_id": "agent-1",
                        "trace_id": "trace-1",
                    },
                    "scores": {"decay_score": 0.9, "relevance_score": 0.8, "importance_score": 7},
                    "retrieval_reason": "direct",
                }
            },
            "edges": [
                {
                    "source": "evt-1",
                    "target": "evt-2",
                    "edge_type": "FOLLOWS",
                    "properties": {"delta_ms": 100},
                }
            ],
            "pagination": {"cursor": "next-page", "has_more": True},
            "meta": {
                "query_ms": 145,
                "nodes_returned": 1,
                "truncated": False,
                "inferred_intents": {"why": 0.7},
                "seed_nodes": ["evt-1"],
                "proactive_nodes_count": 0,
                "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
            },
        }
        resp = AtlasResponse.model_validate(data)
        assert len(resp.nodes) == 1
        assert resp.nodes["evt-1"].node_type == "Event"
        assert resp.nodes["evt-1"].scores.decay_score == 0.9
        assert len(resp.edges) == 1
        assert resp.edges[0].edge_type == "FOLLOWS"
        assert resp.pagination.has_more is True
        assert resp.meta.query_ms == 145


class TestIngestResult:
    def test_ingest_result_parse(self):
        data = {"event_id": "abc-123", "global_position": "1707644400000-0"}
        result = IngestResult.model_validate(data)
        assert result.event_id == "abc-123"
        assert result.global_position == "1707644400000-0"


class TestBatchResult:
    def test_batch_result_parse(self):
        data = {
            "accepted": 3,
            "rejected": 1,
            "results": [
                {"event_id": "e1", "global_position": "100-0"},
                {"event_id": "e2", "global_position": "100-1"},
                {"event_id": "e3", "global_position": "100-2"},
            ],
            "errors": [{"index": 3, "error": "invalid event_type"}],
        }
        result = BatchResult.model_validate(data)
        assert result.accepted == 3
        assert result.rejected == 1
        assert len(result.results) == 3
        assert len(result.errors) == 1


class TestHealthStatus:
    def test_health_status_parse(self):
        data = {"status": "healthy", "redis": True, "neo4j": True, "version": "0.1.0"}
        hs = HealthStatus.model_validate(data)
        assert hs.status == "healthy"
        assert hs.redis is True
        assert hs.neo4j is True
        assert hs.version == "0.1.0"


class TestUserProfile:
    def test_user_profile_parse(self):
        data = {
            "profile_id": "p1",
            "user_id": "u1",
            "display_name": "Alice",
            "timezone": "UTC",
            "language": "en",
        }
        profile = UserProfile.model_validate(data)
        assert profile.display_name == "Alice"
        assert profile.communication_style is None
        assert profile.technical_level is None


class TestSubgraphQuery:
    def test_subgraph_query_defaults(self):
        q = SubgraphQuery(query="test", session_id="s1", agent_id="a1")
        assert q.max_nodes == 100
        assert q.max_depth == 3
        assert q.timeout_ms == 5000
        assert q.intent is None
        assert q.seed_nodes is None
        assert q.cursor is None


class TestIntentType:
    def test_intent_type_enum(self):
        assert IntentType.WHY.value == "why"
        assert IntentType.WHEN.value == "when"
        assert IntentType.WHAT.value == "what"
        assert IntentType.RELATED.value == "related"
        assert IntentType.GENERAL.value == "general"
        assert IntentType.WHO_IS.value == "who_is"
        assert IntentType.HOW_DOES.value == "how_does"
        assert IntentType.PERSONALIZE.value == "personalize"
        assert len(IntentType) == 8


class TestProvenance:
    def test_provenance_parse(self):
        now = datetime.now(timezone.utc)
        data = {
            "event_id": "evt-1",
            "global_position": "1707644400000-0",
            "source": "redis",
            "occurred_at": now.isoformat(),
            "session_id": "sess-1",
            "agent_id": "agent-1",
            "trace_id": "trace-1",
        }
        prov = Provenance.model_validate(data)
        assert prov.event_id == "evt-1"
        assert prov.source == "redis"


class TestNodeScores:
    def test_atlas_node_scores_defaults(self):
        scores = NodeScores()
        assert scores.decay_score == 0.0
        assert scores.relevance_score == 0.0
        assert scores.importance_score == 0


class TestPagination:
    def test_pagination_defaults(self):
        p = Pagination()
        assert p.cursor is None
        assert p.has_more is False


# --- New model tests ---


class TestPreferenceNode:
    def test_defaults(self):
        pref = PreferenceNode()
        assert pref.preference_id == ""
        assert pref.polarity == "positive"
        assert pref.confidence == 0.0

    def test_parse(self):
        pref = PreferenceNode.model_validate(
            {"preference_id": "p1", "category": "ui", "key": "theme", "value": "dark"}
        )
        assert pref.preference_id == "p1"
        assert pref.category == "ui"

    def test_extra_fields_allowed(self):
        pref = PreferenceNode.model_validate({"extra_field": "allowed"})
        assert pref.extra_field == "allowed"  # type: ignore[attr-defined]


class TestSkillNode:
    def test_defaults(self):
        skill = SkillNode()
        assert skill.skill_id == ""
        assert skill.name == ""
        assert skill.level == ""

    def test_parse(self):
        skill = SkillNode.model_validate(
            {"skill_id": "s1", "name": "python", "level": "expert", "confidence": 0.95}
        )
        assert skill.name == "python"
        assert skill.confidence == 0.95


class TestBehavioralPatternNode:
    def test_defaults(self):
        bp = BehavioralPatternNode()
        assert bp.pattern_id == ""
        assert bp.frequency == 0

    def test_parse(self):
        bp = BehavioralPatternNode.model_validate(
            {"pattern_id": "bp1", "pattern_type": "temporal", "description": "morning coder"}
        )
        assert bp.pattern_type == "temporal"
        assert bp.description == "morning coder"


class TestInterestNode:
    def test_defaults(self):
        interest = InterestNode()
        assert interest.entity_id == ""
        assert interest.strength == 0.0

    def test_parse(self):
        interest = InterestNode.model_validate(
            {"entity_id": "e1", "name": "AI", "entity_type": "topic", "strength": 0.9}
        )
        assert interest.name == "AI"
        assert interest.strength == 0.9


class TestEntityResponse:
    def test_defaults(self):
        entity = EntityResponse()
        assert entity.entity_id is None
        assert entity.name is None

    def test_parse(self):
        entity = EntityResponse.model_validate(
            {"entity_id": "ent-1", "name": "Test", "entity_type": "concept"}
        )
        assert entity.entity_id == "ent-1"
        assert entity.entity_type == "concept"

    def test_extra_fields_allowed(self):
        entity = EntityResponse.model_validate({"entity_id": "e1", "custom": "value"})
        assert entity.custom == "value"  # type: ignore[attr-defined]


class TestGDPRModels:
    def test_export_response(self):
        resp = GDPRExportResponse.model_validate({"events": [{"id": "1"}], "entities": []})
        assert len(resp.events) == 1
        assert resp.entities == []

    def test_delete_response(self):
        resp = GDPRDeleteResponse.model_validate({"deleted_nodes": 5, "deleted_edges": 10})
        assert resp.deleted_nodes == 5
        assert resp.deleted_edges == 10

    def test_delete_response_defaults(self):
        resp = GDPRDeleteResponse()
        assert resp.deleted_nodes == 0
        assert resp.deleted_edges == 0


class TestAdminResponseModels:
    def test_reconsolidate_response(self):
        resp = ReconsolidateResponse.model_validate({"status": "started"})
        assert resp.status == "started"

    def test_prune_response(self):
        resp = PruneResponse.model_validate({"pruned": 10, "dry_run": False})
        assert resp.pruned == 10
        assert resp.dry_run is False

    def test_prune_response_defaults(self):
        resp = PruneResponse()
        assert resp.pruned == 0
        assert resp.dry_run is True

    def test_detailed_health_response(self):
        resp = DetailedHealthResponse.model_validate(
            {"redis": {"connected": True}, "neo4j": {"connected": False}}
        )
        assert resp.redis == {"connected": True}
        assert resp.neo4j == {"connected": False}

    def test_detailed_health_extra_fields(self):
        resp = DetailedHealthResponse.model_validate({"redis": {}, "workers": {"count": 4}})
        assert resp.workers == {"count": 4}  # type: ignore[attr-defined]


class TestMemory:
    def test_memory_defaults(self):
        mem = Memory(text="hello")
        assert mem.text == "hello"
        assert mem.score == 0.0
        assert mem.memory_id == ""
        assert mem.node_type == ""
        assert mem.source_session == ""

    def test_memory_full(self):
        mem = Memory(
            text="test memory",
            memory_id="m1",
            node_type="Event",
            score=0.85,
            source_session="sess-1",
            confidence=0.9,
        )
        assert mem.text == "test memory"
        assert mem.score == 0.85


class TestAtlasResponseConvenience:
    def _make_atlas_with_nodes(self) -> AtlasResponse:
        now = datetime.now(timezone.utc)
        return AtlasResponse(
            nodes={
                "evt-1": AtlasNode(
                    node_id="evt-1",
                    node_type="Event",
                    attributes={"content": "User asked about payments"},
                    provenance=Provenance(
                        event_id="evt-1",
                        global_position="100-0",
                        occurred_at=now,
                        session_id="sess-1",
                        agent_id="agent-1",
                        trace_id="trace-1",
                    ),
                    scores=NodeScores(decay_score=0.9, relevance_score=0.8, importance_score=7),
                ),
                "evt-2": AtlasNode(
                    node_id="evt-2",
                    node_type="Summary",
                    attributes={"summary": "Payment inquiry summary"},
                    scores=NodeScores(decay_score=0.5, relevance_score=0.6, importance_score=3),
                ),
                "evt-3": AtlasNode(
                    node_id="evt-3",
                    node_type="Entity",
                    attributes={"name": "payment"},
                ),
            }
        )

    def test_node_ids(self):
        atlas = self._make_atlas_with_nodes()
        assert atlas.node_ids == ["evt-1", "evt-2", "evt-3"]

    def test_node_ids_empty(self):
        atlas = AtlasResponse()
        assert atlas.node_ids == []

    def test_texts(self):
        atlas = self._make_atlas_with_nodes()
        texts = atlas.texts()
        assert len(texts) == 3
        assert "User asked about payments" in texts
        assert "Payment inquiry summary" in texts
        assert "payment" in texts

    def test_texts_empty(self):
        atlas = AtlasResponse()
        assert atlas.texts() == []

    def test_as_context_string(self):
        atlas = self._make_atlas_with_nodes()
        context = atlas.as_context_string()
        assert "[Event] User asked about payments (score: 0.90)" in context
        assert "[Summary] Payment inquiry summary (score: 0.50)" in context
        assert "[Entity] payment (score: 0.00)" in context
        assert "---" in context

    def test_as_context_string_custom_separator(self):
        atlas = self._make_atlas_with_nodes()
        context = atlas.as_context_string(separator="\n\n")
        assert "\n\n" in context
        assert "---" not in context

    def test_as_context_string_empty(self):
        atlas = AtlasResponse()
        assert atlas.as_context_string() == ""

    def test_texts_priority_order(self):
        """content is preferred over payload_ref, summary, etc."""
        atlas = AtlasResponse(
            nodes={
                "n1": AtlasNode(
                    node_id="n1",
                    node_type="Event",
                    attributes={"content": "primary", "summary": "secondary"},
                ),
            }
        )
        texts = atlas.texts()
        assert texts == ["primary"]
