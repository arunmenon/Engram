"""Unit tests for adapters/fs/archive.py — Filesystem archive store."""

from __future__ import annotations

import gzip
from pathlib import Path

import orjson
import pytest

from context_graph.adapters.fs.archive import FilesystemArchiveStore


class TestFilesystemArchiveStore:
    @pytest.fixture()
    def archive_store(self, tmp_path: Path) -> FilesystemArchiveStore:
        return FilesystemArchiveStore(base_path=tmp_path)

    @pytest.fixture()
    def sample_events(self) -> list[dict]:
        return [
            {"event_id": "evt-1", "event_type": "agent.invoke", "occurred_at_epoch_ms": 1000},
            {"event_id": "evt-2", "event_type": "tool.execute", "occurred_at_epoch_ms": 2000},
        ]

    # ------------------------------------------------------------------
    # archive_events
    # ------------------------------------------------------------------

    async def test_archive_events_creates_gz_file(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict], tmp_path: Path
    ):
        archive_id = await archive_store.archive_events(sample_events, "2025/06/15")

        full_path = tmp_path / archive_id
        assert full_path.exists()
        assert full_path.suffix == ".gz"
        assert ".jsonl" in full_path.name

    async def test_archive_events_returns_relative_path(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict], tmp_path: Path
    ):
        archive_id = await archive_store.archive_events(sample_events, "2025/06/15")

        # archive_id should be relative to base_path, not absolute
        assert not Path(archive_id).is_absolute()
        # Should start with partition key
        assert archive_id.startswith("2025/06/15/")

    async def test_roundtrip_archive_restore(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict]
    ):
        archive_id = await archive_store.archive_events(sample_events, "2025/06/15")
        restored = await archive_store.restore_archive(archive_id)

        assert restored == sample_events

    async def test_jsonl_format_each_line_is_valid_json(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict], tmp_path: Path
    ):
        archive_id = await archive_store.archive_events(sample_events, "2025/06/15")

        full_path = tmp_path / archive_id
        with gzip.open(full_path, "rb") as gz:
            lines = gz.readlines()

        assert len(lines) == len(sample_events)
        for line in lines:
            parsed = orjson.loads(line.strip())
            assert isinstance(parsed, dict)
            assert "event_id" in parsed

    async def test_list_archives_returns_metadata(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict]
    ):
        await archive_store.archive_events(sample_events, "2025/06/15")

        archives = await archive_store.list_archives()

        assert len(archives) == 1
        entry = archives[0]
        assert "archive_id" in entry
        assert "created_at" in entry
        assert entry["archive_id"].endswith(".jsonl.gz")

    async def test_list_archives_with_prefix_filter(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict]
    ):
        await archive_store.archive_events(sample_events, "2025/06/15")
        await archive_store.archive_events(sample_events, "2025/07/01")

        filtered = await archive_store.list_archives(prefix="2025/06")
        assert len(filtered) == 1
        assert "2025/06/15" in filtered[0]["archive_id"]

    async def test_list_archives_empty_directory(self, archive_store: FilesystemArchiveStore):
        archives = await archive_store.list_archives()
        assert archives == []

    async def test_partition_key_creates_directory_structure(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict], tmp_path: Path
    ):
        await archive_store.archive_events(sample_events, "2025/06/15")

        partition_dir = tmp_path / "2025" / "06" / "15"
        assert partition_dir.is_dir()
        gz_files = list(partition_dir.glob("*.jsonl.gz"))
        assert len(gz_files) == 1

    async def test_archive_empty_event_list(
        self, archive_store: FilesystemArchiveStore, tmp_path: Path
    ):
        archive_id = await archive_store.archive_events([], "2025/06/15")

        full_path = tmp_path / archive_id
        assert full_path.exists()

        restored = await archive_store.restore_archive(archive_id)
        assert restored == []

    async def test_multiple_archives_in_same_partition(
        self, archive_store: FilesystemArchiveStore, sample_events: list[dict], tmp_path: Path
    ):
        aid1 = await archive_store.archive_events(sample_events[:1], "2025/06/15")
        aid2 = await archive_store.archive_events(sample_events[1:], "2025/06/15")

        assert aid1 != aid2

        partition_dir = tmp_path / "2025" / "06" / "15"
        gz_files = list(partition_dir.glob("*.jsonl.gz"))
        assert len(gz_files) == 2

        archives = await archive_store.list_archives(prefix="2025/06/15")
        assert len(archives) == 2
