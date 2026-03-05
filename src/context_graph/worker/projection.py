"""Consumer 1: Graph Projection worker.

Reads events from the Redis global stream and projects them into the
Neo4j graph using the pure domain projection logic. Each event becomes
an EventNode, and FOLLOWS / CAUSED_BY edges are created as appropriate.

Source: ADR-0005, ADR-0013 (Consumer 1)
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING

import orjson
import structlog

from context_graph.domain.models import Event
from context_graph.domain.projection import project_event
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from context_graph.ports.graph_store import GraphStore
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ProjectionConsumer(BaseConsumer):
    """Consumer 1: Projects events from Redis Stream into the Neo4j graph.

    For each event received from the stream:
    1. Fetch the full event JSON from Redis (stream only carries event_id).
    2. Run pure domain projection to produce an EventNode and edges.
    3. MERGE the node and edges into Neo4j via the GraphStore.
    4. Track the last event per session for FOLLOWS edge computation.
    """

    _MAX_SESSION_CACHE = 10_000
    _BATCH_SIZE = 50
    _BATCH_TIMEOUT_MS = 100

    @property
    def deferred_ack(self) -> bool:  # noqa: D102
        return True

    def __init__(
        self,
        redis_client: Redis,
        graph_store: GraphStore,
        settings: Settings,
    ) -> None:
        consumer_settings = settings.consumer
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_projection,
            consumer_name="projection-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
            max_retries=consumer_settings.max_retries,
            claim_idle_ms=consumer_settings.claim_idle_ms,
            claim_batch_size=consumer_settings.claim_batch_size,
            dlq_stream_suffix=consumer_settings.dlq_stream_suffix,
        )
        self._graph_store = graph_store
        self._event_key_prefix = settings.redis.event_key_prefix
        self._session_last_event: OrderedDict[str, Event] = OrderedDict()
        self._buffer: list[tuple[str, dict[str, str]]] = []
        self._last_flush_time: float = time.monotonic()

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Buffer a stream entry for micro-batch projection.

        Events are buffered and flushed when either _BATCH_SIZE is reached
        or _BATCH_TIMEOUT_MS has elapsed since the last flush.
        """
        self._buffer.append((entry_id, data))

        elapsed_ms = (time.monotonic() - self._last_flush_time) * 1000.0
        if len(self._buffer) >= self._BATCH_SIZE or elapsed_ms >= self._BATCH_TIMEOUT_MS:
            await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush the buffered events: fetch, project, and batch-write to Neo4j."""
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer.clear()
        self._last_flush_time = time.monotonic()

        all_nodes = []
        all_edges = []

        for entry_id, data in batch:
            event = await self._fetch_event(entry_id, data)
            if event is None:
                continue

            # Look up previous event in this session for FOLLOWS edge
            prev_event = self._session_last_event.get(event.session_id)

            # Run pure domain projection
            result = project_event(event, prev_event)
            all_nodes.append(result.node)
            all_edges.extend(result.edges)

            # Track this event as the latest for its session
            # Move to end if already present (OrderedDict LRU)
            if event.session_id in self._session_last_event:
                self._session_last_event.move_to_end(event.session_id)
            self._session_last_event[event.session_id] = event

            # Evict oldest entry if cache exceeds max size
            while len(self._session_last_event) > self._MAX_SESSION_CACHE:
                self._session_last_event.popitem(last=False)

            # Clean up on session end
            if event.event_type == "system.session_end":
                self._session_last_event.pop(event.session_id, None)

            log.debug(
                "event_projected",
                event_id=str(event.event_id),
                entry_id=entry_id,
                session_id=event.session_id,
                edge_count=len(result.edges),
            )

        # Batch write to Neo4j
        if all_nodes:
            if hasattr(self._graph_store, "merge_event_nodes_batch"):
                await self._graph_store.merge_event_nodes_batch(all_nodes)
            else:
                for node in all_nodes:
                    await self._graph_store.merge_event_node(node)
        if all_edges:
            await self._graph_store.create_edges_batch(all_edges)

        # ACK all entries after successful write (deferred_ack = True)
        entry_ids = [eid for eid, _ in batch]
        if entry_ids:
            await self._redis.xack(self._stream_key, self._group_name, *entry_ids)

    async def on_stop(self) -> None:
        """Flush remaining buffered events before shutdown."""
        if self._buffer:
            log.info("flushing_buffer_on_stop", buffered=len(self._buffer))
            await self._flush_buffer()

    async def _fetch_event(self, entry_id: str, data: dict[str, str]) -> Event | None:
        """Fetch and deserialize a single event from Redis JSON."""
        event_id = data.get("event_id")
        if event_id is None:
            log.warning("stream_entry_missing_event_id", entry_id=entry_id)
            return None

        json_key = f"{self._event_key_prefix}{event_id}"
        raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        if raw_json is None:
            log.warning(
                "event_json_not_found",
                event_id=event_id,
                entry_id=entry_id,
                json_key=json_key,
            )
            return None

        raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
        doc.pop("occurred_at_epoch_ms", None)
        event = Event.model_validate(doc, strict=False)

        if event.global_position is None:
            event = event.model_copy(update={"global_position": entry_id})

        return event
