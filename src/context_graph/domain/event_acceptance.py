"""Immutable acceptance identity and versioned normalized request fingerprints.

These values are server-owned. Persistence must stamp them inside a fenced
append transaction; this module alone does not enable tenant admission.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from context_graph.domain.models import Event

_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
_DIGEST = r"^sha256:[0-9a-f]{64}$"
_RESOURCE = (
    r"^projects/[a-z0-9][a-z0-9-]*/instances/[a-z0-9][a-z0-9-]*/databases/[a-z0-9][a-z0-9-]*$"
)


class EventIdentityConflictError(ValueError):
    """An existing event ID represents another producer or normalized request."""


class EventInterpretationError(ValueError):
    """Current authority has no permission to interpret this accepted contract."""


class Interpretation(Protocol):
    @property
    def tenant_id(self) -> str: ...

    @property
    def database_resource(self) -> str: ...

    @property
    def binding_id(self) -> str: ...

    @property
    def epoch(self) -> int: ...

    @property
    def bundle_digest(self) -> str: ...

    @property
    def engine_revision(self) -> str: ...


@dataclass(frozen=True)
class EventInterpretation:
    """Pinned runtime authority shared by content reads and dispositions."""

    tenant_id: str
    database_resource: str
    binding_id: str
    epoch: int
    bundle_digest: str
    engine_revision: str


class AdmissionContext(BaseModel):
    model_config = {"strict": True, "frozen": True, "extra": "forbid"}

    tenant_id: str = Field(pattern=_ID)
    database_resource: str = Field(pattern=_RESOURCE)
    binding_id: str = Field(pattern=_ID)
    accepted_epoch: int = Field(ge=1)
    bundle_digest: str = Field(pattern=_DIGEST)
    engine_revision: str = Field(min_length=1)
    source_id: str = Field(pattern=_ID)


class EventAcceptance(AdmissionContext):
    envelope_version: Literal[1]
    request_digest: str = Field(pattern=r"^sha256:json-v1:[0-9a-f]{64}$")

    @field_validator("envelope_version", mode="before")
    @classmethod
    def exact_version(cls, value: Any) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported acceptance envelope version")
        return 1

    def require_same_request(
        self, context: AdmissionContext, event: Event, payload: dict[str, Any] | None
    ) -> None:
        identity = (self.tenant_id, self.database_resource, self.binding_id, self.source_id)
        supplied = (
            context.tenant_id,
            context.database_resource,
            context.binding_id,
            context.source_id,
        )
        if identity != supplied or self.request_digest != request_fingerprint(event, payload):
            raise EventIdentityConflictError("Event ID conflicts with its original acceptance")
        if self.accepted_epoch > context.accepted_epoch:
            raise EventInterpretationError("Acceptance is newer than current authority")

    def require_interpretation(self, authority: Interpretation) -> None:
        accepted = (
            self.tenant_id,
            self.database_resource,
            self.binding_id,
            self.bundle_digest,
            self.engine_revision,
        )
        current = (
            authority.tenant_id,
            authority.database_resource,
            authority.binding_id,
            authority.bundle_digest,
            authority.engine_revision,
        )
        if accepted != current or self.accepted_epoch > authority.epoch:
            raise EventInterpretationError(
                "Accepted event contract is not authorized for processing"
            )


def _json_values(value: Any, ancestors: set[int]) -> None:
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("Request payload requires finite JSON numbers")
        return
    if kind not in (dict, list):
        raise ValueError("Request payload requires JSON values")
    if id(value) in ancestors:
        raise ValueError("Request payload cannot contain cycles")
    ancestors.add(id(value))
    try:
        if kind is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("Request payload object keys must be strings")
            values = value.values()
        else:
            values = value
        for item in values:
            _json_values(item, ancestors)
    finally:
        ancestors.remove(id(value))


def request_fingerprint(event: Event, payload: dict[str, Any] | None) -> str:
    """json-v1: sorted compact UTF-8, finite numbers, int/float and -0.0 distinct.

    All public Event fields except server position are semantic. Null and absent
    payload are identical; an empty object differs. Search/enrichment/acceptance
    are never inputs. Changing these encoding rules requires a new version.
    """
    if payload is not None and type(payload) is not dict:
        raise ValueError("Event payload must be an object or null")
    value = {
        "event": event.model_dump(mode="json", exclude={"global_position"}),
        "payload": payload,
    }
    try:
        _json_values(value, set())
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (RecursionError, UnicodeEncodeError) as exc:
        raise ValueError("Request cannot be represented by fingerprint json-v1") from exc
    return "sha256:json-v1:" + hashlib.sha256(encoded).hexdigest()


def stamp_acceptance(
    context: AdmissionContext, event: Event, payload: dict[str, Any] | None
) -> EventAcceptance:
    return EventAcceptance(
        **context.model_dump(),
        envelope_version=1,
        request_digest=request_fingerprint(event, payload),
    )


def validate_accepted_document(
    authority: Interpretation, event_id: str, document: Any, raw_acceptance: Any
) -> tuple[Event, EventAcceptance]:
    """Validate authoritative receipt/content before any derived interpretation.

    This is exact-contract processing. Epoch-only advances are compatible;
    unknown historical contracts require a future explicit replay grant.
    """
    from context_graph.domain.models import Event

    try:
        receipt = EventAcceptance.model_validate(raw_acceptance)
        receipt.require_interpretation(authority)
        if not isinstance(document, dict):
            raise EventInterpretationError("Accepted event content is unavailable")
        event = Event.model_validate(document, strict=False)
        if str(event.event_id) != event_id:
            raise EventInterpretationError("Ledger key and accepted event ID differ")
        if receipt.request_digest != request_fingerprint(event, document.get("payload")):
            raise EventInterpretationError("Accepted content does not match its immutable receipt")
        return event, receipt
    except (ValueError, TypeError) as exc:
        raise EventInterpretationError("Accepted event interpretation is unavailable") from exc
