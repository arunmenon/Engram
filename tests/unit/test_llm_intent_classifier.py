"""Tests for LLM-based intent classification with keyword fallback."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import orjson
import pytest

from context_graph.adapters.llm.intent_classifier import (
    LLMIntentClassifier,
    _normalize_scores,
)
from context_graph.domain.intent import KeywordIntentClassifier, classify_intent
from context_graph.domain.models import IntentType

# ---------------------------------------------------------------------------
# Helper to build a mock litellm response
# ---------------------------------------------------------------------------


def _mock_response(content: str) -> MagicMock:
    """Build a mock litellm completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def _mock_litellm_module() -> Generator[MagicMock]:
    """Ensure litellm is available as a mock module for all tests."""
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"litellm": mock_module}):
        yield mock_module


# ---------------------------------------------------------------------------
# LLMIntentClassifier tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_why_intent(_mock_litellm_module: MagicMock) -> None:
    """LLM returns a 'why' intent classification."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response(orjson.dumps({"why": 0.9, "what": 0.3}).decode())
    )
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("Why did the payment fail?")
    assert "why" in result
    assert result["why"] == 1.0  # normalized to max
    assert "what" in result


@pytest.mark.asyncio
async def test_classify_when_intent(_mock_litellm_module: MagicMock) -> None:
    """LLM returns a 'when' intent classification."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response(orjson.dumps({"when": 0.95}).decode())
    )
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("When did the user last log in?")
    assert "when" in result
    assert result["when"] == 1.0


