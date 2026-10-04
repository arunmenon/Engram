"""Base consumer class for event-log consumer workers.

Provides the lifecycle loop that all consumers share: ensure the group,
recover orphaned and pending items, read new items, process, acknowledge.
Subclasses override ``process_message`` with their specific logic.

The loop is backend-neutral: all delivery mechanics sit behind the
``Subscription`` port (ADR-0019). The Redis Streams implementation is
``adapters.redis.subscription.RedisStreamSubscription``.

Source: ADR-0005, ADR-0013, ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from context_graph.metrics import (
    CONSUMER_LAG,
    CONSUMER_MESSAGE_ERRORS,
    CONSUMER_MESSAGES_DEAD_LETTERED,
    CONSUMER_MESSAGES_PROCESSED,
)
from context_graph.ports.subscription import Delivery

if TYPE_CHECKING:
    from context_graph.ports.subscription import Subscription

log = structlog.get_logger(__name__)


class BaseConsumer:
    """Base class for consumer workers over a ``Subscription``.

    Reads pending/new items, dispatches each to ``process_message``, and
    acknowledges on success. On failure the item stays pending and is
    delivered again on the next read cycle.

    Resilience features (H4, H5):
    - Orphaned items from crashed consumers are claimed at start-up
    - Items delivered more than ``max_retries`` times are dead-lettered
      so they cannot block the pending drain indefinitely
    """

    def __init__(
        self,
        subscription: Subscription,
        batch_size: int = 10,
        block_timeout_ms: int = 5000,
        *,
        max_retries: int = 5,
    ) -> None:
        self._subscription = subscription
        self._group_name = subscription.group_name
        self._consumer_name = subscription.consumer_name
        self._source_name = subscription.source_name
        self._batch_size = batch_size
        self._block_timeout_ms = block_timeout_ms
        self._stopped = False
        self._max_retries = max_retries

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not already exist."""
        await self._subscription.ensure_group()

    # -- H4: Orphaned message recovery ------------------------------------

    async def _claim_orphaned_messages(self) -> int:
        """Claim items orphaned by crashed consumers. Returns the number claimed."""
        return await self._subscription.claim_orphaned(should_stop=lambda: self._stopped)

    # -- H5: Dead-letter queue ---------------------------------------------

    async def _dead_letter_message(
        self,
        entry_id: str,
        data: dict[str, str],
        delivery_count: int,
    ) -> None:
        """Move a permanently-failing item to the dead-letter destination."""
        await self._subscription.dead_letter(
            Delivery(position=entry_id, fields=data), delivery_count
        )

    async def _get_delivery_counts(self) -> dict[str, int]:
        """Return {entry_id: delivery_count} for this consumer's pending items."""
        return await self._subscription.delivery_counts(limit=self._batch_size * 10)

    async def _ack(self, *entry_ids: str) -> None:
        """Acknowledge items. Batching consumers call this after a flush."""
        await self._subscription.ack(*entry_ids)

    # -- Lag metric --------------------------------------------------------

    _LAG_METRIC_INTERVAL = 50  # update lag gauge every N loop iterations

    async def _update_lag_metric(self) -> None:
        """Update the CONSUMER_LAG gauge from the subscription's lag."""
        lag = await self._subscription.lag()
        if lag is not None:
            CONSUMER_LAG.labels(group=self._group_name).set(lag)

    # -- Pending drain -----------------------------------------------------

    async def _drain_pending(self) -> None:
        """Process this consumer's pending items, retrying failures, then return.

        Each sweep reads the pending items once, in order, moving the cursor
        past every item it reads, so a failing item never blocks the items
        behind it. Items that failed are retried in the next sweep. Delivery
        counts are refreshed every sweep and floored by the failures counted
        in this run, so an item delivered more than ``max_retries`` times is
        dead-lettered in this run even if the backend's count does not move.
        The drain ends after a sweep with no failures, which takes at most
        ``max_retries + 1`` sweeps.
        """
        first_seen_counts: dict[str, int] = {}
        failures_this_run: dict[str, int] = {}
        # Processed in this run; with deferred_ack they stay pending until the
        # subclass flushes, and must not be processed again
        processed_this_run: set[str] = set()

        while not self._stopped:
            # H5: Delivery counts for pending items (for dead-letter check)
            delivery_counts = await self._get_delivery_counts()
            cursor: str | None = None
            failed_in_sweep = False

            while not self._stopped:
                pending = await self._subscription.read_pending(self._batch_size, after=cursor)
                if not pending:
                    break
                cursor = pending[-1].position

                for delivery in pending:
                    entry_id = delivery.position
                    if entry_id in processed_this_run:
                        continue

                    # H5: Check delivery count — dead-letter if exceeded
                    reported_count = delivery_counts.get(entry_id, 1)
                    first_seen_count = first_seen_counts.setdefault(entry_id, reported_count)
                    msg_delivery_count = max(
                        reported_count,
                        first_seen_count + failures_this_run.get(entry_id, 0),
                    )
                    if msg_delivery_count > self._max_retries:
                        await self._dead_letter_message(
                            entry_id, delivery.fields, msg_delivery_count
                        )
                        CONSUMER_MESSAGES_DEAD_LETTERED.labels(consumer=self._group_name).inc()
                        continue

                    try:
                        await self.process_message(entry_id, delivery.fields)
                        if not self.deferred_ack:
                            await self._ack(entry_id)
                        processed_this_run.add(entry_id)
                        CONSUMER_MESSAGES_PROCESSED.labels(consumer=self._group_name).inc()
                    except Exception:
                        failures_this_run[entry_id] = failures_this_run.get(entry_id, 0) + 1
                        failed_in_sweep = True
                        CONSUMER_MESSAGE_ERRORS.labels(consumer=self._group_name).inc()
                        log.exception(
                            "pending_message_processing_failed",
                            entry_id=entry_id,
                            group=self._group_name,
                            delivery_count=msg_delivery_count,
                        )

            if not failed_in_sweep:
                break

    # -- Main loop ---------------------------------------------------------

    async def run(self) -> None:
        """Main consumer loop.

        Drains this consumer's pending items, then reads new items,
        dispatching each to ``process_message`` and acknowledging on
        success. Loops until ``stop()`` is called.
        """
        await self.ensure_group()
        log.info(
            "consumer_started",
            group=self._group_name,
            consumer=self._consumer_name,
            stream=self._source_name,
        )

        # H4: Claim orphaned items from crashed consumers before the pending drain
        await self._claim_orphaned_messages()

        # Drain pending items (PEL recovery) before reading new ones
        await self._drain_pending()

        log.info("pending_drain_completed", group=self._group_name)

        # Main loop — new items
        loop_iteration = 0
        while not self._stopped:
            deliveries = await self._subscription.read_new(self._batch_size, self._block_timeout_ms)

            loop_iteration += 1
            if loop_iteration % self._LAG_METRIC_INTERVAL == 0:
                await self._update_lag_metric()

            for delivery in deliveries:
                entry_id = delivery.position
                try:
                    await self.process_message(entry_id, delivery.fields)
                    if not self.deferred_ack:
                        await self._ack(entry_id)
                    CONSUMER_MESSAGES_PROCESSED.labels(consumer=self._group_name).inc()
                except Exception:
                    CONSUMER_MESSAGE_ERRORS.labels(consumer=self._group_name).inc()
                    # Item stays pending for retry on next read cycle
                    log.exception(
                        "message_processing_failed",
                        entry_id=entry_id,
                        group=self._group_name,
                        consumer=self._consumer_name,
                    )

        await self.on_stop()
        log.info(
            "consumer_stopped",
            group=self._group_name,
            consumer=self._consumer_name,
        )

    @property
    def deferred_ack(self) -> bool:
        """Return True to defer acknowledgement until the subclass handles it.

        Batching consumers override this so the base loop does NOT ack
        after each ``process_message`` call.  Instead, the consumer
        acks items itself (via ``_ack``) after a successful flush.
        """
        return False

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a single delivered item. Override in subclasses."""
        raise NotImplementedError

    async def on_stop(self) -> None:
        """Cleanup hook called after the main loop exits.

        Subclasses can override to flush buffers, close resources, etc.
        """

    def stop(self) -> None:
        """Signal the consumer loop to stop gracefully."""
        self._stopped = True
