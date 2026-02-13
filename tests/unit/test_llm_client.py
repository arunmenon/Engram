"""Unit tests for the LLM extraction client adapter.

Tests prompt construction, conversation text reconstruction,
source quote validation, confidence prior application, and
the extract_from_session fallback behavior.
"""

from __future__ import annotations

import pytest

from context_graph.adapters.llm.client import (
    LLMExtractionClient,
    build_conversation_text,
    build_extraction_prompt,
    validate_extraction,
)
from context_graph.domain.extraction import (
    ExtractedEntity,
    ExtractedInterest,
    ExtractedPreference,
    ExtractedSkill,
    SessionExtractionResult,
)
from tests.fixtures.events import make_event, make_session_events, make_tool_event

# ---------------------------------------------------------------------------
# build_extraction_prompt
# ---------------------------------------------------------------------------


class TestBuildExtractionPrompt:
    def test_prompt_contains_schema_info(self) -> None:
        events = make_session_events(n=2)
        prompt = build_extraction_prompt(events, existing_entities=[])
        assert "Entity Types" in prompt
        assert "Preference Categories" in prompt
        assert "Skill Categories" in prompt
        assert "Output Format" in prompt

    def test_prompt_contains_event_data(self) -> None:
        events = [make_tool_event(tool_name="my-tool")]
        prompt = build_extraction_prompt(events, existing_entities=[])
        assert "my-tool" in prompt
        assert "tool.execute" in prompt

    def test_prompt_includes_existing_entities(self) -> None:
        events = make_session_events(n=1)
        existing = [{"name": "python"}, {"name": "redis"}]
        prompt = build_extraction_prompt(events, existing_entities=existing)
        assert "python" in prompt
        assert "redis" in prompt
        assert "Existing Entities" in prompt

    def test_prompt_skips_empty_existing_entities(self) -> None:
        events = make_session_events(n=1)
        prompt = build_extraction_prompt(events, existing_entities=[])
        assert "Existing Entities" not in prompt

    def test_prompt_skips_entities_without_names(self) -> None:
        events = make_session_events(n=1)
        existing = [{"name": ""}, {"type": "tool"}]
        prompt = build_extraction_prompt(events, existing_entities=existing)
        assert "Existing Entities" not in prompt


# ---------------------------------------------------------------------------
# build_conversation_text
# ---------------------------------------------------------------------------


class TestBuildConversationText:
    def test_reconstructs_from_events(self) -> None:
        events = make_session_events(n=3)
        text = build_conversation_text(events)
        assert "[Turn 0]" in text
        assert "[Turn 1]" in text
        assert "[Turn 2]" in text

    def test_includes_tool_name(self) -> None:
        events = [make_tool_event(tool_name="grep")]
        text = build_conversation_text(events)
        assert "tool=grep" in text

    def test_includes_agent_id(self) -> None:
        events = [make_event(agent_id="agent-alpha")]
        text = build_conversation_text(events)
        assert "agent=agent-alpha" in text

    def test_includes_payload_ref(self) -> None:
        events = [make_event(payload_ref="payload:abc123")]
        text = build_conversation_text(events)
        assert "payload:abc123" in text

    def test_empty_events_returns_empty(self) -> None:
        text = build_conversation_text([])
        assert text == ""


# ---------------------------------------------------------------------------
# validate_extraction
# ---------------------------------------------------------------------------


