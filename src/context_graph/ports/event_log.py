"""Event log port interface.

``EventLog`` is the ADR-0019 name for the source-of-truth event store. It
extends the frozen ``EventStore`` protocol with the reads workers need
(stored documents by id, a session's events in order) and hot-tier
retention. Workers read events only through this port; no worker issues
backend commands.

All arguments are backend-neutral: event ids, session ids, ages and group
names. Keys, streams and other storage layout stay inside the adapter.

Uses typing.Protocol for structural subtyping (not ABCs).

Source: ADR-0004, ADR-0014, ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from context_graph.ports.event_store import EventStore

if TYPE_CHECKING:
    from context_graph.ports.archive import ArchiveStore


class EventLog(EventStore, Protocol):
    """Protocol for the event log: append, reads for workers, retention."""

    async def get_documents(self, event_ids: list[str]) -> list[dict[str, Any] | None]:
        """Return the stored document for each id, in the order given.

        A document holds the event fields plus ``payload`` when one was
        stored. Entries are None for ids that are not in the log.
        """
        ...

    async def read_session_ids(self, session_id: str) -> list[str]:
        """Return the ids of a session's events in log order."""
        ...

    async def trim(self, max_age_days: int, consumer_groups: list[str]) -> int:
        """Drop hot-tier log entries older than ``max_age_days``.

        Entries still pending for any of ``consumer_groups`` are kept.
        Returns the number of entries dropped.
        """
        ...

    async def expire(
        self,
        max_age_days: int,
        archive_store: ArchiveStore | None = None,
    ) -> tuple[int, int]:
        """Delete stored documents older than ``max_age_days``.

        When ``archive_store`` is given, documents are archived first.
        Returns ``(archived, deleted)``.
        """
        ...

    async def housekeep(
        self,
        retention_ceiling_days: int,
        session_index_max_age_hours: int,
    ) -> dict[str, int]:
        """Remove backend bookkeeping past retention (dedup records, session indexes).

        Returns counts keyed by what was removed.
        """
        ...
