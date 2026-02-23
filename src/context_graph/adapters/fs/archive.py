"""Filesystem archive adapter.

Implements the ArchiveStore protocol using local filesystem storage.
Events are serialized as gzip-compressed JSONL files partitioned by date.

Source: ADR-0014
"""

from __future__ import annotations

import asyncio
import gzip
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import orjson
import structlog

logger = structlog.get_logger(__name__)


class FilesystemArchiveStore:
    """Archive store backed by the local filesystem.

    Writes gzip-compressed JSONL files into date-partitioned directories
    under the configured base path.
    """

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    async def archive_events(self, events: list[dict[str, Any]], partition_key: str) -> str:
        """Archive events as a gzip-compressed JSONL file.

        File is written to {base_path}/{partition_key}/{timestamp}-{uuid_short}.jsonl.gz.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        uuid_short = uuid.uuid4().hex[:8]
        filename = f"{timestamp}-{uuid_short}.jsonl.gz"

        partition_dir = self._base_path / partition_key
        file_path = partition_dir / filename

        def _write() -> str:
            partition_dir.mkdir(parents=True, exist_ok=True)
            with gzip.open(file_path, "wb") as gz_file:
                for event in events:
                    line = orjson.dumps(event) + b"\n"
                    gz_file.write(line)
            return str(file_path.relative_to(self._base_path))

        archive_id = await asyncio.to_thread(_write)
        logger.info(
            "archived_events",
            archive_id=archive_id,
            event_count=len(events),
            partition_key=partition_key,
        )
        return archive_id

    async def list_archives(
        self, prefix: str | None = None, limit: int = 100
    ) -> list[dict[str, str]]:
        """List available archives under the base path."""
        search_path = self._base_path
        if prefix:
            search_path = self._base_path / prefix

        def _list() -> list[dict[str, str]]:
            if not search_path.exists():
                return []
            results: list[dict[str, str]] = []
            for gz_path in sorted(search_path.rglob("*.jsonl.gz")):
                relative = str(gz_path.relative_to(self._base_path))
                stat = gz_path.stat()
                created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC).isoformat()
                results.append({"archive_id": relative, "created_at": created_at})
                if len(results) >= limit:
                    break
            return results

        return await asyncio.to_thread(_list)

    async def restore_archive(self, archive_id: str) -> list[dict[str, Any]]:
        """Restore events from a gzip-compressed JSONL archive file."""
        file_path = self._base_path / archive_id

        def _read() -> list[dict[str, Any]]:
            events: list[dict[str, Any]] = []
            with gzip.open(file_path, "rb") as gz_file:
                for line in gz_file:
                    stripped = line.strip()
                    if stripped:
                        events.append(orjson.loads(stripped))
            return events

        events = await asyncio.to_thread(_read)
        logger.info(
            "restored_archive",
            archive_id=archive_id,
            event_count=len(events),
        )
        return events

    async def close(self) -> None:
        """No-op for filesystem adapter."""
