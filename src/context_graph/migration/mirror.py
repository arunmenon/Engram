"""Copy and mirror an event log into another backend (ADR-0019 §7, brief phase 3).

One mechanism serves both the bulk copy and the dual run: read the
source log in order (``EventLog.read_after``) and import into the target
(``MigrationTarget.append_imported``), keeping each event's source
position as ``legacy_position``.

- **Copy**: ``copy_once`` until the target has caught up.
- **Dual run**: ``run`` keeps doing that, so every event the source
  accepts reaches the target in source order. The API keeps writing only
  to the source; nothing new is written to the target directly.

Why mirroring rather than the API writing to both stores: writes from the
API would race the copy's tail and could land out of order, breaking
"every migrated event precedes every new one" (brief §6, review finding
6). Reading the source in order cannot reorder anything, a target outage
only delays the mirror, and ingest latency is unchanged.

The target is its own checkpoint: a restart resumes after the target's
newest ``legacy_position``. Imports are idempotent, so re-reading a batch
after a crash is harmless.

Uses ports only; no backend imports.

Source: ADR-0019, docs/research/2026-10/ontology/spanner-design-brief.md
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from context_graph.ports.event_log import ImportedEvent

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.ports.event_log import EventLog, MigrationTarget

log = structlog.get_logger(__name__)


class MirrorRefusedError(RuntimeError):
    """The target already holds events that were not imported."""


@dataclass
class MirrorReport:
    """What one copy pass did."""

    started_after: str | None
    last_source_position: str | None
    imported: int = 0
    skipped_without_document: int = 0
    batches: int = 0


class LogMirror:
    """Copies ``source`` into ``target`` in source order."""

    def __init__(
        self,
        source: EventLog,
        target: MigrationTarget,
        *,
        batch_size: int = 500,
    ) -> None:
        self._source = source
        self._target = target
        self._batch_size = batch_size
        self._prepared = False

    async def prepare(self, *, allow_native: bool = False) -> str | None:
        """Check the target and return the source position to resume after.

        Refuses when the target holds native events, unless ``allow_native``
        (only for a deliberate re-run after cutover, never for a first copy).
        """
        if not allow_native and await self._target.has_native_events():
            msg = (
                "Target event log already holds events that were not imported; "
                "copying now would place migrated events after them"
            )
            raise MirrorRefusedError(msg)
        self._prepared = True
        return await self._target.last_legacy_position()

    async def copy_once(self) -> MirrorReport:
        """Import everything the source holds after the target's checkpoint."""
        if not self._prepared:
            await self.prepare()
        cursor = await self._target.last_legacy_position()
        report = MirrorReport(started_after=cursor, last_source_position=cursor)
        while True:
            entries = await self._source.read_after(cursor, self._batch_size)
            if not entries:
                break
            batch = [
                ImportedEvent(document=entry.document, legacy_position=entry.position)
                for entry in entries
                if entry.document is not None
            ]
            if batch:
                await self._target.append_imported(batch)
            report.imported += len(batch)
            report.skipped_without_document += len(entries) - len(batch)
            report.batches += 1
            cursor = entries[-1].position
            report.last_source_position = cursor
            if len(entries) < self._batch_size:
                break
        log.info(
            "log_mirror_pass",
            started_after=report.started_after,
            last_source_position=report.last_source_position,
            imported=report.imported,
            skipped_without_document=report.skipped_without_document,
        )
        return report

    async def run(
        self,
        *,
        poll_interval_s: float = 1.0,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> int:
        """Mirror until ``should_stop`` returns True. Returns events imported."""
        await self.prepare()
        total = 0
        while not should_stop():
            report = await self.copy_once()
            total += report.imported
            if report.imported == 0:
                await asyncio.sleep(poll_interval_s)
        return total
