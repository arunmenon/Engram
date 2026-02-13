"""LLM extraction client adapter (ADR-0013).

Implements the ExtractionService protocol using structured LLM output.
Constructs prompts with ontology schema, validates extractions against
conversation source text, and applies confidence priors.

Source: ADR-0013 §4, §7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.extraction import (
    SessionExtractionResult,
    apply_confidence_prior,
    validate_source_quote,
)

if TYPE_CHECKING:
    from context_graph.domain.models import Event

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Ontology schema description for the extraction prompt
# ---------------------------------------------------------------------------

_ONTOLOGY_SCHEMA = """
You are a knowledge extraction system. Extract structured information from
the conversation below according to the following schema.

## Entity Types
- agent: An AI agent or assistant
- user: A human user
- service: An external service or API
- tool: A tool or instrument used during the session
- resource: A document, file, or data resource
- concept: An abstract concept or topic

## Preference Categories
- tool: Preference about a specific tool or library
- workflow: Preference about how work is organized
- communication: Preference about communication style
- domain: Preference about a domain-specific topic
- environment: Preference about development or work environment
- style: Preference about coding or design style

## Preference Polarity
- positive: User likes / wants this
- negative: User dislikes / avoids this
- neutral: User mentioned without clear sentiment

## Preference Source
- explicit: User directly stated the preference
- implicit_intentional: Inferred from deliberate user behavior
- implicit_unintentional: Inferred from incidental user behavior

## Skill Categories
- programming_language: Proficiency in a programming language
- tool_proficiency: Proficiency with a specific tool
- domain_knowledge: Knowledge in a specific domain
- workflow_skill: Skill in a workflow or process

## Skill Source
- observed: Inferred from user actions
- declared: User explicitly stated the skill
- inferred: Statistically inferred from patterns

## Interest Source
- explicit: User directly expressed interest
- implicit: Inferred from user behavior
- inferred: Statistically inferred

## Output Format
Return a JSON object with these keys:
- entities: list of {name, entity_type, confidence, source_quote}
- preferences: list of {category, key, polarity, strength, confidence,
    source, context, about_entity, source_quote}
- skills: list of {name, category, proficiency, confidence, source,
    source_quote}
- interests: list of {entity_name, entity_type, weight, source,
    source_quote}

