"""Consumer 4: Consolidation worker (ADR-0008, ADR-0013, ADR-0014).

Scheduled consumer that runs re-consolidation and forgetting:
1. Check session event counts against reflection threshold
2. For qualifying sessions: group into episodes, create summaries
3. Write summary nodes + SUMMARIZES edges to Neo4j
4. Run retention tier enforcement (prune warm edges, cold nodes, archive)
5. Trim Redis hot-tier stream, archive + delete expired docs, clean dedup/sessions

Self-triggers via asyncio timer every `reconsolidation_interval_hours`
(default 6h) in addition to accepting manual consolidation_trigger messages.

Source: ADR-0008 Stage 3, ADR-0013 Consumer 4, ADR-0014
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.adapters.redis.trimmer import (
    archive_and_delete_expired_events,
    cleanup_dedup_set,
    cleanup_session_streams,
    delete_expired_events,
    trim_stream,
)
from context_graph.domain.consolidation import (
    create_summary_from_events,
    group_events_into_episodes,
    should_reconsolidate,
)
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from context_graph.ports.maintenance import GraphMaintenance
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ConsolidationConsumer(BaseConsumer):
    """Consumer 4: Periodic consolidation and forgetting.

    Self-triggers via an in-process asyncio timer every
    ``reconsolidation_interval_hours`` (default 6h). Also accepts
    ``consolidation_trigger`` stream messages for manual triggers.

    Concurrency guard: an ``asyncio.Lock`` prevents overlapping cycles.
    """

    def __init__(
        self,
        redis_client: Redis,
        graph_maintenance: GraphMaintenance,
        settings: Settings,
        archive_store: Any = None,
    ) -> None:
        consumer_settings = settings.consumer
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_consolidation,
            consumer_name="consolidation-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
            max_retries=consumer_settings.max_retries,
            claim_idle_ms=consumer_settings.claim_idle_ms,
            claim_batch_size=consumer_settings.claim_batch_size,
            dlq_stream_suffix=consumer_settings.dlq_stream_suffix,
        )
        self._graph_maintenance = graph_maintenance
        self._settings = settings
        self._event_key_prefix = settings.redis.event_key_prefix
        self._archive_store = archive_store
        self._consolidation_lock = asyncio.Lock()

    # -- lifecycle ----------------------------------------------------------

    async def run(self) -> None:
        """Start the timer loop alongside the base XREADGROUP consumer loop."""
        timer_task = asyncio.create_task(self._timer_loop())
        try:
            await super().run()
        finally:
            timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer_task

    async def _timer_loop(self) -> None:
        """Periodically trigger consolidation cycles (ADR-0014)."""
        interval_hours = self._settings.decay.reconsolidation_interval_hours
        interval_seconds = interval_hours * 3600

        log.info(
            "consolidation_timer_started",
            interval_hours=interval_hours,
        )

        while not self._stopped:
            await asyncio.sleep(interval_seconds)
            if self._stopped:
                break
            log.info("consolidation_timer_fired")
            await self._run_consolidation_cycle_guarded(source="timer")

    # -- message processing -------------------------------------------------

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a consolidation trigger message.

        Checks if this is a consolidation trigger (message_type == 'consolidation_trigger').
        Regular event messages are skipped by this consumer.
        """
        message_type = data.get("message_type", "")
        if message_type != "consolidation_trigger":
            return

        log.info("consolidation_trigger_received", entry_id=entry_id)
        await self._run_consolidation_cycle_guarded(source="stream")

    # -- consolidation cycle ------------------------------------------------

    async def _run_consolidation_cycle_guarded(self, source: str = "unknown") -> None:
        """Run a consolidation cycle with concurrency guard.

        If a cycle is already in progress, this invocation is skipped.
        """
        if self._consolidation_lock.locked():
            log.warning("consolidation_cycle_skipped_already_running", source=source)
            return

        async with self._consolidation_lock:
            log.info("consolidation_cycle_started", source=source)
            try:
                await self._run_consolidation_cycle()
            except Exception:
                log.exception("consolidation_cycle_failed", source=source)
            else:
                log.info("consolidation_cycle_completed", source=source)

    async def _run_consolidation_cycle(self) -> None:
        """Execute a full consolidation cycle."""
        gm = self._graph_maintenance

        # Step 1: Get session event counts
        session_counts = await gm.get_session_event_counts()

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
            records = await gm.run_session_query(
                "MATCH (e:Event {session_id: $sid}) RETURN DISTINCT e.agent_id AS agent_id LIMIT 1",
                {"sid": session_id},
            )
            if records:
                agent_id = records[0]["agent_id"]
                agent_sessions.setdefault(agent_id, []).append(session_id)

        for agent_id, sids in agent_sessions.items():
            all_agent_events: list[dict[str, Any]] = []
            for sid in sids:
                records = await gm.run_session_query(
                    "MATCH (e:Event {session_id: $session_id}) "
                    "RETURN e ORDER BY e.occurred_at LIMIT $limit",
                    {"session_id": sid, "limit": 1000},
                )
                all_agent_events.extend(dict(r.get("e", r)) for r in records)

            if all_agent_events:
                agent_summary = create_summary_from_events(
                    events=all_agent_events,
                    scope="agent",
                    scope_id=agent_id,
                )
                agent_event_ids = [
                    e.get("event_id", "") for e in all_agent_events if e.get("event_id")
                ]
                await gm.write_summary_with_edges(
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

        # Step 4: Trim Redis hot tier + lifecycle cleanup
        await self._trim_redis()

    async def _consolidate_session(self, session_id: str, event_count: int) -> None:
        """Run consolidation for a single session."""
        gm = self._graph_maintenance

        log.info(
            "consolidating_session",
            session_id=session_id,
            event_count=event_count,
        )

        # Fetch session events from Neo4j via protocol
        records = await gm.run_session_query(
            "MATCH (e:Event {session_id: $session_id}) "
            "RETURN e ORDER BY e.occurred_at LIMIT $limit",
            {"session_id": session_id, "limit": event_count},
        )

        events = [dict(r.get("e", r)) for r in records]
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
            await gm.write_summary_with_edges(
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
        await gm.write_summary_with_edges(
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
        updated = await self._graph_maintenance.update_importance_from_centrality()
        log.info("importance_recomputed_from_centrality", updated_count=updated)
        return updated

    async def _run_forgetting(self) -> None:
        """Apply retention tier enforcement across the graph."""
        gm = self._graph_maintenance
        retention = self._settings.retention

        # Step 0: Ensure summaries exist for sessions with pruneable events
        session_counts = await gm.get_session_event_counts()
        for session_id, event_count in session_counts.items():
            if event_count >= self._settings.decay.reflection_threshold:
                await self._consolidate_session(session_id, event_count)

        # Step 1: Prune low-similarity SIMILAR_TO edges in warm tier
        deleted_edges = await gm.delete_edges_by_type_and_age(
            min_score=retention.warm_min_similarity_score,
            max_age_hours=retention.hot_hours,
        )

        # Step 2: Delete cold-tier events that don't meet retention criteria
        deleted_cold = await gm.delete_cold_events(
            max_age_hours=retention.warm_hours,
            min_importance=retention.cold_min_importance,
            min_access_count=retention.cold_min_access_count,
        )

        # Step 3: Delete archive-tier events (beyond cold retention)
        archive_events = await gm.get_archive_event_ids(
            max_age_hours=retention.cold_hours,
        )
        if archive_events:
            deleted_archive = await gm.delete_archive_events(event_ids=archive_events)
        else:
            deleted_archive = 0

        # Step 4: Clean up orphaned nodes (ADR-0014 Amendment, Gap 8)
        orphan_counts, _deleted_entity_ids = await gm.delete_orphan_nodes(
            batch_size=self._settings.retention.orphan_cleanup_batch_size,
        )

        log.info(
            "forgetting_completed",
            deleted_edges=deleted_edges,
            deleted_cold_events=deleted_cold,
            deleted_archive_events=deleted_archive,
            orphan_counts=orphan_counts,
        )

    async def _trim_redis(self) -> None:
        """Trim Redis hot-tier stream, archive + delete expired docs, clean up.

        ADR-0014 hardening: archive-before-delete, dedup cleanup, session stream cleanup.
        """
        redis_settings = self._settings.redis

        # 1. Trim global stream (hot window) — PEL-safe
        trimmed = await trim_stream(
            redis_client=self._redis,
            stream_key=redis_settings.global_stream,
            max_age_days=redis_settings.hot_window_days,
            consumer_groups=[
                redis_settings.group_projection,
                redis_settings.group_extraction,
                redis_settings.group_enrichment,
                redis_settings.group_consolidation,
            ],
        )

        # 2. Archive and delete expired JSON docs, or plain delete if no archive store
        if self._archive_store is not None:
            archived, deleted = await archive_and_delete_expired_events(
                redis_client=self._redis,
                key_prefix=redis_settings.event_key_prefix,
                max_age_days=redis_settings.retention_ceiling_days,
                archive_store=self._archive_store,
            )
        else:
            archived = 0
            deleted = await delete_expired_events(
                redis_client=self._redis,
                key_prefix=redis_settings.event_key_prefix,
                max_age_days=redis_settings.retention_ceiling_days,
            )

        # 3. Clean up dedup sorted set (ADR-0014)
        dedup_removed = await cleanup_dedup_set(
            redis_client=self._redis,
            dedup_key=redis_settings.dedup_set,
            retention_ceiling_days=redis_settings.retention_ceiling_days,
        )

        # 4. Clean up stale session streams (ADR-0014)
        session_streams_deleted = await cleanup_session_streams(
            redis_client=self._redis,
            prefix="events:session:",
            max_age_hours=redis_settings.session_stream_retention_hours,
        )

        log.info(
            "redis_trimmed",
            stream_entries_trimmed=trimmed,
            events_archived=archived,
            expired_docs_deleted=deleted,
            dedup_entries_removed=dedup_removed,
            session_streams_deleted=session_streams_deleted,
        )
