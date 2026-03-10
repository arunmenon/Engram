"""Redis hot-tier trimmer for event retention.

Manages the hot tier of the dual-store architecture:
- Trims stream entries older than the hot window
- Deletes expired JSON documents past the retention ceiling
- Cleans up stale session streams (ADR-0014)
- Archives events before deletion (ADR-0014)
- Maintains dedup sorted set (ADR-0014)

Source: ADR-0008, ADR-0010, ADR-0014
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


async def trim_stream(
    redis_client: Redis,
    stream_key: str,
    max_age_days: int,
    consumer_groups: list[str] | None = None,
    tenant_id: str = "default",
) -> int:
    """Trim stream entries older than max_age_days.

    Uses XTRIM with MINID strategy to remove entries whose IDs
    (timestamp-based) are older than the cutoff. Redis Stream entry IDs
    are ``<milliseconds-epoch>-<seq>``, so we construct a MINID from the
    cutoff timestamp.

    When *consumer_groups* is provided, the trim point is adjusted to
    avoid removing entries that have not yet been processed (PEL-safe).

    Returns the approximate number of trimmed entries.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    min_id = f"{cutoff_ms}-0"

    # PEL-safe: adjust trim point if consumer groups are provided
    if consumer_groups:
        group_progress = await get_consumer_group_progress(redis_client, stream_key)
        min_id = compute_safe_trim_id(min_id, group_progress)

    # Get stream length before trim for reporting
    stream_len_before = await redis_client.xlen(stream_key)

    # XTRIM with MINID removes entries with IDs less than the given ID
    trimmed = await redis_client.xtrim(
        name=stream_key,
        minid=min_id,
        approximate=False,
    )

    stream_len_after = await redis_client.xlen(stream_key)

    log.info(
        "stream_trimmed",
        stream_key=stream_key,
        max_age_days=max_age_days,
        cutoff_ms=cutoff_ms,
        trimmed=trimmed,
        len_before=stream_len_before,
        len_after=stream_len_after,
    )
    return int(trimmed)


