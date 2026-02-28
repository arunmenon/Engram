"""Application settings via Pydantic BaseSettings.

All configuration uses the CG_ environment variable prefix.
Centralized here to prevent hardcoded magic numbers across the codebase.

Sources:
  - ADR-0008: Decay scoring defaults (S_base, S_boost, weights)
  - ADR-0009: Intent weight matrix, traversal bounds
  - ADR-0010: Redis connection, consumer group names
  - ADR-0012: Preference stability defaults, confidence thresholds
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from context_graph.domain.models import EdgeType, IntentType


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = {"env_prefix": "CG_REDIS_"}

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    # Stream keys
    global_stream: str = "events:__global__"
    dedup_set: str = "dedup:events"

    # Consumer group names (ADR-0013)
    group_projection: str = "graph-projection"
    group_extraction: str = "session-extraction"
    group_enrichment: str = "enrichment"
    group_consolidation: str = "consolidation"

    # Consumer group block timeout (ms)
    block_timeout_ms: int = 5000

    # Event key prefix
    event_key_prefix: str = "evt:"

    # RediSearch index name
    event_index: str = "idx:events"

    # Replica acknowledgment — if True, WAIT for 1 replica after writes
    replica_wait: bool = False

    # Hot tier window (days) — stream entries trimmed after this
    hot_window_days: int = 7

    # Total retention ceiling (days) — JSON docs deleted after this
    retention_ceiling_days: int = 90

    # Approximate MAXLEN for global stream XADD (0 = uncapped) — ADR-0014
    global_stream_maxlen: int = 0

    # Session stream retention (hours) — streams older than this are deleted
    session_stream_retention_hours: int = 168  # 7 days


class Neo4jSettings(BaseSettings):
    """Neo4j connection settings."""

    model_config = {"env_prefix": "CG_NEO4J_"}

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: SecretStr = SecretStr("engram-dev-password")
    database: str = "neo4j"
    max_connection_pool_size: int = 50


class DecaySettings(BaseSettings):
    """Ebbinghaus decay scoring parameters (ADR-0008)."""

    model_config = {"env_prefix": "CG_DECAY_"}

    # Stability factor defaults (hours)
    s_base: float = 168.0  # 1 week time constant (half-life ~4.85 days)
    s_boost: float = 24.0  # Each access adds 24h of stability

    # Scoring weights: score = w_r*recency + w_i*importance + w_v*relevance + w_u*user_affinity
    weight_recency: float = 1.0
    weight_importance: float = 1.0
    weight_relevance: float = 1.0
    weight_user_affinity: float = 0.5

    # Similarity threshold for SIMILAR_TO edge creation
    similarity_threshold: float = 0.85

    # Reflection trigger threshold (ADR-0008)
    reflection_threshold: int = 150

    # Re-consolidation interval (hours) — supports fractional for testing
    reconsolidation_interval_hours: float = 6.0


class RetentionSettings(BaseSettings):
    """Neo4j graph retention tier boundaries (ADR-0008)."""

    model_config = {"env_prefix": "CG_RETENTION_"}

    # Neo4j retention tiers (hours)
    hot_hours: int = 24
    warm_hours: int = 168  # 7 days
    cold_hours: int = 720  # 30 days

    # Warm tier: prune SIMILAR_TO edges below this score
    warm_min_similarity_score: float = 0.7

    # Cold tier thresholds
    cold_min_importance: int = 5
    cold_min_access_count: int = 3

    # Orphan cleanup batch size (nodes per transaction) — ADR-0014 Amendment
    orphan_cleanup_batch_size: int = 500


class QuerySettings(BaseSettings):
    """Bounded query limits (ADR-0001, ADR-0009)."""

    model_config = {"env_prefix": "CG_QUERY_"}

    # Traversal bounds
    default_max_depth: int = 3
    max_max_depth: int = 10
    default_max_nodes: int = 100
    max_max_nodes: int = 500
    default_timeout_ms: int = 5000
    max_timeout_ms: int = 30000

    # Multi-intent confidence threshold
    intent_confidence_threshold: float = 0.3

    # Maximum neighbors returned per seed node in subgraph traversal
    default_neighbor_limit: int = 50


class PreferenceSettings(BaseSettings):
    """Preference-specific settings (ADR-0012)."""

    model_config = {"env_prefix": "CG_PREF_"}

    # Default initial stability by category (hours) — ADR-0012 §7
    stability_communication: float = 720.0  # 30 days
    stability_environment: float = 720.0
    stability_tool: float = 336.0  # 14 days
    stability_workflow: float = 336.0
    stability_domain: float = 168.0  # 7 days
    stability_style: float = 168.0

    # Behavioral pattern default stability (hours) — ADR-0012 §1.5
    stability_behavioral_pattern: float = 336.0  # 14 days

    # Confidence thresholds for graph insertion (ADR-0013 §7)
    min_confidence_explicit: float = 0.7
    min_confidence_implicit_intentional: float = 0.4
    min_confidence_implicit_unintentional: float = 0.3
    min_confidence_inferred: float = 0.15

    # Max active preferences per user
    max_preferences_per_user: int = 500


# ---------------------------------------------------------------------------
# Intent Weight Matrix (ADR-0009 + ADR-0012 §3)
# ---------------------------------------------------------------------------

# Default intent weight matrix — configurable per deployment
INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    IntentType.WHY: {
        EdgeType.CAUSED_BY: 5.0,
        EdgeType.FOLLOWS: 1.0,
        EdgeType.SIMILAR_TO: 1.5,
        EdgeType.REFERENCES: 2.0,
        EdgeType.SUMMARIZES: 1.0,
    },
    IntentType.WHEN: {
        EdgeType.CAUSED_BY: 1.0,
        EdgeType.FOLLOWS: 5.0,
        EdgeType.SIMILAR_TO: 0.5,
        EdgeType.REFERENCES: 1.0,
        EdgeType.SUMMARIZES: 0.5,
    },
    IntentType.WHAT: {
        EdgeType.CAUSED_BY: 2.0,
        EdgeType.FOLLOWS: 1.0,
        EdgeType.SIMILAR_TO: 2.0,
        EdgeType.REFERENCES: 5.0,
        EdgeType.SUMMARIZES: 2.0,
    },
    IntentType.RELATED: {
        EdgeType.CAUSED_BY: 1.5,
        EdgeType.FOLLOWS: 0.5,
        EdgeType.SIMILAR_TO: 5.0,
        EdgeType.REFERENCES: 2.0,
        EdgeType.SUMMARIZES: 1.5,
    },
    IntentType.GENERAL: {
        EdgeType.CAUSED_BY: 2.0,
        EdgeType.FOLLOWS: 2.0,
        EdgeType.SIMILAR_TO: 2.0,
        EdgeType.REFERENCES: 2.0,
        EdgeType.SUMMARIZES: 2.0,
    },
    IntentType.WHO_IS: {
        EdgeType.CAUSED_BY: 1.0,
        EdgeType.FOLLOWS: 0.5,
        EdgeType.SIMILAR_TO: 1.0,
        EdgeType.REFERENCES: 3.0,
        EdgeType.SUMMARIZES: 1.0,
        EdgeType.HAS_PROFILE: 5.0,
        EdgeType.HAS_PREFERENCE: 5.0,
        EdgeType.HAS_SKILL: 5.0,
        EdgeType.EXHIBITS_PATTERN: 4.0,
        EdgeType.INTERESTED_IN: 4.0,
        EdgeType.ABOUT: 3.0,
        EdgeType.DERIVED_FROM: 2.0,
        EdgeType.ABSTRACTED_FROM: 1.0,
        EdgeType.PARENT_SKILL: 2.0,
        EdgeType.SAME_AS: 4.0,
        EdgeType.RELATED_TO: 3.0,
    },
    IntentType.HOW_DOES: {
        EdgeType.CAUSED_BY: 2.0,
        EdgeType.FOLLOWS: 3.0,
        EdgeType.SIMILAR_TO: 1.0,
        EdgeType.REFERENCES: 2.0,
        EdgeType.SUMMARIZES: 1.0,
        EdgeType.HAS_PROFILE: 1.0,
        EdgeType.HAS_PREFERENCE: 2.0,
        EdgeType.HAS_SKILL: 3.0,
        EdgeType.EXHIBITS_PATTERN: 5.0,
        EdgeType.INTERESTED_IN: 2.0,
        EdgeType.ABOUT: 1.0,
        EdgeType.DERIVED_FROM: 1.0,
        EdgeType.ABSTRACTED_FROM: 4.0,
        EdgeType.PARENT_SKILL: 1.0,
        EdgeType.SAME_AS: 1.0,
        EdgeType.RELATED_TO: 2.0,
    },
    IntentType.PERSONALIZE: {
        EdgeType.CAUSED_BY: 1.0,
        EdgeType.FOLLOWS: 0.5,
        EdgeType.SIMILAR_TO: 1.5,
        EdgeType.REFERENCES: 2.0,
        EdgeType.SUMMARIZES: 1.0,
        EdgeType.HAS_PROFILE: 4.0,
        EdgeType.HAS_PREFERENCE: 5.0,
        EdgeType.HAS_SKILL: 4.0,
        EdgeType.EXHIBITS_PATTERN: 3.0,
        EdgeType.INTERESTED_IN: 4.0,
        EdgeType.ABOUT: 3.0,
        EdgeType.DERIVED_FROM: 3.0,
        EdgeType.ABSTRACTED_FROM: 1.0,
        EdgeType.PARENT_SKILL: 2.0,
        EdgeType.SAME_AS: 2.0,
        EdgeType.RELATED_TO: 2.0,
    },
}


# ---------------------------------------------------------------------------
# OTel Mapping (ADR-0011 §2)
# ---------------------------------------------------------------------------

OTEL_TO_EVENT_TYPE: dict[str, str] = {
    "invoke_agent": "agent.invoke",
    "create_agent": "agent.create",
    "execute_tool": "tool.execute",
    "chat": "llm.chat",
    "text_completion": "llm.completion",
    "embeddings": "llm.embed",
    "generate_content": "llm.generate",
}


class EmbeddingSettings(BaseSettings):
    """Embedding service settings for semantic entity matching (Tier 2b).

    Controls the sentence-transformer model, Neo4j vector index parameters,
    and similarity thresholds for SAME_AS / RELATED_TO edge creation.

    Embeddings are stored exclusively on Neo4j node properties and searched
    via the Neo4j vector index (entity_embedding_idx).
    """

    model_config = {"env_prefix": "CG_EMBEDDING_"}

    model_name: str = "all-MiniLM-L6-v2"
    dimensions: int = 384
    device: str = "cpu"
    same_as_threshold: float = 0.90
    related_to_threshold: float = 0.75
    knn_k: int = 10
    batch_size: int = 64


class LLMSettings(BaseSettings):
    """LLM extraction settings (ADR-0013).

    OPENAI_API_KEY is read by litellm from env automatically.
    """

    model_config = {"env_prefix": "CG_LLM_"}

    model_id: str = "gpt-5.2-2025-12-11"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout_seconds: int = 60
    max_retries: int = 2


class AuthSettings(BaseSettings):
    """API authentication settings.

    When api_key is set, all endpoints (except /health) require
    ``Authorization: Bearer <api_key>``.  Admin and GDPR endpoints
    additionally require the admin_key.

    Set both to None (default) to disable auth (development mode).
    """

    model_config = {"env_prefix": "CG_AUTH_"}

    api_key: str | None = None
    admin_key: str | None = None


class ArchiveSettings(BaseSettings):
    """Archive storage settings (ADR-0014).

    Controls where expired events are archived before deletion from Redis.
    Supports local filesystem (dev/testing) and GCS (production).
    Set gcs_endpoint for emulator (fake-gcs-server) in local dev.
    """

    model_config = {"env_prefix": "CG_ARCHIVE_"}

    backend: str = "fs"  # "fs" or "gcs"
    enabled: bool = True
    fs_base_path: str = "/tmp/engram-archives"
    gcs_bucket: str = ""
    gcs_prefix: str = "engram/archives"
    gcs_endpoint: str = ""  # e.g. "http://fake-gcs:4443" for emulator
    batch_size: int = 1000


class ConsumerSettings(BaseSettings):
    """Consumer resilience settings (H4, H5).

    Controls orphaned message claiming (XAUTOCLAIM) and dead-letter queue
    behavior for all Redis Stream consumer workers.
    """

    model_config = {"env_prefix": "CG_CONSUMER_"}

    # H4: Min idle time (ms) before claiming orphaned messages from other consumers
    claim_idle_ms: int = 300_000  # 5 minutes

    # H4: Max messages to claim per XAUTOCLAIM call
    claim_batch_size: int = 100

    # H5: Max delivery attempts before dead-lettering a message
    max_retries: int = 5

    # H5: DLQ stream suffix — appended to the source stream key
    dlq_stream_suffix: str = ":dlq"


class Settings(BaseSettings):
    """Root application settings."""

    model_config = {"env_prefix": "CG_"}

    app_name: str = "context-graph"
    debug: bool = False
    log_level: str = "INFO"

    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    redis: RedisSettings = Field(default_factory=RedisSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    decay: DecaySettings = Field(default_factory=DecaySettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    query: QuerySettings = Field(default_factory=QuerySettings)
    preference: PreferenceSettings = Field(default_factory=PreferenceSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    archive: ArchiveSettings = Field(default_factory=ArchiveSettings)
    consumer: ConsumerSettings = Field(default_factory=ConsumerSettings)