Rules:
- Every extraction MUST include a source_quote from the conversation
- Confidence scores: 0.0 to 1.0 (how sure you are)
- Strength/proficiency/weight: 0.0 to 1.0 (how strong the signal is)
- Deduplicate against the existing entities list provided below
""".strip()


def build_extraction_prompt(
    events: list[Event],
    existing_entities: list[dict[str, Any]],
) -> str:
    """Construct the system prompt with ontology schema and existing entities.

    Includes the full extraction target schema description per ADR-0013 §4
    and appends existing entity names for deduplication.
    """
    prompt_parts = [_ONTOLOGY_SCHEMA]

    if existing_entities:
        entity_names = [e.get("name", "") for e in existing_entities if e.get("name")]
        if entity_names:
            prompt_parts.append(
                "\n## Existing Entities (deduplicate against these)\n"
                + "\n".join(f"- {name}" for name in entity_names)
            )

    prompt_parts.append("\n## Conversation\n" + build_conversation_text(events))

    return "\n\n".join(prompt_parts)


def build_conversation_text(events: list[Event]) -> str:
    """Reconstruct a readable conversation from a list of events.

    Produces a turn-by-turn transcript with event metadata for source
    quote validation.
    """
    lines: list[str] = []
    for idx, event in enumerate(events):
        event_type = event.event_type
        agent = event.agent_id
        tool = event.tool_name or ""
        timestamp = event.occurred_at.isoformat()

        header = f"[Turn {idx}] [{timestamp}] {event_type}"
        if tool:
            header += f" tool={tool}"
        header += f" agent={agent}"

        lines.append(header)
        lines.append(f"  payload_ref: {event.payload_ref}")
        if event.status:
            lines.append(f"  status: {event.status}")
        lines.append("")

    return "\n".join(lines)


def validate_extraction(
    result: SessionExtractionResult,
    conversation_text: str,
) -> SessionExtractionResult:
    """Apply confidence priors and validate source quotes.

    Filters out extractions whose source_quote cannot be found in the
    conversation text and applies per-source-type confidence ceilings
    (ADR-0013 §7).
    """
    valid_entities = []
    for entity in result.entities:
        if validate_source_quote(entity.source_quote, conversation_text):
            valid_entities.append(entity)
        else:
            log.debug(
                "entity_source_quote_invalid",
                entity_name=entity.name,
                quote=entity.source_quote[:50],
            )

    valid_preferences = []
    for pref in result.preferences:
        if not validate_source_quote(pref.source_quote, conversation_text):
            log.debug(
                "preference_source_quote_invalid",
                key=pref.key,
                quote=pref.source_quote[:50],
            )
            continue
        adjusted_confidence = apply_confidence_prior(pref.confidence, pref.source)
        valid_preferences.append(pref.model_copy(update={"confidence": adjusted_confidence}))

    valid_skills = []
    for skill in result.skills:
        if not validate_source_quote(skill.source_quote, conversation_text):
            log.debug(
                "skill_source_quote_invalid",
                name=skill.name,
                quote=skill.source_quote[:50],
            )
            continue
        adjusted_confidence = apply_confidence_prior(skill.confidence, skill.source)
        valid_skills.append(skill.model_copy(update={"confidence": adjusted_confidence}))

    valid_interests = []
    for interest in result.interests:
        if not validate_source_quote(interest.source_quote, conversation_text):
            log.debug(
                "interest_source_quote_invalid",
                entity_name=interest.entity_name,
                quote=interest.source_quote[:50],
            )
            continue
        adjusted_confidence = apply_confidence_prior(interest.weight, interest.source)
        valid_interests.append(interest.model_copy(update={"weight": adjusted_confidence}))

    return result.model_copy(
        update={
            "entities": valid_entities,
            "preferences": valid_preferences,
            "skills": valid_skills,
            "interests": valid_interests,
        }
    )


class LLMExtractionClient:
    """LLM-based knowledge extraction client.

    Implements the ExtractionService protocol. Builds structured prompts
    with the ontology schema, calls an LLM for extraction, and validates
    the results against the source conversation.
    """

    def __init__(
        self,
        model_id: str = "claude-haiku-4.5",
        prompt_version: str = "v1",
    ) -> None:
        self._model_id = model_id
        self._prompt_version = prompt_version

    async def extract_from_session(
        self,
        events: list[Event],
        session_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Extract knowledge from session events.

        Builds the extraction prompt, calls the LLM, validates results,
        and returns a dict of extracted items.
        """
        if not events:
            log.info(
                "extraction_skipped_no_events",
                session_id=session_id,
            )
            return _empty_result(session_id, agent_id)

        _conversation_text = build_conversation_text(events)
        _prompt = build_extraction_prompt(events, existing_entities=[])

        # TODO: Call LLM API (instructor + litellm) when available.
        # The prompt is constructed above; once the LLM adapter is wired,
        # replace this block with:
        #   raw_result = await self._call_llm(prompt, conversation_text)
        #   validated = validate_extraction(raw_result, conversation_text)
        #   return validated.model_dump()
        log.info(
            "extraction_llm_not_available",
            session_id=session_id,
            model_id=self._model_id,
            prompt_version=self._prompt_version,
            event_count=len(events),
        )
        return _empty_result(session_id, agent_id)


def _empty_result(session_id: str, agent_id: str) -> dict[str, Any]:
    """Return an empty extraction result dict."""
    return SessionExtractionResult(
        session_id=session_id,
        agent_id=agent_id,
        entities=[],
        preferences=[],
        skills=[],
        interests=[],
    ).model_dump()
