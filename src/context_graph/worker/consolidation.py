"""Consumer 4: Consolidation worker (ADR-0008, ADR-0013).

Scheduled consumer that runs re-consolidation and forgetting:
1. Check session event counts against reflection threshold
2. For qualifying sessions: group into episodes, create summaries
3. Write summary nodes + SUMMARIZES edges to Neo4j
4. Run retention tier enforcement (prune warm edges, cold nodes, archive)
5. Trim Redis hot-tier stream and expired JSON docs

Source: ADR-0008 Stage 3, ADR-0013 Consumer 4
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from context_graph.adapters.neo4j import maintenance
from context_graph.adapters.neo4j.queries import GET_SESSION_EVENTS
from context_graph.adapters.redis.trimmer import delete_expired_events, trim_stream
from context_graph.domain.consolidation import (
    create_summary_from_events,
    group_events_into_episodes,
    should_reconsolidate,
)
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from neo4j import AsyncDriver
    from redis.asyncio import Redis

    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ConsolidationConsumer(BaseConsumer):
    """Consumer 4: Periodic consolidation and forgetting.

    Unlike other consumers that process individual stream messages, this
    consumer uses stream messages as triggers to run batch operations.
    Each received message triggers a full consolidation cycle.

    In production, a scheduler (cron or similar) posts a trigger message
    to the stream at the configured interval (default 6h).
    """

    def __init__(
        self,
        redis_client: Redis,
        neo4j_driver: AsyncDriver,
        settings: Settings,
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_consolidation,
            consumer_name="consolidation-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
        )
        self._neo4j_driver = neo4j_driver
        self._neo4j_database = settings.neo4j.database
        self._settings = settings
        self._event_key_prefix = settings.redis.event_key_prefix

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a consolidation trigger message.

        Checks if this is a consolidation trigger (message_type == 'consolidation_trigger').
        Regular event messages are skipped by this consumer.
        """
        message_type = data.get("message_type", "")
        if message_type != "consolidation_trigger":
            return

        log.info("consolidation_cycle_started", entry_id=entry_id)
        await self._run_consolidation_cycle()
        log.info("consolidation_cycle_completed", entry_id=entry_id)

    async def _run_consolidation_cycle(self) -> None:
        """Execute a full consolidation cycle."""
        # Step 1: Get session event counts
        session_counts = await maintenance.get_session_event_counts(
            self._neo4j_driver,
            self._neo4j_database,
        )

        threshold = self._settings.decay.reflection_threshold
        # Use count*5 as a rough importance sum proxy (average importance of 5 on 1-10 scale)
        sessions_to_consolidate = {
            sid: count
            for sid, count in session_counts.items()
            if should_reconsolidate(float(count * 5), float(threshold))
        }

        if sessions_to_consolidate:
            log.info(
                "sessions_qualifying_for_consolidation",
                count=len(sessions_to_consolidate),
                threshold=threshold,
            )

        # Step 2: Consolidate qualifying sessions
        for session_id, event_count in sessions_to_consolidate.items():
            await self._consolidate_session(session_id, event_count)

        # Step 2b: Create agent-level summaries
        agent_sessions: dict[str, list[str]] = {}
        for session_id in sessions_to_consolidate:
            async with self._neo4j_driver.session(database=self._neo4j_database) as session:
                result = await session.run(
                    "MATCH (e:Event {session_id: $sid}) "
                    "RETURN DISTINCT e.agent_id AS agent_id LIMIT 1",
                    {"sid": session_id},
                )
                record = await result.single()
            if record:
                agent_id = record["agent_id"]
                agent_sessions.setdefault(agent_id, []).append(session_id)

        for agent_id, sids in agent_sessions.items():
            all_agent_events: list[dict[str, Any]] = []
            for sid in sids:
                async with self._neo4j_driver.session(database=self._neo4j_database) as session:
                    result = await session.run(
                        GET_SESSION_EVENTS,
                        {"session_id": sid, "limit": 1000},
                    )
                    records = [record async for record in result]
                all_agent_events.extend(dict(r["e"]) for r in records)

            if all_agent_events:
                agent_summary = create_summary_from_events(
                    events=all_agent_events,
                    scope="agent",
                    scope_id=agent_id,
                )
                agent_event_ids = [
                    e.get("event_id", "") for e in all_agent_events if e.get("event_id")
                ]
                await maintenance.write_summary_with_edges(
                    driver=self._neo4j_driver,
                    database=self._neo4j_database,
                    summary_id=agent_summary.summary_id,
                    scope=agent_summary.scope,
                    scope_id=agent_summary.scope_id,
                    content=agent_summary.content,
                    created_at=agent_summary.created_at.isoformat(),
                    event_count=agent_summary.event_count,
                    time_range=[dt.isoformat() for dt in agent_summary.time_range],
                    event_ids=agent_event_ids,
                )
                log.info("agent_summary_created", agent_id=agent_id, sessions=len(sids))

        # Step 2c: Recompute importance from centrality
        await self._recompute_importance_from_centrality()

        # Step 3: Run forgetting (retention tier enforcement)
        await self._run_forgetting()

        # Step 4: Trim Redis hot tier
        await self._trim_redis()

    async def _consolidate_session(self, session_id: str, event_count: int) -> None:
        """Run consolidation for a single session."""
        log.info(
            "consolidating_session",
            session_id=session_id,
            event_count=event_count,
        )

        # Fetch session events from Neo4j
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:
            result = await session.run(
                GET_SESSION_EVENTS,
                {"session_id": session_id, "limit": event_count},
            )
            records = [record async for record in result]

        events = [dict(record["e"]) for record in records]
        if not events:
            return

        # Group into episodes
        episodes = group_events_into_episodes(events, gap_minutes=30)

        log.info(
            "episodes_grouped",
            session_id=session_id,
            episode_count=len(episodes),
        )

        # Create summaries for each episode
        for idx, episode in enumerate(episodes):
            summary = create_summary_from_events(
                events=episode,
                scope="episode",
                scope_id=f"{session_id}-ep{idx}",
            )

            event_ids = [e.get("event_id", "") for e in episode if e.get("event_id")]

            # Write summary + SUMMARIZES edges to Neo4j
            await maintenance.write_summary_with_edges(
                driver=self._neo4j_driver,
                database=self._neo4j_database,
                summary_id=summary.summary_id,
                scope=summary.scope,
                scope_id=summary.scope_id,
                content=summary.content,
                created_at=summary.created_at.isoformat(),
                event_count=summary.event_count,
                time_range=[dt.isoformat() for dt in summary.time_range],
                event_ids=event_ids,
            )

        # Create a session-level summary covering all events
        session_summary = create_summary_from_events(
            events=events,
            scope="session",
            scope_id=session_id,
        )
        all_event_ids = [e.get("event_id", "") for e in events if e.get("event_id")]
        await maintenance.write_summary_with_edges(
            driver=self._neo4j_driver,
            database=self._neo4j_database,
            summary_id=session_summary.summary_id,
            scope=session_summary.scope,
            scope_id=session_summary.scope_id,
            content=session_summary.content,
            created_at=session_summary.created_at.isoformat(),
            event_count=session_summary.event_count,
            time_range=[dt.isoformat() for dt in session_summary.time_range],
            event_ids=all_event_ids,
        )

        log.info(
            "session_consolidated",
            session_id=session_id,
            episode_summaries=len(episodes),
        )

    async def _recompute_importance_from_centrality(self) -> int:
        """Recompute importance scores based on in-degree centrality."""
        updated = await maintenance.update_importance_from_centrality(
            driver=self._neo4j_driver,
            database=self._neo4j_database,
        )
        log.info("importance_recomputed_from_centrality", updated_count=updated)
        return updated

    async def _run_forgetting(self) -> None:
        """Apply retention tier enforcement across the graph."""
        retention = self._settings.retention

        # Step 0: Ensure summaries exist for sessions with pruneable events
        session_counts = await maintenance.get_session_event_counts(
            self._neo4j_driver, self._neo4j_database
        )
        for session_id, event_count in session_counts.items():
            if event_count >= self._settings.decay.reflection_threshold:
                await self._consolidate_session(session_id, event_count)

        # Step 1: Prune low-similarity SIMILAR_TO edges in warm tier
        deleted_edges = await maintenance.delete_edges_by_type_and_age(
            driver=self._neo4j_driver,
            database=self._neo4j_database,
            min_score=retention.warm_min_similarity_score,
            max_age_hours=retention.hot_hours,
        )

        # Step 2: Delete cold-tier events that don't meet retention criteria
        deleted_cold = await maintenance.delete_cold_events(
            driver=self._neo4j_driver,
            database=self._neo4j_database,
            max_age_hours=retention.warm_hours,
            min_importance=retention.cold_min_importance,
            min_access_count=retention.cold_min_access_count,
        )

        # Step 3: Delete archive-tier events (beyond cold retention)
        archive_events = await maintenance.get_archive_event_ids(
            driver=self._neo4j_driver,
            database=self._neo4j_database,
            max_age_hours=retention.cold_hours,
        )
        if archive_events:
            deleted_archive = await maintenance.delete_archive_events(
                driver=self._neo4j_driver,
                database=self._neo4j_database,
                event_ids=archive_events,
            )
        else:
            deleted_archive = 0

        log.info(
            "forgetting_completed",
            deleted_edges=deleted_edges,
            deleted_cold_events=deleted_cold,
            deleted_archive_events=deleted_archive,
        )

    async def _trim_redis(self) -> None:
        """Trim the Redis hot-tier stream and delete expired JSON docs."""
        redis_settings = self._settings.redis

        trimmed = await trim_stream(
            redis_client=self._redis,
            stream_key=redis_settings.global_stream,
            max_age_days=redis_settings.hot_window_days,
        )

        deleted = await delete_expired_events(
            redis_client=self._redis,
            key_prefix=redis_settings.event_key_prefix,
            max_age_days=redis_settings.retention_ceiling_days,
        )

        log.info(
            "redis_trimmed",
            stream_entries_trimmed=trimmed,
            expired_docs_deleted=deleted,
        )
