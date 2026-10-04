"""Subscription conformance suite (ADR-0019 §1 delivery contract, §5).

Pins: delivery in log order, at-least-once (unacknowledged items are
delivered again, also to a restarted consumer), independent groups, no
double delivery within a group, claiming idle items, delivery counts,
dead-lettering with metadata, lag, and blocking reads.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_graph.ports.subscription import Delivery
    from tests.conformance.conftest import SubscriptionHarness


async def _publish(harness: SubscriptionHarness, count: int) -> list[str]:
    return [await harness.publish({"event_id": f"e{i}"}) for i in range(count)]


def _ids(deliveries: list[Delivery]) -> list[str]:
    return [d.fields["event_id"] for d in deliveries]


class TestDelivery:
    async def test_ensure_group_is_idempotent(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        await subscription.ensure_group()

    async def test_new_items_arrive_in_log_order(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        positions = await _publish(subscription_harness, 3)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()

        first = await subscription.read_new(2, 0)
        second = await subscription.read_new(10, 0)

        assert _ids(first) == ["e0", "e1"]
        assert [d.position for d in first + second] == positions
        assert _ids(second) == ["e2"]
        assert await subscription.read_new(10, 0) == []

    async def test_group_starts_at_the_beginning(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 2)
        subscription = subscription_harness.open("late-group", "c1")
        await subscription.ensure_group()
        assert _ids(await subscription.read_new(10, 0)) == ["e0", "e1"]

    async def test_groups_are_independent(self, subscription_harness: SubscriptionHarness) -> None:
        await _publish(subscription_harness, 2)
        projection = subscription_harness.open("projection", "c1")
        enrichment = subscription_harness.open("enrichment", "c1")
        await projection.ensure_group()
        await enrichment.ensure_group()

        assert _ids(await projection.read_new(10, 0)) == ["e0", "e1"]
        assert _ids(await enrichment.read_new(10, 0)) == ["e0", "e1"]

    async def test_consumers_in_a_group_share_items(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 3)
        first = subscription_harness.open("g", "c1")
        second = subscription_harness.open("g", "c2")
        await first.ensure_group()

        taken = _ids(await first.read_new(2, 0)) + _ids(await second.read_new(10, 0))
        assert sorted(taken) == ["e0", "e1", "e2"]

    async def test_blocking_read_wakes_on_publish(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()

        async def publish_later() -> None:
            await asyncio.sleep(0.05)
            await subscription_harness.publish({"event_id": "late"})

        publisher = asyncio.create_task(publish_later())
        delivered = await subscription.read_new(1, 2000)
        await publisher
        assert _ids(delivered) == ["late"]


class TestAtLeastOnce:
    async def test_unacked_items_are_redelivered(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 2)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        delivered = await subscription.read_new(10, 0)
        await subscription.ack(delivered[0].position)

        assert _ids(await subscription.read_pending(10)) == ["e1"]

    async def test_restarted_consumer_sees_its_pending_items(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 1)
        before_crash = subscription_harness.open("g", "c1")
        await before_crash.ensure_group()
        await before_crash.read_new(10, 0)

        after_restart = subscription_harness.open("g", "c1")
        assert _ids(await after_restart.read_pending(10)) == ["e0"]

    async def test_acked_items_are_not_redelivered(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 2)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        delivered = await subscription.read_new(10, 0)
        await subscription.ack(*(d.position for d in delivered))

        assert await subscription.read_pending(10) == []
        assert await subscription.delivery_counts(limit=100) == {}

    async def test_delivery_counts_grow_with_redelivery(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        (position,) = await _publish(subscription_harness, 1)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        await subscription.read_new(10, 0)
        assert (await subscription.delivery_counts(limit=100))[position] == 1

        await subscription.read_pending(10)
        await subscription.read_pending(10)
        assert (await subscription.delivery_counts(limit=100))[position] == 3

    async def test_pending_pages_with_a_cursor(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        """``after`` skips past items already read, so a failing one cannot block the rest."""
        await _publish(subscription_harness, 4)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        delivered = await subscription.read_new(10, 0)
        await subscription.ack(delivered[2].position)

        first = await subscription.read_pending(1)
        rest = await subscription.read_pending(10, after=first[-1].position)

        assert _ids(first) == ["e0"]
        assert _ids(rest) == ["e1", "e3"]
        assert await subscription.read_pending(10, after=rest[-1].position) == []
        assert _ids(await subscription.read_pending(10)) == ["e0", "e1", "e3"]


class TestRecovery:
    async def test_idle_items_can_be_claimed(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 2)
        crashed = subscription_harness.open("g", "crashed")
        await crashed.ensure_group()
        await crashed.read_new(10, 0)

        rescuer = subscription_harness.open("g", "rescuer", claim_idle_ms=0)
        assert await rescuer.claim_orphaned() == 2
        assert _ids(await rescuer.read_pending(10)) == ["e0", "e1"]
        assert await crashed.read_pending(10) == []

    async def test_busy_items_are_not_claimed(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 1)
        owner = subscription_harness.open("g", "owner")
        await owner.ensure_group()
        await owner.read_new(10, 0)

        other = subscription_harness.open("g", "other", claim_idle_ms=60_000)
        assert await other.claim_orphaned() == 0

    async def test_claim_stops_when_asked(self, subscription_harness: SubscriptionHarness) -> None:
        await _publish(subscription_harness, 1)
        owner = subscription_harness.open("g", "owner")
        await owner.ensure_group()
        await owner.read_new(10, 0)
        rescuer = subscription_harness.open("g", "rescuer", claim_idle_ms=0)
        assert await rescuer.claim_orphaned(should_stop=lambda: True) == 0

    async def test_dead_letter_records_and_acks(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        (position,) = await _publish(subscription_harness, 1)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        (delivery,) = await subscription.read_new(10, 0)

        await subscription.dead_letter(delivery, delivery_count=6)

        assert await subscription.read_pending(10) == []
        (letter,) = await subscription_harness.dead_letters()
        assert letter["original_entry_id"] == position
        assert letter["group"] == "g"
        assert letter["consumer"] == "c1"
        assert letter["delivery_count"] == "6"
        assert letter["event_id"] == "e0"
        assert letter["original_stream"]


class TestLag:
    async def test_lag_counts_undelivered_items(
        self, subscription_harness: SubscriptionHarness
    ) -> None:
        await _publish(subscription_harness, 3)
        subscription = subscription_harness.open("g", "c1")
        await subscription.ensure_group()
        assert await subscription.lag() == 3

        await subscription.read_new(2, 0)
        assert await subscription.lag() == 1
