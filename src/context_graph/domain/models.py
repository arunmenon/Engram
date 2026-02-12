"""Domain models for the context graph.

This module defines the shared contract for all phases. It is FROZEN after Phase 1 —
existing method signatures and model fields MUST NOT be modified. New methods, new fields
(with defaults), and new files MAY be added.

All models are pure Python + Pydantic v2. Zero framework imports.

Sources:
  - ADR-0004: Event schema (8 required + 6 optional fields)
  - ADR-0009: Multi-graph schema (node types, edge types, intent weights)
  - ADR-0011: Ontological foundation (event type taxonomy, entity type hierarchy)
  - ADR-0012: User personalization ontology (5 new node types, 9 new edge types)
  - ADR-0008: Decay scoring, retention tiers
  - ADR-0006: Atlas response pattern
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EventType(enum.StrEnum):
    """Event type taxonomy grounded in OTel GenAI Semantic Conventions (ADR-0011 §2)."""

    # Agent events
    AGENT_INVOKE = "agent.invoke"
    AGENT_CREATE = "agent.create"

    # Tool events
    TOOL_EXECUTE = "tool.execute"

    # LLM events
    LLM_CHAT = "llm.chat"
    LLM_COMPLETION = "llm.completion"
    LLM_EMBED = "llm.embed"
    LLM_GENERATE = "llm.generate"

    # Observation events
    OBSERVATION_INPUT = "observation.input"
    OBSERVATION_OUTPUT = "observation.output"

    # System events
    SYSTEM_SESSION_START = "system.session_start"
    SYSTEM_SESSION_END = "system.session_end"

    # User personalization events (ADR-0012 §6)
    USER_PREFERENCE_STATED = "user.preference.stated"
    USER_PREFERENCE_REVOKED = "user.preference.revoked"
    USER_SKILL_DECLARED = "user.skill.declared"
    USER_PROFILE_UPDATED = "user.profile.updated"


class EntityType(enum.StrEnum):
    """Entity type hierarchy grounded in PROV-O (ADR-0011 §3).

    prov:Agent subtypes: agent, user, service
    prov:Entity subtypes: tool, resource, concept
    """

    AGENT = "agent"
    USER = "user"
    SERVICE = "service"
    TOOL = "tool"
    RESOURCE = "resource"
    CONCEPT = "concept"


class EdgeType(enum.StrEnum):
    """All edge types across the graph schema.

    Core edges (ADR-0009): FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES
    Entity resolution edges (ADR-0011 §3): SAME_AS, RELATED_TO
    User personalization edges (ADR-0012 §2): HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL,
        DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL
    """

    # Core (ADR-0009)
    FOLLOWS = "FOLLOWS"
    CAUSED_BY = "CAUSED_BY"
    SIMILAR_TO = "SIMILAR_TO"
    REFERENCES = "REFERENCES"
    SUMMARIZES = "SUMMARIZES"

    # Entity resolution (ADR-0011)
    SAME_AS = "SAME_AS"
    RELATED_TO = "RELATED_TO"

    # User personalization (ADR-0012)
    HAS_PROFILE = "HAS_PROFILE"
    HAS_PREFERENCE = "HAS_PREFERENCE"
    HAS_SKILL = "HAS_SKILL"
    DERIVED_FROM = "DERIVED_FROM"
    EXHIBITS_PATTERN = "EXHIBITS_PATTERN"
    INTERESTED_IN = "INTERESTED_IN"
    ABOUT = "ABOUT"
    ABSTRACTED_FROM = "ABSTRACTED_FROM"
    PARENT_SKILL = "PARENT_SKILL"


class IntentType(enum.StrEnum):
    """Query intent classification (ADR-0009 + ADR-0012 §3).

    Core intents: why, when, what, related, general
    User personalization intents: who_is, how_does, personalize
    """

    WHY = "why"
    WHEN = "when"
    WHAT = "what"
    RELATED = "related"
    GENERAL = "general"
    WHO_IS = "who_is"
    HOW_DOES = "how_does"
    PERSONALIZE = "personalize"


class RetentionTier(enum.StrEnum):
    """Neo4j graph retention tiers (ADR-0008)."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVE = "archive"


class NodeType(enum.StrEnum):
    """All graph node types.

    Core (ADR-0009): Event, Entity, Summary
    User personalization (ADR-0012): UserProfile, Preference, Skill, Workflow, BehavioralPattern
    """

    EVENT = "Event"
    ENTITY = "Entity"
    SUMMARY = "Summary"
    USER_PROFILE = "UserProfile"
    PREFERENCE = "Preference"
    SKILL = "Skill"
    WORKFLOW = "Workflow"
    BEHAVIORAL_PATTERN = "BehavioralPattern"