async def delete_expired_events(
    redis_client: Redis,
    key_prefix: str,
    max_age_days: int,
    batch_size: int = 100,
    tenant_id: str = "default",
) -> int:
    """Delete JSON event documents past the retention ceiling.

    Scans for keys matching ``{key_prefix}*`` and checks each document's
    ``occurred_at_epoch_ms`` field. Documents older than max_age_days are
    deleted.

    Returns the number of deleted documents.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    deleted_count = 0
    cursor = 0
    scan_pattern = f"t:{tenant_id}:{key_prefix}*"

    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=scan_pattern,
            count=batch_size,
        )

        if keys:
            # Build a pipeline to fetch occurred_at_epoch_ms for each key
            pipe = redis_client.pipeline(transaction=False)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                pipe.execute_command("JSON.GET", key_str, "$.occurred_at_epoch_ms")
            results = await pipe.execute()

            keys_to_delete: list[str] = []
            for key, raw_value in zip(keys, results, strict=True):
                key_str = key.decode() if isinstance(key, bytes) else key
                if raw_value is None:
                    continue

                value_str = raw_value.decode() if isinstance(raw_value, bytes) else raw_value

                try:
                    import orjson

                    parsed = orjson.loads(value_str)
                    epoch_ms = parsed[0] if isinstance(parsed, list) else parsed
                    if isinstance(epoch_ms, int | float) and epoch_ms < cutoff_ms:
                        keys_to_delete.append(key_str)
                except (ValueError, TypeError, IndexError):
                    continue

            if keys_to_delete:
                delete_pipe = redis_client.pipeline(transaction=False)
                for key_str in keys_to_delete:
                    delete_pipe.delete(key_str)
                await delete_pipe.execute()
                deleted_count += len(keys_to_delete)

        if cursor == 0:
            break

    log.info(
        "expired_events_deleted",
        key_prefix=key_prefix,
        max_age_days=max_age_days,
        deleted_count=deleted_count,
        tenant_id=tenant_id,
    )
    return deleted_count


# ---------------------------------------------------------------------------
# ADR-0014: Session stream cleanup
# ---------------------------------------------------------------------------


async def cleanup_session_streams(
    redis_client: Redis,
    prefix: str = "events:session:",
    max_age_hours: int = 168,
    batch_size: int = 100,
    tenant_id: str = "default",
) -> int:
    """Delete per-session streams whose newest entry is older than max_age_hours.

    Scans for keys matching ``t:{tenant_id}:{prefix}*`` and checks each
    stream's newest entry via XREVRANGE ... + COUNT 1. Streams with no entries
    or whose newest entry is older than the cutoff are deleted.

    Returns the number of deleted session streams.
    """
    cutoff_ms = int((time.time() - max_age_hours * 3600) * 1000)
    deleted_count = 0
    cursor = 0
    scan_pattern = f"t:{tenant_id}:{prefix}*"

    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=scan_pattern,
            count=batch_size,
        )

        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key

            # Get the newest entry in the stream
            entries = await redis_client.xrevrange(key_str, count=1)

            if not entries:
                # Empty stream — delete it
                await redis_client.delete(key_str)
                deleted_count += 1
                continue

            # Entry ID format: "<milliseconds>-<seq>"
            entry_id = entries[0][0]
            if isinstance(entry_id, bytes):
                entry_id = entry_id.decode()
            entry_ms = int(entry_id.split("-")[0])

            if entry_ms < cutoff_ms:
                await redis_client.delete(key_str)
                deleted_count += 1

        if cursor == 0:
            break

    log.info(
        "session_streams_cleaned",
        prefix=prefix,
        max_age_hours=max_age_hours,
        deleted_count=deleted_count,
    )
    return deleted_count


# ---------------------------------------------------------------------------
# ADR-0014: Archive-before-delete
# ---------------------------------------------------------------------------


async def archive_and_delete_expired_events(
    redis_client: Redis,
    key_prefix: str,
    max_age_days: int,
    archive_store: Any,
    batch_size: int = 100,
    tenant_id: str = "default",
) -> tuple[int, int]:
    """Archive expired events to the archive store, then delete from Redis.

    Scans for expired JSON documents (same logic as delete_expired_events),
    but archives them via the ArchiveStore before deletion. If archiving
    fails for a batch, those events are NOT deleted (data safety).

    Args:
        redis_client: Redis async client.
        key_prefix: Event key prefix (e.g. "evt:").
        max_age_days: Events older than this are archived and deleted.
        archive_store: An ArchiveStore implementation.
        batch_size: SCAN batch size.

    Returns:
        Tuple of (archived_count, deleted_count).
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    archived_count = 0
    deleted_count = 0
    cursor = 0
    scan_pattern = f"t:{tenant_id}:{key_prefix}*"

    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=scan_pattern,
            count=batch_size,
        )

        if keys:
            # Fetch full JSON docs for all keys in this batch
            pipe = redis_client.pipeline(transaction=False)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                pipe.execute_command("JSON.GET", key_str, "$")
            results = await pipe.execute()

            expired_events: list[dict[str, Any]] = []
            expired_keys: list[str] = []

            for key, raw_value in zip(keys, results, strict=True):
                key_str = key.decode() if isinstance(key, bytes) else key
                if raw_value is None:
                    continue

                value_str = raw_value.decode() if isinstance(raw_value, bytes) else raw_value

                try:
                    import orjson

                    parsed = orjson.loads(value_str)
                    doc = parsed[0] if isinstance(parsed, list) else parsed
                    epoch_ms = doc.get("occurred_at_epoch_ms")
                    if isinstance(epoch_ms, int | float) and epoch_ms < cutoff_ms:
                        expired_events.append(doc)
                        expired_keys.append(key_str)
                except (ValueError, TypeError, IndexError, AttributeError):
                    continue

            if expired_events:
                # Archive first — if this fails, events are NOT deleted
                partition_key = datetime.now(UTC).strftime("%Y/%m/%d")
                try:
                    await archive_store.archive_events(expired_events, partition_key)
                    archived_count += len(expired_events)
                except Exception:
                    log.exception(
                        "archive_failed_skipping_delete",
                        event_count=len(expired_events),
                    )
                    # Skip deletion for this batch — data safety
                    if cursor == 0:
                        break
                    continue

                # Archive succeeded — now delete from Redis
                delete_pipe = redis_client.pipeline(transaction=False)
                for key_str in expired_keys:
                    delete_pipe.delete(key_str)
                await delete_pipe.execute()
                deleted_count += len(expired_keys)

        if cursor == 0:
            break

    log.info(
        "archive_and_delete_completed",
        key_prefix=key_prefix,
        max_age_days=max_age_days,
        archived_count=archived_count,
        deleted_count=deleted_count,
        tenant_id=tenant_id,
    )
    return archived_count, deleted_count


# ---------------------------------------------------------------------------
# ADR-0014: Dedup set maintenance
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Memory pressure: proactive trimming
# ---------------------------------------------------------------------------


