"""Retention management port interface.

Defines the protocol for hot-tier cleanup operations: stream trimming,
expired event deletion, dedup set cleanup, and session stream cleanup.

Source: ADR-0008, ADR-0014
"""

from __future__ import annotations

from typing import Any, Protocol


class RetentionManager(Protocol):
    """Protocol for Redis hot-tier retention operations."""

    async def trim_stream(
        self,
        stream_key: str,
        max_age_days: int,
        consumer_groups: list[str] | None = None,
    ) -> int:
        """Trim stream entries older than max_age_days. PEL-safe."""
        ...

    async def delete_expired_events(
        self,
        key_prefix: str,
        max_age_days: int,
    ) -> int:
        """Delete JSON event documents past the retention ceiling."""
        ...

    async def archive_and_delete_expired_events(
        self,
        key_prefix: str,
        max_age_days: int,
        archive_store: Any,
    ) -> tuple[int, int]:
        """Archive expired events then delete from store."""
        ...

    async def cleanup_dedup_set(
        self,
        dedup_key: str,
        retention_ceiling_days: int,
    ) -> int:
        """Remove old entries from the dedup sorted set."""
        ...

    async def cleanup_session_streams(
        self,
        prefix: str,
        max_age_hours: int,
    ) -> int:
        """Delete stale per-session streams."""
        ...
