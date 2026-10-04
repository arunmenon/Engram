"""Spanner keyword index with native scores (ADR-0019 C4).

Spanner full-text search returns a relevance ``SCORE``; hits carry it
normalised to [0, 1] by the best score in the result, so fusion never
depends on Spanner's scale.

Source: ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.ports.search import SearchHit

if TYPE_CHECKING:
    from context_graph.adapters.spanner.log import SpannerEventLog


class SpannerKeywordIndex:
    """``KeywordIndex`` over ``SpannerEventLog.search_scored``."""

    def __init__(self, event_log: SpannerEventLog) -> None:
        self._event_log = event_log

    @property
    def scores_are_native(self) -> bool:
        return True

    async def search(
        self,
        text: str,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[SearchHit]:
        results = await self._event_log.search_scored(text, session_id=session_id, limit=limit)
        best = max((score for _event, score in results), default=0.0)
        return [
            SearchHit(
                id=str(event.event_id),
                rank=rank,
                score=(score / best) if best > 0 else 0.0,
            )
            for rank, (event, score) in enumerate(results)
        ]
