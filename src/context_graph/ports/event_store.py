"""Event store port interface.

Uses typing.Protocol for structural subtyping (not ABCs).
The Redis adapter implements this protocol.

Source: ADR-0004, ADR-0010
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from context_graph.domain.event_acceptance import AdmissionContext
    from context_graph.domain.models import Event, EventQuery
    from context_graph.domain.pack_admission import PayloadProblem

AppendStatus = Literal["created", "duplicate", "conflict", "rejected", "failed"]


@dataclass(frozen=True)
class AppendOutcome:
    """What happened to one event of an append.

    ``created``: written now, at ``position``. ``duplicate``: its event_id
    was already in the ledger; ``position`` is where, or None when the
    ledger no longer holds the position (an expired document). ``failed``:
    not written; ``error`` says why, and the same event can be sent again.
    ``conflict``: ID reuse with a different authenticated producer or request;
    not retryable as the same request. ``rejected``: a new event violates the
    active pack contract or has no supported handling; ``reason`` and sanitized
    ``problems`` explain the refusal. Neither status writes this event; other
    valid events in the chunk may commit.
    """

    status: AppendStatus
    position: str | None = None
    error: str | None = None
    reason: str | None = None
    problems: tuple[PayloadProblem, ...] = ()


class EventStore(Protocol):
    """Protocol for the event store (Redis implementation)."""

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
    ) -> str:
        """Append a single event. Returns the global_position (stream entry ID).

        Must be idempotent — duplicate event_id submissions are no-ops.
        When *payload* is given it is persisted alongside the event fields.
        """
        ...

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[str]:
        """Append multiple events. Returns list of global_positions.

        Each event is individually idempotent.
        """
        ...

    async def append_batch_outcomes(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[AppendOutcome]:
        """Append multiple events; one outcome per event, in order.

        Like ``append_batch``, each event is individually idempotent, but a
        duplicate is reported as such, and an event the backend could not
        write is reported ``failed`` without failing the others when the
        backend writes events independently (Redis). A backend that writes
        in transactions (Spanner) writes each commit-sized part whole, in
        order: when a later part fails, the events from it on are ``failed``,
        and when the first fails, nothing is written and the error is raised.
        Contract-rejected and identity-conflicting inputs have individual outcomes;
        valid siblings may commit. An event_id repeated within the batch is created once.
        """
        ...

    async def get_by_id(self, event_id: str) -> Event | None:
        """Retrieve a single event by its event_id."""
        ...

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        """Retrieve events for a session, ordered by occurred_at.

        Args:
            session_id: The session to query.
            limit: Max events to return.
            after: Cursor for pagination (global_position).
        """
        ...

    async def search(self, query: EventQuery) -> list[Event]:
        """Search events using RediSearch secondary indexes."""
        ...

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """Full-text BM25 search across event summaries and keywords."""
        ...

    async def close(self) -> None:
        """Release connections."""
        ...


@runtime_checkable
class EventStoreAdmin(Protocol):
    """Protocol for admin-level event store operations."""

    async def health_ping(self) -> bool:
        """Return True if the event store is reachable."""
        ...

    async def stream_length(self) -> int:
        """Return the number of entries in the global event stream."""
        ...


@runtime_checkable
class AdmissionBindable(Protocol):
    """Internal authenticated write view; source context is not client event data."""

    def admission_writer(self, context: AdmissionContext) -> EventStore: ...
