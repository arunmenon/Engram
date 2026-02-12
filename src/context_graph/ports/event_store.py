"""Event store port interface.

Uses typing.Protocol for structural subtyping (not ABCs).
The Redis adapter implements this protocol.

Source: ADR-0004, ADR-0010
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from context_graph.domain.models import Event, EventQuery


class EventStore(Protocol):
    """Protocol for the event store (Redis implementation)."""

    async def append(self, event: Event) -> str:
        """Append a single event. Returns the global_position (stream entry ID).

        Must be idempotent — duplicate event_id submissions are no-ops.
        """
        ...

    async def append_batch(self, events: list[Event]) -> list[str]:
        """Append multiple events. Returns list of global_positions.

        Each event is individually idempotent.
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

    async def close(self) -> None:
        """Release connections."""
        ...
