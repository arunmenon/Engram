"""LLM-based intent classifier with keyword fallback.

Uses litellm for multi-provider LLM routing. On any error (timeout,
parse failure, API error), falls back to the keyword-based
classify_intent() function from domain.intent.

Source: ADR-0009 amendment (LLM intent classification)
"""

from __future__ import annotations

import asyncio
from typing import Any

import orjson
import structlog

from context_graph.domain.intent import classify_intent
from context_graph.domain.models import IntentType

logger = structlog.get_logger(__name__)

# All valid intent type values for validation
_VALID_INTENTS: set[str] = {
    IntentType.WHY,
    IntentType.WHEN,
    IntentType.WHAT,
    IntentType.RELATED,
    IntentType.GENERAL,
    IntentType.WHO_IS,
    IntentType.HOW_DOES,
    IntentType.PERSONALIZE,
}

_FEW_SHOT_PROMPT_TEMPLATE = (
    "You are an intent classifier for a context graph query system.\n"
    "Given a user query enclosed in <user_query> XML tags, classify it into\n"
    "one or more intent types with confidence scores (0.0 to 1.0).\n"
    "Return ONLY valid JSON.\n\n"
    "## Intent Types\n"
    "- why: Causal reasoning, root cause analysis\n"
    "- when: Temporal ordering, time-based queries\n"
    "- what: Entity identification, description\n"
    "- related: Associative, similarity queries\n"
    "- general: Balanced, no specific intent\n"
    "- who_is: Person/user identification\n"
    "- how_does: Process, method, workflow queries\n"
    "- personalize: User preference, customization queries\n\n"
    "## Examples\n\n"
    "<user_query>Why did the payment fail?</user_query>\n"
    'Output: {"why": 0.9, "what": 0.3}\n\n'
    "<user_query>When did the user last log in?</user_query>\n"
    'Output: {"when": 0.9}\n\n'
    "<user_query>Who is Sarah Chen?</user_query>\n"
    'Output: {"who_is": 0.95}\n\n'
    "<user_query>Find events similar to the deployment failure</user_query>\n"
    'Output: {"related": 0.85, "what": 0.3}\n\n'
    "<user_query>How does the authentication flow work?</user_query>\n"
    'Output: {"how_does": 0.9, "what": 0.3}\n\n'
    "<user_query>Show me my preferred tools and settings</user_query>\n"
    'Output: {"personalize": 0.9}\n\n'
    "<user_query>What happened before the crash and why?</user_query>\n"
    'Output: {"why": 0.7, "when": 0.6, "what": 0.4}\n\n'
    "<user_query>Tell me about the recent API changes</user_query>\n"
    'Output: {"what": 0.7, "when": 0.4}\n\n'
    "## Rules\n"
    "- Return a JSON object mapping intent types to confidence scores\n"
    "- Only include intents with confidence > 0.1\n"
    "- At least one intent must be present\n"
    "- Confidence scores should sum to roughly 1.0-2.0 "
    "(can exceed 1.0 for multi-intent)\n\n"
)


class LLMIntentClassifier:
    """LLM-based intent classifier conforming to IntentClassifier protocol.

    On any error, falls back to keyword-based classification.
    """

    def __init__(
        self,
        model_id: str = "gpt-5.2-2025-12-11",
        timeout_seconds: int = 5,
        fallback_on_error: bool = True,
    ) -> None:
        self._model_id = model_id
        self._timeout_seconds = timeout_seconds
        self._fallback_on_error = fallback_on_error

    async def classify(self, query: str) -> dict[str, float]:
        """Classify query intent using LLM with keyword fallback."""
        if not query or not query.strip():
            return {IntentType.GENERAL: 0.5}

        try:
            return await asyncio.wait_for(
                self._classify_with_llm(query),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            logger.warning(
                "llm_intent_timeout",
                query_length=len(query),
                timeout=self._timeout_seconds,
            )
            if self._fallback_on_error:
                return classify_intent(query)
            return {IntentType.GENERAL: 0.5}
        except Exception:
            logger.warning("llm_intent_error", query_length=len(query), exc_info=True)
            if self._fallback_on_error:
                return classify_intent(query)
            return {IntentType.GENERAL: 0.5}

    async def _classify_with_llm(self, query: str) -> dict[str, float]:
        """Call the LLM and parse the intent classification response."""
        import litellm

        prompt = _FEW_SHOT_PROMPT_TEMPLATE + f"<user_query>{query}</user_query>\nOutput:"

        response = await litellm.acompletion(
            model=self._model_id,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
            timeout=self._timeout_seconds,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            return classify_intent(query)

        return self._parse_response(raw_text, query)

    def _parse_response(self, raw_text: str, query: str) -> dict[str, float]:
        """Parse and validate the LLM JSON response."""
        parsed: Any = orjson.loads(raw_text)
        if not isinstance(parsed, dict):
            logger.warning("llm_intent_not_dict", raw=raw_text[:200])
            if self._fallback_on_error:
                return classify_intent(query)
            return {IntentType.GENERAL: 0.5}

        # Filter to valid intents with numeric scores
        result: dict[str, float] = {}
        for key, value in parsed.items():
            if key in _VALID_INTENTS and isinstance(value, (int, float)) and value > 0.1:
                result[key] = float(value)

        if not result:
            return classify_intent(query)

        # Normalize so max confidence = 1.0
        return _normalize_scores(result)


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize confidence scores so the maximum is 1.0."""
    if not scores:
        return scores
    max_score = max(scores.values())
    if max_score <= 0:
        return scores
    return {k: round(v / max_score, 4) for k, v in scores.items()}
