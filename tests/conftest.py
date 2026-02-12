"""Shared pytest fixtures for the context-graph test suite.

This conftest provides event factory fixtures that wrap the helpers in
``tests.fixtures.events``.  No external service dependencies are required
for unit tests.
"""

from __future__ import annotations

import pytest

from tests.fixtures.events import (
    make_agent_event,
    make_event,
    make_llm_event,
    make_session_events,
    make_tool_event,
)


@pytest.fixture()
def event_factory():
    """Return the ``make_event`` factory callable."""
    return make_event


@pytest.fixture()
def session_events_factory():
    """Return the ``make_session_events`` factory callable."""
    return make_session_events


@pytest.fixture()
def tool_event_factory():
    """Return the ``make_tool_event`` factory callable."""
    return make_tool_event


@pytest.fixture()
def agent_event_factory():
    """Return the ``make_agent_event`` factory callable."""
    return make_agent_event


@pytest.fixture()
def llm_event_factory():
    """Return the ``make_llm_event`` factory callable."""
    return make_llm_event


@pytest.fixture()
def sample_event():
    """A single pre-built Event for tests that just need one."""
    return make_event()


@pytest.fixture()
def sample_session_events():
    """Five sequential events sharing a session, for relationship tests."""
    return make_session_events(n=5)
