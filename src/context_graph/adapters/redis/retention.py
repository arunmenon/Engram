"""Redis implementation of the RetentionManager protocol.

Thin wrapper class delegating to the stateless functions in trimmer.py.

Source: ADR-0008, ADR-0014
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context_graph.adapters.redis.trimmer import (
    archive_and_delete_expired_events as _archive_and_delete,
)
from context_graph.adapters.redis.trimmer import (
    cleanup_dedup_set as _cleanup_dedup,
)
from context_graph.adapters.redis.trimmer import (
    cleanup_session_streams as _cleanup_sessions,
)
from context_graph.adapters.redis.trimmer import (
    delete_expired_events as _delete_expired,
)
from context_graph.adapters.redis.trimmer import (
    trim_stream as _trim_stream,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisRetentionManager:
    """Redis implementation of the RetentionManager protocol."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def trim_stream(
        self,
        stream_key: str,
        max_age_days: int,
        consumer_groups: list[str] | None = None,
    ) -> int:
        return await _trim_stream(
            redis_client=self._redis,
            stream_key=stream_key,
            max_age_days=max_age_days,
            consumer_groups=consumer_groups,
        )

    async def delete_expired_events(
        self,
        key_prefix: str,
        max_age_days: int,
    ) -> int:
        return await _delete_expired(
            redis_client=self._redis,
            key_prefix=key_prefix,
            max_age_days=max_age_days,
        )

    async def archive_and_delete_expired_events(
        self,
        key_prefix: str,
        max_age_days: int,
        archive_store: Any,
    ) -> tuple[int, int]:
        return await _archive_and_delete(
            redis_client=self._redis,
            key_prefix=key_prefix,
            max_age_days=max_age_days,
            archive_store=archive_store,
        )

    async def cleanup_dedup_set(
        self,
        dedup_key: str,
        retention_ceiling_days: int,
    ) -> int:
        return await _cleanup_dedup(
            redis_client=self._redis,
            dedup_key=dedup_key,
            retention_ceiling_days=retention_ceiling_days,
        )

    async def cleanup_session_streams(
        self,
        prefix: str,
        max_age_hours: int,
    ) -> int:
        return await _cleanup_sessions(
            redis_client=self._redis,
            prefix=prefix,
            max_age_hours=max_age_hours,
        )
