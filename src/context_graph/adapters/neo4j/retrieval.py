"""Neo4j-bound retrieval pipeline (compatibility layer, ADR-0019 C3).

The retrieval logic now lives in ``context_graph.retrieval.engine``
(backend-neutral, composed from ports). This module keeps the earlier
construction API, ``RetrievalPipeline(RetrievalDeps(driver=..., ...))``,
for ``Neo4jGraphStore``'s deprecated query methods and existing callers.
It wires the engine to ``Neo4jGraphReads`` over the given driver, to a
vector index over ``search_similar_entities`` and to a keyword index over
``event_store.search_bm25``.

New code builds ``RetrievalEngine`` directly (see ``api/app.py``).

Source: ADR-0006, ADR-0009, ADR-0019
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from context_graph.adapters.neo4j.graph_reads import Neo4jGraphReads
from context_graph.adapters.search import EventStoreKeywordIndex
from context_graph.ports.search import SearchHit
from context_graph.retrieval.engine import RetrievalEngine

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.embedding import EmbeddingService
    from context_graph.ports.event_store import EventStore
    from context_graph.ports.intent import IntentClassifier
    from context_graph.ports.llm import LLMClient
    from context_graph.settings import DecaySettings, PPRSettings


@dataclass(frozen=True)
class RetrievalDeps:
    """Dependency bundle for the retrieval pipeline."""

    driver: AsyncDriver
    database: str
    embedding_service: EmbeddingService | None
    intent_classifier: IntentClassifier | None
    llm_client: LLMClient | None
    event_store: EventStore | None
    decay: DecaySettings
    ppr_settings: PPRSettings | None
    query_timeout_s: float
    neighbor_limit: int
    search_similar_entities: Any  # callable from store
    hyde_hot_path_timeout: float = 2.0


class _CallableVectorIndex:
    """``VectorIndex`` over a ``search_similar_entities``-shaped callable."""

    def __init__(self, search_similar_entities: Any) -> None:
        self._search = search_similar_entities

    @property
    def scores_are_native(self) -> bool:
        return True

    async def nearest(
        self,
        embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[SearchHit]:
        results = await self._search(embedding, top_k=top_k, threshold=threshold)
        return [
            SearchHit(
                id=result["entity_id"],
                rank=rank,
                score=max(0.0, min(1.0, float(result["score"]))),
            )
            for rank, result in enumerate(results)
        ]


class RetrievalPipeline(RetrievalEngine):
    """``RetrievalEngine`` built from a Neo4j driver and loose dependencies."""

    def __init__(self, deps: RetrievalDeps) -> None:
        self._deps = deps
        super().__init__(
            Neo4jGraphReads(deps.driver, deps.database),
            decay=deps.decay,
            keyword_index=(
                EventStoreKeywordIndex(deps.event_store) if deps.event_store is not None else None
            ),
            vector_index=_CallableVectorIndex(deps.search_similar_entities),
            embedding_service=deps.embedding_service,
            intent_classifier=deps.intent_classifier,
            llm_client=deps.llm_client,
            ppr_settings=deps.ppr_settings,
            query_timeout_s=deps.query_timeout_s,
            neighbor_limit=deps.neighbor_limit,
            hyde_hot_path_timeout=deps.hyde_hot_path_timeout,
        )

    async def _get_graph_seeds(
        self,
        query: SubgraphQuery,
        seed_limit: int,
        seed_query: str | None = None,
        *,
        seed_strategy: str = "general",
    ) -> list[tuple[str, float]]:
        """Seed by strategy. ``seed_query`` (query text) is ignored: strategies are named."""
        return await super()._get_graph_seeds(query, seed_limit, seed_strategy=seed_strategy)
