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
- Event ids derive from the delivery id, so a redelivery is deduplicated
  by the ledger.
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

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ports.event_store import EventStore
    from context_graph.settings import Settings
    from context_graph.sources.events import SourceEvent

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["webhooks"])

SIGNATURE_HEADERS = {"github": "x-hub-signature-256", "jira": "x-hub-signature"}
DELIVERY_HEADERS = {"github": "x-github-delivery", "jira": "x-atlassian-webhook-identifier"}

# Namespace for event ids derived from webhook deliveries
WEBHOOK_NAMESPACE = uuid5(NAMESPACE_URL, "https://engram/webhooks")


def _secret(settings: Settings, source: str) -> bytes | None:
    secret = getattr(settings.webhooks, f"{source}_secret", None)
    return secret.get_secret_value().encode() if secret else None


def signature_valid(secret: bytes, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _translate(source: str, request: Request, payload: dict[str, Any]) -> list[SourceEvent]:
    if source == "github":
        return github.translate(request.headers.get("x-github-event", ""), payload)
    return jira.translate(payload)


def build_events(
    source: str, delivery_id: str, translated: list[SourceEvent], now: datetime
) -> list[tuple[Event, dict[str, Any]]]:
    """Ledger events (with payloads) for a delivery's translated events."""
    events = []
    for index, item in enumerate(translated):
        occurred_at = now
        if item.occurred_at:
            try:
                occurred_at = datetime.fromisoformat(item.occurred_at.replace("Z", "+00:00"))
            except ValueError:
                occurred_at = now
        payload = dict(item.payload)
        if item.cdevents_type:
            payload["cdevents_type"] = item.cdevents_type
        event = Event(
            event_id=uuid5(WEBHOOK_NAMESPACE, f"{source}:{delivery_id}:{index}"),
            event_type=item.event_type,
            occurred_at=occurred_at,
            session_id=f"pdlc:{item.scope}",
            agent_id=f"webhook:{source}",
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
    body = await request.body()
    if len(body) > settings.webhooks.max_body_bytes:
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

    delivery_id = request.headers.get(DELIVERY_HEADERS[source]) or hashlib.sha256(body).hexdigest()
    registry: OntologyRegistry | None = getattr(request.app.state, "ontology", None)
    translated = [
        item
        for item in _translate(source, request, payload)
        if registry is None or item.event_type in registry.event_types
    ]
    event_store: EventStore = request.app.state.event_store
    event_ids = []
    for event, event_payload in build_events(source, delivery_id, translated, datetime.now(UTC)):
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
