"""Consumer 3: Enrichment worker.

Reads events from the Redis global stream and enriches them with keywords
and importance scoring in the Neo4j graph. Future phases will add embedding
computation, SIMILAR_TO edge creation, and entity extraction for REFERENCES edges.

Source: ADR-0008 (Stage 2), ADR-0013 (Consumer 3)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import orjson
import structlog

from context_graph.adapters.neo4j import queries
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from neo4j import AsyncDriver
    from redis.asyncio import Redis

    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

DEFAULT_IMPORTANCE = 5


class EnrichmentConsumer(BaseConsumer):
    """Consumer 3: Enriches events with keywords and importance scoring.

    For each event received from the stream:
    1. Deserialize the event data from the stream entry.
    2. Extract keywords from the event_type (split by '.') and tool_name.
    3. Determine importance_score from importance_hint or use default.
    4. Update the Neo4j node with keywords and importance_score.
    """

    def __init__(
        self,
        redis_client: Redis,
        neo4j_driver: AsyncDriver,
        settings: Settings,
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_enrichment,
            consumer_name="enrichment-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
        )
        self._neo4j_driver = neo4j_driver
        self._neo4j_database = settings.neo4j.database
        self._event_key_prefix = settings.redis.event_key_prefix

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a single stream entry: extract keywords and update Neo4j."""
        event_id = data.get("event_id")
        if event_id is None:
            log.warning("enrichment_missing_event_id", entry_id=entry_id)
            return

        # Fetch the full event document from Redis JSON
        json_key = f"{self._event_key_prefix}{event_id}"
        raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        if raw_json is None:
            log.warning(
                "enrichment_event_json_not_found",
                event_id=event_id,
                entry_id=entry_id,
            )
            return

        raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed

        # Extract keywords from event_type
        event_type = doc.get("event_type", "")
        keywords = extract_keywords(event_type, doc.get("tool_name"))

        # Determine importance score
        importance_hint = doc.get("importance_hint")
        importance_score = importance_hint if importance_hint is not None else DEFAULT_IMPORTANCE

        # Update Neo4j node
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.UPDATE_EVENT_ENRICHMENT,
                    {
                        "event_id": event_id,
                        "keywords": keywords,
                        "importance_score": importance_score,
                    },
                )
            )

        log.debug(
            "event_enriched",
            event_id=event_id,
            keywords=keywords,
            importance_score=importance_score,
        )

        # TODO: Embedding computation (requires sentence-transformers, Phase 3+)
        # TODO: SIMILAR_TO edge creation (requires embeddings)
        # TODO: Entity extraction for REFERENCES edges


def extract_keywords(event_type: str, tool_name: str | None = None) -> list[str]:
    """Extract keywords from an event_type string and optional tool_name.

    Splits event_type by '.' to get component parts, and adds tool_name
    if present and not already included.
    """
    keywords = [part for part in event_type.split(".") if part]
    if tool_name and tool_name not in keywords:
        keywords.append(tool_name)
    return keywords
