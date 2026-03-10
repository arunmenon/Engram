"""Base consumer class for Redis Stream consumer workers.

Provides the XREADGROUP lifecycle loop that all consumers share:
create group, read messages, process, acknowledge. Subclasses
override ``process_message`` with their specific logic.

Source: ADR-0005, ADR-0013
"""

from __future__ import annotations

import asyncio
import random
import time as _time
from typing import TYPE_CHECKING

import structlog

from context_graph.metrics import (
    CONSUMER_BATCH_ACTUAL_SIZE,
    CONSUMER_LAG,
    CONSUMER_MESSAGE_ERRORS,
    CONSUMER_MESSAGES_DEAD_LETTERED,
    CONSUMER_MESSAGES_PROCESSED,
    CONSUMER_THROUGHPUT,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


def _build_tenant_stream_key(base_stream: str, tenant_id: str) -> str:
    """Build a tenant-prefixed stream key: ``t:{tenant_id}:{base_stream}``.

    Mirrors the key layout used by ``adapters.redis.store._tenant_stream_key``.
    """
    return f"t:{tenant_id}:{base_stream}"


class BaseConsumer:
    """Base class for Redis Stream consumer workers.

    Manages the XREADGROUP loop: read pending/new messages, dispatch to
    ``process_message``, and XACK on success. On failure the message
    stays in the Pending Entries List (PEL) for automatic retry on
    next read cycle.

    Resilience features (H4, H5):
    - XAUTOCLAIM recovers orphaned messages from crashed consumers
    - Dead-letter queue prevents permanently-failing messages from
      blocking the PEL drain indefinitely
    """

    # Exponential backoff defaults
    _BACKOFF_BASE_S: float = 1.0
    _BACKOFF_MAX_S: float = 60.0
    _BACKOFF_JITTER: float = 0.5

    def __init__(
        self,
        redis_client: Redis,
        group_name: str,
        consumer_name: str,
        stream_key: str,
        batch_size: int = 10,
        block_timeout_ms: int = 5000,
        *,
        tenant_id: str = "default",
        max_retries: int = 5,
        claim_idle_ms: int = 300_000,
        claim_batch_size: int = 100,
        dlq_stream_suffix: str = ":dlq",
        adaptive_batch_size: bool = False,
    ) -> None:
        self._redis = redis_client
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._tenant_id = tenant_id
        # Apply tenant prefix to stream key
        self._stream_key = _build_tenant_stream_key(stream_key, tenant_id)
        self._batch_size = batch_size
        self._block_timeout_ms = block_timeout_ms
        self._stopped = False
        self._consecutive_errors = 0
        # Resilience settings (H4, H5)
        self._max_retries = max_retries
        self._claim_idle_ms = claim_idle_ms
        self._claim_batch_size = claim_batch_size
        self._dlq_stream_key = f"{self._stream_key}{dlq_stream_suffix}"
        # Adaptive batch sizing
        self._adaptive_batch_size = adaptive_batch_size

    async def _backoff_delay(self) -> None:
        """Sleep with exponential backoff + jitter after consecutive errors.

        Delay = min(base * 2^errors, max) * (1 + random * jitter).
        Resets ``_consecutive_errors`` is handled by the caller on success.
        """
        delay = min(
            self._BACKOFF_BASE_S * (2**self._consecutive_errors),
            self._BACKOFF_MAX_S,
        )
        jittered = delay * (1.0 + random.random() * self._BACKOFF_JITTER)  # noqa: S311
        log.warning(
            "consumer_backoff",
            delay_s=round(jittered, 2),
            consecutive_errors=self._consecutive_errors,
            consumer=self._consumer_name,
        )
        await asyncio.sleep(jittered)

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not already exist.

        Uses ``XGROUP CREATE ... MKSTREAM`` so the stream is created
        automatically if it doesn't exist. The ``$`` ID means only new
        messages are delivered (pending messages from before group
        creation are ignored).
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

    async def _claim_orphaned_messages(self) -> int:
        """Claim messages orphaned by crashed consumers via XAUTOCLAIM.

        Scans the PEL for messages idle longer than ``_claim_idle_ms``
        that belong to ANY consumer in the group. Claims them for this
        consumer so the PEL drain loop can process them.

        Returns the number of messages claimed.
        """
        claimed_total = 0
        start_id = "0-0"

        while not self._stopped:
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

            next_start_id = (
                next_start_id_raw.decode()
                if isinstance(next_start_id_raw, bytes)
                else str(next_start_id_raw)
            )

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

    # -- H5: Dead-letter queue ---------------------------------------------

    async def _dead_letter_message(
        self,
        entry_id: str,
        data: dict[str, str],
        delivery_count: int,
    ) -> None:
        """Move a permanently-failing message to the dead-letter queue.

        Writes the message to the DLQ stream with metadata, then ACKs
        it from the source stream to remove it from the PEL.
        """
        dlq_data: dict[str, str | int | float] = {
            "original_stream": self._stream_key,
            "original_entry_id": entry_id,
            "group": self._group_name,
            "consumer": self._consumer_name,
            "delivery_count": str(delivery_count),
            **data,
        }
        await self._redis.xadd(self._dlq_stream_key, dlq_data)  # type: ignore[arg-type]
        await self._redis.xack(self._stream_key, self._group_name, entry_id)
        log.warning(
            "message_dead_lettered",
            entry_id=entry_id,
            group=self._group_name,
            consumer=self._consumer_name,
            delivery_count=delivery_count,
            dlq_stream=self._dlq_stream_key,
        )

    async def _get_delivery_counts(self) -> dict[str, int]:
        """Return {entry_id: delivery_count} for this consumer's pending messages.

        Uses XPENDING <stream> <group> - + <count> <consumer> which returns
        detailed PEL info including each message's delivery count.
        """
        result = await self._redis.xpending_range(
            name=self._stream_key,
            groupname=self._group_name,
            min="-",
            max="+",
            count=self._batch_size * 10,  # fetch enough to cover pending messages
            consumername=self._consumer_name,
        )
        counts: dict[str, int] = {}
        for entry in result:
            msg_id_raw = entry.get("message_id", b"")
            msg_id = msg_id_raw.decode() if isinstance(msg_id_raw, bytes) else str(msg_id_raw)
            times_delivered = entry.get("times_delivered", 0)
            counts[msg_id] = int(times_delivered)
        return counts

    # -- Lag metric --------------------------------------------------------

    _LAG_METRIC_INTERVAL = 50  # update lag gauge every N loop iterations

    async def _update_lag_metric(self) -> None:
        """Update the CONSUMER_LAG gauge from XINFO GROUPS."""
        try:
            info = await self._redis.xinfo_groups(self._stream_key)
            for group in info:
                if group.get("name") == self._group_name:
                    CONSUMER_LAG.labels(group=self._group_name).set(max(0, group.get("lag", 0)))
        except Exception:  # noqa: BLE001
            pass  # Non-critical metric, don't crash on failure

    # -- Adaptive batch sizing ---------------------------------------------

    # Lag thresholds for scaling batch size (pending message count)
    _LAG_THRESHOLD_2X: int = 1_000
    _LAG_THRESHOLD_4X: int = 10_000

    async def _get_pending_count(self) -> int:
        """Return the number of pending messages for this consumer group.

        Uses XPENDING summary (not the detailed range variant) which
        returns the total pending count efficiently.
        """
        try:
            summary = await self._redis.xpending(self._stream_key, self._group_name)
            pending = summary.get("pending", 0) if summary else 0
            return int(pending)
        except Exception:  # noqa: BLE001
            return 0

    def _compute_batch_size(self, pending_count: int) -> int:
        """Scale batch size based on consumer lag.

        Returns 1x, 2x, or 4x the base batch size depending on the
        number of pending (unprocessed) messages.  This allows consumers
        to catch up faster during traffic spikes without requiring
        configuration changes.
        """
        if pending_count >= self._LAG_THRESHOLD_4X:
            return self._batch_size * 4
        if pending_count >= self._LAG_THRESHOLD_2X:
            return self._batch_size * 2
        return self._batch_size

    # -- Main loop ---------------------------------------------------------

    async def run(self) -> None:
        """Main consumer loop.

        Reads messages via XREADGROUP, dispatches each to
        ``process_message``, and ACKs on success. Loops until
        ``stop()`` is called.
        """
        await self.ensure_group()
        log.info(
            "consumer_started",
            group=self._group_name,
            consumer=self._consumer_name,
            stream=self._stream_key,
        )

        # H4: Claim orphaned messages from crashed consumers before PEL drain
        await self._claim_orphaned_messages()

        # H5: Get delivery counts for pending messages (for dead-letter check)
        delivery_counts = await self._get_delivery_counts()

        # Drain pending messages (PEL recovery) before reading new ones
        while not self._stopped:
            pending = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self._consumer_name,
                streams={self._stream_key: "0"},
                count=self._batch_size,
                block=0,
            )
            if not pending or not any(entries for _, entries in pending):
                break
            for _stream_name, entries in pending:
                for entry_id_raw, data in entries:
                    entry_id = (
                        entry_id_raw.decode()
                        if isinstance(entry_id_raw, bytes)
                        else str(entry_id_raw)
                    )

                    # H5: Check delivery count — dead-letter if exceeded
                    msg_delivery_count = delivery_counts.get(entry_id, 1)
                    if msg_delivery_count > self._max_retries:
                        decoded_data = {
                            (k.decode() if isinstance(k, bytes) else k): (
                                v.decode() if isinstance(v, bytes) else v
                            )
                            for k, v in data.items()
                        }
                        await self._dead_letter_message(entry_id, decoded_data, msg_delivery_count)
                        CONSUMER_MESSAGES_DEAD_LETTERED.labels(consumer=self._group_name).inc()
                        continue

                    decoded_data = {
                        (k.decode() if isinstance(k, bytes) else k): (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in data.items()
                    }
                    try:
                        await self.process_message(entry_id, decoded_data)
                        if not self.deferred_ack:
                            await self._redis.xack(
                                self._stream_key,
                                self._group_name,
                                entry_id,
                            )
                        CONSUMER_MESSAGES_PROCESSED.labels(consumer=self._group_name).inc()
                    except Exception:
                        CONSUMER_MESSAGE_ERRORS.labels(consumer=self._group_name).inc()
                        log.exception(
                            "pending_message_processing_failed",
                            entry_id=entry_id,
                            group=self._group_name,
                            delivery_count=msg_delivery_count,
                        )

        log.info("pending_drain_completed", group=self._group_name)

        # Main loop — new messages
        loop_iteration = 0
        while not self._stopped:
            # Adaptive batch sizing: scale read count based on lag
            effective_batch_size = self._batch_size
            if self._adaptive_batch_size and loop_iteration % self._LAG_METRIC_INTERVAL == 0:
                pending_count = await self._get_pending_count()
                CONSUMER_LAG.labels(group=self._group_name).set(pending_count)
                effective_batch_size = self._compute_batch_size(pending_count)
                CONSUMER_BATCH_ACTUAL_SIZE.labels(consumer=self._group_name).observe(
                    effective_batch_size
                )

            batch_t0 = _time.monotonic()
            messages = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self._consumer_name,
                streams={self._stream_key: ">"},
                count=effective_batch_size,
                block=self._block_timeout_ms,
            )

            loop_iteration += 1
            if loop_iteration % self._LAG_METRIC_INTERVAL == 0:
                await self._update_lag_metric()

            if not messages:
                continue

            batch_msg_count = 0
            for _stream_name, entries in messages:
                for entry_id_raw, data in entries:
                    batch_msg_count += 1
                    entry_id = (
                        entry_id_raw.decode()
                        if isinstance(entry_id_raw, bytes)
                        else str(entry_id_raw)
                    )
                    decoded_data = {
                        (k.decode() if isinstance(k, bytes) else k): (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in data.items()
                    }

                    try:
                        await self.process_message(entry_id, decoded_data)
                        if not self.deferred_ack:
                            await self._redis.xack(
                                self._stream_key,
                                self._group_name,
                                entry_id,
                            )
                        CONSUMER_MESSAGES_PROCESSED.labels(consumer=self._group_name).inc()
                        self._consecutive_errors = 0
                    except Exception:
                        CONSUMER_MESSAGE_ERRORS.labels(consumer=self._group_name).inc()
                        self._consecutive_errors += 1
                        # Message stays in PEL for retry on next read cycle
                        log.exception(
                            "message_processing_failed",
                            entry_id=entry_id,
                            group=self._group_name,
                            consumer=self._consumer_name,
                        )
                        await self._backoff_delay()

            # Update throughput gauge
            batch_elapsed = _time.monotonic() - batch_t0
            if batch_elapsed > 0 and batch_msg_count > 0:
                CONSUMER_THROUGHPUT.labels(consumer=self._group_name).set(
                    batch_msg_count / batch_elapsed
                )

            # Allow batching consumers to flush after each XREADGROUP round
            await self.on_batch_complete()

        await self.on_stop()
        log.info(
            "consumer_stopped",
            group=self._group_name,
            consumer=self._consumer_name,
        )

    @property
    def deferred_ack(self) -> bool:
        """Return True to defer XACK until the subclass handles it.

        Batching consumers override this so the base loop does NOT ACK
        after each ``process_message`` call.  Instead, the consumer
        ACKs messages itself after a successful flush.
        """
        return False

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a single stream message. Override in subclasses."""
        raise NotImplementedError

    async def on_batch_complete(self) -> None:
        """Hook called after processing each XREADGROUP batch.

        Batching consumers can override to flush any remaining buffer
        that didn't reach the batch size threshold.
        """

    async def on_stop(self) -> None:
        """Cleanup hook called after the main loop exits.

        Subclasses can override to flush buffers, close resources, etc.
        """

    def stop(self) -> None:
        """Signal the consumer loop to stop gracefully."""
        self._stopped = True
