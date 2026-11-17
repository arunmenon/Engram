"""Spanner implementation of the EventLog port (ADR-0019 step 4).

Follows the Spanner design brief:

- D1: positions are ``<commit ts, UTC to nanoseconds>/<batch index>/<event id>``,
  fixed width; the old Redis id, when migrated, goes to ``legacy_position``;
- G2: append is one read-write transaction: read by ``event_id``; a live
  duplicate returns its position, otherwise the row is written with the
  commit timestamp and the position is built from the commit response;
- D3: rows carry ``shard = crc32(session_id) mod N`` for the sharded time
  index that subscriptions poll;
- G6: keyword search uses Spanner full-text search (``SEARCH``/``SCORE``)
  over the ``summary`` and ``keywords`` fields, as RediSearch did;
- G7: retention keeps the hot-window model. Redis keeps four structures
  (stream entry, JSON document, session stream, dedup record); here one
  row carries a flag for each (``in_log``, ``document``,
  ``in_session_index``, ``dedup_active``) and is deleted when all are gone.

The Google client is synchronous; calls run in worker threads so they do
not block the event loop (brief G12).

Source: ADR-0004, ADR-0010, ADR-0014, ADR-0019
"""

from __future__ import annotations

import asyncio
import copy
import json
import zlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import orjson
import structlog

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.spanner.commits import CommitBudget, event_row_cost
from context_graph.adapters.spanner.errors import translate_spanner_error
from context_graph.adapters.spanner.tenant_control import tenant_snapshot
from context_graph.domain.event_acceptance import (
    AdmissionContext,
    EventAcceptance,
    EventInterpretation,
    EventInterpretationError,
    stamp_acceptance,
    validate_accepted_document,
)
from context_graph.domain.keyword_search import event_search_text, query_terms
from context_graph.domain.models import Event
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.source_trust import AcceptedRecord, VerifiedSourceProvenance
from context_graph.ports.errors import ConflictError, InvalidRequestError, RuntimeFencedError
from context_graph.ports.event_log import ImportedEvent, LogEntry
from context_graph.ports.event_store import AppendOutcome
from context_graph.settings import KeywordSearchSettings

if TYPE_CHECKING:
    from context_graph.adapters.spanner.tenant_control import TenantFence
    from context_graph.domain.models import EventQuery
    from context_graph.ports.archive import ArchiveStore
    from context_graph.tenancy import TenantBinding

log = structlog.get_logger(__name__)

EVENT_COLUMNS = [
    "event_id",
    "shard",
    "commit_ts",
    "batch_index",
    "session_id",
    "occurred_at_ms",
    "session_tag",
    "agent_tag",
    "trace_tag",
    "event_type_tag",
    "tool_name_tag",
    "document",
    "in_log",
    "in_session_index",
    "dedup_active",
    "summary",
    "keywords",
    "legacy_position",
    "search_text",
    "acceptance",
]

LedgerEntry = tuple[str, str, dict[str, Any] | None, int, EventAcceptance | None]


# Columns that rebuild a position
POSITION_COLUMNS = "commit_ts, batch_index, event_id"


def shard_for(session_id: str, shards: int) -> int:
    """Stable shard for a session (design brief D3)."""
    return zlib.crc32(session_id.encode()) % shards


def format_position(commit_ts: datetime, batch_index: int, event_id: str) -> str:
    """Fixed-width position: sorts as a string in commit order (D1)."""
    nanos = getattr(commit_ts, "nanosecond", None)
    if nanos is None:
        nanos = commit_ts.microsecond * 1000
    utc = commit_ts.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{nanos:09d}Z/{batch_index:06d}/{event_id}"


