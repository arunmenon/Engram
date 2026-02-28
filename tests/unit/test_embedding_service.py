"""Unit tests for SentenceTransformerEmbedder adapter.

Mocks the sentence_transformers dependency so tests run without
having the (heavy) sentence-transformers package installed.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

from context_graph.adapters.embedding.service import SentenceTransformerEmbedder

# Install a fake sentence_transformers module into sys.modules so
# @patch("sentence_transformers.SentenceTransformer") can resolve
# its target without the real package being installed.
_fake_st_module = types.ModuleType("sentence_transformers")
_fake_st_module.SentenceTransformer = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sentence_transformers", _fake_st_module)


class TestSentenceTransformerEmbedder:
    """Tests for the SentenceTransformerEmbedder adapter."""

    def test_constructor_stores_config(self) -> None:
        """Model name and device are stored as instance attributes."""
        embedder = SentenceTransformerEmbedder(
            model_name="test-model",
            device="cuda",
        )

        assert embedder._model_name == "test-model"
        assert embedder._device == "cuda"
        assert embedder._model is None

    def test_constructor_defaults(self) -> None:
        """Default model_name and device values are applied."""
        embedder = SentenceTransformerEmbedder()

        assert embedder._model_name == "all-MiniLM-L6-v2"
        assert embedder._device == "cpu"

    @patch("sentence_transformers.SentenceTransformer")
    def test_lazy_model_loading(self, mock_st_class: MagicMock) -> None:
        """Model is None initially and loaded on first _ensure_model call."""
        mock_model_instance = MagicMock()
        mock_st_class.return_value = mock_model_instance

        embedder = SentenceTransformerEmbedder(
            model_name="test-model",
            device="cpu",
        )

        # Model not loaded yet
        assert embedder._model is None

        # Trigger lazy load
        result = embedder._ensure_model()

        assert result is mock_model_instance
        assert embedder._model is mock_model_instance
        mock_st_class.assert_called_once_with("test-model", device="cpu")

        # Second call should not re-instantiate
        mock_st_class.reset_mock()
        result_again = embedder._ensure_model()

        assert result_again is mock_model_instance
        mock_st_class.assert_not_called()

    @patch("sentence_transformers.SentenceTransformer")
    async def test_embed_text_returns_list(self, mock_st_class: MagicMock) -> None:
        """embed_text returns a list of floats from model.encode().tolist()."""
        expected_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        mock_numpy_array = MagicMock()
        mock_numpy_array.tolist.return_value = expected_vector

        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = mock_numpy_array
        mock_st_class.return_value = mock_model_instance

        embedder = SentenceTransformerEmbedder()
        result = await embedder.embed_text("hello world")

        assert result == expected_vector
        assert isinstance(result, list)
        mock_model_instance.encode.assert_called_once_with(
            "hello world",
            normalize_embeddings=True,
        )
        mock_numpy_array.tolist.assert_called_once()

    @patch("sentence_transformers.SentenceTransformer")
    async def test_embed_text_normalize_embeddings(
        self,
        mock_st_class: MagicMock,
    ) -> None:
        """Verify normalize_embeddings=True is always passed to model.encode."""
        mock_numpy_array = MagicMock()
        mock_numpy_array.tolist.return_value = [0.5, 0.5]

        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = mock_numpy_array
        mock_st_class.return_value = mock_model_instance

        embedder = SentenceTransformerEmbedder()
        await embedder.embed_text("test input")

        # Extract the kwargs from the encode call
        call_kwargs = mock_model_instance.encode.call_args.kwargs
        assert call_kwargs["normalize_embeddings"] is True

    @patch("sentence_transformers.SentenceTransformer")
    async def test_embed_batch_returns_list_of_lists(
        self,
        mock_st_class: MagicMock,
    ) -> None:
        """embed_batch returns a list of embedding vectors for multiple texts."""
        expected_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]

        mock_numpy_array = MagicMock()
        mock_numpy_array.tolist.return_value = expected_vectors

        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = mock_numpy_array
        mock_st_class.return_value = mock_model_instance

        embedder = SentenceTransformerEmbedder()
        input_texts = ["text one", "text two", "text three"]
        result = await embedder.embed_batch(input_texts)

        assert result == expected_vectors
        assert len(result) == 3
        mock_model_instance.encode.assert_called_once_with(
            input_texts,
            normalize_embeddings=True,
        )

    async def test_embed_batch_empty_returns_empty(self) -> None:
        """embed_batch with an empty list returns [] without loading the model."""
        embedder = SentenceTransformerEmbedder()
        result = await embedder.embed_batch([])

        assert result == []
        # Model should never have been loaded
        assert embedder._model is None
