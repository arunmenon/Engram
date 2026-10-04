"""Build worker ports over one mocked Redis client (ADR-0019 step 1 tests).

Workers take a ``Subscription`` and an ``EventLog``. Tests that assert on
the Redis commands a worker sends build both Redis adapters over the same
mock client, so the assertions written against the old direct-Redis
workers still hold.
"""

from __future__ import annotations

from typing import Any

from context_graph.adapters.redis.store import RedisEventStore
from context_graph.adapters.redis.subscription import RedisStreamSubscription


def redis_ports(
    redis_client: Any,
    settings: Any,
    group_name: str,
    consumer_name: str,
) -> dict[str, Any]:
    """Return ``subscription`` and ``event_log`` keyword arguments for a worker."""
    return {
        "subscription": RedisStreamSubscription(
            redis_client,
            group_name,
            consumer_name,
            settings.redis.global_stream,
        ),
        "event_log": RedisEventStore(client=redis_client, settings=settings.redis),
    }
