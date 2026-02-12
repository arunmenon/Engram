"""RediSearch index definitions for event documents.

Creates a secondary index on JSON documents stored at ``evt:*`` keys,
enabling filtered search and sorted retrieval via the FT.SEARCH command.

Source: ADR-0010
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from redis.commands.search.field import NumericField, TagField
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
