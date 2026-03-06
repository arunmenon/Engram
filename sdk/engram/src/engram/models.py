from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Enums (subset used by SDK clients) ---


class IntentType(str, enum.Enum):
    WHY = "why"
    WHEN = "when"
    WHAT = "what"
    RELATED = "related"
    GENERAL = "general"
    WHO_IS = "who_is"
    HOW_DOES = "how_does"
    PERSONALIZE = "personalize"


class EventStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# --- Event (for ingest) ---


class Event(BaseModel):
    """Event to be ingested. Most fields are auto-populated by SessionManager."""

    model_config = {"populate_by_name": True}

    event_id: UUID
    event_type: str
    occurred_at: datetime
    session_id: str
    agent_id: str
    trace_id: str
    payload_ref: str
    global_position: str | None = None
    tool_name: str | None = None
    parent_event_id: UUID | None = None
    ended_at: datetime | None = None
    status: EventStatus | None = None
    schema_version: int = 1
    importance_hint: int | None = Field(default=None, ge=1, le=10)
    payload: dict[str, Any] | None = None


# --- Ingest responses ---


class IngestResult(BaseModel):
    """Result from ingesting a single event."""

    event_id: str
    global_position: str


class BatchResult(BaseModel):
    """Result from batch ingest."""

    accepted: int
    rejected: int
    results: list[IngestResult]
    errors: list[dict[str, Any]]


# --- Atlas response models ---


class Provenance(BaseModel):
    """Provenance metadata for a graph node."""

    event_id: str
    global_position: str
    source: str = "redis"
    occurred_at: datetime
    session_id: str
    agent_id: str
    trace_id: str


class NodeScores(BaseModel):
    """Scoring information for a graph node."""

    decay_score: float = 0.0
    relevance_score: float = 0.0
    importance_score: int = 0


class AtlasNode(BaseModel):
    """A node in the Atlas response."""

    node_id: str
    node_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance | None = None
    scores: NodeScores = Field(default_factory=NodeScores)
    retrieval_reason: str = "direct"
    proactive_signal: str | None = None


class AtlasEdge(BaseModel):
    """An edge in the Atlas response."""

    source: str
    target: str
    edge_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class QueryCapacity(BaseModel):
    """Capacity limits for a query."""

    max_nodes: int
    used_nodes: int
    max_depth: int


class QueryMeta(BaseModel):
    """Metadata about a query response."""

    query_ms: int = 0
    nodes_returned: int = 0
    truncated: bool = False
    inferred_intents: dict[str, float] = Field(default_factory=dict)
    intent_override: str | None = None
    seed_nodes: list[str] = Field(default_factory=list)
    seed_strategy: str | None = None
    proactive_nodes_count: int = 0
    scoring_weights: dict[str, float] = Field(
        default_factory=lambda: {"recency": 1.0, "importance": 1.0, "relevance": 1.0}
    )
    capacity: QueryCapacity | None = None


class Pagination(BaseModel):
    """Cursor-based pagination info."""

    cursor: str | None = None
    has_more: bool = False


class AtlasResponse(BaseModel):
    """Atlas response returned by context, subgraph, and lineage endpoints."""

    nodes: dict[str, AtlasNode] = Field(default_factory=dict)
    edges: list[AtlasEdge] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)
    meta: QueryMeta = Field(default_factory=QueryMeta)

    # --- Convenience accessors ---

    _TEXT_KEYS = (
        "content",
        "payload_ref",
        "summary",
        "text",
        "belief_text",
        "description",
        "name",
    )

    @property
    def node_ids(self) -> list[str]:
        """Return all node IDs in insertion order."""
        return list(self.nodes.keys())

    def texts(self) -> list[str]:
        """Extract the primary text from each node."""
        result: list[str] = []
        for node in self.nodes.values():
            for key in self._TEXT_KEYS:
                val = node.attributes.get(key)
                if val and isinstance(val, str):
                    result.append(val)
                    break
        return result

    def as_context_string(self, separator: str = "\n---\n") -> str:
        """Format nodes as a single string suitable for LLM context injection."""
        parts: list[str] = []
        for node in self.nodes.values():
            text = ""
            for key in self._TEXT_KEYS:
                val = node.attributes.get(key)
                if val and isinstance(val, str):
                    text = val
                    break
            if text:
                score = node.scores.decay_score
                parts.append(f"[{node.node_type}] {text} (score: {score:.2f})")
        return separator.join(parts)


