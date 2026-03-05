"""Engram SDK — Python client for the Engram context graph.

Simple API:
    import engram
    await engram.record("User asked about payments", agent_id="my-agent")
    context = await engram.recall(query="payment issues")
    lineage = await engram.trace("evt-abc-123")

Full API:
    from engram import EngramClient
    async with EngramClient(base_url="http://localhost:8000") as client:
        result = await client.ingest(event)
"""

from engram.client import EngramClient
from engram.config import EngramConfig, configure
from engram.exceptions import (
    AuthenticationError,
    ConfigurationError,
    EngramError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TransportError,
    ValidationError,
)
from engram.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    BatchResult,
    BehavioralPatternNode,
    DetailedHealthResponse,
    EntityResponse,
    Event,
    GDPRDeleteResponse,
    GDPRExportResponse,
    HealthStatus,
    IngestResult,
    InterestNode,
    Memory,
    Pagination,
    PreferenceNode,
    Provenance,
    PruneResponse,
    QueryMeta,
    ReconsolidateResponse,
    SkillNode,
    SubgraphQuery,
    UserProfile,
)
from engram.sessions import SessionManager
from engram.simple import aclose, add, recall, record, search, trace
from engram.sync_client import EngramSyncClient

__version__ = "0.1.0"

__all__ = [
    # Simple API
    "configure",
    "record",
    "recall",
    "trace",
    "add",
    "search",
    "aclose",
    # Client
    "EngramClient",
    "EngramSyncClient",
    "EngramConfig",
    "SessionManager",
    # Models
    "Event",
    "IngestResult",
    "BatchResult",
    "AtlasResponse",
    "AtlasNode",
    "AtlasEdge",
    "Provenance",
    "QueryMeta",
    "Pagination",
    "SubgraphQuery",
    "HealthStatus",
    "UserProfile",
    "Memory",
    "PreferenceNode",
    "SkillNode",
    "BehavioralPatternNode",
    "InterestNode",
    "EntityResponse",
    "GDPRExportResponse",
    "GDPRDeleteResponse",
    "ReconsolidateResponse",
    "PruneResponse",
    "DetailedHealthResponse",
    # Exceptions
    "EngramError",
    "TransportError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "NotFoundError",
    "ServerError",
    "ConfigurationError",
    # Version
    "__version__",
]
