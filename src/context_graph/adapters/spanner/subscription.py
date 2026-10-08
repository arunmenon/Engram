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
import json
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

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
from context_graph.adapters.spanner.tenant_control import tenant_snapshot
from context_graph.domain.event_acceptance import (
    EventAcceptance,
    EventInterpretation,
    EventInterpretationError,
    validate_accepted_document,
)
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.subscription import Delivery

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.adapters.spanner.tenant_control import TenantFence

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
        tenant_fence: TenantFence | None = None,
        tenant_read_operation: str = "read",
        tenant_engine_revision: str | None = None,
    ) -> None:
        self._database = database
        self._tenant_fence = tenant_fence
        self._interpretation = None
        if tenant_read_operation not in ("read", "processing"):
            raise ValueError("Unknown tenant read operation")
        self._tenant_read_operation: Literal["read", "processing"] = (
            "processing" if tenant_read_operation == "processing" else "read"
        )
        if tenant_fence is not None:
            tenant_fence.check_database(database)
            if not tenant_engine_revision:
                raise ValueError("Bound subscription requires a pinned engine revision")
            self._interpretation = EventInterpretation(
                tenant_fence.tenant_id,
                tenant_fence.database_resource,
                tenant_fence.binding_id,
                tenant_fence.epoch,
                tenant_fence.bundle_digest,
                tenant_engine_revision,
            )
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
        if self._tenant_fence is not None:
            return await asyncio.to_thread(
                self._tenant_fence.run, self._database, fn, operation="processing"
            )
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
            with tenant_snapshot(
                self._database, self._tenant_fence, operation=self._tenant_read_operation
            ) as snapshot:
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

    def _terminal_pending(self, transaction: Any, position: str) -> Any:
        """Validate present pending content in the same transaction as disposition."""
        from google.cloud.spanner_v1 import KeySet

        assert self._interpretation is not None
        event_id = event_id_of(position)
        pending = list(
            transaction.read(
                "ConsumerDeliveries",
                ["consumer", "commit_ts", "batch_index", "delivery_count"],
                KeySet(keys=[[self._group_name, event_id]]),
            )
        )
        if not pending:
            return None
        consumer, timestamp, batch, count = pending[0]
        if (
            consumer != self._consumer_name
            or format_position(timestamp, batch, event_id) != position
        ):
            raise RuntimeFencedError("Delivery position or consumer is no longer authorized")
        rows = list(
            transaction.read(
                "Events",
                ["document", "acceptance", "commit_ts", "batch_index"],
                KeySet(keys=[[event_id]]),
            )
        )
        if not rows:
            raise RuntimeFencedError("Pending event content is unavailable")
        document, receipt, timestamp, batch = rows[0]
        if format_position(timestamp, batch, event_id) != position:
            raise RuntimeFencedError("Pending event position differs from its ledger entry")
        try:
            event, accepted = validate_accepted_document(
                self._interpretation, event_id, json_value(document), json_value(receipt)
            )
        except (EventInterpretationError, TypeError, ValueError) as exc:
            raise RuntimeFencedError("Pending event interpretation is not authorized") from exc
        return event, accepted, count

    def _repeat_dead_letter(self, transaction: Any, event_id: str, position: str) -> None:
        """Absent pending can only repeat a matching committed disposition."""
        from google.cloud.spanner_v1 import KeySet

        assert self._interpretation is not None
        rows = list(
            transaction.read(
                "ConsumerDeadLetters", ["fields"], KeySet(keys=[[self._group_name, event_id]])
            )
        )
        if not rows:
            raise RuntimeFencedError("No authorized pending or completed disposition")
        try:
            fields = json_value(rows[0][0])
            accepted = EventAcceptance.model_validate(json.loads(fields["acceptance"]))
            accepted.require_interpretation(self._interpretation)
            identity = (
                fields["original_entry_id"],
                fields["event_id"],
                fields["group"],
                fields["consumer"],
                fields["original_stream"],
                fields["binding_id"],
                fields["tenant_id"],
                fields["database_resource"],
                fields["bundle_digest"],
                fields["engine_revision"],
            )
            expected = (
                position,
                event_id,
                self._group_name,
                self._consumer_name,
                self.source_name,
                self._interpretation.binding_id,
                self._interpretation.tenant_id,
                self._interpretation.database_resource,
                self._interpretation.bundle_digest,
                self._interpretation.engine_revision,
            )
            if (
                identity != expected
                or not 1 <= int(fields["disposition_epoch"]) <= self._interpretation.epoch
            ):
                raise ValueError("Disposition identity mismatch")
        except (ValueError, TypeError, KeyError) as exc:
            raise RuntimeFencedError(
                "Completed disposition does not match current authority"
            ) from exc

    async def ack(self, *positions: str) -> None:
        from google.cloud.spanner_v1 import KeySet

        if not positions:
            return
        keys = KeySet(keys=[[self._group_name, event_id_of(p)] for p in positions])

        def work(transaction: Any) -> None:
            if self._interpretation is not None:
                unique: dict[str, str] = {}
                for position in positions:
                    event_id = event_id_of(position)
                    if event_id in unique and unique[event_id] != position:
                        raise RuntimeFencedError("Contradictory positions for one event")
                    unique[event_id] = position
                # Validate the entire batch before recording any deletion.
                for position in unique.values():
                    self._terminal_pending(transaction, position)
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
            actual_fields = fields
            if self._interpretation is not None:
                if delivery.fields.get("event_id", event_id) != event_id:
                    raise RuntimeFencedError("Delivery fields conflict with its position")
                pending = self._terminal_pending(transaction, delivery.position)
                if pending is None:
                    self._repeat_dead_letter(transaction, event_id, delivery.position)
                    return
                if type(delivery_count) is not int or delivery_count < 1:
                    raise RuntimeFencedError("Invalid disposition delivery count")
                event, accepted, stored_count = pending
                authority = self._interpretation
                actual_fields = {
                    "original_stream": self.source_name,
                    "original_entry_id": delivery.position,
                    "group": self._group_name,
                    "consumer": self._consumer_name,
                    "event_id": event_id,
                    "event_type": event.event_type,
                    "delivery_count": str(max(delivery_count, stored_count)),
                    "acceptance": accepted.model_dump_json(),
                    "tenant_id": authority.tenant_id,
                    "database_resource": authority.database_resource,
                    "binding_id": authority.binding_id,
                    "bundle_digest": authority.bundle_digest,
                    "engine_revision": authority.engine_revision,
                    "disposition_epoch": str(authority.epoch),
                }
            transaction.insert_or_update(
                "ConsumerDeadLetters",
                ["group_name", "event_id", "dead_lettered_at", "fields"],
                [[self._group_name, event_id, datetime.now(UTC), json_param(actual_fields)]],
            )
            transaction.delete("ConsumerDeliveries", KeySet(keys=[[self._group_name, event_id]]))

        await self._transact(work)

    async def dead_letters(self) -> list[dict[str, str]]:
        """Dead-lettered items for this group, oldest first."""
        params, types = self._params()

        def query() -> list[list[Any]]:
            with tenant_snapshot(
                self._database, self._tenant_fence, operation=self._tenant_read_operation
            ) as snapshot:
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
            with tenant_snapshot(
                self._database, self._tenant_fence, operation=self._tenant_read_operation
            ) as snapshot:
                return [
                    list(row)
                    for row in snapshot.execute_sql(
                        f"SELECT COUNT(*) {_UNDELIVERED}", params=params, param_types=types
                    )
                ]

        try:
            rows = await asyncio.to_thread(query)
        except RuntimeFencedError:
            raise
        except Exception:  # noqa: BLE001
            return None  # Non-critical metric, as in the Redis adapter
        return int(rows[0][0])