class EventStatus(enum.StrEnum):
    """Event outcome status (ADR-0011 §2, aligned with schema.org Action status)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ReferenceRole(enum.StrEnum):
    """REFERENCES edge role values (ADR-0011 §3, aligned with schema.org Action vocabulary)."""

    AGENT = "agent"
    INSTRUMENT = "instrument"
    OBJECT = "object"
    RESULT = "result"
    PARTICIPANT = "participant"


class PreferencePolarity(enum.StrEnum):
    """Preference polarity (ADR-0012 §1.2)."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class PreferenceSource(enum.StrEnum):
    """Preference source tracking — CHI 2025 trichotomy (ADR-0012 §5)."""

    EXPLICIT = "explicit"
    IMPLICIT_INTENTIONAL = "implicit_intentional"
    IMPLICIT_UNINTENTIONAL = "implicit_unintentional"
    INFERRED = "inferred"


class PreferenceCategory(enum.StrEnum):
    """Preference category (ADR-0012 §1.2)."""

    TOOL = "tool"
    WORKFLOW = "workflow"
    COMMUNICATION = "communication"
    DOMAIN = "domain"
    ENVIRONMENT = "environment"
    STYLE = "style"


class PreferenceScope(enum.StrEnum):
    """Preference scope (ADR-0012 §1.2)."""

    GLOBAL = "global"
    AGENT = "agent"
    SESSION = "session"


class WorkflowAbstractionLevel(enum.StrEnum):
    """Workflow abstraction level (ADR-0012 §1.4)."""

    CASE = "case"
    STRATEGY = "strategy"
    SKILL = "skill"


class BehavioralPatternType(enum.StrEnum):
    """Behavioral pattern types (ADR-0012 §1.5)."""

    DELEGATION = "delegation"
    ESCALATION = "escalation"
    ROUTINE = "routine"
    AVOIDANCE = "avoidance"
    EXPLORATION = "exploration"
    SPECIALIZATION = "specialization"


class DerivationMethod(enum.StrEnum):
    """DERIVED_FROM edge derivation methods (ADR-0012 §2)."""

    STATED = "stated"
    RULE_EXTRACTION = "rule_extraction"
    LLM_EXTRACTION = "llm_extraction"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    STATISTICAL_INFERENCE = "statistical_inference"
    PATTERN_MATCH = "pattern_match"
    GRAPH_PATTERN = "graph_pattern"
    HIERARCHY_PROPAGATION = "hierarchy_propagation"


class CausalMechanism(enum.StrEnum):
    """CAUSED_BY edge mechanism (ADR-0009)."""

    DIRECT = "direct"
    INFERRED = "inferred"


# ---------------------------------------------------------------------------
# Event Model — THE shared contract (ADR-0004 + amendments)
# ---------------------------------------------------------------------------


