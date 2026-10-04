"""In-memory append-only stream with consumer groups (ADR-0019 step 3).

Shared by ``MemoryEventLog`` (which appends) and ``MemorySubscription``
(which reads as a consumer group). Semantics follow Redis Streams
consumer groups, the reference backend:

- positions are ``<epoch-ms>-<sequence>`` strings, strictly increasing;
- a group starts at the beginning of the stream;
- a delivered item stays in the group's pending list until acknowledged;
- each delivery (new read, pending re-read or claim) increments the
  item's delivery count;
- pending items idle longer than a limit can be claimed by another consumer.

Single-process and not durable: for tests and the reference backend only.

Source: ADR-0019
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def position_sort_key(position: str) -> tuple[int, int]:
    """Order positions numerically: ``<ms>-<seq>``."""
    millis, _, sequence = position.partition("-")
    return int(millis), int(sequence or 0)


@dataclass
class PendingEntry:
    """One delivered, unacknowledged item in a group's pending list."""

    consumer: str
    delivery_count: int
    last_delivered_at: float


@dataclass
class ConsumerGroup:
    """State of one consumer group."""

    name: str
    last_delivered: str = "0-0"
    pending: OrderedDict[str, PendingEntry] = field(default_factory=OrderedDict)


@dataclass
class StreamEntry:
    position: str
    fields: dict[str, str]
    appended_at_ms: int


class MemoryStream:
    """An append-only stream with Redis-like consumer groups."""

    def __init__(self, name: str, clock: Callable[[], float] = time.time) -> None:
        self.name = name
        self._clock = clock
        self._entries: list[StreamEntry] = []
        self._groups: dict[str, ConsumerGroup] = {}
        self._last_position = "0-0"
        self._appended = asyncio.Condition()
        self.dead_letters: list[dict[str, str]] = []

    # -- appends ------------------------------------------------------------

    def _next_position(self) -> str:
        now_ms = int(self._clock() * 1000)
        last_ms, last_seq = position_sort_key(self._last_position)
        position = f"{last_ms}-{last_seq + 1}" if now_ms <= last_ms else f"{now_ms}-0"
        self._last_position = position
        return position

    async def append(self, fields: dict[str, str]) -> str:
        """Append an item and wake blocked readers. Returns its position."""
        position = self._next_position()
        appended_at_ms = position_sort_key(position)[0]
        self._entries.append(StreamEntry(position, dict(fields), appended_at_ms))
        async with self._appended:
            self._appended.notify_all()
        return position

    def __len__(self) -> int:
        return len(self._entries)

    def entries(self) -> list[StreamEntry]:
        return list(self._entries)

    def trim_before(self, min_position: str) -> int:
        """Drop entries with position < ``min_position``. Returns the number dropped."""
        min_key = position_sort_key(min_position)
        kept = [e for e in self._entries if position_sort_key(e.position) >= min_key]
        dropped = len(self._entries) - len(kept)
        self._entries = kept
        return dropped

    # -- groups -------------------------------------------------------------

    def group(self, name: str) -> ConsumerGroup | None:
        return self._groups.get(name)

    def create_group(self, name: str) -> bool:
        """Create a group reading from the start. Returns False if it exists."""
        if name in self._groups:
            return False
        self._groups[name] = ConsumerGroup(name=name)
        return True

    def group_progress(self, name: str) -> str | None:
        """Oldest pending position for a group, else its last delivered position."""
        group = self._groups.get(name)
        if group is None:
            return None
        if group.pending:
            return min(group.pending, key=position_sort_key)
        return group.last_delivered

    def read_new(self, group_name: str, consumer: str, count: int) -> list[StreamEntry]:
        group = self._groups[group_name]
        last_key = position_sort_key(group.last_delivered)
        delivered = [e for e in self._entries if position_sort_key(e.position) > last_key][:count]
        now = self._clock()
        for entry in delivered:
            group.pending[entry.position] = PendingEntry(consumer, 1, now)
            group.last_delivered = entry.position
        return delivered

    async def wait_for_append(self, timeout_s: float) -> None:
        """Wait until something is appended or the timeout passes."""
        if timeout_s <= 0:
            return
        async with self._appended:
            try:
                await asyncio.wait_for(self._appended.wait(), timeout=timeout_s)
            except TimeoutError:
                return

    def read_pending(
        self, group_name: str, consumer: str, count: int, *, after: str | None = None
    ) -> list[StreamEntry]:
        """This consumer's pending entries in log order, after ``after`` when given."""
        group = self._groups[group_name]
        by_position = {e.position: e for e in self._entries}
        delivered: list[StreamEntry] = []
        now = self._clock()
        floor = position_sort_key(after) if after else None
        for position in sorted(group.pending, key=position_sort_key):
            pending = group.pending[position]
            if pending.consumer != consumer or position not in by_position:
                continue
            if floor is not None and position_sort_key(position) <= floor:
                continue
            pending.delivery_count += 1
            pending.last_delivered_at = now
            delivered.append(by_position[position])
            if len(delivered) >= count:
                break
        return delivered

    def claim_idle(self, group_name: str, consumer: str, min_idle_s: float) -> int:
        group = self._groups[group_name]
        now = self._clock()
        claimed = 0
        for pending in group.pending.values():
            if now - pending.last_delivered_at >= min_idle_s:
                pending.consumer = consumer
                pending.delivery_count += 1
                pending.last_delivered_at = now
                claimed += 1
        return claimed

    def ack(self, group_name: str, positions: tuple[str, ...]) -> int:
        group = self._groups[group_name]
        removed = 0
        for position in positions:
            if group.pending.pop(position, None) is not None:
                removed += 1
        return removed

    def lag(self, group_name: str) -> int | None:
        group = self._groups.get(group_name)
        if group is None:
            return None
        last_key = position_sort_key(group.last_delivered)
        return sum(1 for e in self._entries if position_sort_key(e.position) > last_key)
