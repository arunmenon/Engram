"""Consumer 1: Graph Projection worker.

Reads events from the Redis global stream and projects them into the
Neo4j graph using the pure domain projection logic. Each event becomes
an EventNode, and FOLLOWS / CAUSED_BY edges are created as appropriate.

Source: ADR-0005, ADR-0013 (Consumer 1)
"""

from __future__ import annotations

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

    def __init__(
        self,
        redis_client: Redis,
        graph_store: GraphStore,
        settings: Settings,
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_projection,
            consumer_name="projection-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
        )
        self._graph_store = graph_store
        self._event_key_prefix = settings.redis.event_key_prefix
        self._session_last_event: dict[str, Event] = {}

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a single stream entry: fetch event, project, write to Neo4j."""
        event_id = data.get("event_id")
        if event_id is None:
            log.warning("stream_entry_missing_event_id", entry_id=entry_id)
            return

        # Fetch the full event document from Redis JSON
        json_key = f"{self._event_key_prefix}{event_id}"
        raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        if raw_json is None:
            log.warning(
                "event_json_not_found",
                event_id=event_id,
                entry_id=entry_id,
                json_key=json_key,
            )
            return

        # Deserialize the event
        raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
        doc.pop("occurred_at_epoch_ms", None)
        event = Event.model_validate(doc, strict=False)

        # Ensure global_position is set from the stream entry ID
        if event.global_position is None:
            event = event.model_copy(update={"global_position": entry_id})

        # Look up previous event in this session for FOLLOWS edge
        prev_event = self._session_last_event.get(event.session_id)

        # Run pure domain projection
        result = project_event(event, prev_event)

        # Write to Neo4j
        await self._graph_store.merge_event_node(result.node)
        if result.edges:
            await self._graph_store.create_edges_batch(result.edges)

        # Track this event as the latest for its session
        self._session_last_event[event.session_id] = event

        log.debug(
            "event_projected",
            event_id=event_id,
            entry_id=entry_id,
            session_id=event.session_id,
            edge_count=len(result.edges),
        )
