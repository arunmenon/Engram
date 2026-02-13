"""Consumer 2: Session Knowledge Extraction worker (ADR-0013).

Listens for ``system.session_end`` events on the Redis global stream.
When a session ends, collects all session events, runs LLM-based
knowledge extraction, and writes results (entities, preferences,
skills, interests) to Neo4j.

Source: ADR-0013 Consumer 2
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.domain.models import Event
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from neo4j import AsyncDriver
    from redis.asyncio import Redis

    from context_graph.adapters.llm.client import LLMExtractionClient
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ExtractionConsumer(BaseConsumer):
    """Consumer 2: Session Knowledge Extraction.

    Triggers on ``system.session_end`` events. Collects all events from
    the ended session, runs LLM extraction, and writes extracted
    knowledge to the Neo4j graph.
    """

    def __init__(
        self,
        redis_client: Redis,
        neo4j_driver: AsyncDriver,
        neo4j_database: str,
        llm_client: LLMExtractionClient,
        settings: Settings,
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_extraction,
            consumer_name="extraction-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
        )
        self._neo4j_driver = neo4j_driver
        self._neo4j_database = neo4j_database
        self._llm_client = llm_client
        self._settings = settings
        self._event_key_prefix = settings.redis.event_key_prefix

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a stream entry: check for session_end and trigger extraction."""
        event_type = data.get("event_type", "")
        if event_type != "system.session_end":
            return

        session_id = data.get("session_id")
        agent_id = data.get("agent_id", "unknown")
        if not session_id:
            log.warning(
                "session_end_missing_session_id",
                entry_id=entry_id,
            )
            return

        log.info(
            "extraction_triggered",
            entry_id=entry_id,
            session_id=session_id,
            agent_id=agent_id,
        )

        events = await self._collect_session_events(session_id)
        if not events:
            log.info(
                "extraction_no_events",
                session_id=session_id,
            )
            return

        result = await self._llm_client.extract_from_session(
            events=events,
            session_id=session_id,
            agent_id=agent_id,
        )

        await self._write_extraction_results(session_id, agent_id, result)

        log.info(
            "extraction_completed",
            session_id=session_id,
            entities=len(result.get("entities", [])),
            preferences=len(result.get("preferences", [])),
            skills=len(result.get("skills", [])),
            interests=len(result.get("interests", [])),
        )

    async def _collect_session_events(self, session_id: str) -> list[Event]:
        """Collect all events for a session from Redis JSON store.

        Scans Redis keys matching the event key prefix pattern, filtering
        by session_id. Falls back to an empty list if no events found.
        """
        events: list[Event] = []

        # Use XRANGE on the global stream to find entries for this session
        all_entries = await self._redis.xrange(
            self._settings.redis.global_stream,
            min="-",
            max="+",
        )

        for _entry_id, entry_data in all_entries:
            decoded = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in entry_data.items()
            }
            if decoded.get("session_id") != session_id:
                continue

            event_id = decoded.get("event_id")
            if not event_id:
                continue

            json_key = f"{self._event_key_prefix}{event_id}"
            raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
            if raw_json is None:
                continue

            raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
            parsed = orjson.loads(raw_str)
            doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
            doc.pop("occurred_at_epoch_ms", None)

            try:
                event = Event.model_validate(doc, strict=False)
                events.append(event)
            except Exception:
                log.warning(
                    "event_parse_failed",
                    event_id=event_id,
                    session_id=session_id,
                )

        events.sort(key=lambda e: e.occurred_at)
        log.debug(
            "session_events_collected",
            session_id=session_id,
            event_count=len(events),
        )
        return events

    async def _write_extraction_results(
        self,
        session_id: str,
        agent_id: str,
        result: dict[str, Any],
    ) -> None:
        """Write extraction results to Neo4j via user_queries module."""
        from context_graph.adapters.neo4j import user_queries as uq

        user_entity_id = f"user:{agent_id}"

        for pref_data in result.get("preferences", []):
            source_quote = pref_data.get("source_quote", "")
            await uq.write_preference_with_edges(
                driver=self._neo4j_driver,
                database=self._neo4j_database,
                user_entity_id=user_entity_id,
                preference_data=pref_data,
                source_event_ids=[],
                derivation_info={
                    "method": "llm_extraction",
                    "session_id": session_id,
                    "source_quote": source_quote,
                },
            )

        for skill_data in result.get("skills", []):
            source_quote = skill_data.get("source_quote", "")
            await uq.write_skill_with_edges(
                driver=self._neo4j_driver,
                database=self._neo4j_database,
                user_entity_id=user_entity_id,
                skill_data=skill_data,
                source_event_ids=[],
                derivation_info={
                    "method": "llm_extraction",
                    "session_id": session_id,
                    "source_quote": source_quote,
                },
            )

        for interest_data in result.get("interests", []):
            await uq.write_interest_edge(
                driver=self._neo4j_driver,
                database=self._neo4j_database,
                user_entity_id=user_entity_id,
                entity_name=interest_data.get("entity_name", ""),
                entity_type=interest_data.get("entity_type", "concept"),
                weight=interest_data.get("weight", 0.5),
                source=interest_data.get("source", "inferred"),
            )

        log.info(
            "extraction_results_written",
            session_id=session_id,
            user_entity_id=user_entity_id,
        )
