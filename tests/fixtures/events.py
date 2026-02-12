"""Event factory functions for tests.

Provides convenience builders for creating Event instances with sensible
defaults. Every function accepts **overrides so callers can replace any field.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from context_graph.domain.models import Event


def make_event(**overrides) -> Event:
    """Create a single Event with sensible defaults.

    All required fields are populated with deterministic test values except
    ``event_id`` which gets a fresh UUID on each call.  Pass keyword arguments
    to override any field.
    """
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


def make_session_events(n: int = 5, session_id: str | None = None) -> list[Event]:
    """Create *n* events in sequence for a single session.

    Events are ordered by ``occurred_at`` with 1-second spacing.  Each event
    after the first carries a ``parent_event_id`` pointing at the previous
    event, implying a FOLLOWS relationship.
    """
    from datetime import timedelta

    session_id = session_id or f"session-{uuid4().hex[:8]}"
    base_time = datetime.now(UTC)
    trace_id = f"trace-{uuid4().hex[:8]}"

    events: list[Event] = []
    for i in range(n):
        parent_id = events[-1].event_id if events else None
        event = make_event(
            session_id=session_id,
            trace_id=trace_id,
            occurred_at=base_time + timedelta(seconds=i),
            parent_event_id=parent_id,
        )
        events.append(event)
    return events


def make_tool_event(tool_name: str = "test-tool", **overrides) -> Event:
    """Convenience factory for ``tool.execute`` events."""
    overrides.setdefault("event_type", "tool.execute")
    overrides.setdefault("tool_name", tool_name)
    return make_event(**overrides)


def make_agent_event(**overrides) -> Event:
    """Convenience factory for ``agent.invoke`` events."""
    overrides.setdefault("event_type", "agent.invoke")
    return make_event(**overrides)


def make_llm_event(**overrides) -> Event:
    """Convenience factory for ``llm.chat`` events."""
    overrides.setdefault("event_type", "llm.chat")
    return make_event(**overrides)
