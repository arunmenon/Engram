"""Unit tests for the EntityEmbeddingStore Redis adapter.

Tests vector storage, KNN search, deletion, and retrieval using a
mocked async Redis client. No live Redis instance required.
"""

from __future__ import annotations

import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.redis.embedding_store import (
    EntityEmbeddingStore,
    SemanticMatch,
    _float_vector_to_bytes,
)

# ---------------------------------------------------------------------------
# _float_vector_to_bytes
# ---------------------------------------------------------------------------


class TestFloatVectorToBytes:
    def test_packs_known_values_correctly(self) -> None:
        vector = [1.0, 0.0, -1.0]
        result = _float_vector_to_bytes(vector)
        unpacked = struct.unpack("<3f", result)
        assert unpacked == pytest.approx((1.0, 0.0, -1.0))
        assert len(result) == 3 * 4  # 3 floats * 4 bytes each

    def test_empty_list_produces_empty_bytes(self) -> None:
        result = _float_vector_to_bytes([])
        assert result == b""


# ---------------------------------------------------------------------------
# SemanticMatch
# ---------------------------------------------------------------------------


class TestSemanticMatch:
    def test_creation_with_all_fields(self) -> None:
        match = SemanticMatch(
            entity_id="ent-123",
            name="Python",
            entity_type="concept",
            distance=0.25,
            similarity=0.75,
        )
        assert match.entity_id == "ent-123"
        assert match.name == "Python"
        assert match.entity_type == "concept"
        assert match.distance == 0.25
        assert match.similarity == 0.75

    def test_similarity_equals_one_minus_distance(self) -> None:
        distance = 0.3
        similarity = round(1.0 - distance, 6)
        match = SemanticMatch(
            entity_id="ent-456",
            name="Redis",
            entity_type="tool",
            distance=distance,
            similarity=similarity,
        )
        assert match.similarity == pytest.approx(1.0 - match.distance)


# ---------------------------------------------------------------------------
# EntityEmbeddingStore
# ---------------------------------------------------------------------------