class TestValidateExtraction:
    def _make_result(self, **kwargs) -> SessionExtractionResult:
        defaults = {
            "session_id": "sess-1",
            "agent_id": "agent-1",
            "entities": [],
            "preferences": [],
            "skills": [],
            "interests": [],
        }
        defaults.update(kwargs)
        return SessionExtractionResult(**defaults)

    def test_filters_invalid_entity_quotes(self) -> None:
        result = self._make_result(
            entities=[
                ExtractedEntity(
                    name="python",
                    entity_type="concept",
                    confidence=0.9,
                    source_quote="I love python programming",
                ),
                ExtractedEntity(
                    name="rust",
                    entity_type="concept",
                    confidence=0.8,
                    source_quote="this quote does not exist in conversation",
                ),
            ]
        )
        conversation = "I love python programming and use it daily"
        validated = validate_extraction(result, conversation)
        assert len(validated.entities) == 1
        assert validated.entities[0].name == "python"

    def test_applies_confidence_prior_to_preferences(self) -> None:
        result = self._make_result(
            preferences=[
                ExtractedPreference(
                    category="tool",
                    key="vim",
                    polarity="positive",
                    strength=0.9,
                    confidence=0.99,
                    source="implicit_unintentional",
                    source_quote="using vim for editing",
                ),
            ]
        )
        conversation = "I was using vim for editing the file"
        validated = validate_extraction(result, conversation)
        assert len(validated.preferences) == 1
        # implicit_unintentional ceiling is 0.5
        assert validated.preferences[0].confidence <= 0.5

    def test_applies_confidence_prior_to_skills(self) -> None:
        result = self._make_result(
            skills=[
                ExtractedSkill(
                    name="Python",
                    category="programming_language",
                    proficiency=0.8,
                    confidence=0.95,
                    source="inferred",
                    source_quote="wrote python code",
                ),
            ]
        )
        conversation = "The user wrote python code to process the data"
        validated = validate_extraction(result, conversation)
        assert len(validated.skills) == 1
        # inferred ceiling is 0.6
        assert validated.skills[0].confidence <= 0.6

    def test_filters_invalid_skill_quotes(self) -> None:
        result = self._make_result(
            skills=[
                ExtractedSkill(
                    name="Go",
                    category="programming_language",
                    proficiency=0.7,
                    confidence=0.8,
                    source="observed",
                    source_quote="completely fabricated quote",
                ),
            ]
        )
        conversation = "working on the python project"
        validated = validate_extraction(result, conversation)
        assert len(validated.skills) == 0

    def test_filters_invalid_interest_quotes(self) -> None:
        result = self._make_result(
            interests=[
                ExtractedInterest(
                    entity_name="kubernetes",
                    entity_type="tool",
                    weight=0.8,
                    source="explicit",
                    source_quote="nonexistent quote about k8s",
                ),
            ]
        )
        conversation = "deploying to production server"
        validated = validate_extraction(result, conversation)
        assert len(validated.interests) == 0

    def test_valid_interest_preserved(self) -> None:
        result = self._make_result(
            interests=[
                ExtractedInterest(
                    entity_name="docker",
                    entity_type="tool",
                    weight=0.9,
                    source="explicit",
                    source_quote="really interested in docker",
                ),
            ]
        )
        conversation = "I am really interested in docker containers"
        validated = validate_extraction(result, conversation)
        assert len(validated.interests) == 1
        # explicit ceiling is 0.95, weight 0.9 stays
        assert validated.interests[0].weight <= 0.95


# ---------------------------------------------------------------------------
# LLMExtractionClient.extract_from_session
# ---------------------------------------------------------------------------


class TestLLMExtractionClient:
    @pytest.fixture()
    def client(self) -> LLMExtractionClient:
        return LLMExtractionClient(model_id="test-model", prompt_version="v1")

    async def test_returns_empty_when_no_events(self, client: LLMExtractionClient) -> None:
        result = await client.extract_from_session(
            events=[], session_id="sess-1", agent_id="agent-1"
        )
        assert result["session_id"] == "sess-1"
        assert result["agent_id"] == "agent-1"
        assert result["entities"] == []
        assert result["preferences"] == []
        assert result["skills"] == []
        assert result["interests"] == []

    async def test_returns_empty_when_llm_unavailable(self, client: LLMExtractionClient) -> None:
        events = make_session_events(n=3)
        result = await client.extract_from_session(
            events=events, session_id="sess-2", agent_id="agent-2"
        )
        assert result["session_id"] == "sess-2"
        assert result["entities"] == []

    async def test_result_contains_expected_keys(self, client: LLMExtractionClient) -> None:
        events = make_session_events(n=1)
        result = await client.extract_from_session(events=events, session_id="s", agent_id="a")
        expected_keys = {
            "session_id",
            "agent_id",
            "model_id",
            "prompt_version",
            "entities",
            "preferences",
            "skills",
            "interests",
        }
        assert expected_keys.issubset(set(result.keys()))
