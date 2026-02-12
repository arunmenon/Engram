"""Embedding service port interface.

Source: ADR-0008 Stage 2, ADR-0009
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingService(Protocol):
    """Protocol for embedding generation (sentence-transformers implementation)."""

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        ...
