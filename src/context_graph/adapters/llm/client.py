"""LLM extraction client adapter (ADR-0013).

Implements the ExtractionService protocol using structured LLM output.
Constructs prompts with ontology schema, validates extractions against
conversation source text, and applies confidence priors.

Uses litellm for multi-provider LLM routing with JSON mode.

Source: ADR-0013 §4, §7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.domain.extraction import (
    ExtractedEntity,
    ExtractedInterest,
    ExtractedPersona,
    ExtractedPreference,
    ExtractedSkill,
    SessionExtractionResult,
    apply_confidence_prior,
    validate_source_quote,
)

if TYPE_CHECKING:
    from context_graph.domain.models import Event

log = structlog.get_logger(__name__)


def _try_parse_inline_payload(payload_ref: str) -> dict[str, Any] | None:
    """Try to parse a payload_ref string as inline JSON.

    Returns the parsed dict if *payload_ref* is a valid JSON object (starts
    with ``{``), otherwise returns ``None``.  This provides backward
    compatibility for legacy events that embedded conversation content
    directly in the ``payload_ref`` field.
    """
    if not payload_ref or not payload_ref.strip().startswith("{"):
        return None
    try:
        parsed = orjson.loads(payload_ref)
        if isinstance(parsed, dict):
            return parsed
    except (orjson.JSONDecodeError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Ontology schema description for the extraction prompt
# ---------------------------------------------------------------------------

_ONTOLOGY_SCHEMA = """
You are a knowledge extraction system specializing in extracting structured
user information from support and technical conversations. Your goal is to
identify ALL entities, user preferences, skills, interests, and persona
information present in the conversation. Pay special attention to implicit
signals — role titles, technical vocabulary, communication patterns, and
tool mentions all carry extractable knowledge.

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
- declared: User explicitly stated the skill ("I'm experienced with X")
- inferred: Statistically inferred from patterns

## Interest Source
- explicit: User directly expressed interest
- implicit: Inferred from user behavior
- inferred: Statistically inferred

## Persona Fields
- name: The user's name if mentioned
- role: Job title or role (e.g., "Engineering Team Lead", "Customer Support Agent")
- tech_level: One of "beginner", "intermediate", "advanced", "expert"
- communication_style: How the user communicates (e.g., "Direct, technical")

## Output Format
Return a JSON object with ALL of these keys (use empty arrays if none found):
- persona: {name, role, tech_level, communication_style, source_quote} or null
- entities: list of {name, entity_type, confidence, source_quote}
- preferences: list of {category, key, polarity, strength, confidence,
    source, context, about_entity, source_quote}
- skills: list of {name, category, proficiency, confidence, source,
    source_quote}
- interests: list of {entity_name, entity_type, weight, source,
    source_quote}

## Few-Shot Example

Given a conversation where a support agent helps "Sarah Chen" (Engineering Team Lead)
with a PayPal API integration issue, and she mentions preferring code snippets over
step-by-step instructions, the expected output would be:

```json
{
  "persona": {
    "name": "Sarah Chen",
    "role": "Engineering Team Lead",
    "tech_level": "advanced",
    "communication_style": "Direct, technical",
    "source_quote": "Sarah Chen, Engineering Team Lead"
  },
  "entities": [
    {"name": "Sarah Chen", "entity_type": "user", "confidence": 0.95, "source_quote": "Sarah Chen"},
    {"name": "PayPal", "entity_type": "service", "confidence": 0.95, "source_quote": "PayPal API"},
    {"name": "Node.js", "entity_type": "tool", "confidence": 0.9, "source_quote": "Node.js SDK"}
  ],
  "preferences": [
    {"category": "communication", "key": "code_snippets_over_instructions", "polarity": "positive",
     "strength": 0.8, "confidence": 0.85, "source": "explicit",
     "context": "prefers seeing code examples", "about_entity": "code snippets",
     "source_quote": "just show me the code snippet"},
    {"category": "style", "key": "direct_technical_communication", "polarity": "positive",
     "strength": 0.7, "confidence": 0.7, "source": "implicit_intentional",
     "context": "uses technical terminology naturally", "about_entity": null,
     "source_quote": "webhook endpoint returning 403"}
  ],
  "skills": [
    {"name": "Node.js", "category": "programming_language", "proficiency": 0.8,
     "confidence": 0.85, "source": "observed", "source_quote": "our Node.js integration"},
    {"name": "API Integration", "category": "domain_knowledge", "proficiency": 0.7,
     "confidence": 0.75, "source": "inferred", "source_quote": "webhook endpoint"}
  ],
  "interests": [
    {"entity_name": "PayPal", "entity_type": "service", "weight": 0.8,
     "source": "explicit", "source_quote": "PayPal API integration"}
  ]
}
```

## Extraction Rules
- Every extraction MUST include a source_quote — a phrase from the conversation that supports it
- source_quote should be a short phrase (5-20 words) from the conversation, not a full sentence
- Confidence scores: 0.0 to 1.0 (how sure you are about this extraction)
- Strength/proficiency/weight: 0.0 to 1.0 (how strong the signal is)
- Extract persona info whenever a user's name, role, or technical level is apparent
- Look for IMPLICIT preferences: communication style, tool choices, vocabulary level
- Look for IMPLICIT skills: technical terminology usage, role-based knowledge
- Deduplicate against the existing entities list provided below
""".strip()


def build_extraction_prompt(
    events: list[Event],
    existing_entities: list[dict[str, Any]],
    event_payloads: list[dict[str, Any]] | None = None,
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

    conversation_body = build_conversation_text(events, event_payloads=event_payloads)
    prompt_parts.append(
        "\n## Conversation\n<conversation>\n" + conversation_body + "\n</conversation>"
    )

    return "\n\n".join(prompt_parts)


def build_conversation_text(
    events: list[Event],
    event_payloads: list[dict[str, Any]] | None = None,
) -> str:
    """Reconstruct a readable conversation from a list of events.

    Produces a turn-by-turn transcript with event metadata and actual
    message content (from payloads) for source quote validation.
    """
    payload_lookup: dict[str, dict[str, Any]] = {}
    if event_payloads:
        for doc in event_payloads:
            eid = doc.get("event_id", "")
            if eid:
                payload_lookup[eid] = doc

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

        # Include actual message content from payload
        event_id_str = str(event.event_id)
        doc = payload_lookup.get(event_id_str, {})
        payload = doc.get("payload")
        # Fallback: try parsing payload_ref as inline JSON for legacy events
        if payload is None:
            payload = _try_parse_inline_payload(event.payload_ref)
        if isinstance(payload, dict):
            content = payload.get("content")
            if content:
                lines.append(f"  content: {content}")
            # Also include tool input/output if present
            tool_input = payload.get("input")
            if tool_input:
                input_str = str(tool_input)
                if len(input_str) > 500:
                    input_str = input_str[:500] + "..."
                lines.append(f"  input: {input_str}")
            tool_output = payload.get("output")
            if tool_output:
                output_str = str(tool_output)
                if len(output_str) > 500:
                    output_str = output_str[:500] + "..."
                lines.append(f"  output: {output_str}")

        lines.append("")

    return "\n".join(lines)


def validate_extraction(
    result: SessionExtractionResult,
    conversation_text: str,
    min_thresholds: dict[str, float] | None = None,
) -> SessionExtractionResult:
    """Apply confidence priors, validate source quotes, and gate on min thresholds.

    Filters out extractions whose source_quote cannot be found in the
    conversation text and applies per-source-type confidence ceilings
    (ADR-0013 §7). When *min_thresholds* is provided, extractions whose
    adjusted confidence falls below the threshold for their source type
    are also dropped.
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
        if min_thresholds:
            min_conf = min_thresholds.get(pref.source, 0.0)
            if adjusted_confidence < min_conf:
                log.debug(
                    "preference_below_min_threshold",
                    key=pref.key,
                    confidence=adjusted_confidence,
                    min=min_conf,
                )
                continue
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
        if min_thresholds:
            min_conf = min_thresholds.get(skill.source, 0.0)
            if adjusted_confidence < min_conf:
                log.debug(
                    "skill_below_min_threshold",
                    name=skill.name,
                    confidence=adjusted_confidence,
                    min=min_conf,
                )
                continue
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
        if min_thresholds:
            min_conf = min_thresholds.get(interest.source, 0.0)
            if adjusted_confidence < min_conf:
                log.debug(
                    "interest_below_min_threshold",
                    entity_name=interest.entity_name,
                    confidence=adjusted_confidence,
                    min=min_conf,
                )
                continue
        valid_interests.append(interest.model_copy(update={"weight": adjusted_confidence}))

    return result.model_copy(
        update={
            "entities": valid_entities,
            "preferences": valid_preferences,
            "skills": valid_skills,
            "interests": valid_interests,
        }
    )


# ---------------------------------------------------------------------------
# LLM output coercion — normalize enum values the LLM may get wrong
# ---------------------------------------------------------------------------

_PREFERENCE_SOURCE_MAP: dict[str, str] = {
    "explicit": "explicit",
    "implicit": "implicit_intentional",
    "implicit_intentional": "implicit_intentional",
    "implicit_unintentional": "implicit_unintentional",
    "inferred": "implicit_unintentional",
    "observed": "implicit_intentional",
}

_SKILL_SOURCE_MAP: dict[str, str] = {
    "observed": "observed",
    "declared": "declared",
    "inferred": "inferred",
    "explicit": "declared",
    "implicit": "observed",
    "implicit_intentional": "observed",
}

_INTEREST_SOURCE_MAP: dict[str, str] = {
    "explicit": "explicit",
    "implicit": "implicit",
    "inferred": "inferred",
    "observed": "implicit",
    "implicit_intentional": "implicit",
    "implicit_unintentional": "implicit",
}


def _coerce_preference(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a preference dict's enum fields to valid Literal values."""
    raw = dict(raw)
    if "source" in raw:
        raw["source"] = _PREFERENCE_SOURCE_MAP.get(raw["source"], "implicit_intentional")
    return raw


def _coerce_skill(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a skill dict's enum fields to valid Literal values."""
    raw = dict(raw)
    if "source" in raw:
        raw["source"] = _SKILL_SOURCE_MAP.get(raw["source"], "observed")
    return raw


def _coerce_interest(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize an interest dict's enum fields to valid Literal values."""
    raw = dict(raw)
    if "source" in raw:
        raw["source"] = _INTEREST_SOURCE_MAP.get(raw["source"], "implicit")
    return raw


def _parse_items_individually(
    raw_list: list[dict[str, Any]],
    model_cls: type,
    coerce_fn: Any | None = None,
    label: str = "item",
    session_id: str = "",
) -> list[Any]:
    """Validate each item individually so one bad item doesn't drop all results."""
    valid = []
    for item in raw_list:
        try:
            if coerce_fn:
                item = coerce_fn(item)
            valid.append(model_cls.model_validate(item))
        except Exception:
            log.debug(
                f"{label}_validation_failed",
                session_id=session_id,
                data=str(item)[:200],
            )
    return valid


class LLMExtractionClient:
    """LLM-based knowledge extraction client.

    Implements the ExtractionService protocol. Builds structured prompts
    with the ontology schema, calls an LLM for extraction, and validates
    the results against the source conversation.
    """

    def __init__(
        self,
        model_id: str = "gpt-5.2-2025-12-11",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 2,
        prompt_version: str = "v1",
    ) -> None:
        self._model_id = model_id
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_retries = max_retries
        self._prompt_version = prompt_version

    async def generate_text(self, prompt: str) -> str | None:
        """Generate text from a prompt. Used for HyDE and other expansions."""
        # TODO: Implement actual LLM call via litellm
        return None

    async def _call_llm(self, system_prompt: str) -> str:
        """Call the LLM via litellm and return raw response text.

        Raises on network/API errors after retries are exhausted.
        """
        import litellm

        response = await litellm.acompletion(
            model=self._model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Extract ALL structured knowledge from the "
                        "conversation above. You MUST extract: "
                        "(1) persona info if any user name, role, "
                        "or tech level is mentioned, "
                        "(2) all entities (people, tools, services), "
                        "(3) all preferences (explicit AND implicit), "
                        "(4) all skills (declared, observed, inferred), "
                        "(5) all interests. "
                        "Return ONLY valid JSON matching the schema."
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
            num_retries=self._max_retries,
        )
        raw = response.choices[0].message.content
        return str(raw) if raw is not None else ""

    async def extract_from_session(
        self,
        events: list[Event],
        session_id: str,
        agent_id: str,
        event_payloads: list[dict[str, Any]] | None = None,
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

        conversation_text = build_conversation_text(events, event_payloads=event_payloads)
        prompt = build_extraction_prompt(
            events, existing_entities=[], event_payloads=event_payloads
        )

        for attempt in range(self._max_retries + 1):
            try:
                raw_text = await self._call_llm(prompt)
                parsed = orjson.loads(raw_text)

                # Parse persona — may be a dict or None
                persona_raw = parsed.get("persona")
                persona = None
                if isinstance(persona_raw, dict) and any(persona_raw.values()):
                    try:
                        persona = ExtractedPersona(**persona_raw)
                    except Exception:
                        log.debug("persona_parse_failed", session_id=session_id)

                # Per-item validation with enum coercion (GAP 8 + GAP 9)
                entities = _parse_items_individually(
                    parsed.get("entities", []),
                    ExtractedEntity,
                    label="entity",
                    session_id=session_id,
                )
                preferences = _parse_items_individually(
                    parsed.get("preferences", []),
                    ExtractedPreference,
                    coerce_fn=_coerce_preference,
                    label="preference",
                    session_id=session_id,
                )
                skills = _parse_items_individually(
                    parsed.get("skills", []),
                    ExtractedSkill,
                    coerce_fn=_coerce_skill,
                    label="skill",
                    session_id=session_id,
                )
                interests = _parse_items_individually(
                    parsed.get("interests", []),
                    ExtractedInterest,
                    coerce_fn=_coerce_interest,
                    label="interest",
                    session_id=session_id,
                )

                raw_result = SessionExtractionResult(
                    session_id=session_id,
                    agent_id=agent_id,
                    model_id=self._model_id,
                    prompt_version=self._prompt_version,
                    entities=entities,
                    preferences=preferences,
                    skills=skills,
                    interests=interests,
                    persona=persona,
                )

                if detect_degenerate_output(raw_result):
                    log.warning(
                        "extraction_degenerate_output",
                        session_id=session_id,
                        attempt=attempt,
                    )
                    if attempt < self._max_retries:
                        continue
                    return _empty_result(session_id, agent_id)

                validated = validate_extraction(raw_result, conversation_text)
                log.info(
                    "extraction_llm_success",
                    session_id=session_id,
                    model_id=self._model_id,
                    entities=len(validated.entities),
                    preferences=len(validated.preferences),
                    skills=len(validated.skills),
                    interests=len(validated.interests),
                )
                return validated.model_dump()

            except orjson.JSONDecodeError:
                log.warning(
                    "extraction_json_parse_failed",
                    session_id=session_id,
                    attempt=attempt,
                )
                if attempt >= self._max_retries:
                    return _empty_result(session_id, agent_id)
            except Exception:
                log.exception(
                    "extraction_llm_error",
                    session_id=session_id,
                    attempt=attempt,
                    model_id=self._model_id,
                )
                if attempt >= self._max_retries:
                    return _empty_result(session_id, agent_id)

        return _empty_result(session_id, agent_id)


def detect_degenerate_output(result: SessionExtractionResult) -> bool:
    """Check if extraction output is degenerate (all confidences nearly identical).

    Returns True if the standard deviation of all confidence scores is < 0.02,
    which suggests the model is not discriminating between extractions.
    A well-calibrated LLM may legitimately assign similar scores (e.g. 0.8-0.9)
    when evidence quality is uniformly strong, so the threshold is kept low.
    """
    confidences: list[float] = []
    for entity in result.entities:
        confidences.append(entity.confidence)
    for pref in result.preferences:
        confidences.append(pref.confidence)
    for skill in result.skills:
        confidences.append(skill.confidence)
    for interest in result.interests:
        confidences.append(interest.weight)

    if len(confidences) < 3:
        return False

    mean = sum(confidences) / len(confidences)
    variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
    std_dev = variance**0.5
    return bool(std_dev < 0.02)


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
