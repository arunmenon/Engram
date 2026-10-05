"""Consumer 1: Graph Projection worker.

Reads events delivered by its subscription and projects them into the
graph using the pure domain projection logic. Each event becomes
an EventNode, and FOLLOWS / CAUSED_BY edges are created as appropriate.

Source: ADR-0005, ADR-0013 (Consumer 1)
"""

from __future__ import annotations

import time
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.models import Event
from context_graph.domain.projection import project_event
from context_graph.metrics import CONSUMER_MESSAGE_ERRORS
from context_graph.ports.errors import is_transient
from context_graph.settings import OntologySettings
from context_graph.worker.consumer import BaseConsumer
from context_graph.worker.pack_projection import apply_plan, apply_plans

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import PackProjector, ProjectionPlan
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_store import GraphStore
    from context_graph.ports.subscription import Subscription
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

DEFAULT_LOOKUP_LIMIT: int = OntologySettings.model_fields["lookup_limit"].default


class ProjectionConsumer(BaseConsumer):
    """Consumer 1: Projects delivered events into the graph.

    For each event received from the subscription:
    1. Fetch the full event from the event log (deliveries carry only event_id).
    2. Run pure domain projection to produce an EventNode and edges.
    3. MERGE the node and edges into Neo4j via the GraphStore.
    4. Track the last event per session for FOLLOWS edge computation.
    5. Apply the active ontology packs' projection rules for the event's
       type (ADR-0018), when a ``pack_projector`` is given.
    """

    _MAX_SESSION_CACHE = 10_000

    @property
    def deferred_ack(self) -> bool:  # noqa: D102
        return True

    def __init__(
        self,
        subscription: Subscription,
        event_log: EventLog,
        graph_store: GraphStore,
        settings: Settings,
        pack_projector: PackProjector | None = None,
        pack_lookup_limit: int = DEFAULT_LOOKUP_LIMIT,
    ) -> None:
        super().__init__(
            subscription,
            batch_size=settings.consumer.projection_batch_size,
            block_timeout_ms=settings.consumer.block_timeout_ms,
            max_retries=settings.consumer.max_retries,
            transient_backoff_ms=settings.consumer.transient_backoff_ms,
            transient_backoff_max_ms=settings.consumer.transient_backoff_max_ms,
        )
        # Events per flush, and the longest a partial flush waits
        # (CG_CONSUMER_PROJECTION_BATCH_SIZE / _BATCH_TIMEOUT_MS)
        self._BATCH_SIZE = settings.consumer.projection_batch_size
        self._BATCH_TIMEOUT_MS = settings.consumer.projection_batch_timeout_ms
        self._event_log = event_log
        self._graph_store = graph_store
        self._pack_projector = pack_projector
        self._pack_lookup_limit = pack_lookup_limit
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
        pack_events: list[tuple[str, dict[str, str], Event, dict[str, Any]]] = []

        fetched = await self._fetch_batch(batch)
        for entry_id, data in batch:
            loaded = fetched.get(entry_id)
            if loaded is None:
                continue
            event, document = loaded
            if self._pack_projector is not None and self._pack_projector.handles(event.event_type):
                pack_events.append((entry_id, data, event, document))

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

        # Batch write to the graph (writes are idempotent, so a retry is safe)
        if all_nodes:
            if hasattr(self._graph_store, "merge_event_nodes_batch"):
                await self._retry_transient(
                    lambda: self._graph_store.merge_event_nodes_batch(all_nodes),
                    "merge_event_nodes",
                )
            else:
                for node in all_nodes:
                    await self._retry_transient(
                        partial(self._graph_store.merge_event_node, node), "merge_event_node"
                    )
        if all_edges:
            await self._retry_transient(
                lambda: self._graph_store.create_edges_batch(all_edges), "create_edges"
            )

        # Ontology pack rules (ADR-0018), in log order, after the Event nodes exist.
        if self._pack_projector is not None and pack_events:
            await self._apply_pack_rules(pack_events)

        # ACK all entries after successful write (deferred_ack = True)
        entry_ids = [eid for eid, _ in batch]
        if entry_ids:
            await self._ack(*entry_ids)

    async def _apply_pack_rules(
        self, pack_events: list[tuple[str, dict[str, str], Event, dict[str, Any]]]
    ) -> None:
        """Plan each event's pack rules, then write the whole flush in four staged calls.

        An event whose rules cannot be planned (a bad value) is dead-lettered
        on its own. An unavailable backend is retried in place. When the
        staged write fails for another reason, the events are written one at
        a time, so only the event that fails is dead-lettered and the batch
        goes on.
        """
        assert self._pack_projector is not None
        planned: list[tuple[str, dict[str, str], Event, ProjectionPlan]] = []
        for entry_id, data, event, document in pack_events:
            try:
                planned.append((entry_id, data, event, self._pack_projector.plan(event, document)))
            except Exception:
                await self._pack_failed(entry_id, data, event)
        if not planned:
            return
        try:
            await self._retry_transient(
                partial(
                    apply_plans,
                    self._graph_store,  # type: ignore[arg-type]
                    [plan for *_ids, plan in planned],
                    self._pack_lookup_limit,
                ),
                "apply_pack_plans",
            )
            return
        except Exception as exc:
            if is_transient(exc):
                raise  # stopping mid-outage: the batch stays pending
            log.warning("pack_batch_failed_retrying_per_event", events=len(planned), error=str(exc))
        for entry_id, data, event, plan in planned:
            try:
                await self._retry_transient(
                    partial(
                        apply_plan,
                        self._graph_store,  # type: ignore[arg-type]
                        plan,
                        self._pack_lookup_limit,
                    ),
                    "apply_pack_plan",
                )
            except Exception as exc:
                if is_transient(exc):
                    raise
                await self._pack_failed(entry_id, data, event)

    async def _pack_failed(self, entry_id: str, data: dict[str, str], event: Event) -> None:
        CONSUMER_MESSAGE_ERRORS.labels(consumer=self._group_name).inc()
        log.exception(
            "pack_projection_failed",
            event_id=str(event.event_id),
            event_type=event.event_type,
            entry_id=entry_id,
        )
        await self._dead_letter_message(entry_id, data, 1)

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
        previous_id = await self._retry_transient(
            partial(self._event_log.previous_in_session, event.session_id, event_id),
            "previous_in_session",
        )
        if previous_id is None:
            return None
        (document,) = await self._retry_transient(
            partial(self._event_log.get_documents, [previous_id]), "get_documents"
        )
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

    async def _fetch_batch(
        self, batch: list[tuple[str, dict[str, str]]]
    ) -> dict[str, tuple[Event, dict[str, Any]]]:
        """The events of a flush and their stored documents (payload included), in one read."""
        wanted = [(entry_id, data.get("event_id")) for entry_id, data in batch]
        for entry_id, event_id in wanted:
            if event_id is None:
                log.warning("stream_entry_missing_event_id", entry_id=entry_id)
        ids = [event_id for _entry, event_id in wanted if event_id is not None]
        documents = await self._retry_transient(
            partial(self._event_log.get_documents, ids), "get_documents"
        )
        by_id = dict(zip(ids, documents, strict=True))
        fetched: dict[str, tuple[Event, dict[str, Any]]] = {}
        for entry_id, event_id in wanted:
            if event_id is None:
                continue
            doc = by_id.get(event_id)
            if doc is None:
                log.warning("event_json_not_found", event_id=event_id, entry_id=entry_id)
                continue
            event = Event.model_validate(doc, strict=False)
            if event.global_position is None:
                event = event.model_copy(update={"global_position": entry_id})
            fetched[entry_id] = (event, doc)
        return fetched
