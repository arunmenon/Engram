"""Unit tests for entity embedding index functions in adapters/redis/indexes.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.commands.search.field import TagField, VectorField

from context_graph.adapters.redis.indexes import (
    ensure_entity_embedding_index,
    entity_embedding_index_definition,
    entity_embedding_index_fields,
)

# ---------------------------------------------------------------------------
# TestEntityEmbeddingIndexDefinition
# ---------------------------------------------------------------------------


class TestEntityEmbeddingIndexDefinition:
    """Tests for entity_embedding_index_definition()."""

    def test_default_prefix(self) -> None:
        """Default prefix is 'entity_emb:' and index type is JSON."""
        definition = entity_embedding_index_definition()
        args = definition.args
        assert "JSON" in args
        prefix_index = args.index("PREFIX")
        assert args[prefix_index + 2] == "entity_emb:"

    def test_custom_prefix(self) -> None:
        """Custom prefix is used when provided."""
        definition = entity_embedding_index_definition(prefix="custom_emb:")
        args = definition.args
        assert "JSON" in args
        prefix_index = args.index("PREFIX")
        assert args[prefix_index + 2] == "custom_emb:"


# ---------------------------------------------------------------------------
# TestEntityEmbeddingIndexFields
# ---------------------------------------------------------------------------


class TestEntityEmbeddingIndexFields:
    """Tests for entity_embedding_index_fields()."""

    def test_returns_four_fields(self) -> None:
        """Returns exactly 4 fields: name, entity_type, entity_id, embedding."""
        fields = entity_embedding_index_fields()
        assert len(fields) == 4

    def test_tag_fields_present(self) -> None:
        """First three fields are TagFields for name, entity_type, entity_id."""
        fields = entity_embedding_index_fields()
        tag_fields = [f for f in fields if isinstance(f, TagField)]
        assert len(tag_fields) == 3
        tag_names = [f.as_name for f in tag_fields]
        assert "name" in tag_names
        assert "entity_type" in tag_names
        assert "entity_id" in tag_names

    def test_vector_field_hnsw(self) -> None:
        """Fourth field is a VectorField with HNSW algorithm and default 384 dims."""
        fields = entity_embedding_index_fields()
        vector_fields = [f for f in fields if isinstance(f, VectorField)]
        assert len(vector_fields) == 1
        vector_field = vector_fields[0]
        assert vector_field.as_name == "embedding"
        # The VectorField stores algorithm and attributes in its args list.
        # Verify HNSW algorithm and DIM=384 are present in the args.
        assert "HNSW" in vector_field.args
        dim_index = vector_field.args.index("DIM")
        assert vector_field.args[dim_index + 1] == 384

    def test_custom_dimensions(self) -> None:
        """Custom dimensions parameter changes the vector DIM attribute."""
        fields = entity_embedding_index_fields(dimensions=768)
        vector_fields = [f for f in fields if isinstance(f, VectorField)]
        assert len(vector_fields) == 1
        vector_field = vector_fields[0]
        dim_index = vector_field.args.index("DIM")
        assert vector_field.args[dim_index + 1] == 768


# ---------------------------------------------------------------------------
# TestEnsureEntityEmbeddingIndex
# ---------------------------------------------------------------------------


class TestEnsureEntityEmbeddingIndex:
    """Tests for ensure_entity_embedding_index()."""

    @pytest.mark.asyncio
    async def test_index_already_exists_is_noop(self) -> None:
        """When the index already exists, ft().info() succeeds and create_index is NOT called."""
        mock_ft = MagicMock()
        mock_ft.info = AsyncMock(return_value={"index_name": "idx:entity_embeddings"})
        mock_ft.create_index = AsyncMock()

        mock_client = MagicMock()
        mock_client.ft = MagicMock(return_value=mock_ft)

        await ensure_entity_embedding_index(mock_client, index_name="idx:entity_embeddings")

        mock_client.ft.assert_called_with("idx:entity_embeddings")
        mock_ft.info.assert_awaited_once()
        mock_ft.create_index.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_index_does_not_exist_creates_index(self) -> None:
        """When ft().info() raises, create_index is called with correct fields and definition."""
        mock_ft = MagicMock()
        mock_ft.info = AsyncMock(side_effect=Exception("Unknown index"))
        mock_ft.create_index = AsyncMock()

        mock_client = MagicMock()
        mock_client.ft = MagicMock(return_value=mock_ft)

        await ensure_entity_embedding_index(
            mock_client,
            index_name="idx:entity_embeddings",
            prefix="entity_emb:",
            dimensions=384,
        )

        mock_ft.info.assert_awaited_once()
        mock_ft.create_index.assert_awaited_once()

        call_kwargs = mock_ft.create_index.call_args
        created_fields = call_kwargs.kwargs["fields"]
        created_definition = call_kwargs.kwargs["definition"]

        # Verify 4 fields passed to create_index
        assert len(created_fields) == 4

        # Verify definition uses correct prefix and JSON type
        assert "entity_emb:" in created_definition.args
        assert "JSON" in created_definition.args