async def trim_under_pressure(
    redis_client: Redis,
    global_stream: str = "events:__global__",
    event_key_prefix: str = "evt:",
    dedup_key: str = "dedup:events",
    session_prefix: str = "events:session:",
    hot_window_days: int = 7,
    retention_ceiling_days: int = 90,
    tenant_id: str = "default",
) -> int:
    """Aggressively trim data when Redis memory is under pressure.

    Reduces retention windows to free memory quickly:
    - Session streams: halved retention (hot_window_days / 2)
    - Cold tier JSON docs: halved retention (retention_ceiling_days / 2)
    - Dedup entries: capped at 30 days regardless of normal ceiling

    Returns the total number of items freed (trimmed + deleted + cleaned).
    Logs a WARNING with detailed stats for operator visibility.
    """
    freed_total = 0

    # 1. Trim session streams at half the normal retention
    half_session_hours = max(1, (hot_window_days * 24) // 2)
    session_freed = await cleanup_session_streams(
        redis_client,
        prefix=session_prefix,
        max_age_hours=half_session_hours,
        tenant_id=tenant_id,
    )
    freed_total += session_freed

    # 2. Delete COLD tier JSON docs at half the normal retention ceiling
    half_retention_days = max(1, retention_ceiling_days // 2)
    json_freed = await delete_expired_events(
        redis_client,
        key_prefix=event_key_prefix,
        max_age_days=half_retention_days,
        tenant_id=tenant_id,
    )
    freed_total += json_freed

    # 3. Clean dedup entries older than 30 days (aggressive cap)
    dedup_freed = await cleanup_dedup_set(
        redis_client,
        dedup_key=f"t:{tenant_id}:{dedup_key}",
        retention_ceiling_days=30,
        tenant_id=tenant_id,
    )
    freed_total += dedup_freed

    # 4. Trim global stream at half the hot window
    half_hot_days = max(1, hot_window_days // 2)
    stream_freed = await trim_stream(
        redis_client,
        stream_key=f"t:{tenant_id}:{global_stream}",
        max_age_days=half_hot_days,
        tenant_id=tenant_id,
    )
    freed_total += stream_freed

    log.warning(
        "pressure_trim_completed",
        session_streams_freed=session_freed,
        json_docs_freed=json_freed,
        dedup_entries_freed=dedup_freed,
        stream_entries_freed=stream_freed,
        total_freed=freed_total,
        tenant_id=tenant_id,
    )

    return freed_total


# ---------------------------------------------------------------------------
# PEL-safe stream trimming helpers
# ---------------------------------------------------------------------------


def _stream_id_sort_key(stream_id: str) -> tuple[int, int]:
    """Convert stream ID like '1707644400000-0' to sortable tuple."""
    parts = stream_id.split("-", 1)
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


async def get_consumer_group_progress(
    redis_client: Redis,
    stream_key: str,
) -> dict[str, str]:
    """Get oldest unprocessed entry ID per consumer group.

    Uses XINFO GROUPS to enumerate groups and XPENDING to find
    the oldest pending (unacknowledged) entry for each group.
    Falls back to last-delivered-id when there are no pending entries.
    """
    progress: dict[str, str] = {}
    try:
        groups = await redis_client.xinfo_groups(stream_key)
    except Exception:
        return progress

    for group in groups:
        group_name = group.get("name", "")
        if isinstance(group_name, bytes):
            group_name = group_name.decode()

        last_delivered = group.get("last-delivered-id", "0-0")
        if isinstance(last_delivered, bytes):
            last_delivered = last_delivered.decode()

        # Check for pending entries (oldest unacked)
        try:
            pending = await redis_client.xpending(stream_key, group_name)
            pending_min = pending.get("min") if pending else None
            if pending_min:
                if isinstance(pending_min, bytes):
                    pending_min = pending_min.decode()
                progress[group_name] = pending_min
            else:
                progress[group_name] = last_delivered
        except Exception:
            progress[group_name] = last_delivered

    return progress


def compute_safe_trim_id(
    age_cutoff_id: str,
    group_progress: dict[str, str],
) -> str:
    """Return the minimum of age cutoff and oldest unprocessed across all groups.

    If a consumer group is lagging behind the age cutoff, the trim point
    is moved forward to avoid removing unprocessed entries.
    """
    if not group_progress:
        return age_cutoff_id

    oldest_group_id = min(group_progress.values(), key=_stream_id_sort_key)

    if _stream_id_sort_key(oldest_group_id) < _stream_id_sort_key(age_cutoff_id):
        lagging = {
            k: v
            for k, v in group_progress.items()
            if _stream_id_sort_key(v) < _stream_id_sort_key(age_cutoff_id)
        }
        log.warning(
            "consumer_groups_lagging",
            lagging_groups=lagging,
            age_cutoff=age_cutoff_id,
        )
        return oldest_group_id

    return age_cutoff_id


async def cleanup_dedup_set(
    redis_client: Redis,
    dedup_key: str,
    retention_ceiling_days: int = 90,
    tenant_id: str = "default",
) -> int:
    """Remove old entries from the dedup sorted set.

    Removes entries with scores (epoch_ms) older than retention_ceiling_days.
    This prevents the dedup set from growing unbounded.
    The dedup_key should already be tenant-prefixed by the caller.

    Returns the number of removed entries.
    """
    cutoff_ms = int((time.time() - retention_ceiling_days * 86400) * 1000)

    removed: int = await redis_client.zremrangebyscore(
        dedup_key,
        "-inf",
        cutoff_ms,
    )
    log.info(
        "dedup_set_cleaned",
        dedup_key=dedup_key,
        retention_ceiling_days=retention_ceiling_days,
        cutoff_ms=cutoff_ms,
        removed=removed,
        tenant_id=tenant_id,
    )
    return removed
