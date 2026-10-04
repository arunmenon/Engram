"""Spanner implementation of the Subscription port (ADR-0019 step 4).

Consumer groups over the ``Events`` ledger, by polling (design brief D2,
G3, G4):

- ``ConsumerCursors``: per group and shard, the last position delivered
  (the Redis group's last-delivered id, kept per shard);
- ``ConsumerDeliveries``: delivered, unacknowledged items with consumer,
  delivery count and last delivery time (the Redis pending entries list);
- ``ConsumerDeadLetters``: dead-lettered items with the same metadata the
  Redis DLQ stream carries.

Each read runs in a read-write transaction. Spanner's serializable
transactions lock the ranges they read, so a producer either committed
before the read (and is seen) or commits after it with a later commit
timestamp: a cursor never skips an event. This gives the guarantee the
brief's D2 sought from strong reads at a returned timestamp, without a
separate checkpoint step. Order is total by position, so it holds within
every session, which is what the port promises.

Source: ADR-0005, ADR-0019, spanner-design-brief.md D2/D3/G3/G4
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.spanner.errors import translate_spanner_error
from context_graph.adapters.spanner.log import (
    POSITION_COLUMNS,
    after_position,
    event_id_of,
    format_position,
    json_param,
    json_value,
)
from context_graph.adapters.spanner.schema import CURSOR_FLOOR_TIMESTAMP
from context_graph.ports.subscription import Delivery

if TYPE_CHECKING:
    from collections.abc import Callable

# Events after the group's cursor in their shard, oldest first
_UNDELIVERED = (
    "FROM Events e JOIN ConsumerCursors c ON c.group_name = @group AND c.shard = e.shard "
    "WHERE e.in_log AND (e.commit_ts > c.commit_ts OR (e.commit_ts = c.commit_ts "
    "AND (e.batch_index > c.batch_index OR (e.batch_index = c.batch_index "
    "AND e.event_id > c.event_id))))"
)


@translate_errors(translate_spanner_error)
class SpannerSubscription:
    """Consumer group over the Spanner event ledger.

    Satisfies the ``context_graph.ports.subscription.Subscription`` protocol.
    """

    def __init__(
        self,
        database: Any,
        group_name: str,
        consumer_name: str,
        *,
        shards: int = 16,
        claim_idle_ms: int = 300_000,
        poll_interval_ms: int = 50,
    ) -> None:
        self._database = database
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._shards = shards
        self._claim_idle = timedelta(milliseconds=claim_idle_ms)
        self._poll_interval_s = poll_interval_ms / 1000.0

    @property
    def group_name(self) -> str:
        return self._group_name

    @property
    def consumer_name(self) -> str:
        return self._consumer_name

    @property
    def source_name(self) -> str:
        return "Events"

    def _params(self, **extra: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        from google.cloud.spanner_v1 import param_types

        params: dict[str, Any] = {"group": self._group_name, "consumer": self._consumer_name}
        types: dict[str, Any] = {"group": param_types.STRING, "consumer": param_types.STRING}
        for name, (value, value_type) in extra.items():
            params[name] = value
            types[name] = value_type
        return params, types

    async def _transact(self, fn: Callable[[Any], Any]) -> Any:
        return await asyncio.to_thread(self._database.run_in_transaction, fn)

    # -- group lifecycle --------------------------------------------------

    async def ensure_group(self) -> None:
        from google.cloud.spanner_v1 import KeySet

        floor = datetime.fromisoformat(CURSOR_FLOOR_TIMESTAMP.replace("Z", "+00:00"))

        def work(transaction: Any) -> None:
            exists = list(
                transaction.read(
                    "ConsumerGroups", ["group_name"], KeySet(keys=[[self._group_name]])
                )
            )
            if exists:
                return
            transaction.insert(
                "ConsumerGroups",
                ["group_name", "created_at"],
                [[self._group_name, datetime.now(UTC)]],
            )
            transaction.insert(
                "ConsumerCursors",
                ["group_name", "shard", "commit_ts", "batch_index", "event_id"],
                [[self._group_name, shard, floor, -1, ""] for shard in range(self._shards)],
            )

        await self._transact(work)

    # -- reads -------------------------------------------------------------

    def _read_new_sync(self, transaction: Any, count: int) -> list[Delivery]:
        from google.cloud.spanner_v1 import param_types

        params, types = self._params(limit=(count, param_types.INT64))
        rows = list(
            transaction.execute_sql(
                f"SELECT e.event_id, e.shard, e.commit_ts, e.batch_index {_UNDELIVERED} "
                "ORDER BY e.commit_ts, e.batch_index, e.event_id LIMIT @limit",
                params=params,
                param_types=types,
            )
        )
        if not rows:
            return []
        now = datetime.now(UTC)
        transaction.insert_or_update(
            "ConsumerDeliveries",
            [
                "group_name",
                "event_id",
                "consumer",
                "delivery_count",
                "last_delivered_at",
                "commit_ts",
                "batch_index",
            ],
            [
                [self._group_name, event_id, self._consumer_name, 1, now, commit_ts, batch]
                for event_id, _shard, commit_ts, batch in rows
            ],
        )
        newest_per_shard: dict[int, list[Any]] = {}
        for event_id, shard, commit_ts, batch in rows:
            newest_per_shard[shard] = [self._group_name, shard, commit_ts, batch, event_id]
        transaction.update(
            "ConsumerCursors",
            ["group_name", "shard", "commit_ts", "batch_index", "event_id"],
            list(newest_per_shard.values()),
        )
        return [
            Delivery(position=format_position(ts, batch, event_id), fields={"event_id": event_id})
            for event_id, _shard, ts, batch in rows
        ]

    async def read_new(self, count: int, block_ms: int) -> list[Delivery]:
        deadline = time.monotonic() + max(block_ms, 0) / 1000.0
        while True:
            deliveries: list[Delivery] = await self._transact(
                lambda transaction: self._read_new_sync(transaction, count)
            )
            if deliveries or time.monotonic() >= deadline:
                return deliveries
            await asyncio.sleep(min(self._poll_interval_s, max(deadline - time.monotonic(), 0)))

    async def read_pending(self, count: int, *, after: str | None = None) -> list[Delivery]:
        from google.cloud.spanner_v1 import param_types

        params, types = self._params(limit=(count, param_types.INT64))
        after_clause = ""
        if after:
            clause, after_params, after_types = after_position(after)
            after_clause = f"AND {clause} "
            params.update(after_params)
            types.update(after_types)

        def work(transaction: Any) -> list[Delivery]:
            rows = list(
                transaction.execute_sql(
                    "SELECT event_id, commit_ts, batch_index, delivery_count "
                    "FROM ConsumerDeliveries@{FORCE_INDEX=ConsumerDeliveriesByConsumer} "
                    f"WHERE group_name = @group AND consumer = @consumer {after_clause}"
                    f"ORDER BY {POSITION_COLUMNS} LIMIT @limit",
                    params=params,
                    param_types=types,
                )
            )
            if not rows:
                return []
            now = datetime.now(UTC)
            transaction.update(
                "ConsumerDeliveries",
                ["group_name", "event_id", "delivery_count", "last_delivered_at"],
                [[self._group_name, eid, count + 1, now] for eid, _ts, _b, count in rows],
            )
            return [
                Delivery(position=format_position(ts, batch, eid), fields={"event_id": eid})
                for eid, ts, batch, _count in rows
            ]

        deliveries: list[Delivery] = await self._transact(work)
        return deliveries

    async def delivery_counts(self, limit: int) -> dict[str, int]:
        from google.cloud.spanner_v1 import param_types

        params, types = self._params(limit=(limit, param_types.INT64))

        def query() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [
                    list(row)
                    for row in snapshot.execute_sql(
                        "SELECT event_id, commit_ts, batch_index, delivery_count "
                        "FROM ConsumerDeliveries WHERE group_name = @group "
                        f"AND consumer = @consumer ORDER BY {POSITION_COLUMNS} LIMIT @limit",
                        params=params,
                        param_types=types,
                    )
                ]

        rows = await asyncio.to_thread(query)
        return {format_position(ts, batch, eid): count for eid, ts, batch, count in rows}

    # -- acknowledgement, recovery, dead letters ---------------------------

    async def ack(self, *positions: str) -> None:
        from google.cloud.spanner_v1 import KeySet

        if not positions:
            return
        keys = KeySet(keys=[[self._group_name, event_id_of(p)] for p in positions])

        def work(transaction: Any) -> None:
            transaction.delete("ConsumerDeliveries", keys)

        await self._transact(work)

    async def claim_orphaned(self, should_stop: Callable[[], bool] | None = None) -> int:
        from google.cloud.spanner_v1 import param_types

        if should_stop is not None and should_stop():
            return 0
        now = datetime.now(UTC)
        params, types = self._params(
            now=(now, param_types.TIMESTAMP),
            idle_before=(now - self._claim_idle, param_types.TIMESTAMP),
        )

        def work(transaction: Any) -> int:
            claimed: int = transaction.execute_update(
                "UPDATE ConsumerDeliveries SET consumer = @consumer, "
                "delivery_count = delivery_count + 1, last_delivered_at = @now "
                "WHERE group_name = @group AND last_delivered_at <= @idle_before",
                params=params,
                param_types=types,
            )
            return claimed

        claimed: int = await self._transact(work)
        return claimed

    async def dead_letter(self, delivery: Delivery, delivery_count: int) -> None:
        from google.cloud.spanner_v1 import KeySet

        event_id = event_id_of(delivery.position)
        fields = {
            "original_stream": self.source_name,
            "original_entry_id": delivery.position,
            "group": self._group_name,
            "consumer": self._consumer_name,
            "delivery_count": str(delivery_count),
            **delivery.fields,
        }

        def work(transaction: Any) -> None:
            transaction.insert_or_update(
                "ConsumerDeadLetters",
                ["group_name", "event_id", "dead_lettered_at", "fields"],
                [[self._group_name, event_id, datetime.now(UTC), json_param(fields)]],
            )
            transaction.delete("ConsumerDeliveries", KeySet(keys=[[self._group_name, event_id]]))

        await self._transact(work)

    async def dead_letters(self) -> list[dict[str, str]]:
        """Dead-lettered items for this group, oldest first."""
        params, types = self._params()

        def query() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [
                    list(row)
                    for row in snapshot.execute_sql(
                        "SELECT fields FROM ConsumerDeadLetters WHERE group_name = @group "
                        "ORDER BY dead_lettered_at",
                        params=params,
                        param_types=types,
                    )
                ]

        rows = await asyncio.to_thread(query)
        return [json_value(row[0]) for row in rows]

    async def lag(self) -> int | None:
        params, types = self._params()

        def query() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [
                    list(row)
                    for row in snapshot.execute_sql(
                        f"SELECT COUNT(*) {_UNDELIVERED}", params=params, param_types=types
                    )
                ]

        try:
            rows = await asyncio.to_thread(query)
        except Exception:  # noqa: BLE001
            return None  # Non-critical metric, as in the Redis adapter
        return int(rows[0][0])
