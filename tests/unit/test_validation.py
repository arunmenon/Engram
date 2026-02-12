"""Unit tests for domain validation (src/context_graph/domain/validation.py).

Covers ``validate_event`` envelope checks and ``validate_event_type_prefix``.
No external dependencies required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from context_graph.domain.models import Event
from context_graph.domain.validation import (
    KNOWN_PREFIXES,
    MAX_FUTURE_DRIFT_SECONDS,
    validate_event,
    validate_event_type_prefix,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_event(**overrides) -> Event:
    """Build a valid Event for validation tests."""
    defaults: dict = {
        "event_id": uuid4(),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(UTC),
        "session_id": "test-session",
        "agent_id": "test-agent",
        "trace_id": "test-trace",
        "payload_ref": "payload:test",
    }
    defaults.update(overrides)
    return Event(**defaults)


# ---------------------------------------------------------------------------
# validate_event — happy path
# ---------------------------------------------------------------------------


class TestValidateEventValid:
    """Tests that a well-formed event passes all checks."""

    def test_valid_event_returns_is_valid(self) -> None:
        """A properly constructed event should yield is_valid=True."""
        event = _make_valid_event()
        result = validate_event(event)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_event_with_optional_fields(self) -> None:
        """An event with optional fields populated should still pass."""
        event = _make_valid_event(
            tool_name="calculator",
            parent_event_id=uuid4(),
            ended_at=datetime.now(UTC) + timedelta(seconds=5),
            importance_hint=5,
        )
        result = validate_event(event)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_event — event_type pattern
# ---------------------------------------------------------------------------


class TestValidateEventTypePattern:
    """Tests for the dot-namespace pattern check inside validate_event.

    Note: Pydantic's own regex check on the ``event_type`` field prevents
    most invalid patterns from reaching ``validate_event``.  These tests
    exercise the secondary validation layer for patterns that somehow get
    past Pydantic (e.g. via ``model_construct``).
    """

    def test_invalid_event_type_via_model_construct(self) -> None:
        """An event_type without dots should fail validation."""
        # model_construct bypasses Pydantic field validation
        event = Event.model_construct(
            event_id=uuid4(),
            event_type="INVALID",
            occurred_at=datetime.now(UTC),
            session_id="s",
            agent_id="a",
            trace_id="t",
            payload_ref="p",
        )
        result = validate_event(event)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "event_type" in error_fields


# ---------------------------------------------------------------------------
# validate_event — self-referential parent_event_id
# ---------------------------------------------------------------------------


class TestValidateEventSelfReferentialParent:
    """Tests for the parent_event_id != event_id check."""

    def test_self_referential_parent_is_invalid(self) -> None:
        """An event whose parent_event_id equals its own event_id must fail."""
        shared_id = uuid4()
        event = _make_valid_event(event_id=shared_id, parent_event_id=shared_id)
        result = validate_event(event)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "parent_event_id" in error_fields

    def test_different_parent_is_valid(self) -> None:
        """An event with a distinct parent_event_id should pass."""
        event = _make_valid_event(parent_event_id=uuid4())
        result = validate_event(event)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_event — ended_at before occurred_at
# ---------------------------------------------------------------------------


class TestValidateEventEndedBeforeOccurred:
    """Tests for the ended_at >= occurred_at check."""

    def test_ended_before_occurred_is_invalid(self) -> None:
        """ended_at before occurred_at must produce a validation error."""
        now = datetime.now(UTC)
        event = _make_valid_event(
            occurred_at=now,
            ended_at=now - timedelta(seconds=10),
        )
        result = validate_event(event)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "ended_at" in error_fields

    def test_ended_equal_to_occurred_is_valid(self) -> None:
        """ended_at equal to occurred_at (zero-duration) should be accepted."""
        now = datetime.now(UTC)
        event = _make_valid_event(occurred_at=now, ended_at=now)
        result = validate_event(event)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_event — future occurred_at beyond drift limit
# ---------------------------------------------------------------------------


class TestValidateEventFutureDrift:
    """Tests for the max-future-drift check on occurred_at."""

    def test_far_future_occurred_at_is_invalid(self) -> None:
        """An occurred_at more than MAX_FUTURE_DRIFT_SECONDS ahead must fail."""
        future_time = datetime.now(UTC) + timedelta(seconds=MAX_FUTURE_DRIFT_SECONDS + 60)
        event = _make_valid_event(occurred_at=future_time)
        result = validate_event(event)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "occurred_at" in error_fields

    def test_slight_future_occurred_at_is_valid(self) -> None:
        """An occurred_at within the drift window should be accepted."""
        near_future = datetime.now(UTC) + timedelta(seconds=MAX_FUTURE_DRIFT_SECONDS - 60)
        event = _make_valid_event(occurred_at=near_future)
        result = validate_event(event)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_event_type_prefix
# ---------------------------------------------------------------------------


class TestValidateEventTypePrefix:
    """Tests for the known-prefix helper."""

    @pytest.mark.parametrize("prefix", sorted(KNOWN_PREFIXES))
    def test_known_prefixes_return_true(self, prefix: str) -> None:
        """Every known prefix should be recognized."""
        event_type = f"{prefix}.action"
        assert validate_event_type_prefix(event_type) is True

    @pytest.mark.parametrize("unknown", ["custom", "foo", "xyz", "plugin"])
    def test_unknown_prefix_returns_false(self, unknown: str) -> None:
        """Unrecognized prefixes should return False."""
        event_type = f"{unknown}.action"
        assert validate_event_type_prefix(event_type) is False

    def test_no_dot_returns_false(self) -> None:
        """A string with no dot has no recognized prefix."""
        assert validate_event_type_prefix("nodot") is False