class TestEntityEmbeddingStore:
    @pytest.fixture()
    def mock_redis(self) -> AsyncMock:
        """Create a mocked async Redis client."""
        client = AsyncMock()
        # ft() is a sync method that returns an object with async search
        ft_mock = MagicMock()
        ft_mock.search = AsyncMock()
        client.ft = MagicMock(return_value=ft_mock)
        # pipeline() is a sync method that returns a pipeline object
        pipe_mock = MagicMock()
        pipe_mock.execute_command = MagicMock()
        pipe_mock.execute = AsyncMock(return_value=[])
        client.pipeline = MagicMock(return_value=pipe_mock)
        return client

    @pytest.fixture()
    def store(self, mock_redis: AsyncMock) -> EntityEmbeddingStore:
        """Create an EntityEmbeddingStore with a mocked Redis client."""
        return EntityEmbeddingStore(
            redis_client=mock_redis,
            prefix="entity_emb:",
            index_name="idx:entity_embeddings",
        )

    async def test_store_embedding(
        self, store: EntityEmbeddingStore, mock_redis: AsyncMock
    ) -> None:
        """Verify JSON.SET is called with the correct key and document."""
        await store.store_embedding(
            entity_id="ent-1",
            name="Python",
            entity_type="concept",
            embedding=[0.1, 0.2, 0.3],
        )
        mock_redis.execute_command.assert_awaited_once()
        call_args = mock_redis.execute_command.call_args
        assert call_args[0][0] == "JSON.SET"
        assert call_args[0][1] == "entity_emb:ent-1"
        assert call_args[0][2] == "$"
        # The fourth arg is the JSON-encoded doc string
        import orjson

        stored_doc = orjson.loads(call_args[0][3])
        assert stored_doc["entity_id"] == "ent-1"
        assert stored_doc["name"] == "Python"
        assert stored_doc["entity_type"] == "concept"
        assert stored_doc["embedding"] == [0.1, 0.2, 0.3]

    async def test_store_batch_pipeline(
        self, store: EntityEmbeddingStore, mock_redis: AsyncMock
    ) -> None:
        """Verify pipeline is used for batch writes with correct keys."""
        entities = [
            {"entity_id": "ent-a", "name": "Redis", "entity_type": "tool"},
            {"entity_id": "ent-b", "name": "Neo4j", "entity_type": "tool"},
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        await store.store_batch(entities, embeddings)

        pipe_mock = mock_redis.pipeline.return_value
        mock_redis.pipeline.assert_called_once_with(transaction=False)
        assert pipe_mock.execute_command.call_count == 2
        pipe_mock.execute.assert_awaited_once()

        # Verify first call writes ent-a
        first_call = pipe_mock.execute_command.call_args_list[0]
        assert first_call[0][0] == "JSON.SET"
        assert first_call[0][1] == "entity_emb:ent-a"

        # Verify second call writes ent-b
        second_call = pipe_mock.execute_command.call_args_list[1]
        assert second_call[0][1] == "entity_emb:ent-b"

    @patch("redis.commands.search.query.Query")
    async def test_search_similar_no_filter(
        self,
        mock_query_cls: MagicMock,
        store: EntityEmbeddingStore,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify FT.SEARCH KNN query without type filter uses wildcard."""
        # Set up the Query mock chain
        query_instance = MagicMock()
        query_instance.sort_by.return_value = query_instance
        query_instance.return_fields.return_value = query_instance
        query_instance.paging.return_value = query_instance
        query_instance.dialect.return_value = query_instance
        mock_query_cls.return_value = query_instance

        # Empty search results
        search_result = MagicMock()
        search_result.docs = []
        mock_redis.ft.return_value.search = AsyncMock(return_value=search_result)

        await store.search_similar(query_embedding=[0.1, 0.2, 0.3], k=5)

        # Verify the query string uses wildcard (no filter)
        query_str = mock_query_cls.call_args[0][0]
        assert query_str.startswith("*=>")
        assert "KNN 5" in query_str

        # Verify ft() called with correct index name
        mock_redis.ft.assert_called_with("idx:entity_embeddings")

    @patch("redis.commands.search.query.Query")
    async def test_search_similar_with_type_filter(
        self,
        mock_query_cls: MagicMock,
        store: EntityEmbeddingStore,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify filter clause is included in query when entity_type_filter is set."""
        query_instance = MagicMock()
        query_instance.sort_by.return_value = query_instance
        query_instance.return_fields.return_value = query_instance
        query_instance.paging.return_value = query_instance
        query_instance.dialect.return_value = query_instance
        mock_query_cls.return_value = query_instance

        search_result = MagicMock()
        search_result.docs = []
        mock_redis.ft.return_value.search = AsyncMock(return_value=search_result)

        await store.search_similar(
            query_embedding=[0.1, 0.2],
            k=10,
            entity_type_filter="concept",
        )

        query_str = mock_query_cls.call_args[0][0]
        assert "@entity_type:{concept}" in query_str
        assert "KNN 10" in query_str

    @patch("redis.commands.search.query.Query")
    async def test_search_similar_converts_distance_to_similarity(
        self,
        mock_query_cls: MagicMock,
        store: EntityEmbeddingStore,
        mock_redis: AsyncMock,
    ) -> None:
        """Mock FT.SEARCH result and verify similarity = 1.0 - distance."""
        query_instance = MagicMock()
        query_instance.sort_by.return_value = query_instance
        query_instance.return_fields.return_value = query_instance
        query_instance.paging.return_value = query_instance
        query_instance.dialect.return_value = query_instance
        mock_query_cls.return_value = query_instance

        # Create mock document with expected attributes
        mock_doc = MagicMock()
        mock_doc.entity_id = "ent-42"
        mock_doc.name = "FastAPI"
        mock_doc.entity_type = "framework"
        mock_doc.dist = "0.3"

        search_result = MagicMock()
        search_result.docs = [mock_doc]
        mock_redis.ft.return_value.search = AsyncMock(return_value=search_result)

        matches = await store.search_similar(query_embedding=[0.5, 0.5], k=5)

        assert len(matches) == 1
        assert matches[0].entity_id == "ent-42"
        assert matches[0].name == "FastAPI"
        assert matches[0].entity_type == "framework"
        assert matches[0].distance == pytest.approx(0.3)
        assert matches[0].similarity == pytest.approx(round(1.0 - 0.3, 6))

    @patch("redis.commands.search.query.Query")
    async def test_search_similar_empty_results(
        self,
        mock_query_cls: MagicMock,
        store: EntityEmbeddingStore,
        mock_redis: AsyncMock,
    ) -> None:
        """Returns empty list when no documents match."""
        query_instance = MagicMock()
        query_instance.sort_by.return_value = query_instance
        query_instance.return_fields.return_value = query_instance
        query_instance.paging.return_value = query_instance
        query_instance.dialect.return_value = query_instance
        mock_query_cls.return_value = query_instance

        search_result = MagicMock()
        search_result.docs = []
        mock_redis.ft.return_value.search = AsyncMock(return_value=search_result)

        matches = await store.search_similar(query_embedding=[0.1], k=3)
        assert matches == []

    async def test_delete_embedding(
        self, store: EntityEmbeddingStore, mock_redis: AsyncMock
    ) -> None:
        """Verify redis.delete is called with correct key and returns bool."""
        mock_redis.delete.return_value = 1
        result = await store.delete_embedding("ent-99")

        mock_redis.delete.assert_awaited_once_with("entity_emb:ent-99")
        assert result is True

    async def test_delete_embedding_returns_false_when_missing(
        self, store: EntityEmbeddingStore, mock_redis: AsyncMock
    ) -> None:
        """Returns False when key does not exist."""
        mock_redis.delete.return_value = 0
        result = await store.delete_embedding("ent-nonexistent")
        assert result is False

    async def test_get_embedding(self, store: EntityEmbeddingStore, mock_redis: AsyncMock) -> None:
        """Verify JSON.GET with $.embedding path returns the vector."""
        import orjson

        embedding_vector = [0.1, 0.2, 0.3, 0.4]
        # Redis JSON.GET returns a JSON-encoded array wrapper: [[0.1, 0.2, ...]]
        mock_redis.execute_command.return_value = orjson.dumps([embedding_vector])

        result = await store.get_embedding("ent-7")

        mock_redis.execute_command.assert_awaited_once_with(
            "JSON.GET", "entity_emb:ent-7", "$.embedding"
        )
        assert result == embedding_vector

    async def test_get_embedding_returns_none_when_missing(
        self, store: EntityEmbeddingStore, mock_redis: AsyncMock
    ) -> None:
        """Returns None when the key does not exist in Redis."""
        mock_redis.execute_command.return_value = None
        result = await store.get_embedding("ent-missing")
        assert result is None
