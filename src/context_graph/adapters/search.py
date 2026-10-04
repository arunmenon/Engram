"""Search index adapters over the existing stores (ADR-0019 C4).

Today's backends answer search through methods on the stores:
RediSearch BM25 through ``EventStore.search_bm25`` and the Neo4j vector
index through ``GraphStore.search_similar_entities``. These adapters
present them as ``KeywordIndex`` and ``VectorIndex`` with normalised
scores, so the retrieval engine depends only on the search ports.

Both adapters use only port methods, so they work over any backend that
implements those methods.

Source: ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.ports.search import SearchHit

if TYPE_CHECKING:
    from context_graph.ports.event_store import EventStore
    from context_graph.ports.graph_store import GraphStore


def rank_score(rank: int) -> float:
    """Score derived from a 0-based rank: 1.0, 0.5, 0.33, ... (always in (0, 1])."""
    return 1.0 / (rank + 1)


class EventStoreKeywordIndex:
    """``KeywordIndex`` over ``EventStore.search_bm25``.

    ``search_bm25`` returns events in relevance order without scores, so
    scores are derived from rank.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store

    @property
    def scores_are_native(self) -> bool:
        return False

    async def search(
        self,
        text: str,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[SearchHit]:
        events = await self._event_store.search_bm25(text, session_id=session_id, limit=limit)
        return [
            SearchHit(id=str(event.event_id), rank=rank, score=rank_score(rank))
            for rank, event in enumerate(events)
        ]


class GraphVectorIndex:
    """``VectorIndex`` over ``GraphStore.search_similar_entities``.

    The Neo4j vector index returns cosine similarity already in [0, 1];
    scores are clamped to that range in case a backend returns raw cosine.
    """

    def __init__(self, graph_store: GraphStore) -> None:
        self._graph_store = graph_store

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
        results = await self._graph_store.search_similar_entities(
            embedding, top_k=top_k, threshold=threshold
        )
        return [
            SearchHit(
                id=result["entity_id"],
                rank=rank,
                score=max(0.0, min(1.0, float(result["score"]))),
                fields={k: v for k, v in result.items() if k not in {"entity_id", "score"}},
            )
            for rank, result in enumerate(results)
        ]
