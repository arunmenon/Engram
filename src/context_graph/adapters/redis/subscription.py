"""Redis Streams implementation of the Subscription port.

Holds the consumer-group mechanics previously inlined in
``worker.consumer.BaseConsumer``: XGROUP CREATE, XAUTOCLAIM, XPENDING,
XREADGROUP, XACK, the dead-letter stream and XINFO GROUPS lag.

Source: ADR-0005, ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.redis.errors import translate_redis_error
from context_graph.ports.subscription import Delivery

if TYPE_CHECKING:
    from collections.abc import Callable

    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


def _decode(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _decode_fields(data: dict[Any, Any]) -> dict[str, str]:
    return {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in data.items()
    }


@translate_errors(translate_redis_error)
class RedisStreamSubscription:
    """Consumer group over a Redis Stream.

    Satisfies the ``context_graph.ports.subscription.Subscription`` protocol.
    """

    def __init__(
        self,
        redis_client: Redis,
        group_name: str,
        consumer_name: str,
        stream_key: str,
        *,
        claim_idle_ms: int = 300_000,
        claim_batch_size: int = 100,
        dlq_stream_suffix: str = ":dlq",
    ) -> None:
        self._redis = redis_client
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._stream_key = stream_key
        self._claim_idle_ms = claim_idle_ms
        self._claim_batch_size = claim_batch_size
        self._dlq_stream_key = f"{stream_key}{dlq_stream_suffix}"

    @property
    def group_name(self) -> str:
        return self._group_name

    @property
    def consumer_name(self) -> str:
        return self._consumer_name

    @property
    def source_name(self) -> str:
        return self._stream_key

    @property
    def dlq_stream_key(self) -> str:
        return self._dlq_stream_key

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not already exist.

        Uses ``XGROUP CREATE ... MKSTREAM`` with ID ``0`` so the stream is
        created automatically and existing entries are delivered.
        """
        try:
            await self._redis.xgroup_create(
                name=self._stream_key,
                groupname=self._group_name,
                id="0",
                mkstream=True,
            )
            log.info(
                "consumer_group_created",
                group=self._group_name,
                stream=self._stream_key,
            )
        except Exception as exc:  # noqa: BLE001
            # BUSYGROUP means group already exists — that's fine
            error_msg = str(exc)
            if "BUSYGROUP" in error_msg:
                log.debug(
                    "consumer_group_exists",
                    group=self._group_name,
                    stream=self._stream_key,
                )
            else:
                raise

    # -- H4: Orphaned message recovery (XAUTOCLAIM) -----------------------

    async def claim_orphaned(self, should_stop: Callable[[], bool] | None = None) -> int:
        """Claim messages orphaned by crashed consumers via XAUTOCLAIM.

        Scans the PEL for messages idle longer than ``claim_idle_ms``
        that belong to ANY consumer in the group and claims them for this
        consumer. Returns the number of messages claimed.
        """
        claimed_total = 0
        start_id = "0-0"

        while not (should_stop is not None and should_stop()):
            # XAUTOCLAIM <stream> <group> <consumer> <min-idle-time> <start> [COUNT count]
            result = await self._redis.xautoclaim(
                name=self._stream_key,
                groupname=self._group_name,
                consumername=self._consumer_name,
                min_idle_time=self._claim_idle_ms,
                start_id=start_id,
                count=self._claim_batch_size,
            )
            # result is a tuple: (next_start_id, [(id, data), ...], [deleted_ids])
            next_start_id_raw, claimed_entries, _deleted_ids = result

            if not claimed_entries:
                break

            claimed_total += len(claimed_entries)

            next_start_id = _decode(next_start_id_raw)

            # If next_start_id is "0-0", we've scanned the entire PEL
            if next_start_id == "0-0":
                break

            start_id = next_start_id

        if claimed_total > 0:
            log.info(
                "orphaned_messages_claimed",
                group=self._group_name,
                consumer=self._consumer_name,
                claimed=claimed_total,
            )

        return claimed_total

    # -- H5: Delivery counts and dead-letter queue -------------------------

    async def delivery_counts(self, limit: int) -> dict[str, int]:
        """Return {entry_id: delivery_count} for this consumer's pending messages.

        Uses XPENDING <stream> <group> - + <count> <consumer>.
        """
        result: list[dict[str, Any]] = await self._redis.xpending_range(
            name=self._stream_key,
            groupname=self._group_name,
            min="-",
            max="+",
            count=limit,
            consumername=self._consumer_name,
        )
        counts: dict[str, int] = {}
        for entry in result:
            msg_id_raw = entry.get("message_id", b"")
            msg_id = _decode(msg_id_raw)
            times_delivered = entry.get("times_delivered", 0)
            counts[msg_id] = int(times_delivered)
        return counts

    async def dead_letter(self, delivery: Delivery, delivery_count: int) -> None:
        """Write the message to the DLQ stream with metadata, then XACK it."""
        dlq_data: dict[str, str | int | float] = {
            "original_stream": self._stream_key,
            "original_entry_id": delivery.position,
            "group": self._group_name,
            "consumer": self._consumer_name,
            "delivery_count": str(delivery_count),
            **delivery.fields,
        }
        await self._redis.xadd(self._dlq_stream_key, dlq_data)  # type: ignore[arg-type]
        await self._redis.xack(self._stream_key, self._group_name, delivery.position)
        log.warning(
            "message_dead_lettered",
            entry_id=delivery.position,
            group=self._group_name,
            consumer=self._consumer_name,
            delivery_count=delivery_count,
            dlq_stream=self._dlq_stream_key,
        )

    # -- Reads and acknowledgement -----------------------------------------

    async def _read(self, stream_id: str, count: int, block_ms: int | None) -> list[Delivery]:
        response: Any = await self._redis.xreadgroup(
            groupname=self._group_name,
            consumername=self._consumer_name,
            streams={self._stream_key: stream_id},
            count=count,
            block=block_ms,
        )
        deliveries: list[Delivery] = []
        for _stream_name, entries in response or []:
            for entry_id_raw, data in entries:
                deliveries.append(
                    Delivery(position=_decode(entry_id_raw), fields=_decode_fields(data))
                )
        return deliveries

    async def read_pending(self, count: int, *, after: str | None = None) -> list[Delivery]:
        """XREADGROUP from ID ``0`` (or ``after``): this consumer's PEL, without blocking.

        With an explicit ID, XREADGROUP returns only pending entries whose
        ID is greater than it, so passing the last ID read pages through the PEL.
        """
        return await self._read(after or "0", count, 0)

    async def read_new(self, count: int, block_ms: int) -> list[Delivery]:
        """XREADGROUP from ID ``>``: messages never delivered to the group.

        ``BLOCK 0`` means "wait forever" in Redis, but the port defines
        ``block_ms <= 0`` as "do not wait", so BLOCK is omitted then.
        """
        return await self._read(">", count, block_ms if block_ms > 0 else None)

    async def ack(self, *positions: str) -> None:
        await self._redis.xack(self._stream_key, self._group_name, *positions)

    # -- Lag ---------------------------------------------------------------

    async def lag(self) -> int | None:
        """Return the group's lag from XINFO GROUPS, or None if unavailable."""
        try:
            info: list[dict[str, Any]] = await self._redis.xinfo_groups(self._stream_key)
            for group in info:
                # The name is bytes on a client without decode_responses
                if _decode(group.get("name", b"")) == self._group_name:
                    return max(0, int(group.get("lag", 0)))
        except Exception:  # noqa: BLE001
            return None  # Non-critical metric, don't crash on failure
        return None
