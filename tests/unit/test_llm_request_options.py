"""Ensure all chat entry points use compatible options for the chosen model."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from context_graph.adapters.llm.client import LLMExtractionClient
from context_graph.adapters.llm.intent_classifier import LLMIntentClassifier


@pytest.mark.parametrize("model", ["gpt-6-luna", "openai/gpt-6-luna", "test-model"])
@pytest.mark.parametrize("path", ["text", "extraction", "intent"])
async def test_chat_request_options(model: str, path: str) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"general": 0.9}'))]
    )
    completion = AsyncMock(return_value=response)
    with patch("litellm.acompletion", completion):
        client = LLMExtractionClient(model_id=model)
        if path == "text":
            await client.generate_text("hello")
        elif path == "extraction":
            await client._call_llm("hello")
        else:
            await LLMIntentClassifier(model_id=model)._classify_with_llm("hello")
    options = completion.call_args.kwargs
    assert options["model"] == model
    expected_tokens = 256 if path == "intent" else 4096
    if "gpt-6-luna" in model:
        assert options["reasoning_effort"] == "none"
        assert options["max_completion_tokens"] == expected_tokens
        assert "max_tokens" not in options
        assert "temperature" not in options
    else:
        assert options["max_tokens"] == expected_tokens
        assert "temperature" in options
        assert "reasoning_effort" not in options
