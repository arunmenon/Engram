"""Redis hot-tier trimmer for event retention.

Manages the hot tier of the dual-store architecture:
- Trims stream entries older than the hot window
- Deletes expired JSON documents past the retention ceiling

Source: ADR-0008, ADR-0010
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


async def trim_stream(
    redis_client: Redis,
    stream_key: str,
    max_age_days: int,
) -> int:
    """Trim stream entries older than max_age_days.

    Uses XTRIM with MINID strategy to remove entries whose IDs
    (timestamp-based) are older than the cutoff. Redis Stream entry IDs
    are ``<milliseconds-epoch>-<seq>``, so we construct a MINID from the
    cutoff timestamp.

    Returns the approximate number of trimmed entries.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    min_id = f"{cutoff_ms}-0"

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
    scan_pattern = f"{key_prefix}*"

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
    )
    return deleted_count