# --- Subgraph query input ---


class SubgraphQuery(BaseModel):
    """Input for subgraph query endpoint."""

    query: str
    session_id: str
    agent_id: str
    max_nodes: int = 100
    max_depth: int = 3
    timeout_ms: int = 5000
    intent: str | None = None
    seed_nodes: list[str] | None = None
    cursor: str | None = None


# --- Health ---


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    redis: bool
    neo4j: bool
    version: str


# --- User profile ---


class UserProfile(BaseModel):
    """User profile from GET /v1/users/{user_id}/profile."""

    profile_id: str | None = None
    user_id: str | None = None
    display_name: str | None = None
    timezone: str | None = None
    language: str | None = None
    communication_style: str | None = None
    technical_level: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Entity ---


class EntityResponse(BaseModel):
    """Entity from GET /v1/entities/{entity_id}. Server returns a dict."""

    model_config = {"extra": "allow"}

    entity_id: str | None = None
    name: str | None = None
    entity_type: str | None = None


# --- Admin ---


class StatsResponse(BaseModel):
    """Admin stats response."""

    nodes: dict[str, int] = Field(default_factory=dict)
    edges: dict[str, int] = Field(default_factory=dict)
    total_nodes: int = 0
    total_edges: int = 0
    redis: dict[str, Any] = Field(default_factory=dict)


# --- User sub-models (preferences, skills, patterns, interests) ---


class PreferenceNode(BaseModel):
    """User preference from GET /v1/users/{user_id}/preferences."""

    model_config = ConfigDict(extra="allow")

    preference_id: str = ""
    category: str = ""
    key: str = ""
    value: str = ""
    polarity: str = "positive"
    confidence: float = 0.0


class SkillNode(BaseModel):
    """User skill from GET /v1/users/{user_id}/skills."""

    model_config = ConfigDict(extra="allow")

    skill_id: str = ""
    name: str = ""
    level: str = ""
    confidence: float = 0.0


class BehavioralPatternNode(BaseModel):
    """Behavioral pattern from GET /v1/users/{user_id}/patterns."""

    model_config = ConfigDict(extra="allow")

    pattern_id: str = ""
    pattern_type: str = ""
    description: str = ""
    frequency: int = 0
    confidence: float = 0.0


class InterestNode(BaseModel):
    """User interest from GET /v1/users/{user_id}/interests."""

    model_config = ConfigDict(extra="allow")

    entity_id: str = ""
    name: str = ""
    entity_type: str = ""
    strength: float = 0.0


# --- GDPR response models ---


class GDPRExportResponse(BaseModel):
    """GDPR data export response from GET /v1/users/{user_id}/data-export."""

    model_config = ConfigDict(extra="allow")

    events: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)


class GDPRDeleteResponse(BaseModel):
    """GDPR cascade erasure response from DELETE /v1/users/{user_id}."""

    model_config = ConfigDict(extra="allow")

    deleted_nodes: int = 0
    deleted_edges: int = 0


# --- Admin response models ---


class ReconsolidateResponse(BaseModel):
    """Response from POST /v1/admin/reconsolidate."""

    model_config = ConfigDict(extra="allow")

    status: str = ""


class PruneResponse(BaseModel):
    """Response from POST /v1/admin/prune."""

    model_config = ConfigDict(extra="allow")

    pruned: int = 0
    dry_run: bool = True


class DetailedHealthResponse(BaseModel):
    """Response from GET /v1/admin/health/detailed."""

    model_config = ConfigDict(extra="allow")

    redis: dict[str, Any] = Field(default_factory=dict)
    neo4j: dict[str, Any] = Field(default_factory=dict)


# --- Simple API models ---


class Memory(BaseModel):
    """A single memory item returned by the simple search() API."""

    model_config = ConfigDict(extra="allow")

    text: str
    confidence: float = 0.0
    source_session: str = ""
    created_at: str = ""
    memory_id: str = ""
    node_type: str = ""
    score: float = 0.0
