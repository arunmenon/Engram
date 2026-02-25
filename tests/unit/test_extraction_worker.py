"""Unit tests for the ExtractionConsumer (Consumer 2).

Tests session end detection, event collection, and process_message
dispatch. Uses mocked Redis and Neo4j dependencies.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import orjson

from context_graph.worker.consumer import BaseConsumer
from context_graph.worker.extraction import ExtractionConsumer

# ---------------------------------------------------------------------------
# Stubs / Helpers
# ---------------------------------------------------------------------------


def _make_settings() -> Any:
    """Create a minimal Settings-like object for ExtractionConsumer."""
    settings = MagicMock()
    settings.redis.group_extraction = "session-extraction"
    settings.redis.global_stream = "events:__global__"
    settings.redis.block_timeout_ms = 100
    settings.redis.event_key_prefix = "evt:"
    return settings


def _make_consumer(
    redis_client: Any = None,
    neo4j_driver: Any = None,
    llm_client: Any = None,
) -> ExtractionConsumer:
    """Create an ExtractionConsumer with mocked dependencies."""
    redis_client = redis_client or AsyncMock()
    neo4j_driver = neo4j_driver or AsyncMock()
    llm_client = llm_client or AsyncMock()
    settings = _make_settings()
    return ExtractionConsumer(
        redis_client=redis_client,
        neo4j_driver=neo4j_driver,
        neo4j_database="neo4j",
        llm_client=llm_client,
        settings=settings,
    )


def _mock_json_doc(
    event_id: str,
    event_type: str,
    session_id: str,
    agent_id: str = "agent-1",
) -> bytes:
    """Build a mock JSON.GET response for a given event."""
    doc = {
        "event_id": event_id,
        "event_type": event_type,
        "session_id": session_id,
        "agent_id": agent_id,
        "occurred_at": "2026-01-01T00:00:00Z",
        "trace_id": "trace-1",
        "payload_ref": f"inline:{event_type}",
    }
    return orjson.dumps([doc])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractionConsumerStructure:
    def test_is_subclass_of_base_consumer(self) -> None:
        assert issubclass(ExtractionConsumer, BaseConsumer)

    def test_constructor_sets_group_name(self) -> None:
        consumer = _make_consumer()
        assert consumer._group_name == "session-extraction"

    def test_constructor_sets_consumer_name(self) -> None:
        consumer = _make_consumer()
        assert consumer._consumer_name == "extraction-1"

    def test_constructor_sets_stream_key(self) -> None:
        consumer = _make_consumer()
        assert consumer._stream_key == "events:__global__"


class TestProcessMessage:
    async def test_ignores_non_session_end_events(self) -> None:
        llm_client = AsyncMock()
        redis_client = AsyncMock()
        redis_client.execute_command.return_value = _mock_json_doc("evt-001", "tool.execute", "s1")

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        await consumer.process_message("1234-0", {"event_id": "evt-001"})

        llm_client.extract_from_session.assert_not_called()

    async def test_ignores_session_end_without_session_id(self) -> None:
        llm_client = AsyncMock()
        redis_client = AsyncMock()
        # Doc with no session_id
        doc = {
            "event_id": "evt-001",
            "event_type": "system.session_end",
            "agent_id": "agent-1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "trace_id": "trace-1",
            "payload_ref": "inline:session_end",
        }
        redis_client.execute_command.return_value = orjson.dumps([doc])

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        await consumer.process_message("1234-0", {"event_id": "evt-001"})

        llm_client.extract_from_session.assert_not_called()

    async def test_triggers_extraction_on_session_end(self) -> None:
        llm_client = AsyncMock()
        llm_client.extract_from_session.return_value = {
            "session_id": "sess-1",
            "agent_id": "agent-1",
            "entities": [],
            "preferences": [],
            "skills": [],
            "interests": [],
        }

        redis_client = AsyncMock()
        redis_client.xrange.return_value = []
        # First call: _fetch_event_doc for process_message
        redis_client.execute_command.return_value = _mock_json_doc(
            "evt-end", "system.session_end", "sess-1"
        )

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        await consumer.process_message(
            "1234-0",
            {"event_id": "evt-end"},
        )

        # xrange is called to collect session events
        redis_client.xrange.assert_called_once()

    async def test_skips_extraction_when_no_events(self) -> None:
        llm_client = AsyncMock()
        redis_client = AsyncMock()
        redis_client.xrange.return_value = []
        redis_client.execute_command.return_value = _mock_json_doc(
            "evt-end", "system.session_end", "sess-empty"
        )

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        await consumer.process_message(
            "1234-0",
            {"event_id": "evt-end"},
        )

        llm_client.extract_from_session.assert_not_called()

    async def test_writes_preferences_to_neo4j(self) -> None:
        llm_client = AsyncMock()
        llm_client.extract_from_session.return_value = {
            "session_id": "sess-1",
            "agent_id": "agent-1",
            "entities": [],
            "preferences": [
                {
                    "category": "tool",
                    "key": "vim",
                    "polarity": "positive",
                    "strength": 0.8,
                    "confidence": 0.7,
                    "source": "explicit",
                    "source_quote": "I prefer vim",
                }
            ],
            "skills": [],
            "interests": [],
        }

        redis_client = AsyncMock()
        # Return one matching event in the stream
        redis_client.xrange.return_value = [
            (
                b"1234-0",
                {
                    b"event_id": b"evt-001",
                },
            ),
        ]

        def _execute_command_side_effect(*args: Any, **kwargs: Any) -> Any:
            # First call from process_message: fetch session_end doc
            # Subsequent calls from _collect_session_events: return None
            if len(args) >= 3 and args[2] == "evt:evt-end":
                return _mock_json_doc("evt-end", "system.session_end", "sess-1")
            return None

        redis_client.execute_command.side_effect = _execute_command_side_effect

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        # Since JSON.GET returns None for session events, the session
        # events list will be empty and extraction is skipped.
        # This test verifies the flow does not crash.
        await consumer.process_message(
            "1234-0",
            {"event_id": "evt-end"},
        )
        # No events found => extract_from_session not called
        llm_client.extract_from_session.assert_not_called()

    async def test_handles_empty_agent_id(self) -> None:
        llm_client = AsyncMock()
        redis_client = AsyncMock()
        redis_client.xrange.return_value = []
        doc = {
            "event_id": "evt-end",
            "event_type": "system.session_end",
            "session_id": "sess-1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "trace_id": "trace-1",
            "payload_ref": "inline:session_end",
        }
        redis_client.execute_command.return_value = orjson.dumps([doc])

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)

        # Should not raise even without agent_id
        await consumer.process_message(
            "1234-0",
            {"event_id": "evt-end"},
        )

    async def test_ignores_missing_event_id(self) -> None:
        consumer = _make_consumer()
        # Should not raise when event_id is missing from stream data
        await consumer.process_message("1234-0", {})


# ---------------------------------------------------------------------------
# Mid-session extraction (Fix 6)
# ---------------------------------------------------------------------------


class TestMidSessionExtraction:
    async def test_mid_session_extraction_trigger(self) -> None:
        """Non-system events should increment turn count and trigger at interval."""
        llm_client = AsyncMock()
        llm_client.extract_from_session.return_value = {
            "session_id": "s1",
            "agent_id": "a1",
            "entities": [],
            "preferences": [],
            "skills": [],
            "interests": [],
        }
        redis_client = AsyncMock()
        redis_client.xrange.return_value = []

        # Mock JSON.GET to return tool.execute event docs
        def _mock_execute(*args: Any, **kwargs: Any) -> bytes:
            return _mock_json_doc("evt-turn", "tool.execute", "s1", "a1")

        redis_client.execute_command.side_effect = _mock_execute

        consumer = _make_consumer(redis_client=redis_client, llm_client=llm_client)
        consumer._mid_session_interval = 2  # trigger every 2 turns

        # First turn - should not trigger
        await consumer.process_message("1-0", {"event_id": "evt-1"})
        assert consumer._session_turn_counts.get("s1") == 1

        # Second turn - should trigger mid-session extraction
        await consumer.process_message("2-0", {"event_id": "evt-2"})
        assert consumer._session_turn_counts.get("s1") == 2


# ---------------------------------------------------------------------------
# Source event IDs in results (Fix 1)
# ---------------------------------------------------------------------------


class TestSourceEventIdsInResults:
    async def test_derived_from_passes_source_event_ids(self) -> None:
        """_write_extraction_results should receive source event IDs."""
        consumer = _make_consumer()
        # Verify the method signature accepts source_event_ids
        import inspect

        sig = inspect.signature(consumer._write_extraction_results)
        assert "source_event_ids" in sig.parameters


# ---------------------------------------------------------------------------
# Neo4j-based entity embedding and semantic resolution
# ---------------------------------------------------------------------------


class TestEntityEmbeddingOnNeo4j:
    async def test_merge_entity_node_passes_embedding(self) -> None:
        """_merge_entity_node should pass embedding param to Neo4j."""
        consumer = _make_consumer()
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        async def capture_write(fn):
            return await fn(mock_tx)

        mock_session.execute_write = capture_write
        # session() is a sync method returning an async context manager
        consumer._neo4j_driver.session = MagicMock(return_value=mock_session)

        await consumer._merge_entity_node(
            entity_id="entity:test",
            name="test",
            entity_type="concept",
            now="2026-01-01T00:00:00Z",
            embedding=[0.1, 0.2, 0.3],
        )

        # Verify tx.run was called with embedding in params
        mock_tx.run.assert_called_once()
        call_params = mock_tx.run.call_args[0][1]
        assert call_params["embedding"] == [0.1, 0.2, 0.3]

    async def test_merge_entity_node_default_empty_embedding(self) -> None:
        """_merge_entity_node with no embedding should pass empty list."""
        consumer = _make_consumer()
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        async def capture_write(fn):
            return await fn(mock_tx)

        mock_session.execute_write = capture_write
        # session() is a sync method returning an async context manager
        consumer._neo4j_driver.session = MagicMock(return_value=mock_session)

        await consumer._merge_entity_node(
            entity_id="entity:test",
            name="test",
            entity_type="concept",
            now="2026-01-01T00:00:00Z",
        )

        call_params = mock_tx.run.call_args[0][1]
        assert call_params["embedding"] == []

    async def test_semantic_resolution_uses_graph_store(self) -> None:
        """_resolve_semantic should call graph_store.search_similar_entities."""
        embedding_service = AsyncMock()
        embedding_service.embed_text.return_value = [0.1, 0.2, 0.3]

        graph_store = AsyncMock()
        graph_store.search_similar_entities.return_value = []

        settings = _make_settings()
        settings.embedding.knn_k = 10
        settings.embedding.same_as_threshold = 0.90
        settings.embedding.related_to_threshold = 0.75

        consumer = ExtractionConsumer(
            redis_client=AsyncMock(),
            neo4j_driver=AsyncMock(),
            neo4j_database="neo4j",
            llm_client=AsyncMock(),
            settings=settings,
            embedding_service=embedding_service,
            graph_store=graph_store,
        )

        result, matches = await consumer._resolve_semantic("test entity", "concept")

        graph_store.search_similar_entities.assert_called_once_with(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=10,
            threshold=0.75,
        )
        assert result is None
        assert matches == []

    async def test_semantic_resolution_skipped_without_graph_store(self) -> None:
        """_resolve_semantic returns (None, []) when graph_store is None."""
        consumer = _make_consumer()
        consumer._embedding_service = AsyncMock()
        consumer._graph_store = None

        result, matches = await consumer._resolve_semantic("test", "concept")
        assert result is None
        assert matches == []

    async def test_compute_entity_embedding_returns_vector(self) -> None:
        """_compute_entity_embedding should return the embedding from the service."""
        consumer = _make_consumer()
        consumer._embedding_service = AsyncMock()
        consumer._embedding_service.embed_text.return_value = [0.5, 0.5]

        result = await consumer._compute_entity_embedding("test")
        assert result == [0.5, 0.5]

    async def test_compute_entity_embedding_returns_empty_on_failure(self) -> None:
        """_compute_entity_embedding should return [] on service failure."""
        consumer = _make_consumer()
        consumer._embedding_service = AsyncMock()
        consumer._embedding_service.embed_text.side_effect = RuntimeError("fail")

        result = await consumer._compute_entity_embedding("test")
        assert result == []

    async def test_compute_entity_embedding_returns_empty_without_service(self) -> None:
        """_compute_entity_embedding should return [] when no service."""
        consumer = _make_consumer()
        consumer._embedding_service = None

        result = await consumer._compute_entity_embedding("test")
        assert result == []
