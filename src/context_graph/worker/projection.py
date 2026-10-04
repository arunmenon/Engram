"""Consumer 1: Graph Projection worker.

Reads events delivered by its subscription and projects them into the
graph using the pure domain projection logic. Each event becomes
an EventNode, and FOLLOWS / CAUSED_BY edges are created as appropriate.

Source: ADR-0005, ADR-0013 (Consumer 1)
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING

import structlog

from context_graph.domain.models import Event
from context_graph.domain.projection import project_event
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_store import GraphStore
    from context_graph.ports.subscription import Subscription
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ProjectionConsumer(BaseConsumer):
    """Consumer 1: Projects delivered events into the graph.

    For each event received from the subscription:
    1. Fetch the full event from the event log (deliveries carry only event_id).
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
        subscription: Subscription,
        event_log: EventLog,
        graph_store: GraphStore,
        settings: Settings,
    ) -> None:
        super().__init__(
            subscription,
            block_timeout_ms=settings.consumer.block_timeout_ms,
            max_retries=settings.consumer.max_retries,
        )
        self._event_log = event_log
        self._graph_store = graph_store
        self._session_last_event: OrderedDict[str, Event] = OrderedDict()
        self._buffer: list[tuple[str, dict[str, str]]] = []
        self._last_flush_time: float = time.monotonic()

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Buffer a stream entry for micro-batch projection.

        Events are buffered and flushed when either _BATCH_SIZE is reached
        or _BATCH_TIMEOUT_MS has elapsed since the last flush. A partial
        batch left when traffic stops is flushed by ``on_idle``.
        """
        self._buffer.append((entry_id, data))

        if len(self._buffer) >= self._BATCH_SIZE or self._batch_timeout_elapsed():
            await self._flush_buffer()

    def _batch_timeout_elapsed(self) -> bool:
        elapsed_ms = (time.monotonic() - self._last_flush_time) * 1000.0
        return elapsed_ms >= self._BATCH_TIMEOUT_MS

    async def on_idle(self) -> None:
        """Flush a partial batch once reads go quiet and the batch timeout has passed."""
        if self._buffer and self._batch_timeout_elapsed():
            log.debug("flushing_buffer_on_idle", buffered=len(self._buffer))
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
            prev_event = await self._previous_event(event)

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
            await self._ack(*entry_ids)

    async def _previous_event(self, event: Event) -> Event | None:
        """The event this one FOLLOWS, or None.

        The in-memory cache answers while the worker runs. After a restart,
        an eviction, or when another replica projected the session's
        earlier events, the ledger answers instead: the event just before
        this one in the session's log order. That draws the same edge an
        uninterrupted run would, including none after a session end.
        """
        cached = self._session_last_event.get(event.session_id)
        if cached is not None:
            return cached
        event_id = str(event.event_id)
        session_ids = await self._event_log.read_session_ids(event.session_id)
        if event_id not in session_ids:
            return None
        index = session_ids.index(event_id)
        if index == 0:
            return None
        (document,) = await self._event_log.get_documents([session_ids[index - 1]])
        if document is None:
            return None
        previous = Event.model_validate(document, strict=False)
        if previous.event_type == "system.session_end":
            return None
        log.debug(
            "previous_event_from_ledger",
            event_id=event_id,
            previous_event_id=str(previous.event_id),
            session_id=event.session_id,
        )
        return previous

    async def on_stop(self) -> None:
        """Flush remaining buffered events before shutdown."""
        if self._buffer:
            log.info("flushing_buffer_on_stop", buffered=len(self._buffer))
            await self._flush_buffer()

    async def _fetch_event(self, entry_id: str, data: dict[str, str]) -> Event | None:
        """Fetch and deserialize a single event from the event log."""
        event_id = data.get("event_id")
        if event_id is None:
            log.warning("stream_entry_missing_event_id", entry_id=entry_id)
            return None

        documents = await self._event_log.get_documents([event_id])
        doc = documents[0]
        if doc is None:
            log.warning(
                "event_json_not_found",
                event_id=event_id,
                entry_id=entry_id,
            )
            return None

        event = Event.model_validate(doc, strict=False)

        if event.global_position is None:
            event = event.model_copy(update={"global_position": entry_id})

        return event
