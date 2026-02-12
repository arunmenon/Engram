"""Event ingestion endpoints.

POST /v1/events       — ingest a single event
POST /v1/events/batch — ingest a batch of events

Source: ADR-0004, ADR-0010

Note: The domain Event model uses ``strict=True`` (Pydantic) to enforce
type-level invariants at the adapter boundary.  JSON payloads carry UUIDs and
datetimes as strings, so we parse with ``strict=False`` to allow the standard
coercion and then run domain validation on the coerced model.
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from context_graph.adapters.redis.store import RedisEventStore  # noqa: TCH001 — runtime: Depends()
from context_graph.api.dependencies import get_event_store
from context_graph.domain.models import Event  # noqa: TCH001 — runtime: model_validate
from context_graph.domain.validation import ValidationError, validate_event

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

EventStoreDep = Annotated[RedisEventStore, Depends(get_event_store)]


def _parse_event(data: dict[str, Any]) -> Event:
    """Parse a dict into an Event with coercion (strict=False).

    The domain Event model has ``strict=True`` which rejects string->UUID
    and string->datetime coercion.  JSON payloads require coercion, so we
    parse with ``strict=False`` here at the API boundary.
    """
    return Event.model_validate(data, strict=False)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/events", status_code=201)
async def ingest_event(
    request: Request,
    event_store: EventStoreDep,
) -> ORJSONResponse:
    """Ingest a single event into the event ledger.

    Validates the event envelope, then appends to Redis Streams.
    Returns the event_id and auto-assigned global_position.
    """
    body = await request.json()

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

    global_position = await event_store.append(event)

    logger.info(
        "event_ingested",
        event_id=str(event.event_id),
        event_type=event.event_type,
        global_position=global_position,
    )

    return ORJSONResponse(
        status_code=201,
        content={
            "event_id": str(event.event_id),
            "global_position": global_position,
        },
    )


@router.post("/events/batch", status_code=201)
async def ingest_event_batch(
    request: Request,
    event_store: EventStoreDep,
) -> ORJSONResponse:
    """Ingest a batch of events.

    Each event is validated individually. Valid events are appended to
    the event store. Errors are collected and returned alongside results.
    """
    body = await request.json()

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
    if len(raw_events) > 1000:
        return ORJSONResponse(
            status_code=422,
            content={"detail": [{"message": "'events' must contain at most 1000 items"}]},
        )

    results: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    valid_events: list[Event] = []

    for idx, raw_event in enumerate(raw_events):
        # Parse
        try:
            event = _parse_event(raw_event)
        except PydanticValidationError as exc:
            event_id = raw_event.get("event_id") if isinstance(raw_event, dict) else None
            errors.append(
                {
                    "index": idx,
                    "event_id": event_id,
                    "errors": [
                        {
                            "field": ".".join(str(part) for part in err["loc"]),
                            "message": err["msg"],
                        }
                        for err in exc.errors()
                    ],
                }
            )
            continue

        # Domain validation
        validation_result = validate_event(event)
        if validation_result.is_valid:
            valid_events.append(event)
        else:
            errors.append(
                {
                    "index": idx,
                    "event_id": str(event.event_id),
                    "errors": [
                        {"field": err.field, "message": err.message}
                        for err in validation_result.errors
                    ],
                }
            )

    if valid_events:
        positions = await event_store.append_batch(valid_events)
        for event, position in zip(valid_events, positions, strict=True):
            results.append(
                {
                    "event_id": str(event.event_id),
                    "global_position": position,
                }
            )

    logger.info(
        "batch_ingested",
        accepted=len(results),
        rejected=len(errors),
        total=len(raw_events),
    )

    return ORJSONResponse(
        status_code=201,
        content={
            "accepted": len(results),
            "rejected": len(errors),
            "results": results,
            "errors": errors,
        },
    )
