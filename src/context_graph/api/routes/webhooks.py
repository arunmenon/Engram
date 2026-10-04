"""Tool webhooks: GitHub and Jira deliveries into the ledger (ADR-0018 phase 1).

``POST /v1/webhooks/github`` and ``POST /v1/webhooks/jira`` verify the
delivery's HMAC-SHA256 signature (``X-Hub-Signature-256`` for GitHub,
``X-Hub-Signature`` for Jira, ``sha256=<hex>``) with the secret in
``CG_WEBHOOK_<SOURCE>_SECRET``, translate it into ontology events
(``context_graph.sources``) and append them to the event log like
``POST /v1/events``. The projection worker then applies the active packs'
rules.

- Authentication is the signature, not the API key: webhook senders
  cannot add one.
- Event ids derive from the signed body, so a redelivery or a replayed
  body is deduplicated by the ledger; the delivery id is the trace id.
- The size limit is enforced from ``Content-Length`` and while reading.
- Events are ingested as ``agent_id = webhook:<source>``; the projector
  marks nodes from configured sources ``source_trust: trusted``.
- Event types the active packs do not declare are not ingested.

Responses: 202 with the event ids (an empty list when the delivery is
not translated), 401 on a bad signature, 413 when too large, 503 when the
source has no secret configured.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, uuid5

import orjson
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from context_graph.domain.models import Event
from context_graph.metrics import EVENTS_INGESTED_TOTAL
from context_graph.sources import github, jira
from context_graph.sources.events import WEBHOOK_AGENT_PREFIX

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ports.event_store import EventStore
    from context_graph.settings import Settings
    from context_graph.sources.events import SourceEvent

logger = structlog.get_logger(__name__)

_HEX_DIGEST = re.compile(r"[0-9a-fA-F]{64}")

router = APIRouter(tags=["webhooks"])

SIGNATURE_HEADERS = {"github": "x-hub-signature-256", "jira": "x-hub-signature"}
DELIVERY_HEADERS = {"github": "x-github-delivery", "jira": "x-atlassian-webhook-identifier"}

# Namespace for event ids derived from webhook deliveries
WEBHOOK_NAMESPACE = uuid5(NAMESPACE_URL, "https://engram/webhooks")


def _secret(settings: Settings, source: str) -> bytes | None:
    secret = getattr(settings.webhooks, f"{source}_secret", None)
    return secret.get_secret_value().encode() if secret else None


def signature_valid(secret: bytes, body: bytes, header: str | None) -> bool:
    """Constant-time check of ``sha256=<hex>`` against the body's HMAC-SHA256."""
    if not header or not header.startswith("sha256="):
        return False
    given = header.removeprefix("sha256=")
    if not _HEX_DIGEST.fullmatch(given):
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest().encode()
    return hmac.compare_digest(expected, given.lower().encode())


async def _read_body(request: Request, limit: int) -> bytes | None:
    """The body, or None once it exceeds ``limit`` bytes (checked while reading)."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        return None
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _translate(source: str, request: Request, payload: dict[str, Any]) -> list[SourceEvent]:
    if source == "github":
        return github.translate(request.headers.get("x-github-event", ""), payload)
    return jira.translate(payload)


def _occurred_at(value: object, now: datetime) -> datetime:
    if isinstance(value, str) and value:
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return now
        return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return now


def build_events(
    source: str,
    delivery_id: str,
    body_digest: str,
    translated: list[SourceEvent],
    now: datetime,
) -> list[tuple[Event, dict[str, Any]]]:
    """Ledger events (with payloads) for a delivery's translated events.

    Event ids derive from the signed body, so a redelivery, or a captured
    body replayed under a new delivery id, is deduplicated by the ledger.
    """
    events = []
    for index, item in enumerate(translated):
        occurred_at = _occurred_at(item.occurred_at, now)
        payload = dict(item.payload)
        if item.cdevents_type:
            payload["cdevents_type"] = item.cdevents_type
        event = Event(
            event_id=uuid5(WEBHOOK_NAMESPACE, f"{source}:{body_digest}:{index}"),
            event_type=item.event_type,
            occurred_at=occurred_at,
            session_id=f"pdlc:{item.scope}",
            agent_id=f"{WEBHOOK_AGENT_PREFIX}{source}",
            trace_id=delivery_id,
            payload_ref=f"webhook:{source}:{delivery_id}",
        )
        events.append((event, payload))
    return events


@router.post("/webhooks/{source}", status_code=202)
async def receive_webhook(source: str, request: Request) -> ORJSONResponse:
    if source not in SIGNATURE_HEADERS:
        return ORJSONResponse(status_code=404, content={"detail": f"unknown source {source!r}"})
    settings: Settings = request.app.state.settings
    secret = _secret(settings, source)
    if secret is None:
        return ORJSONResponse(
            status_code=503, content={"detail": f"{source} webhooks are not configured"}
        )
    body = await _read_body(request, settings.webhooks.max_body_bytes)
    if body is None:
        return ORJSONResponse(status_code=413, content={"detail": "delivery too large"})
    if not signature_valid(secret, body, request.headers.get(SIGNATURE_HEADERS[source])):
        logger.warning("webhook_signature_invalid", source=source)
        return ORJSONResponse(status_code=401, content={"detail": "invalid signature"})
    try:
        payload = orjson.loads(body)
    except orjson.JSONDecodeError:
        return ORJSONResponse(status_code=400, content={"detail": "body is not JSON"})
    if not isinstance(payload, dict):
        return ORJSONResponse(status_code=400, content={"detail": "body is not a JSON object"})

    body_digest = hashlib.sha256(body).hexdigest()
    delivery_id = request.headers.get(DELIVERY_HEADERS[source]) or body_digest
    registry: OntologyRegistry | None = getattr(request.app.state, "ontology", None)
    translated = [
        item
        for item in _translate(source, request, payload)
        if registry is None or item.event_type in registry.event_types
    ]
    event_store: EventStore = request.app.state.event_store
    event_ids = []
    events = build_events(source, delivery_id, body_digest, translated, datetime.now(UTC))
    for event, event_payload in events:
        await event_store.append(event, payload=event_payload)
        EVENTS_INGESTED_TOTAL.inc()
        event_ids.append(str(event.event_id))
    logger.info(
        "webhook_ingested",
        source=source,
        delivery_id=delivery_id,
        event_types=[item.event_type for item in translated],
    )
    return ORJSONResponse(status_code=202, content={"event_ids": event_ids})
