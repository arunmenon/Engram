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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from context_graph.ports.event_store import EventStore

if TYPE_CHECKING:
    from context_graph.ports.archive import ArchiveStore


@dataclass(frozen=True)
class LogEntry:
    """One entry of the log, in log order (``read_after``).

    ``document`` is None when the stored document has expired while the
    entry is still in the log's hot window.
    """

    position: str
    event_id: str
    document: dict[str, Any] | None = None


@dataclass(frozen=True)
class ImportedEvent:
    """An event copied from another log (ADR-0019 §7).

    ``document`` holds the event fields (and ``payload`` when stored);
    ``legacy_position`` is its position in the source log, kept so
    provenance that cites the old position still resolves.
    """

    document: dict[str, Any] = field(default_factory=dict)
    legacy_position: str = ""


class EventLog(EventStore, Protocol):
    """Protocol for the event log: append, reads for workers, retention."""

    async def read_after(self, position: str | None, limit: int) -> list[LogEntry]:
        """Return up to ``limit`` log entries after ``position`` in log order.

        ``position`` None starts at the oldest entry still in the log. The
        last entry's position is the cursor for the next call.
        """
        ...

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


class MigrationTarget(Protocol):
    """An event log that can receive a copy of another log (ADR-0019 §7).

    Imports keep source order: within one call, and across calls in call
    order. Imports are idempotent by ``event_id``: an event already present
    keeps its position, which is returned.
    """

    async def append_imported(self, events: list[ImportedEvent]) -> list[str]:
        """Append copied events in order. Returns their positions in this log."""
        ...

    async def last_legacy_position(self) -> str | None:
        """Source position of the newest imported entry, or None if none.

        A copy resumes after it, so the target is its own checkpoint.
        """
        ...

    async def has_native_events(self) -> bool:
        """True if the log holds any entry that was not imported.

        A copy must not start then: imported events would land after
        native ones, breaking "every migrated event precedes every new one".
        """
        ...
