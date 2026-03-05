"""Sentence-transformers embedding adapter.

Implements the ``EmbeddingService`` protocol defined in
``context_graph.ports.embedding``.

The model is loaded lazily on first use (not at import time) to
avoid paying startup cost when embedding is not needed.
Inference runs in ``run_in_executor`` so the synchronous
sentence-transformers forward pass does not block the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class SentenceTransformerEmbedder:
    """Async wrapper around ``sentence_transformers.SentenceTransformer``.

    Parameters
    ----------
    model_name:
        HuggingFace model identifier (default ``all-MiniLM-L6-v2``).
    device:
        Torch device string (``cpu``, ``cuda``, ``mps``).
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._model: Any = None

    def _ensure_model(self) -> Any:
        """Lazy-load the sentence-transformer model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            log.info(
                "loading_embedding_model",
                model=self._model_name,
                device=self._device,
            )
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        """Generate a normalized embedding vector for a single text string."""
        loop = asyncio.get_running_loop()
        model = self._ensure_model()
        vector = await loop.run_in_executor(
            None,
            lambda: model.encode(text, normalize_embeddings=True).tolist(),
        )
        return vector  # type: ignore[no-any-return]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized embedding vectors for multiple texts."""
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        model = self._ensure_model()
        vectors = await loop.run_in_executor(
            None,
            lambda: model.encode(texts, normalize_embeddings=True).tolist(),
        )
        return vectors  # type: ignore[no-any-return]
