"""Google Cloud Storage archive adapter.

Implements the ArchiveStore protocol using GCS.
Events are serialized as gzip-compressed JSONL blobs partitioned by date.

The google-cloud-storage package is an optional dependency — importing this
module without it installed will raise a clear error at construction time.

Source: ADR-0014
"""

from __future__ import annotations

import asyncio
import gzip
import io
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import orjson
import structlog

if TYPE_CHECKING:
    from google.cloud import storage as gcs_types

logger = structlog.get_logger(__name__)


def _require_gcs() -> Any:
    """Import and return the google.cloud.storage module, or raise."""
    try:
        from google.cloud import storage  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "google-cloud-storage is required for GCSArchiveStore. "
            "Install it with: pip install google-cloud-storage"
        ) from exc
    return storage


class GCSArchiveStore:
    """Archive store backed by Google Cloud Storage.

    Writes gzip-compressed JSONL blobs into date-partitioned paths
    under the configured bucket and prefix.

    Pass ``endpoint`` to connect to a GCS emulator (e.g. fake-gcs-server)
    instead of the real GCS API.
    """

    def __init__(
        self,
        bucket_name: str,
        prefix: str = "engram/archives",
        client: gcs_types.Client | None = None,
        endpoint: str = "",
    ) -> None:
        self._bucket_name = bucket_name
        self._prefix = prefix.rstrip("/")
        self._client: Any = client
        self._endpoint = endpoint
        self._owns_client = client is None

    def _get_client(self) -> Any:
        """Lazily initialize the GCS client.

        When ``self._endpoint`` is set, configures the ``STORAGE_EMULATOR_HOST``
        env var which the google-cloud-storage library natively respects —
        it skips auth entirely and talks HTTP to the emulator.
        """
        if self._client is None:
            if self._endpoint:
                import os  # noqa: PLC0415

                os.environ["STORAGE_EMULATOR_HOST"] = self._endpoint
            storage = _require_gcs()
            self._client = storage.Client()
        return self._client

    async def archive_events(self, events: list[dict[str, Any]], partition_key: str) -> str:
        """Archive events as a gzip-compressed JSONL blob in GCS."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        uuid_short = uuid.uuid4().hex[:8]
        blob_path = f"{self._prefix}/{partition_key}/{timestamp}-{uuid_short}.jsonl.gz"

        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as gz_file:
            for event in events:
                line = orjson.dumps(event) + b"\n"
                gz_file.write(line)
        compressed_data = buffer.getvalue()

        def _upload() -> None:
            client = self._get_client()
            bucket = client.bucket(self._bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(compressed_data, content_type="application/gzip")

        await asyncio.to_thread(_upload)
        logger.info(
            "archived_events_gcs",
            blob_path=blob_path,
            event_count=len(events),
            bucket=self._bucket_name,
        )
        return blob_path

    async def list_archives(
        self, prefix: str | None = None, limit: int = 100
    ) -> list[dict[str, str]]:
        """List available archive blobs in GCS."""
        search_prefix = self._prefix
        if prefix:
            search_prefix = f"{self._prefix}/{prefix}"

        def _list() -> list[dict[str, str]]:
            client = self._get_client()
            bucket = client.bucket(self._bucket_name)
            blobs = bucket.list_blobs(prefix=search_prefix, max_results=limit)
            results: list[dict[str, str]] = []
            for blob in blobs:
                if blob.name.endswith(".jsonl.gz"):
                    created_at = (
                        blob.time_created.isoformat()
                        if blob.time_created
                        else datetime.now(UTC).isoformat()
                    )
                    results.append({"archive_id": blob.name, "created_at": created_at})
            return results

        return await asyncio.to_thread(_list)

    async def restore_archive(self, archive_id: str) -> list[dict[str, Any]]:
        """Restore events from a gzip-compressed JSONL blob in GCS."""

        def _download() -> bytes:
            client = self._get_client()
            bucket = client.bucket(self._bucket_name)
            blob = bucket.blob(archive_id)
            return bytes(blob.download_as_bytes())

        compressed = await asyncio.to_thread(_download)
        raw = gzip.decompress(compressed)

        events: list[dict[str, Any]] = []
        for line in raw.split(b"\n"):
            stripped = line.strip()
            if stripped:
                events.append(orjson.loads(stripped))

        logger.info(
            "restored_archive_gcs",
            archive_id=archive_id,
            event_count=len(events),
            bucket=self._bucket_name,
        )
        return events

    async def close(self) -> None:
        """Close the GCS client if we created it."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None
