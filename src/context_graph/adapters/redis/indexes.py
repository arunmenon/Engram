"""RediSearch index definitions for event and entity embedding documents.

Creates secondary indexes on JSON documents:
- ``evt:*`` keys for event search (ADR-0010)
- ``entity_emb:*`` keys for entity embedding vector search (Tier 2b)

Source: ADR-0010, ADR-0011
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from redis.commands.search.field import NumericField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger()


def event_index_definition(prefix: str = "evt:") -> IndexDefinition:
    """Return the IndexDefinition for the events JSON index."""
    return IndexDefinition(prefix=[prefix], index_type=IndexType.JSON)  # type: ignore[no-untyped-call]


def event_index_fields() -> list[TagField | NumericField]:
    """Return the field schema for the events JSON index."""
    return [
        TagField("$.session_id", as_name="session_id"),
        TagField("$.agent_id", as_name="agent_id"),
        TagField("$.trace_id", as_name="trace_id"),
        TagField("$.event_type", as_name="event_type"),
        TagField("$.tool_name", as_name="tool_name"),
        NumericField("$.occurred_at_epoch_ms", as_name="occurred_at_epoch_ms", sortable=True),
        NumericField("$.importance_hint", as_name="importance_hint", sortable=True),
    ]


async def ensure_event_index(client: Redis, index_name: str, prefix: str = "evt:") -> None:
    """Create the events RediSearch index if it does not already exist.

    This is idempotent — if the index already exists, the call is a no-op.
    """
    try:
        await client.ft(index_name).info()  # type: ignore[no-untyped-call]
        log.info("redisearch_index_exists", index_name=index_name)
    except Exception:  # noqa: BLE001
        # Index doesn't exist yet — create it
        fields: list[Any] = event_index_fields()
        await client.ft(index_name).create_index(
            fields=fields,
            definition=event_index_definition(prefix),
        )
        log.info("redisearch_index_created", index_name=index_name)


# ---------------------------------------------------------------------------
# Entity embedding vector index (Tier 2b — HNSW)
# ---------------------------------------------------------------------------


def entity_embedding_index_definition(prefix: str = "entity_emb:") -> IndexDefinition:
    """Return the IndexDefinition for the entity embedding JSON index."""
    return IndexDefinition(prefix=[prefix], index_type=IndexType.JSON)  # type: ignore[no-untyped-call]


def entity_embedding_index_fields(
    dimensions: int = 384,
    hnsw_m: int = 16,
    hnsw_ef_construction: int = 200,
    hnsw_ef_runtime: int = 100,
) -> list[TagField | VectorField]:
    """Return the field schema for the entity embedding vector index.

    Parameters
    ----------
    dimensions:
        Embedding vector dimensionality (384 for all-MiniLM-L6-v2).
    hnsw_m:
        HNSW max edges per node.
    hnsw_ef_construction:
        HNSW construction-time beam width.
    hnsw_ef_runtime:
        HNSW query-time beam width.
    """
    return [
        TagField("$.name", as_name="name"),
        TagField("$.entity_type", as_name="entity_type"),
        TagField("$.entity_id", as_name="entity_id"),
        VectorField(
            "$.embedding",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": dimensions,
                "DISTANCE_METRIC": "COSINE",
                "M": hnsw_m,
                "EF_CONSTRUCTION": hnsw_ef_construction,
                "EF_RUNTIME": hnsw_ef_runtime,
            },
            as_name="embedding",
        ),
    ]


async def ensure_entity_embedding_index(
    client: Redis,
    index_name: str = "idx:entity_embeddings",
    prefix: str = "entity_emb:",
    dimensions: int = 384,
    hnsw_m: int = 16,
    hnsw_ef_construction: int = 200,
    hnsw_ef_runtime: int = 100,
) -> None:
    """Create the entity embedding HNSW index if it does not already exist.

    Idempotent — if the index already exists, the call is a no-op.
    """
    try:
        await client.ft(index_name).info()  # type: ignore[no-untyped-call]
        log.info("entity_embedding_index_exists", index_name=index_name)
    except Exception:  # noqa: BLE001
        fields: list[Any] = entity_embedding_index_fields(
            dimensions=dimensions,
            hnsw_m=hnsw_m,
            hnsw_ef_construction=hnsw_ef_construction,
            hnsw_ef_runtime=hnsw_ef_runtime,
        )
        await client.ft(index_name).create_index(
            fields=fields,
            definition=entity_embedding_index_definition(prefix),
        )
        log.info("entity_embedding_index_created", index_name=index_name)
