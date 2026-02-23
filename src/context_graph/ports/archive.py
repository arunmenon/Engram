"""Archive store port interface.

Uses typing.Protocol for structural subtyping.
Adapters for GCS and local filesystem implement this protocol.

Source: ADR-0014
"""

from __future__ import annotations

from typing import Any, Protocol


class ArchiveStore(Protocol):
    """Protocol for event archive storage (GCS/filesystem implementations)."""

    async def archive_events(self, events: list[dict[str, Any]], partition_key: str) -> str:
        """Archive a batch of events to persistent storage.

        Args:
            events: Event dicts to archive (includes adapter fields like occurred_at_epoch_ms).
            partition_key: Date-based partition key (e.g. "2026/02/23").

        Returns:
            Archive identifier (e.g. blob path or file path).
        """
        ...

    async def list_archives(
        self, prefix: str | None = None, limit: int = 100
    ) -> list[dict[str, str]]:
        """List available archives.

        Args:
            prefix: Optional prefix filter (e.g. "2026/02/").
            limit: Maximum number of results.

        Returns:
            List of dicts with 'archive_id' and 'created_at' keys.
        """
        ...

    async def restore_archive(self, archive_id: str) -> list[dict[str, Any]]:
        """Restore events from an archive.

        Args:
            archive_id: The archive identifier returned by archive_events.

        Returns:
            List of event dicts as they were archived.
        """
        ...

    async def close(self) -> None:
        """Release any held resources."""
        ...
