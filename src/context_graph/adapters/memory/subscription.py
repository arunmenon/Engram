"""In-memory implementation of the Subscription port (ADR-0019 step 3).

A consumer group over a ``MemoryStream``. Follows the Redis consumer
group behaviour the conformance suite pins: deliveries stay pending until
acknowledged, re-reads and claims increment delivery counts, dead letters
carry the same metadata fields as the Redis DLQ stream.

Source: ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.ports.subscription import Delivery

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.adapters.memory.stream import MemoryStream, StreamEntry


def _delivery(entry: StreamEntry) -> Delivery:
    return Delivery(position=entry.position, fields=dict(entry.fields))


class MemorySubscription:
    """Consumer group over an in-memory stream.

    Satisfies the ``context_graph.ports.subscription.Subscription`` protocol.
    """

    def __init__(
        self,
        stream: MemoryStream,
        group_name: str,
        consumer_name: str,
        *,
        claim_idle_ms: int = 300_000,
    ) -> None:
        self._stream = stream
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._claim_idle_s = claim_idle_ms / 1000.0

    @property
    def group_name(self) -> str:
        return self._group_name

    @property
    def consumer_name(self) -> str:
        return self._consumer_name

    @property
    def source_name(self) -> str:
        return self._stream.name

    @property
    def dead_letters(self) -> list[dict[str, str]]:
        """Dead-lettered items for this stream (all groups), oldest first."""
        return self._stream.dead_letters

    async def ensure_group(self) -> None:
        self._stream.create_group(self._group_name)

    async def claim_orphaned(self, should_stop: Callable[[], bool] | None = None) -> int:
        if should_stop is not None and should_stop():
            return 0
        return self._stream.claim_idle(self._group_name, self._consumer_name, self._claim_idle_s)

    async def delivery_counts(self, limit: int) -> dict[str, int]:
        group = self._stream.group(self._group_name)
        if group is None:
            return {}
        counts: dict[str, int] = {}
        for position, pending in group.pending.items():
            if pending.consumer == self._consumer_name:
                counts[position] = pending.delivery_count
                if len(counts) >= limit:
                    break
        return counts

    async def read_pending(self, count: int) -> list[Delivery]:
        entries = self._stream.read_pending(self._group_name, self._consumer_name, count)
        return [_delivery(e) for e in entries]

    async def read_new(self, count: int, block_ms: int) -> list[Delivery]:
        entries = self._stream.read_new(self._group_name, self._consumer_name, count)
        if not entries and block_ms > 0:
            await self._stream.wait_for_append(block_ms / 1000.0)
            entries = self._stream.read_new(self._group_name, self._consumer_name, count)
        return [_delivery(e) for e in entries]

    async def ack(self, *positions: str) -> None:
        self._stream.ack(self._group_name, positions)

    async def dead_letter(self, delivery: Delivery, delivery_count: int) -> None:
        self._stream.dead_letters.append(
            {
                "original_stream": self._stream.name,
                "original_entry_id": delivery.position,
                "group": self._group_name,
                "consumer": self._consumer_name,
                "delivery_count": str(delivery_count),
                **delivery.fields,
            }
        )
        self._stream.ack(self._group_name, (delivery.position,))

    async def lag(self) -> int | None:
        return self._stream.lag(self._group_name)