def after_position(position: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """SQL condition, params and types for rows strictly after ``position``.

    For tables keyed by (commit_ts, batch_index, event_id) in log order.
    """
    from google.cloud.spanner_v1 import param_types

    timestamp, batch_index, event_id = position.split("/", 2)
    clause = (
        "(commit_ts > CAST(@after_ts AS TIMESTAMP) OR (commit_ts = CAST(@after_ts AS TIMESTAMP) "
        "AND (batch_index > @after_batch OR (batch_index = @after_batch "
        "AND event_id > @after_event_id))))"
    )
    params = {"after_ts": timestamp, "after_batch": int(batch_index), "after_event_id": event_id}
    types = {
        "after_ts": param_types.STRING,
        "after_batch": param_types.INT64,
        "after_event_id": param_types.STRING,
    }
    return clause, params, types


def event_id_of(position: str) -> str:
    """The event id a position names."""
    return position.rsplit("/", 1)[-1]


# New Spanner JSON cells hold every float as {"$float": "<repr>"}.
#
# Real Spanner refuses some JSON numbers as "cannot round-trip through string
# representation": about 1 in 1,000 ordinary decimals (-0.707176497086,
# 0.0928069675519494), whatever the digit count or notation, while the
# emulator accepts them all (trial of 2026-10-05,
# docs/review/2026-10-05-spanner-trial-results.md). A refused number fails
# the whole write: an event whose payload holds one, or a node with an
# embedding in its properties. Native JSON also normalizes integral floats
# and negative zero, which must remain distinct for json-v1 request identity.
# Tag every float; the decoder still reads legacy native numbers unchanged.
FLOAT_TAG = "$float"
OBJECT_TAG = "$engram_object"


def _encode_floats(value: Any) -> Any:
    if isinstance(value, float):
        return {FLOAT_TAG: repr(value)}
    if isinstance(value, dict):
        # A user object can look exactly like either codec marker. Store its
        # entries as pairs so object_hook sees the escape before the literal
        # marker, and does not decode the returned user object a second time.
        if len(value) == 1 and next(iter(value)) in (FLOAT_TAG, OBJECT_TAG):
            return {OBJECT_TAG: [[key, _encode_floats(item)] for key, item in value.items()]}
        return {key: _encode_floats(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_floats(item) for item in value]
    return value


def _decode_float(obj: dict[str, Any]) -> Any:
    if len(obj) == 1 and isinstance(obj.get(OBJECT_TAG), list):
        entries = obj[OBJECT_TAG]
        if all(
            isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str)
            for pair in entries
        ) and len({pair[0] for pair in entries}) == len(entries):
            return dict(entries)
    if len(obj) == 1 and isinstance(obj.get(FLOAT_TAG), str):
        try:
            return float(obj[FLOAT_TAG])
        except ValueError:
            # Older cells could contain literal nonnumeric markers. Numeric
            # legacy markers remain floats: their original intent is ambiguous.
            return obj
    return obj


def json_value(value: Any) -> Any:
    """Plain Python value from a Spanner JSON cell (JsonObject or str); floats decoded."""
    if value is None:
        return None
    serialize = getattr(value, "serialize", None)
    if serialize is not None:
        serialized = serialize()
        return json.loads(serialized, object_hook=_decode_float) if serialized is not None else None
    if isinstance(value, str):
        return json.loads(value, object_hook=_decode_float)
    return value


def json_param(value: Any) -> Any:
    """A JSON cell for ``value``, floats encoded (see ``FLOAT_TAG``)."""
    from google.cloud.spanner_v1.data_types import JsonObject

    return JsonObject(_encode_floats(value))


def _tag(value: Any) -> str | None:
    """RediSearch TAG fields match case-insensitively; store lowercased."""
    return str(value).lower() if value is not None else None


def _epoch_ms(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp() * 1000)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


@translate_errors(translate_spanner_error)
class SpannerEventLog:
    """EventLog over a Spanner database (``adapters.spanner.schema``).

    Satisfies ``EventLog``, ``EventStoreAdmin`` and ``HealthCheckable``.
    """

    def __init__(
        self,
        database: Any,
        *,
        shards: int = 16,
        keyword: KeywordSearchSettings | None = None,
        commit_budget: CommitBudget | None = None,
        retention_batch_rows: int = 1_000,
        tenant_fence: TenantFence | None = None,
        tenant_read_operation: str = "read",
        tenant_engine_revision: str | None = None,
        tenant_binding: TenantBinding | None = None,
    ) -> None:
        self._database = database
        self._tenant_fence = tenant_fence
        self._tenant_engine_revision = tenant_engine_revision
        self._admission_policy = None
        if tenant_binding is not None:
            from context_graph.adapters.spanner.tenant_control import TenantFence

            # Recompute the digest to detect mutation of nested registry values.
            checked_binding = replace(tenant_binding)
            if (
                tenant_fence != TenantFence.from_binding(checked_binding)
                or tenant_engine_revision != checked_binding.engine_revision
            ):
                raise RuntimeFencedError("Admission binding differs from ledger authority")
            self._admission_policy = compile_admission_policy(checked_binding.bundle)
        if tenant_read_operation not in ("read", "processing"):
            raise ValueError("Unknown tenant read operation")
        self._tenant_read_operation: Literal["read", "processing"] = (
            "read" if tenant_read_operation == "read" else "processing"
        )
        if tenant_fence is not None:
            tenant_fence.check_database(database)
        self._shards = shards
        self._keyword = keyword or KeywordSearchSettings()
        self._budget = commit_budget or CommitBudget()
        self._retention_rows = retention_batch_rows

    @property
    def requires_source_provenance(self) -> bool:
        return self._tenant_fence is not None

    @property
    def database(self) -> Any:
        """The Spanner database, shared with subscriptions by the registry."""
        return self._database

    @property
    def shards(self) -> int:
        return self._shards

    async def _run(self, fn: Any, *args: Any) -> Any:
        return await asyncio.to_thread(fn, *args)

    def _transact_sync(self, fn: Any, *, admission: bool = False) -> Any:
        if self._tenant_fence is not None:
            return self._tenant_fence.run(
                self._database, fn, operation="admission" if admission else "processing"
            )
        return self._database.run_in_transaction(fn)

    async def _query(
        self, sql: str, params: dict[str, Any] | None = None, types: dict[str, Any] | None = None
    ) -> list[list[Any]]:
        def query() -> list[list[Any]]:
            with tenant_snapshot(
                self._database, self._tenant_fence, operation=self._tenant_read_operation
            ) as snapshot:
                return [
                    list(row) for row in snapshot.execute_sql(sql, params=params, param_types=types)
                ]

        result: list[list[Any]] = await self._run(query)
        return result

    # -- lifecycle / admin --------------------------------------------------

    async def ensure_indexes(self) -> None:
        """Indexes are part of the schema (``adapters.spanner.schema``)."""

    async def health_ping(self) -> bool:
        try:
            await self._query("SELECT 1")
        except RuntimeFencedError:
            raise
        except Exception:  # noqa: BLE001
            return False
        return True

    async def stream_length(self) -> int:
        rows = await self._query("SELECT COUNT(*) FROM Events WHERE in_log")
        return int(rows[0][0])

    async def close(self) -> None:
        """The client owns no connection that needs closing per store."""

    # -- writes -------------------------------------------------------------

    def _row(
        self,
        event_id: str,
        session_id: str,
        batch_index: int,
        document: dict[str, Any] | None,
        occurred_at_ms: int,
        acceptance: EventAcceptance | None = None,
    ) -> list[Any]:
        from google.cloud import spanner

        doc = document or {}
        return [
            event_id,
            shard_for(session_id, self._shards),
            spanner.COMMIT_TIMESTAMP,
            batch_index,
            session_id,
            occurred_at_ms,
            _tag(session_id),
            _tag(doc.get("agent_id")),
            _tag(doc.get("trace_id")),
            _tag(doc.get("event_type")),
            _tag(doc.get("tool_name")),
            json_param(document) if document is not None else None,
            True,
            True,
            True,
            _text(doc.get("summary")),
            _text(doc.get("keywords")),
            doc.get("legacy_position"),
            _text(doc.get("search_text")),
            json_param(acceptance.model_dump()) if acceptance is not None else None,
        ]

    def _append_entries_sync(self, entries: list[LedgerEntry]) -> list[str]:
        """Append (event_id, session_id, document, occurred_at_ms); raise if any chunk fails."""
        positions = []
        for chunk in self._budget.chunks(
            entries,
            lambda entry: event_row_cost(entry[2], entry[4].model_dump() if entry[4] else None),
        ):
            outcomes = self._append_chunk_sync(chunk)
            if any(outcome.status == "conflict" for outcome in outcomes):
                raise ConflictError("Event ID conflicts with its original acceptance")
            if rejected := next((item for item in outcomes if item.status == "rejected"), None):
                raise InvalidRequestError(rejected.error or "Event admission rejected")
            positions += [outcome.position or "" for outcome in outcomes]
        return positions

    def _append_outcomes_sync(self, entries: list[LedgerEntry]) -> list[AppendOutcome]:
        """Append in commit-sized chunks, in order; each entry's outcome.

        Each chunk is one transaction, written whole or not at all. When the
        first chunk fails nothing is written and the error is raised. When a
        later one fails, the chunks before it stay written and every entry
        from the failed chunk on is ``failed``: sending them again is safe.
        """
        outcomes: list[AppendOutcome] = []
        chunks = self._budget.chunks(
            entries,
            lambda entry: event_row_cost(entry[2], entry[4].model_dump() if entry[4] else None),
        )
        for number, chunk in enumerate(chunks):
            try:
                outcomes += self._append_chunk_sync(chunk)
            except RuntimeFencedError:
                raise
            except Exception as exc:
                if number == 0:
                    raise
                log.warning("append_chunk_failed", written=len(outcomes), error=str(exc))
                error = f"not written: {exc}"
                return outcomes + [AppendOutcome("failed", error=error)] * (
                    len(entries) - len(outcomes)
                )
        return outcomes

    def _append_chunk_sync(self, entries: list[LedgerEntry]) -> list[AppendOutcome]:
        """Atomically write eligible new rows; preserve each input's outcome."""
        from google.cloud.spanner_v1 import KeySet

        holder: dict[str, Any] = {}

        def work(transaction: Any) -> list[tuple[str, int, bool] | str | AppendOutcome]:
            holder["transaction"] = transaction
            ids = sorted({entry[0] for entry in entries})
            existing: dict[str, tuple[str, EventAcceptance | None]] = {}
            columns = ["event_id", "commit_ts", "batch_index", "dedup_active", "acceptance"]
            for row in transaction.read("Events", columns, KeySet(keys=[[eid] for eid in ids])):
                event_id, commit_ts, batch_index, dedup_active, raw = row
                if self._tenant_fence is not None:
                    try:
                        accepted = EventAcceptance.model_validate(json_value(raw))
                    except ValueError as exc:
                        raise RuntimeFencedError(
                            "Existing event acceptance is missing or invalid"
                        ) from exc
                    # Existing identity survives document/dedup expiry until physical purge.
                    existing[event_id] = (
                        format_position(commit_ts, batch_index, event_id),
                        accepted,
                    )
                elif dedup_active:
                    existing[event_id] = (format_position(commit_ts, batch_index, event_id), None)
            results: list[tuple[str, int, bool] | str | AppendOutcome] = []
            written: dict[str, tuple[int, EventAcceptance | None]] = {}
            rows = []
            for event_id, session_id, document, occurred_at_ms, acceptance in entries:
                previous = existing.get(event_id)
                pending = written.get(event_id)
                original = previous[1] if previous else pending[1] if pending else None
                if self._tenant_fence is not None and (previous or pending):
                    if original is None or acceptance is None:
                        raise RuntimeFencedError("Bound append requires immutable acceptance")
                    if (original.tenant_id, original.database_resource, original.binding_id) != (
                        acceptance.tenant_id,
                        acceptance.database_resource,
                        acceptance.binding_id,
                    ):
                        raise RuntimeFencedError("Existing acceptance belongs to another binding")
                    if (original.source_id, original.request_digest) != (
                        acceptance.source_id,
                        acceptance.request_digest,
                    ):
                        results.append(
                            AppendOutcome(
                                "conflict", error="Event ID conflicts with its original acceptance"
                            )
                        )
                        continue
                    if original.accepted_epoch > acceptance.accepted_epoch:
                        raise RuntimeFencedError(
                            "Existing acceptance is newer than current authority"
                        )
                if previous:
                    results.append(previous[0])
                elif pending:
                    results.append((event_id, pending[0], False))
                else:
                    if self._tenant_fence is not None:
                        if self._admission_policy is None or document is None:
                            raise RuntimeFencedError("Bound event admission policy is unavailable")
                        decision = self._admission_policy.decide(
                            document["event_type"], document.get("payload")
                        )
                        if not decision.allowed:
                            results.append(
                                AppendOutcome(
                                    "rejected",
                                    error="Event does not satisfy its active pack contract",
                                    reason=decision.reason,
                                    problems=decision.problems,
                                )
                            )
                            continue
                    batch_index = len(written)
                    written[event_id] = (batch_index, acceptance)
                    rows.append(
                        self._row(
                            event_id, session_id, batch_index, document, occurred_at_ms, acceptance
                        )
                    )
                    results.append((event_id, batch_index, True))
            if rows:
                transaction.insert_or_update("Events", EVENT_COLUMNS, rows)
            return results

        results = self._transact_sync(work, admission=True)
        commit_ts = holder["transaction"].committed
        return [
            item
            if isinstance(item, AppendOutcome)
            else AppendOutcome("duplicate", item)
            if isinstance(item, str)
            else AppendOutcome(
                "created" if item[2] else "duplicate",
                format_position(commit_ts, item[1], item[0]),
            )
            for item in results
        ]

    def _acceptance(
        self, context: AdmissionContext | None, event: Event, payload: dict[str, Any] | None
    ) -> EventAcceptance | None:
        if self._tenant_fence is None:
            if context is not None:
                raise RuntimeFencedError("Unbound ledger cannot accept tenant authority")
            return None
        fence = self._tenant_fence
        if context is None or (
            context.tenant_id,
            context.database_resource,
            context.binding_id,
            context.accepted_epoch,
            context.bundle_digest,
            context.engine_revision,
        ) != (
            fence.tenant_id,
            fence.database_resource,
            fence.binding_id,
            fence.epoch,
            fence.bundle_digest,
            self._tenant_engine_revision,
        ):
            raise RuntimeFencedError("Authenticated admission authority does not match ledger")
        if self._admission_policy is None:
            raise RuntimeFencedError("Bound event admission policy is unavailable")
        return stamp_acceptance(context, event, payload)

    def _document(self, event: Event, payload: dict[str, Any] | None) -> dict[str, Any]:
        document: dict[str, Any] = orjson.loads(event.model_dump_json())
        if payload is not None:
            document["payload"] = payload
        search_text = event_search_text(event, payload, self._keyword.text_max_chars)
        if search_text:
            document["search_text"] = search_text
        return document

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
        *,
        admission_context: AdmissionContext | None = None,
    ) -> str:
        positions = await self.append_batch([event], [payload], admission_context=admission_context)
        return positions[0]

    def admission_writer(self, context: AdmissionContext) -> _AdmittedEventWriter:
        if self._admission_policy is None:
            raise RuntimeFencedError("Bound event admission policy is unavailable")
        return _AdmittedEventWriter(self, context)

    def _entry(
        self, event: Event, payload: dict[str, Any] | None, context: AdmissionContext | None
    ) -> LedgerEntry:
        # Freeze caller-owned values before crossing into the transaction thread.
        frozen_event = event.model_copy(deep=True)
        frozen_payload = copy.deepcopy(payload)
        acceptance = self._acceptance(context, frozen_event, frozen_payload)
        return (
            str(frozen_event.event_id),
            frozen_event.session_id,
            self._document(frozen_event, frozen_payload),
            _epoch_ms(frozen_event.occurred_at),
            acceptance,
        )

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
        *,
        admission_context: AdmissionContext | None = None,
    ) -> list[str]:
        if payloads is not None and len(payloads) != len(events):
            raise InvalidRequestError("Event and payload counts must match")
        entries = [
            self._entry(
                event,
                payloads[idx] if payloads and idx < len(payloads) else None,
                admission_context,
            )
            for idx, event in enumerate(events)
        ]
        positions: list[str] = await self._run(self._append_entries_sync, entries)
        return positions

    async def append_batch_outcomes(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
        *,
        admission_context: AdmissionContext | None = None,
    ) -> list[AppendOutcome]:
        """Fenced chunks with per-event admission, identity and storage outcomes."""
        if payloads is not None and len(payloads) != len(events):
            raise InvalidRequestError("Event and payload counts must match")
        entries = [
            self._entry(
                event,
                payloads[idx] if payloads and idx < len(payloads) else None,
                admission_context,
            )
            for idx, event in enumerate(events)
        ]
        outcomes: list[AppendOutcome] = await self._run(self._append_outcomes_sync, entries)
        return outcomes

    # -- migration (ADR-0019 §7, design brief phase 3) ------------------------

    async def append_imported(self, events: list[ImportedEvent]) -> list[str]:
        """Import copied events in order, in commit-sized transactions.

        ``batch_index`` keeps their order within a transaction and commit
        timestamps across them. A failed chunk raises; the chunks before it
        stay written, which the mirror's checkpoint (``last_legacy_position``)
        picks up from.
        """
        if self._tenant_fence is not None:
            raise RuntimeFencedError("Bound restore requires an explicit trusted-import contract")
        if not events:
            return []
        entries = []
        for imported in events:
            document = dict(imported.document)
            document.pop("global_position", None)
            document["legacy_position"] = imported.legacy_position
            occurred_at = datetime.fromisoformat(str(document["occurred_at"]))
            entries.append(
                (
                    str(document["event_id"]),
                    str(document["session_id"]),
                    document,
                    _epoch_ms(occurred_at),
                    None,
                )
            )
        positions: list[str] = await self._run(self._append_entries_sync, entries)
        return positions

    async def last_legacy_position(self) -> str | None:
        rows = await self._query(
            "SELECT legacy_position FROM Events WHERE legacy_position IS NOT NULL "
            "ORDER BY commit_ts DESC, batch_index DESC, event_id DESC LIMIT 1"
        )
        return str(rows[0][0]) if rows else None

    async def has_native_events(self) -> bool:
        rows = await self._query("SELECT 1 FROM Events WHERE legacy_position IS NULL LIMIT 1")
        return bool(rows)

    async def read_after(self, position: str | None, limit: int) -> list[LogEntry]:
        from google.cloud.spanner_v1 import param_types

        where = ["in_log"]
        params: dict[str, Any] = {"limit": limit}
        types: dict[str, Any] = {"limit": param_types.INT64}
        if position:
            clause, after_params, after_types = after_position(position)
            where.append(clause)
            params.update(after_params)
            types.update(after_types)
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS}, acceptance FROM Events "
            f"WHERE {' AND '.join(where)} "
            f"ORDER BY {POSITION_COLUMNS} LIMIT @limit",
            params,
            types,
        )
        return [
            LogEntry(
                position=format_position(ts, batch, eid),
                event_id=eid,
                document=self._public(doc, ts, batch, eid, acceptance),
                provenance=(
                    VerifiedSourceProvenance(
                        eid, EventAcceptance.model_validate(json_value(acceptance))
                    )
                    if self._tenant_fence is not None
                    else None
                ),
            )
            for doc, ts, batch, eid, acceptance in rows
        ]

    async def append_entry(self, event_id: str, session_id: str) -> str:
        """Append a bare log entry with no document (test support for subscriptions)."""
        if self._tenant_fence is not None:
            raise RuntimeFencedError("Bound ledger refuses bare unstamped entries")
        positions: list[str] = await self._run(
            self._append_entries_sync,
            [(event_id, session_id, None, _epoch_ms(datetime.now(UTC)), None)],
        )
        return positions[0]

    # -- reads --------------------------------------------------------------

    def _validated_document(self, document: Any, event_id: str, acceptance: Any) -> Any:
        doc = json_value(document)
        if self._tenant_fence is None:
            return doc
        fence = self._tenant_fence
        if self._tenant_engine_revision is None:
            raise RuntimeFencedError("Bound ledger interpretation is not configured")
        authority = EventInterpretation(
            fence.tenant_id,
            fence.database_resource,
            fence.binding_id,
            fence.epoch,
            fence.bundle_digest,
            self._tenant_engine_revision,
        )
        try:
            _event, receipt = validate_accepted_document(
                authority, event_id, doc, json_value(acceptance)
            )
        except (EventInterpretationError, ValueError, TypeError) as exc:
            raise RuntimeFencedError("Accepted event interpretation is unavailable") from exc
        doc["acceptance"] = receipt.model_dump()
        return doc

    def _public(
        self,
        document: Any,
        commit_ts: datetime,
        batch_index: int,
        event_id: str,
        acceptance: Any = None,
    ) -> Any:
        doc = self._validated_document(document, event_id, acceptance)
        if doc is None:
            return None
        doc["global_position"] = format_position(commit_ts, batch_index, event_id)
        return doc

    async def _documents(self, event_ids: list[str]) -> dict[str, dict[str, Any]]:
        from google.cloud.spanner_v1 import KeySet

        if not event_ids:
            return {}

        def read() -> dict[str, dict[str, Any]]:
            out = {}
            with tenant_snapshot(
                self._database, self._tenant_fence, operation=self._tenant_read_operation
            ) as snapshot:
                for event_id, document, commit_ts, batch_index, acceptance in snapshot.read(
                    "Events",
                    ["event_id", "document", "commit_ts", "batch_index", "acceptance"],
                    KeySet(keys=[[eid] for eid in sorted(set(event_ids))]),
                ):
                    doc = self._public(document, commit_ts, batch_index, event_id, acceptance)
                    if doc is not None:
                        out[event_id] = doc
            if (
                self._tenant_fence is not None
                and self._tenant_read_operation == "processing"
                and set(event_ids) - out.keys()
            ):
                raise RuntimeFencedError("Accepted processing input is missing from ledger")
            return out

        result: dict[str, dict[str, Any]] = await self._run(read)
        return result

    async def get_accepted_records(self, event_ids: list[str]) -> list[AcceptedRecord]:
        """Read content and provenance together from authoritative fenced storage."""
        from google.cloud.spanner_v1 import KeySet

        if self._tenant_fence is None:
            raise RuntimeFencedError("Authenticated records require a bound ledger")
        if not event_ids:
            return []

        def read() -> list[AcceptedRecord]:
            found = {}
            with tenant_snapshot(
                self._database, self._tenant_fence, operation="processing"
            ) as snapshot:
                for event_id, document, ts, batch, acceptance in snapshot.read(
                    "Events",
                    ["event_id", "document", "commit_ts", "batch_index", "acceptance"],
                    KeySet(keys=[[eid] for eid in sorted(set(event_ids))]),
                ):
                    doc = self._public(document, ts, batch, event_id, acceptance)
                    if doc is not None:
                        found[event_id] = AcceptedRecord(
                            doc,
                            VerifiedSourceProvenance(
                                event_id, EventAcceptance.model_validate(json_value(acceptance))
                            ),
                        )
            if set(event_ids) - found.keys():
                raise RuntimeFencedError("Accepted processing input is missing from ledger")
            return [found[event_id] for event_id in event_ids]

        result: list[AcceptedRecord] = await self._run(read)
        return result

    async def get_documents(self, event_ids: list[str]) -> list[dict[str, Any] | None]:
        found = await self._documents(event_ids)
        return [dict(found[eid]) if eid in found else None for eid in event_ids]

    async def get_by_id(self, event_id: str) -> Event | None:
        found = await self._documents([event_id])
        doc = found.get(event_id)
        return Event.model_validate(doc, strict=False) if doc is not None else None

    async def read_session_ids(self, session_id: str) -> list[str]:
        from google.cloud.spanner_v1 import param_types

        rows = await self._query(
            "SELECT event_id FROM Events@{FORCE_INDEX=EventsBySession} "
            "WHERE session_id = @session AND in_session_index "
            f"ORDER BY {POSITION_COLUMNS}",
            {"session": session_id},
            {"session": param_types.STRING},
        )
        return [row[0] for row in rows]

    async def previous_in_session(self, session_id: str, event_id: str) -> str | None:
        """The session index read backwards from the event's position, one row."""
        from google.cloud.spanner_v1 import param_types

        rows = await self._query(
            "SELECT p.event_id FROM Events AS e "
            "JOIN Events@{FORCE_INDEX=EventsBySession} AS p ON p.session_id = e.session_id "
            "WHERE e.event_id = @event AND e.session_id = @session AND e.in_session_index "
            "AND p.in_session_index AND (p.commit_ts < e.commit_ts "
            "OR (p.commit_ts = e.commit_ts AND p.batch_index < e.batch_index) "
            "OR (p.commit_ts = e.commit_ts AND p.batch_index = e.batch_index "
            "AND p.event_id < e.event_id)) "
            "ORDER BY p.commit_ts DESC, p.batch_index DESC, p.event_id DESC LIMIT 1",
            {"event": event_id, "session": session_id},
            {"event": param_types.STRING, "session": param_types.STRING},
        )
        return str(rows[0][0]) if rows else None

    async def _search_documents(
        self,
        where: list[str],
        params: dict[str, Any],
        types: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        clauses = " AND ".join(["document IS NOT NULL", *where])
        params = {**params, "limit": limit, "offset": offset}
        types = {**types, "limit": param_types.INT64, "offset": param_types.INT64}
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS}, acceptance FROM Events WHERE {clauses} "
            f"ORDER BY occurred_at_ms, {POSITION_COLUMNS} LIMIT @limit OFFSET @offset",
            params,
            types,
        )
        return [
            Event.model_validate(self._public(doc, ts, batch, eid, acceptance), strict=False)
            for doc, ts, batch, eid, acceptance in rows
        ]

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        offset = 0
        if after is not None:
            try:
                offset = int(after)
            except ValueError:
                offset = 0
        return await self._search_documents(
            ["session_tag = @session"],
            {"session": session_id.lower()},
            {"session": param_types.STRING},
            limit,
            offset,
        )

    async def search(self, query: EventQuery) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        where: list[str] = []
        params: dict[str, Any] = {}
        types: dict[str, Any] = {}
        for column, value in (
            ("session_tag", query.session_id),
            ("agent_tag", query.agent_id),
            ("trace_tag", query.trace_id),
            ("event_type_tag", query.event_type),
            ("tool_name_tag", query.tool_name),
        ):
            if value:
                where.append(f"{column} = @{column}")
                params[column] = value.lower()
                types[column] = param_types.STRING
        if query.after:
            where.append("occurred_at_ms >= @after_ms")
            params["after_ms"] = _epoch_ms(query.after)
            types["after_ms"] = param_types.INT64
        if query.before:
            where.append("occurred_at_ms <= @before_ms")
            params["before_ms"] = _epoch_ms(query.before)
            types["before_ms"] = param_types.INT64
        return await self._search_documents(where, params, types, query.limit, query.offset)

    async def search_scored(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Event, float]]:
        """Full-text search returning events with their Spanner ``SCORE``, best first.

        Matches events containing any query term (``domain/keyword_search.py``).
        """
        from google.cloud.spanner_v1 import param_types

        terms = query_terms(query_text or "", self._keyword.max_query_terms)
        if not terms:
            return []
        where = ["document IS NOT NULL", "SEARCH(text_tokens, @q)"]
        # Terms are word characters only, none of them query syntax
        params: dict[str, Any] = {"q": " OR ".join(terms), "limit": limit}
        types: dict[str, Any] = {"q": param_types.STRING, "limit": param_types.INT64}
        if session_id:
            where.append("session_tag = @session")
            params["session"] = session_id.lower()
            types["session"] = param_types.STRING
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS}, SCORE(text_tokens, @q) AS relevance, acceptance "
            f"FROM Events WHERE {' AND '.join(where)} "
            f"ORDER BY relevance DESC, {POSITION_COLUMNS} LIMIT @limit",
            params,
            types,
        )
        return [
            (
                Event.model_validate(self._public(doc, ts, batch, eid, acceptance), strict=False),
                float(score),
            )
            for doc, ts, batch, eid, score, acceptance in rows
        ]

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        return [event for event, _score in await self.search_scored(query_text, session_id, limit)]

    # -- retention (ADR-0014, brief G7) ---------------------------------------

    async def _execute_updates(
        self, statements: list[tuple[str, dict[str, Any], dict[str, Any]]]
    ) -> list[int]:
        def work(transaction: Any) -> list[int]:
            return [
                transaction.execute_update(sql, params=params, param_types=types)
                for sql, params, types in statements
            ]

        counts: list[int] = await self._run(self._transact_sync, work)
        return counts

    async def _update_in_batches(
        self, change: str, where: str, params: dict[str, Any], types: dict[str, Any]
    ) -> int:
        """Apply ``change`` (DML on ``Events e``) to the rows matching ``where``, a batch at a time.

        Each transaction selects up to ``CG_SPANNER_RETENTION_BATCH_ROWS``
        matching ids, then changes those rows, checking ``where`` again, so a
        retention pass over a large ledger never exceeds a commit's limits.
        ``change`` must take each row out of ``where``, or the loop would not
        end. (The ids are read first because the emulator refuses DML whose
        subquery reads ``Events`` itself.)
        """
        from google.cloud.spanner_v1 import param_types

        select = f"SELECT e.event_id FROM Events e WHERE {where} LIMIT @rows"
        update = f"{change} WHERE e.event_id IN UNNEST(@ids) AND {where}"
        select_params = {**params, "rows": self._retention_rows}
        select_types = {**types, "rows": param_types.INT64}
        update_types = {**types, "ids": param_types.Array(param_types.STRING)}

        def work(transaction: Any) -> tuple[int, int]:
            ids = [
                row[0]
                for row in transaction.execute_sql(
                    select, params=select_params, param_types=select_types
                )
            ]
            if not ids:
                return 0, 0
            changed: int = transaction.execute_update(
                update, params={**params, "ids": ids}, param_types=update_types
            )
            return len(ids), changed

        total = 0
        while True:
            batch: tuple[int, int] = await self._run(self._transact_sync, work)
            selected, changed = batch
            total += changed
            if selected < self._retention_rows:
                return total

    async def trim(self, max_age_days: int, consumer_groups: list[str]) -> int:
        from google.cloud.spanner_v1 import param_types

        # Commit timestamps come from the database clock, so the cutoff does
        # too: a skewed application host must not trim fresh entries.
        # An entry is still needed by a group while it is pending for it or
        # lies after the group's cursor in its shard (not yet delivered).
        where = (
            "e.in_log "
            "AND e.commit_ts < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY) "
            "AND NOT EXISTS (SELECT 1 FROM ConsumerDeliveries d "
            "  WHERE d.group_name IN UNNEST(@groups) AND d.event_id = e.event_id) "
            "AND NOT EXISTS (SELECT 1 FROM ConsumerCursors c "
            "  WHERE c.group_name IN UNNEST(@groups) AND c.shard = e.shard "
            "  AND (e.commit_ts > c.commit_ts OR (e.commit_ts = c.commit_ts "
            "  AND (e.batch_index > c.batch_index OR (e.batch_index = c.batch_index "
            "  AND e.event_id > c.event_id)))))"
        )
        trimmed = await self._update_in_batches(
            "UPDATE Events e SET in_log = FALSE",
            where,
            {"days": max_age_days, "groups": list(consumer_groups)},
            {"days": param_types.INT64, "groups": param_types.Array(param_types.STRING)},
        )
        await self._purge()
        return trimmed

    async def expire(
        self,
        max_age_days: int,
        archive_store: ArchiveStore | None = None,
    ) -> tuple[int, int]:
        """Archive (when given) and drop documents older than the cutoff, a batch at a time.

        An archive failure stops the pass: documents not archived are kept.
        """
        from google.cloud.spanner_v1 import param_types

        cutoff_ms = _epoch_ms(datetime.now(UTC) - timedelta(days=max_age_days))
        partition_key = datetime.now(UTC).strftime("%Y/%m/%d")
        archived = deleted = 0
        while True:
            rows = await self._query(
                f"SELECT document, {POSITION_COLUMNS}, occurred_at_ms, acceptance FROM Events "
                "WHERE document IS NOT NULL AND occurred_at_ms < @cutoff LIMIT @rows",
                {"cutoff": cutoff_ms, "rows": self._retention_rows},
                {"cutoff": param_types.INT64, "rows": param_types.INT64},
            )
            if not rows:
                break
            documents = []
            for doc, ts, batch, eid, occurred_ms, acceptance in rows:
                public = self._public(doc, ts, batch, eid, acceptance)
                if public is not None:
                    public["occurred_at_epoch_ms"] = occurred_ms
                    documents.append(public)
            if archive_store is not None:
                try:
                    await archive_store.archive_events(documents, partition_key)
                except RuntimeFencedError:
                    raise
                except Exception:
                    log.exception("archive_failed_skipping_delete", event_count=len(documents))
                    break
                archived += len(documents)
            (changed,) = await self._execute_updates(
                [
                    (
                        "UPDATE Events SET document = NULL "
                        "WHERE event_id IN UNNEST(@ids) AND document IS NOT NULL",
                        {"ids": [eid for _doc, _ts, _batch, eid, _ms, _acceptance in rows]},
                        {"ids": param_types.Array(param_types.STRING)},
                    )
                ]
            )
            deleted += changed
            if len(rows) < self._retention_rows:
                break
        if deleted:
            await self._purge()
        return archived, deleted

    async def housekeep(
        self,
        retention_ceiling_days: int,
        session_index_max_age_hours: int,
    ) -> dict[str, int]:
        from google.cloud.spanner_v1 import param_types

        dedup_cutoff_ms = _epoch_ms(datetime.now(UTC) - timedelta(days=retention_ceiling_days))
        stale_sessions = await self._query(
            "SELECT session_id FROM Events WHERE in_session_index GROUP BY session_id "
            "HAVING MAX(commit_ts) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)",
            {"hours": session_index_max_age_hours},
            {"hours": param_types.INT64},
        )
        session_ids = [row[0] for row in stale_sessions]
        dedup_removed = await self._update_in_batches(
            "UPDATE Events e SET dedup_active = FALSE",
            "e.dedup_active AND e.occurred_at_ms <= @cutoff",
            {"cutoff": dedup_cutoff_ms},
            {"cutoff": param_types.INT64},
        )
        if session_ids:
            await self._update_in_batches(
                "UPDATE Events e SET in_session_index = FALSE",
                "e.in_session_index AND e.session_id IN UNNEST(@sessions)",
                {"sessions": session_ids},
                {"sessions": param_types.Array(param_types.STRING)},
            )
        await self._purge()
        return {
            "dedup_entries_removed": dedup_removed,
            "session_streams_deleted": len(session_ids),
        }

    async def _purge(self) -> None:
        """Delete rows no structure needs any more (all four flags cleared)."""
        await self._update_in_batches(
            "DELETE FROM Events e",
            "NOT e.in_log AND e.document IS NULL AND NOT e.dedup_active AND NOT e.in_session_index",
            {},
            {},
        )

    # -- test support -------------------------------------------------------

    async def set_document_fields(self, event_id: str, **fields: Any) -> None:
        """Add fields to a stored document; ``summary``/``keywords`` are indexed for search."""
        from google.cloud.spanner_v1 import KeySet

        if self._tenant_fence is not None and fields.keys() - {"summary", "keywords"}:
            raise InvalidRequestError("Bound enrichment can update only summary and keywords")

        def work(transaction: Any) -> None:
            (row,) = list(
                transaction.read("Events", ["document", "acceptance"], KeySet(keys=[[event_id]]))
            )
            document = self._validated_document(row[0], event_id, row[1]) or {}
            document.pop("acceptance", None)
            document.update(fields)
            transaction.update(
                "Events",
                ["event_id", "document", "summary", "keywords"],
                [
                    [
                        event_id,
                        json_param(document),
                        _text(document.get("summary")),
                        _text(document.get("keywords")),
                    ]
                ],
            )

        await self._run(self._transact_sync, work)


@dataclass(frozen=True)
class _AdmittedEventWriter:
    """One request's immutable source context; never changes a shared store."""

    store: SpannerEventLog
    context: AdmissionContext

    def __getattr__(self, name: str) -> Any:
        return getattr(self.store, name)

    async def append(self, event: Event, payload: dict[str, Any] | None = None) -> str:
        return await self.store.append(event, payload, admission_context=self.context)

    async def append_batch(
        self, events: list[Event], payloads: list[dict[str, Any] | None] | None = None
    ) -> list[str]:
        return await self.store.append_batch(events, payloads, admission_context=self.context)

    async def append_batch_outcomes(
        self, events: list[Event], payloads: list[dict[str, Any] | None] | None = None
    ) -> list[AppendOutcome]:
        return await self.store.append_batch_outcomes(
            events, payloads, admission_context=self.context
        )
