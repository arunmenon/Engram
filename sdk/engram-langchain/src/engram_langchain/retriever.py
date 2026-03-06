"""LangChain retriever that fetches context from the Engram graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

if TYPE_CHECKING:
    from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun

from engram.models import SubgraphQuery


class EngramRetriever(BaseRetriever):
    """Retriever that queries the Engram context graph for relevant documents.

    Converts AtlasNode results into LangChain Document objects with full
    provenance metadata.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client: Any = Field(description="Engram client instance")
    session_id: str = Field(description="Session ID for scoping queries")
    agent_id: str = Field(default="langchain", description="Agent ID for queries")
    max_nodes: int = Field(default=20, description="Maximum nodes to return")

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        raise NotImplementedError(
            "EngramRetriever requires async usage. "
            "Use `await retriever.ainvoke(query)` or `aget_relevant_documents(query)` instead."
        )

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        subgraph_query = SubgraphQuery(
            query=query,
            session_id=self.session_id,
            agent_id=self.agent_id,
            max_nodes=self.max_nodes,
        )
        response = await self.client.query_subgraph(subgraph_query)
        return _atlas_to_documents(response)


def _atlas_to_documents(response: Any) -> list[Document]:
    """Convert an AtlasResponse into a list of LangChain Documents."""
    documents: list[Document] = []
    for node_id, node in response.nodes.items():
        page_content = _extract_content(node)
        metadata: dict[str, Any] = {
            "node_id": node_id,
            "node_type": node.node_type,
            "retrieval_reason": node.retrieval_reason,
            "decay_score": node.scores.decay_score,
            "relevance_score": node.scores.relevance_score,
            "importance_score": node.scores.importance_score,
        }
        if node.provenance:
            metadata["event_id"] = node.provenance.event_id
            metadata["session_id"] = node.provenance.session_id
            metadata["agent_id"] = node.provenance.agent_id
            metadata["occurred_at"] = node.provenance.occurred_at.isoformat()
        if node.proactive_signal:
            metadata["proactive_signal"] = node.proactive_signal
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


def _extract_content(node: Any) -> str:
    """Extract text content from an AtlasNode's attributes."""
    attributes = node.attributes
    for key in ("content", "payload_ref", "summary", "text", "belief_text", "description", "name"):
        if key in attributes and isinstance(attributes[key], str):
            return attributes[key]
    if attributes:
        return str(attributes)
    return f"[{node.node_type}:{node.node_id}]"
