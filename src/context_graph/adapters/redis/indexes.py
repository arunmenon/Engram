"""RediSearch index definitions for event documents.

Creates secondary indexes on JSON documents:
- ``evt:*`` keys for event search (ADR-0010)

Entity embeddings are stored on Neo4j node properties and searched
via the Neo4j vector index (entity_embedding_idx). See ADR-0009 amendment.

Source: ADR-0010
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from redis.commands.search.field import NumericField, TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger()


def event_index_definition(prefix: str = "evt:") -> IndexDefinition:
    """Return the IndexDefinition for the events JSON index."""
    return IndexDefinition(prefix=[prefix], index_type=IndexType.JSON)  # type: ignore[no-untyped-call]


def event_index_fields() -> list[TagField | NumericField | TextField]:
    """Return the field schema for the events JSON index."""
    return [
        TagField("$.session_id", as_name="session_id"),
        TagField("$.agent_id", as_name="agent_id"),
        TagField("$.trace_id", as_name="trace_id"),
        TagField("$.event_type", as_name="event_type"),
        TagField("$.tool_name", as_name="tool_name"),
        NumericField("$.occurred_at_epoch_ms", as_name="occurred_at_epoch_ms", sortable=True),
        NumericField("$.importance_hint", as_name="importance_hint", sortable=True),
        # Full-text fields for BM25 retrieval (L4 hybrid search)
        TextField("$.summary", as_name="summary", weight=2.0),
        TextField("$.keywords", as_name="keywords", weight=1.5),
        # Payload text built at ingest (domain/keyword_search.py)
        TextField("$.search_text", as_name="search_text", weight=1.0),
    ]


async def ensure_event_index(client: Redis, index_name: str, prefix: str = "evt:") -> None:
    """Create the events RediSearch index if it does not already exist.

    This is idempotent — if the index already exists, the call is a no-op.
    """
    try:
        info = await client.ft(index_name).info()  # type: ignore[no-untyped-call]
        log.info("redisearch_index_exists", index_name=index_name)
    except Exception:  # noqa: BLE001
        # Index doesn't exist yet — create it
        fields: list[Any] = event_index_fields()
        await client.ft(index_name).create_index(
            fields=fields,
            definition=event_index_definition(prefix),
        )
        log.info("redisearch_index_created", index_name=index_name)
        return
    await _add_missing_text_fields(client, index_name, info)


def _attribute_names(info: Any) -> set[str]:
    """Attribute names from FT.INFO (dict or flat-list replies, bytes or str)."""

    def text(value: Any) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)

    attributes = info.get("attributes", []) if isinstance(info, dict) else []
    names: set[str] = set()
    for attribute in attributes:
        items = list(attribute)
        for index in range(len(items) - 1):
            if text(items[index]) == "attribute":
                names.add(text(items[index + 1]))
    return names


async def _add_missing_text_fields(client: Redis, index_name: str, info: Any) -> None:
    """Add text fields introduced after the index was created (FT.ALTER).

    RediSearch re-scans existing documents for the new field.
    """
    existing = _attribute_names(info)
    if not existing:
        # Unrecognised FT.INFO reply: altering blindly could duplicate fields
        log.warning("redisearch_index_fields_unknown", index_name=index_name)
        return
    for field in event_index_fields():
        if isinstance(field, TextField) and field.as_name not in existing:
            field_args = field.redis_args()  # type: ignore[no-untyped-call]
            await client.execute_command(  # type: ignore[no-untyped-call]
                "FT.ALTER", index_name, "SCHEMA", "ADD", *field_args
            )
            log.info("redisearch_field_added", index_name=index_name, field=field.as_name)