@pytest.mark.asyncio
async def test_classify_multi_intent(_mock_litellm_module: MagicMock) -> None:
    """LLM returns multiple intents for a complex query."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response(orjson.dumps({"why": 0.7, "when": 0.6, "what": 0.4}).decode())
    )
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("What happened before the crash and why?")
    assert len(result) == 3
    assert result["why"] == 1.0  # highest, normalized
    assert result["when"] < 1.0
    assert result["what"] < result["when"]


@pytest.mark.asyncio
async def test_fallback_on_llm_error(_mock_litellm_module: MagicMock) -> None:
    """Falls back to keyword classification on LLM API error."""
    _mock_litellm_module.acompletion = AsyncMock(side_effect=RuntimeError("API unavailable"))
    classifier = LLMIntentClassifier(model_id="test-model", fallback_on_error=True)
    result = await classifier.classify("Why did this happen?")
    expected = classify_intent("Why did this happen?")
    assert result == expected


@pytest.mark.asyncio
async def test_fallback_on_timeout(_mock_litellm_module: MagicMock) -> None:
    """Falls back to keyword classification on timeout."""

    async def _slow_completion(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(10)

    _mock_litellm_module.acompletion = _slow_completion
    classifier = LLMIntentClassifier(
        model_id="test-model", timeout_seconds=1, fallback_on_error=True
    )
    result = await classifier.classify("When did this happen?")
    expected = classify_intent("When did this happen?")
    assert result == expected


@pytest.mark.asyncio
async def test_fallback_on_parse_error(_mock_litellm_module: MagicMock) -> None:
    """Falls back to keyword classification on JSON parse error."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response("this is not valid json {{{")
    )
    classifier = LLMIntentClassifier(model_id="test-model", fallback_on_error=True)
    result = await classifier.classify("Why did this break?")
    expected = classify_intent("Why did this break?")
    assert result == expected


def test_confidence_normalization() -> None:
    """Scores are normalized so max = 1.0."""
    scores = {"why": 0.5, "what": 0.25, "when": 0.1}
    normalized = _normalize_scores(scores)
    assert normalized["why"] == 1.0
    assert normalized["what"] == 0.5
    assert normalized["when"] == 0.2


@pytest.mark.asyncio
async def test_keyword_classifier_protocol_conformance() -> None:
    """KeywordIntentClassifier conforms to the IntentClassifier protocol."""
    classifier = KeywordIntentClassifier()
    result = await classifier.classify("Why did this happen?")
    assert isinstance(result, dict)
    assert "why" in result


@pytest.mark.asyncio
async def test_llm_classifier_with_valid_response(_mock_litellm_module: MagicMock) -> None:
    """LLM classifier processes a well-formed response correctly."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response(orjson.dumps({"who_is": 0.95, "what": 0.2}).decode())
    )
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("Who is Sarah Chen?")
    assert "who_is" in result
    assert result["who_is"] == 1.0
    # 0.2 is above 0.1 threshold, so what should be present
    assert "what" in result


@pytest.mark.asyncio
async def test_empty_query() -> None:
    """Empty query returns general intent without calling LLM."""
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("")
    assert result == {IntentType.GENERAL: 0.5}


@pytest.mark.asyncio
async def test_all_eight_intents_recognized(_mock_litellm_module: MagicMock) -> None:
    """All 8 intent types are recognized when returned by LLM."""
    all_intents = {
        "why": 0.8,
        "when": 0.7,
        "what": 0.6,
        "related": 0.5,
        "general": 0.4,
        "who_is": 0.3,
        "how_does": 0.2,
        "personalize": 0.15,
    }
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response(orjson.dumps(all_intents).decode())
    )
    classifier = LLMIntentClassifier(model_id="test-model")
    result = await classifier.classify("complex query")
    # All intents above 0.1 threshold should be present
    assert len(result) == 8
    assert result["why"] == 1.0  # max, normalized


@pytest.mark.asyncio
async def test_default_settings_use_keyword() -> None:
    """Default settings use keyword classification (no LLM)."""
    from context_graph.settings import IntentSettings

    settings = IntentSettings()
    assert settings.use_llm is False
    assert settings.fallback_on_error is True
    assert settings.timeout_seconds == 5


def test_normalize_max_confidence() -> None:
    """Normalize preserves relative ordering and sets max to 1.0."""
    scores = {"why": 1.0, "when": 0.5}
    normalized = _normalize_scores(scores)
    assert normalized["why"] == 1.0
    assert normalized["when"] == 0.5


@pytest.mark.asyncio
async def test_json_parse_handles_malformed(_mock_litellm_module: MagicMock) -> None:
    """Malformed JSON from LLM triggers keyword fallback."""
    _mock_litellm_module.acompletion = AsyncMock(
        return_value=_mock_response('{"why": "not_a_number"}')
    )
    classifier = LLMIntentClassifier(model_id="test-model", fallback_on_error=True)
    # "not_a_number" is not a float, so no valid intents -> falls back to keyword
    result = await classifier.classify("Why did this happen?")
    expected = classify_intent("Why did this happen?")
    assert result == expected


@pytest.mark.asyncio
async def test_keyword_classifier_matches_function() -> None:
    """KeywordIntentClassifier produces same output as classify_intent()."""
    classifier = KeywordIntentClassifier()
    queries = [
        "Why did the payment fail?",
        "When was the last deployment?",
        "What tools are available?",
        "Find similar events",
        "Who is the team lead?",
        "How does authentication work?",
        "Show my preferences",
        "Tell me something",
    ]
    for query in queries:
        result = await classifier.classify(query)
        expected = classify_intent(query)
        assert result == expected, f"Mismatch for query: {query}"


# ---------------------------------------------------------------------------
# fallback_on_error=False tests (Finding #7)
# ---------------------------------------------------------------------------


class TestFallbackDisabled:
    """Test behavior when fallback_on_error=False."""

    @pytest.mark.asyncio
    async def test_returns_general_on_error_when_fallback_disabled(
        self, _mock_litellm_module: MagicMock
    ) -> None:
        """When fallback is disabled and LLM fails, should return general:0.5."""
        _mock_litellm_module.acompletion = AsyncMock(side_effect=RuntimeError("API error"))
        classifier = LLMIntentClassifier(fallback_on_error=False)
        result = await classifier.classify("Why did the payment fail?")
        assert result == {IntentType.GENERAL: 0.5}

    @pytest.mark.asyncio
    async def test_returns_general_on_timeout_when_fallback_disabled(
        self, _mock_litellm_module: MagicMock
    ) -> None:
        """When fallback is disabled and LLM times out, should return general:0.5."""

        async def slow_response(*args: object, **kwargs: object) -> None:
            await asyncio.sleep(10)

        _mock_litellm_module.acompletion = slow_response
        classifier = LLMIntentClassifier(fallback_on_error=False, timeout_seconds=1)
        result = await classifier.classify("test query")
        assert result == {IntentType.GENERAL: 0.5}

    @pytest.mark.asyncio
    async def test_returns_general_on_non_dict_response_when_fallback_disabled(
        self, _mock_litellm_module: MagicMock
    ) -> None:
        """When fallback is disabled and LLM returns a non-dict, should return general:0.5."""
        _mock_litellm_module.acompletion = AsyncMock(return_value=_mock_response("[1, 2, 3]"))
        classifier = LLMIntentClassifier(fallback_on_error=False)
        result = await classifier.classify("Why did this happen?")
        # JSON is valid but not a dict -> fallback_on_error=False path returns general:0.5
        assert result == {IntentType.GENERAL: 0.5}
