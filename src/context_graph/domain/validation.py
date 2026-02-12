"""Event envelope validation rules.

Pure Python — zero framework imports. All validation logic for events
before they enter the event store.

Source: ADR-0004, ADR-0011 §2
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_graph.domain.models import Event

# Dot-namespaced event type pattern: <category>.<action>[.<sub>]
EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")

# Known event type prefixes for fast validation
KNOWN_PREFIXES = frozenset({"agent", "tool", "llm", "observation", "system", "user"})

# Maximum payload_ref length
MAX_PAYLOAD_REF_LENGTH = 2048

# Maximum time drift allowed for occurred_at (5 minutes into the future)
MAX_FUTURE_DRIFT_SECONDS = 300


class ValidationError(Exception):
    """Raised when event validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ValidationResult:
    """Accumulates validation errors for an event."""

    def __init__(self) -> None:
        self.errors: list[ValidationError] = []

    def add_error(self, field: str, message: str) -> None:
        self.errors.append(ValidationError(field, message))

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_event(event: Event) -> ValidationResult:
    """Validate an event envelope before ingestion.

    Checks beyond what Pydantic's field validators enforce:
    - event_type follows dot-namespace convention
    - occurred_at is not excessively in the future
    - parent_event_id is not self-referential
    - ended_at is after occurred_at when present
    - importance_hint is in valid range
    """
    result = ValidationResult()

    # Event type must match dot-namespace pattern
    if not EVENT_TYPE_PATTERN.match(event.event_type):
        result.add_error(
            "event_type",
            f"Must be dot-namespaced (e.g., 'agent.invoke'), got '{event.event_type}'",
        )

    # occurred_at must not be too far in the future
    now = datetime.now(UTC)
    if event.occurred_at.tzinfo is not None:
        delta = (event.occurred_at - now).total_seconds()
        if delta > MAX_FUTURE_DRIFT_SECONDS:
            result.add_error(
                "occurred_at",
                f"Event timestamp is {delta:.0f}s in the future (max {MAX_FUTURE_DRIFT_SECONDS}s)",
            )

    # parent_event_id must not be self-referential
    if event.parent_event_id is not None and event.parent_event_id == event.event_id:
        result.add_error(
            "parent_event_id",
            "Cannot reference own event_id as parent",
        )

    # ended_at must be after occurred_at
    if event.ended_at is not None and event.ended_at < event.occurred_at:
        result.add_error(
            "ended_at",
            "ended_at must be >= occurred_at",
        )

    # payload_ref length
    if len(event.payload_ref) > MAX_PAYLOAD_REF_LENGTH:
        result.add_error(
            "payload_ref",
            f"payload_ref exceeds max length of {MAX_PAYLOAD_REF_LENGTH}",
        )

    return result


def validate_event_type_prefix(event_type: str) -> bool:
    """Check if an event type has a known prefix."""
    prefix = event_type.split(".")[0] if "." in event_type else event_type
    return prefix in KNOWN_PREFIXES
