"""Event store port interface.

Uses typing.Protocol for structural subtyping (not ABCs).
The Redis adapter implements this protocol.

Source: ADR-0004, ADR-0010
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from context_graph.domain.models import Event, EventQuery


class EventStore(Protocol):
    """Protocol for the event store (Redis implementation)."""

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "default",
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
        tenant_id: str = "default",
    ) -> list[str]:
        """Append multiple events. Returns list of global_positions.

        Each event is individually idempotent.
        """
        ...

    async def get_by_id(self, event_id: str, tenant_id: str = "default") -> Event | None:
        """Retrieve a single event by its event_id."""
        ...

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
        tenant_id: str = "default",
    ) -> list[Event]:
        """Retrieve events for a session, ordered by occurred_at.

        Args:
            session_id: The session to query.
            limit: Max events to return.
            after: Cursor for pagination (global_position).
        """
        ...

    async def search(self, query: EventQuery, tenant_id: str = "default") -> list[Event]:
        """Search events using RediSearch secondary indexes."""
        ...

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
        tenant_id: str = "default",
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

    async def stream_length(self, tenant_id: str = "default") -> int:
        """Return the number of entries in the global event stream."""
        ...
