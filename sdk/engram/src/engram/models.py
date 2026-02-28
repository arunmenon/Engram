from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

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
