"""Search index ports: keyword and vector (ADR-0019 §1, C4).

Both return ``SearchHit`` lists ordered best first. Each hit carries its
0-based ``rank`` and a ``score`` normalised to 0–1 (higher is better), so
fusion (RRF) and thresholds never depend on a backend's native scale
(BM25 versus cosine). ``fields`` carries any extra data the index returns.

Each index states whether its scores are native relevance scores or
derived from rank (``scores_are_native``).

Uses typing.Protocol for structural subtyping (not ABCs).

Source: ADR-0019
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SearchHit:
    """One search result."""

    id: str
    rank: int
    score: float
    fields: dict[str, Any] = field(default_factory=dict)


class KeywordIndex(Protocol):
    """Full-text search over event text fields."""

    @property
    def scores_are_native(self) -> bool:
        """True if scores are the backend's relevance, False if derived from rank."""
        ...

    async def search(
        self,
        text: str,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[SearchHit]:
        """Return event ids matching ``text``, best first."""
        ...


class VectorIndex(Protocol):
    """Nearest-neighbour search over entity embeddings."""

    @property
    def scores_are_native(self) -> bool:
        """True if scores are the backend's similarity, False if derived from rank."""
        ...

    async def nearest(
        self,
        embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[SearchHit]:
        """Return entity ids nearest ``embedding`` with score >= ``threshold``, best first."""
        ...