class Event(BaseModel):
    """Immutable event record.

    8 required + 6 optional fields per ADR-0004 (amended by ADR-0010).
    This is the single source of truth for the event schema.
    """

    model_config = {"strict": True}

    # Required fields
    event_id: UUID
    event_type: str = Field(..., pattern=r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")
    occurred_at: datetime
    session_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    trace_id: str = Field(..., min_length=1)
    payload_ref: str = Field(..., min_length=1)
    global_position: str | None = Field(
        default=None,
        description="Redis Stream entry ID, auto-assigned on ingestion",
    )

    # Optional fields
    tool_name: str | None = None
    parent_event_id: UUID | None = None
    ended_at: datetime | None = None
    status: EventStatus | None = None
    schema_version: int | None = Field(default=1, ge=1)
    importance_hint: int | None = Field(default=None, ge=1, le=10)


# ---------------------------------------------------------------------------
# Graph Node Models — projected into Neo4j
# ---------------------------------------------------------------------------


class EventNode(BaseModel):
    """Event node in the Neo4j graph projection (ADR-0009)."""

    event_id: str
    event_type: str
    occurred_at: datetime
    session_id: str
    agent_id: str
    trace_id: str
    tool_name: str | None = None
    global_position: str

    # Derived attributes (populated by enrichment — ADR-0008 Stage 2)
    keywords: list[str] = Field(default_factory=list)
    summary: str | None = None
    embedding: list[float] = Field(default_factory=list)
    importance_score: int | None = Field(default=None, ge=1, le=10)
    access_count: int = 0
    last_accessed_at: datetime | None = None


class EntityNode(BaseModel):
    """Entity node derived during enrichment (ADR-0009)."""

    entity_id: str
    name: str
    entity_type: EntityType
    first_seen: datetime
    last_seen: datetime
    mention_count: int = 1


class SummaryNode(BaseModel):
    """Summary node created during re-consolidation (ADR-0009)."""

    summary_id: str
    scope: str  # "episode" | "session" | "agent"
    scope_id: str
    content: str
    created_at: datetime
    event_count: int
    time_range: list[datetime] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# User Personalization Node Models (ADR-0012)
# ---------------------------------------------------------------------------


class UserProfileNode(BaseModel):
    """UserProfile node (ADR-0012 §1.1)."""

    profile_id: str
    user_id: str
    display_name: str | None = None
    timezone: str | None = None
    language: str | None = None
    communication_style: str | None = None
    technical_level: str | None = None
    created_at: datetime
    updated_at: datetime


class PreferenceNode(BaseModel):
    """Preference node (ADR-0012 §1.2)."""

    preference_id: str
    category: PreferenceCategory
    key: str
    polarity: PreferencePolarity
    strength: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: PreferenceSource
    context: str | None = None
    scope: PreferenceScope
    scope_id: str | None = None
    observation_count: int = 1
    first_observed_at: datetime
    last_confirmed_at: datetime
    access_count: int = 0
    stability: float = 168.0
    superseded_by: str | None = None
    consent_ref: str | None = None


class SkillNode(BaseModel):
    """Skill node (ADR-0012 §1.3)."""

    skill_id: str
    name: str
    # "programming_language" | "tool_proficiency" | "domain_knowledge" | "workflow_skill"
    category: str
    description: str | None = None
    created_at: datetime


class WorkflowNode(BaseModel):
    """Workflow node (ADR-0012 §1.4)."""

    workflow_id: str
    name: str
    abstraction_level: WorkflowAbstractionLevel
    success_rate: float | None = None
    execution_count: int = 1
    avg_duration_ms: int | None = None
    source_session_ids: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BehavioralPatternNode(BaseModel):
    """BehavioralPattern node (ADR-0012 §1.5)."""

    pattern_id: str
    pattern_type: BehavioralPatternType
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    observation_count: int = 1
    involved_agents: list[str] = Field(default_factory=list)
    first_detected_at: datetime
    last_confirmed_at: datetime
    access_count: int = 0
    stability: float = 336.0


# ---------------------------------------------------------------------------
# Edge Models
# ---------------------------------------------------------------------------


class Edge(BaseModel):
    """Generic graph edge with type and properties."""

    source: str
    target: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Atlas Response Pattern (ADR-0006 + ADR-0009)
# ---------------------------------------------------------------------------


class Provenance(BaseModel):
    """Provenance pointer for a graph node (ADR-0009)."""

    event_id: str
    global_position: str
    source: str = "redis"
    occurred_at: datetime
    session_id: str
    agent_id: str
    trace_id: str


class NodeScores(BaseModel):
    """Decay and relevance scores for a graph node (ADR-0008 + ADR-0009)."""

    decay_score: float = 0.0
    relevance_score: float = 0.0
    importance_score: int = 0


class AtlasNode(BaseModel):
    """A node in an Atlas response."""

    node_id: str
    node_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance | None = None
    scores: NodeScores = Field(default_factory=NodeScores)
    retrieval_reason: str = "direct"  # "direct" | "proactive"
    proactive_signal: str | None = None


class AtlasEdge(BaseModel):
    """An edge in an Atlas response."""

    source: str
    target: str
    edge_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class QueryCapacity(BaseModel):
    """Query bounds used and available (ADR-0001)."""

    max_nodes: int
    used_nodes: int
    max_depth: int


class QueryMeta(BaseModel):
    """Response metadata with retrieval reasoning (ADR-0006 + ADR-0009 amendment)."""

    query_ms: int = 0
    nodes_returned: int = 0
    truncated: bool = False
    inferred_intents: dict[str, float] = Field(default_factory=dict)
    intent_override: str | None = None
    seed_nodes: list[str] = Field(default_factory=list)
    proactive_nodes_count: int = 0
    scoring_weights: dict[str, float] = Field(
        default_factory=lambda: {"recency": 1.0, "importance": 1.0, "relevance": 1.0}
    )
    capacity: QueryCapacity | None = None


class Pagination(BaseModel):
    """Cursor-based pagination."""

    cursor: str | None = None
    has_more: bool = False


class AtlasResponse(BaseModel):
    """Atlas response pattern (ADR-0006).

    All graph query responses use this shape.
    """

    nodes: dict[str, AtlasNode] = Field(default_factory=dict)
    edges: list[AtlasEdge] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)
    meta: QueryMeta = Field(default_factory=QueryMeta)


# ---------------------------------------------------------------------------
# Query Models
# ---------------------------------------------------------------------------


class EventQuery(BaseModel):
    """Parameters for searching events in the event store."""

    session_id: str | None = None
    agent_id: str | None = None
    trace_id: str | None = None
    event_type: str | None = None
    tool_name: str | None = None
    after: datetime | None = None
    before: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SubgraphQuery(BaseModel):
    """Parameters for subgraph retrieval (ADR-0006 + ADR-0009 amendment).

    The system infers intent and seed nodes from `query` when not provided.
    """

    query: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    max_nodes: int = Field(default=100, ge=1, le=500)
    max_depth: int = Field(default=3, ge=1, le=10)
    timeout_ms: int = Field(default=5000, ge=100, le=30000)
    intent: IntentType | None = None
    seed_nodes: list[str] | None = None


class LineageQuery(BaseModel):
    """Parameters for lineage traversal."""

    node_id: str = Field(..., min_length=1)
    max_depth: int = Field(default=3, ge=1, le=10)
    max_nodes: int = Field(default=100, ge=1, le=500)
    intent: IntentType | None = None
