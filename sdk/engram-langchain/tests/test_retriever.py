"""Tests for the EngramRetriever."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from engram.models import AtlasResponse
from engram_langchain.retriever import EngramRetriever, _atlas_to_documents, _extract_content


@pytest.fixture
def retriever(mock_client: AsyncMock) -> EngramRetriever:
    return EngramRetriever(
        client=mock_client,
        session_id="test-session",
        agent_id="test-agent",
        max_nodes=10,
    )


class TestRetriever:
    """Test the EngramRetriever."""

    def test_sync_raises_not_implemented(self, retriever: EngramRetriever) -> None:
        with pytest.raises(NotImplementedError, match="async"):
            retriever._get_relevant_documents("test query")

    @pytest.mark.asyncio
    async def test_async_retrieval_calls_query_subgraph(
        self,
        retriever: EngramRetriever,
        mock_client: AsyncMock,
        sample_atlas_response: AtlasResponse,
    ) -> None:
        mock_client.query_subgraph.return_value = sample_atlas_response
        await retriever._aget_relevant_documents("billing question")
        mock_client.query_subgraph.assert_awaited_once()
        call_args = mock_client.query_subgraph.call_args[0][0]
        assert call_args.query == "billing question"
        assert call_args.session_id == "test-session"
        assert call_args.agent_id == "test-agent"
        assert call_args.max_nodes == 10

    @pytest.mark.asyncio
    async def test_async_retrieval_returns_documents(
        self,
        retriever: EngramRetriever,
        mock_client: AsyncMock,
        sample_atlas_response: AtlasResponse,
    ) -> None:
        mock_client.query_subgraph.return_value = sample_atlas_response
        docs = await retriever._aget_relevant_documents("billing question")
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(
        self, retriever: EngramRetriever, mock_client: AsyncMock
    ) -> None:
        docs = await retriever._aget_relevant_documents("nothing here")
        assert docs == []


class TestAtlasToDocuments:
    """Test conversion of Atlas responses to LangChain Documents."""

    def test_converts_nodes_to_documents(self, sample_atlas_response: AtlasResponse) -> None:
        docs = _atlas_to_documents(sample_atlas_response)
        assert len(docs) == 2

    def test_document_page_content(self, sample_atlas_response: AtlasResponse) -> None:
        docs = _atlas_to_documents(sample_atlas_response)
        contents = {d.page_content for d in docs}
        assert "User asked about billing" in contents
        assert "Billing is managed through Stripe" in contents

    def test_document_metadata_includes_node_info(
        self, sample_atlas_response: AtlasResponse
    ) -> None:
        docs = _atlas_to_documents(sample_atlas_response)
        doc = next(d for d in docs if d.metadata["node_id"] == "evt-001")
        assert doc.metadata["node_type"] == "Event"
        assert doc.metadata["retrieval_reason"] == "direct"
        assert doc.metadata["decay_score"] == 0.95
        assert doc.metadata["relevance_score"] == 0.88
        assert doc.metadata["importance_score"] == 7

    def test_document_metadata_includes_provenance(
        self, sample_atlas_response: AtlasResponse
    ) -> None:
        docs = _atlas_to_documents(sample_atlas_response)
        doc = next(d for d in docs if d.metadata["node_id"] == "evt-001")
        assert doc.metadata["event_id"] == "evt-001"
        assert doc.metadata["session_id"] == "sess-abc"
        assert doc.metadata["agent_id"] == "agent-1"
        assert "occurred_at" in doc.metadata


class TestExtractContent:
    """Test content extraction from AtlasNodes."""

    def test_extracts_content_key(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Event", attributes={"content": "hello"})
        assert _extract_content(node) == "hello"

    def test_extracts_payload_ref_fallback(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Event", attributes={"payload_ref": "data"})
        assert _extract_content(node) == "data"

    def test_falls_back_to_str_attributes(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Event", attributes={"custom": 42})
        result = _extract_content(node)
        assert "42" in result

    def test_empty_attributes_uses_type_and_id(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Entity", attributes={})
        assert _extract_content(node) == "[Entity:n1]"
