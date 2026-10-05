"""Event ingestion endpoints.

POST /v1/events        — ingest a single event
POST /v1/events/batch  — ingest up to ``CG_INGEST_BATCH_MAX_EVENTS`` events
POST /v1/events/import — admin bulk import: gzip NDJSON, ordered, streamed outcomes

Bodies are bounded in size and read time and may be gzip-encoded
(``api/ingest.py``). Each event reports ``created`` or ``duplicate``
(the ledger is idempotent by event_id), or why it was refused or failed.

Source: ADR-0004, ADR-0010

Note: The domain Event model uses ``strict=True`` (Pydantic) to enforce
type-level invariants at the adapter boundary.  JSON payloads carry UUIDs and
datetimes as strings, so we parse with ``strict=False`` to allow the standard
coercion and then run domain validation on the coerced model.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import orjson
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse, StreamingResponse
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from context_graph.api.dependencies import get_event_store
from context_graph.api.ingest import BodyError, check_events, read_body
from context_graph.domain.models import Event  # noqa: TCH001 — runtime: model_validate
from context_graph.domain.validation import ValidationError, validate_event
from context_graph.metrics import EVENTS_BATCH_SIZE, EVENTS_INGESTED_TOTAL
from context_graph.ports.event_store import (  # noqa: TCH001 — runtime: Depends()
    AppendOutcome,
    EventStore,
)
from context_graph.sources.events import WEBHOOK_AGENT_PREFIX

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["events"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class IngestResult(BaseModel):
    """Result of a single event ingestion."""

    event_id: str
    global_position: str


class BatchError(BaseModel):
    """Error detail for a single event in a batch."""

    index: int
    event_id: str | None
    errors: list[dict[str, str]]


class BatchResponse(BaseModel):
    """Response from batch ingestion."""

    accepted: int
    rejected: int
    results: list[IngestResult]
    errors: list[BatchError]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EventStoreDep = Annotated[EventStore, Depends(get_event_store)]


def _parse_event(data: dict[str, Any]) -> Event:
    """Parse a dict into an Event with coercion (strict=False).

    The domain Event model has ``strict=True`` which rejects string->UUID
    and string->datetime coercion.  JSON payloads require coercion, so we
    parse with ``strict=False`` here at the API boundary.
    """
    return Event.model_validate(data, strict=False)


def _undeclared(request: Request, event: Event) -> str | None:
    """Why an event is refused by the active ontology packs, or None (ADR-0018).

    Agent ids under ``webhook:`` belong to the signed webhook routes, whose
    events the projector marks trusted; the generic ingest refuses them.
    """
    if event.agent_id.startswith(WEBHOOK_AGENT_PREFIX):
        return f"agent_id prefix {WEBHOOK_AGENT_PREFIX!r} is reserved for the webhook routes"
    registry = getattr(request.app.state, "ontology", None)
    if registry is None or registry.accepts_event_type(event.event_type):
        return None
    return (
        f"event type {event.event_type!r} is not declared by the active ontology packs "
        f"({', '.join(p.name for p in registry.packs)})"
    )


def _check_declared(request: Request, event: Event) -> None:
    reason = _undeclared(request, event)
    if reason is not None:
        field = "agent_id" if reason.startswith("agent_id") else "event_type"
        raise ValidationError(field=field, message=reason)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _quota_exceeded(request: Request, count: int) -> ORJSONResponse | None:
    """429 when the client's event quota cannot cover ``count`` events.

    The quota is ``CG_INGEST_EVENTS_PER_MINUTE`` per client (review 3.7): a
    batch costs one request against the request rate limit, but as many
    events as it carries against this.
    """
    quota = getattr(request.app.state, "event_quota", None)
    if quota is None:
        return None
    client = request.client.host if request.client else "unknown"
    wait_s = quota.charge(client, count)
    if wait_s is None:
        return None
    return ORJSONResponse(
        status_code=429,
        content={"detail": "event quota exceeded", "retry_after": round(wait_s, 1)},
        headers={"Retry-After": str(int(wait_s) + 1)},
    )


def _refusal(request: Request) -> Any:
    def refuse(event: Event) -> tuple[str, str] | None:
        reason = _undeclared(request, event)
        if reason is None:
            return None
        return ("agent_id" if reason.startswith("agent_id") else "event_type", reason)

    return refuse


async def _json_body(request: Request) -> Any:
    settings = request.app.state.settings.ingest
    raw = await read_body(request, settings.max_body_bytes, settings.body_read_timeout_s)
    try:
        return orjson.loads(raw)
    except orjson.JSONDecodeError as exc:
        raise BodyError(400, f"body is not valid JSON: {exc}") from exc


def _body_error(exc: BodyError) -> ORJSONResponse:
    return ORJSONResponse(status_code=exc.status, content={"detail": [{"message": exc.message}]})


@router.post("/events", status_code=201)
async def ingest_event(
    request: Request,
    event_store: EventStoreDep,
) -> ORJSONResponse:
    """Ingest a single event into the event ledger.

    Validates the event envelope, then appends it. Returns the event_id,
    its global_position and whether it was ``created`` or a ``duplicate``.
    """
    try:
        body = await _json_body(request)
    except BodyError as exc:
        return _body_error(exc)
    if not isinstance(body, dict):
        return ORJSONResponse(
            status_code=422, content={"detail": [{"message": "body must be a JSON object"}]}
        )

    raw_payload = body.get("payload")
    event_payload: dict[str, Any] | None = raw_payload if isinstance(raw_payload, dict) else None
    try:
        event = _parse_event(body)
    except PydanticValidationError as exc:
        return ORJSONResponse(status_code=422, content={"detail": exc.errors()})

    validation_result = validate_event(event)
    if not validation_result.is_valid:
        raise ValidationError(
            field=validation_result.errors[0].field,
            message=validation_result.errors[0].message,
        )
    _check_declared(request, event)
    if (limited := _quota_exceeded(request, 1)) is not None:
        return limited

    (outcome,) = await event_store.append_batch_outcomes([event], payloads=[event_payload])
    if outcome.status == "failed":
        return ORJSONResponse(
            status_code=503, content={"detail": f"the event was not stored: {outcome.error}"}
        )
    if outcome.status == "created":
        EVENTS_INGESTED_TOTAL.inc()

    logger.info(
        "event_ingested",
        event_id=str(event.event_id),
        event_type=event.event_type,
        global_position=outcome.position,
        status=outcome.status,
    )
    return ORJSONResponse(
        status_code=201,
        content={
            "event_id": str(event.event_id),
            "global_position": outcome.position,
            "status": outcome.status,
        },
    )


@router.post("/events/batch", status_code=201)
async def ingest_event_batch(
    request: Request,
    event_store: EventStoreDep,
) -> ORJSONResponse:
    """Ingest a batch of events.

    Each event is validated on its own; valid ones are appended in one
    store call. ``results`` lists the stored ones (``created`` or
    ``duplicate``), ``errors`` the refused ones and any the store failed to
    write (``field: "store"``; send them again). 201 when any event is
    stored; otherwise 422 if every event was refused, 503 if the store failed.
    """
    try:
        body = await _json_body(request)
    except BodyError as exc:
        return _body_error(exc)
    if not isinstance(body, dict) or "events" not in body:
        return ORJSONResponse(
            status_code=422,
            content={"detail": [{"message": "Request body must contain 'events' list"}]},
        )

    raw_events = body["events"]
    if not isinstance(raw_events, list) or len(raw_events) == 0:
        return ORJSONResponse(
            status_code=422,
            content={"detail": [{"message": "'events' must be a non-empty list"}]},
        )
    max_events = request.app.state.settings.ingest.batch_max_events
    if len(raw_events) > max_events:
        return ORJSONResponse(
            status_code=422,
            content={"detail": [{"message": f"'events' must contain at most {max_events} items"}]},
        )

    checked = check_events(raw_events, _refusal(request))
    if checked.events and (limited := _quota_exceeded(request, len(checked.events))) is not None:
        return limited

    results: list[dict[str, Any]] = []
    errors = list(checked.errors)
    store_failures = 0
    if checked.events:
        outcomes = await event_store.append_batch_outcomes(
            checked.events, payloads=checked.payloads
        )
        for index, event, outcome in zip(checked.indexes, checked.events, outcomes, strict=True):
            if outcome.status == "failed":
                store_failures += 1
                errors.append(
                    {
                        "index": index,
                        "event_id": str(event.event_id),
                        "errors": [{"field": "store", "message": outcome.error or "not stored"}],
                    }
                )
                continue
            results.append(
                {
                    "event_id": str(event.event_id),
                    "global_position": outcome.position,
                    "status": outcome.status,
                }
            )
        EVENTS_INGESTED_TOTAL.inc(sum(1 for r in results if r["status"] == "created"))
        EVENTS_BATCH_SIZE.observe(len(raw_events))
    errors.sort(key=lambda error: error["index"])

    logger.info(
        "batch_ingested",
        accepted=len(results),
        rejected=len(errors),
        store_failures=store_failures,
        total=len(raw_events),
    )
    status_code = 201 if results else (503 if store_failures else 422)
    return ORJSONResponse(
        status_code=status_code,
        content={
            "accepted": len(results),
            "rejected": len(errors),
            "results": results,
            "errors": errors,
        },
    )


# ---------------------------------------------------------------------------
# Bulk import (admin)
# ---------------------------------------------------------------------------

import_router = APIRouter(tags=["events"])


def _import_refusal(request: Request) -> Any:
    """Like the generic ingest, except a configured admin key vouches for ``webhook:`` ids.

    The route runs behind ``require_admin_key``. When that key is set, the
    caller proved it, and may import tool history under the webhook agent
    ids the projector trusts (trust comes from the credential). When no key
    is configured (development), nothing was proved and those ids are refused.
    """
    vouched = request.app.state.settings.auth.admin_key is not None
    refuse_generic = _refusal(request)

    def refuse(event: Event) -> tuple[str, str] | None:
        if vouched and event.agent_id.startswith(WEBHOOK_AGENT_PREFIX):
            registry = getattr(request.app.state, "ontology", None)
            if registry is None or registry.accepts_event_type(event.event_type):
                return None
        result: tuple[str, str] | None = refuse_generic(event)
        return result

    return refuse


def _ndjson(record: dict[str, Any]) -> bytes:
    return orjson.dumps(record) + b"\n"


@import_router.post("/events/import")
async def import_events(
    request: Request,
    event_store: EventStoreDep,
    order: Literal["occurred_at", "input"] = "occurred_at",
) -> Any:
    """Bulk import: NDJSON events in, one NDJSON outcome per event out (admin key).

    The body is one event per line (blank lines skipped), optionally gzip
    encoded, at most ``CG_INGEST_IMPORT_MAX_BODY_BYTES`` and
    ``CG_INGEST_IMPORT_MAX_EVENTS``. Events are validated like
    ``/v1/events/batch``. With a configured admin key, ``webhook:`` agent
    ids are accepted, so tool history imports as trusted.

    Ordering contract: with ``order=occurred_at`` (default) the valid events
    are appended in occurrence order, ties in input order; with
    ``order=input``, in input order. Either way they land after everything
    already in the ledger: ``global_position`` is arrival order, and the
    live ledger is never reordered. Import a session's history before its
    live events, and send one import at a time per session.

    Events are appended ``CG_INGEST_IMPORT_BATCH_SIZE`` at a time. The
    response streams a line per event, ``{"index", "event_id", "status",
    ...}`` with status ``created``, ``duplicate``, ``rejected`` (with
    ``errors``) or ``failed`` (with ``error``), then ``{"summary": {...}}``.
    If the store becomes unavailable, the rest are ``failed`` and the import
    stops; imports are idempotent, so send the same file again.
    """
    settings = request.app.state.settings.ingest
    try:
        raw = await read_body(request, settings.import_max_body_bytes, settings.body_read_timeout_s)
    except BodyError as exc:
        return _body_error(exc)
    items: list[Any] = []
    unparsable: dict[int, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            items.append(orjson.loads(line))
        except orjson.JSONDecodeError as exc:
            unparsable[len(items)] = f"line is not valid JSON: {exc}"
            items.append(None)
        if len(items) > settings.import_max_events:
            return ORJSONResponse(
                status_code=413,
                content={
                    "detail": [
                        {"message": f"an import holds at most {settings.import_max_events} events"}
                    ]
                },
            )
    if not items:
        return ORJSONResponse(
            status_code=422, content={"detail": [{"message": "the body holds no events"}]}
        )

    checked = check_events(items, _import_refusal(request))
    for error in checked.errors:
        if error["index"] in unparsable:
            error["errors"] = [{"field": "", "message": unparsable[error["index"]]}]
    queue = sorted(range(len(checked.events)), key=lambda i: checked.indexes[i])
    if order == "occurred_at":
        queue.sort(key=lambda i: (checked.events[i].occurred_at, checked.indexes[i]))
    batch_size = max(1, settings.import_batch_size)

    async def outcomes() -> Any:
        counts = {"created": 0, "duplicate": 0, "rejected": len(checked.errors), "failed": 0}
        for error in sorted(checked.errors, key=lambda e: e["index"]):
            yield _ndjson({**error, "status": "rejected"})
        stopped: str | None = None
        for start in range(0, len(queue), batch_size):
            chunk = queue[start : start + batch_size]
            events = [checked.events[i] for i in chunk]
            if stopped is None:
                try:
                    results = await event_store.append_batch_outcomes(
                        events, payloads=[checked.payloads[i] for i in chunk]
                    )
                except Exception as exc:  # noqa: BLE001 - reported per event, then stop
                    logger.warning("import_append_failed", error=str(exc), at=start)
                    stopped = f"the store failed: {exc}"
            if stopped is not None:
                results = [AppendOutcome("failed", error=stopped)] * len(chunk)
            for i, event, outcome in zip(chunk, events, results, strict=True):
                counts[outcome.status] += 1
                line: dict[str, Any] = {
                    "index": checked.indexes[i],
                    "event_id": str(event.event_id),
                    "status": outcome.status,
                }
                if outcome.status == "failed":
                    line["error"] = outcome.error
                else:
                    line["global_position"] = outcome.position
                yield _ndjson(line)
        EVENTS_INGESTED_TOTAL.inc(counts["created"])
        logger.info("events_imported", order=order, received=len(items), **counts)
        yield _ndjson({"summary": {"received": len(items), "order": order, **counts}})

    return StreamingResponse(outcomes(), media_type="application/x-ndjson")
