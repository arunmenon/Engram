"""Subscription port interface.

A subscription is a named consumer group reading the event log. The
contract (ADR-0019 §1):

- A delivery carries the event's log ``position`` and the fields the log
  published with it (at minimum ``event_id``). Workers fetch event bodies
  through the ``EventLog`` port, never from the subscription.
- Delivery is at least once. An item stays pending until acknowledged.
- Order is preserved within a session; there is no order across sessions.
- Items pending longer than the backend's idle limit may be claimed by
  another consumer of the same group.
- Items delivered more than the retry limit are moved to a dead-letter
  destination and acknowledged.

Uses typing.Protocol for structural subtyping (not ABCs).

Source: ADR-0005, ADR-0019
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Delivery:
    """One item delivered to a consumer.

    ``position`` is an opaque string: the backend's log position for the
    item. ``fields`` are the decoded fields published with the item.
    """

    position: str
    fields: dict[str, str] = field(default_factory=dict)


class Subscription(Protocol):
    """Protocol for a consumer group over the event log."""

    @property
    def group_name(self) -> str:
        """The consumer group this subscription reads as."""
        ...

    @property
    def consumer_name(self) -> str:
        """This consumer's name within the group."""
        ...

    @property
    def source_name(self) -> str:
        """The log (or stream) the group reads, for logging only."""
        ...

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not exist. Idempotent."""
        ...

    async def claim_orphaned(self, should_stop: Callable[[], bool] | None = None) -> int:
        """Claim items left pending by crashed consumers of this group.

        Stops early when ``should_stop`` returns True. Returns the number
        of items claimed.
        """
        ...

    async def delivery_counts(self, limit: int) -> dict[str, int]:
        """Return ``{position: times_delivered}`` for this consumer's pending items."""
        ...

    async def read_pending(self, count: int) -> list[Delivery]:
        """Re-read items already delivered to this consumer but not acknowledged."""
        ...

    async def read_new(self, count: int, block_ms: int) -> list[Delivery]:
        """Read items never delivered to this group, waiting up to ``block_ms``."""
        ...

    async def ack(self, *positions: str) -> None:
        """Acknowledge items so they are not delivered again."""
        ...

    async def dead_letter(self, delivery: Delivery, delivery_count: int) -> None:
        """Move a permanently failing item to the dead-letter destination and acknowledge it."""
        ...

    async def lag(self) -> int | None:
        """Return how many items the group has yet to read, or None if unknown."""
        ...
