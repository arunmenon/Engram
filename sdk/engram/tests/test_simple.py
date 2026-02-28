from __future__ import annotations

import httpx
import pytest
import respx

import engram.simple as simple_mod
from engram.config import reset_config
from tests.conftest import make_atlas_response, make_ingest_response


@pytest.fixture(autouse=True)
def _reset_simple_state():
    """Reset simple module state between tests."""
    simple_mod._default_client = None
    simple_mod._default_session = None
    reset_config()
    yield
    simple_mod._default_client = None
    simple_mod._default_session = None
    reset_config()


@pytest.fixture
def mock_simple_api():
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


class TestRecordCreatesSession:
    async def test_record_creates_session(self, mock_simple_api: respx.MockRouter) -> None:
        """First record() auto-creates client and session."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        # Mock: session_start + the actual record
        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        result = await simple_mod.record("test message", agent_id="my-agent")

        assert result.global_position == "1707644400000-0"
        assert simple_mod._default_client is not None
        assert simple_mod._default_session is not None

        # Should have 2 calls: session_start + record
        assert len(mock_simple_api.calls) == 2


class TestRecordReusesSession:
    async def test_record_reuses_session(self, mock_simple_api: respx.MockRouter) -> None:
        """Second record() reuses same session."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        await simple_mod.record("first")
        session_after_first = simple_mod._default_session
        session_id = session_after_first.id

        await simple_mod.record("second")
        assert simple_mod._default_session is session_after_first
        assert simple_mod._default_session.id == session_id


class TestRecallUsesSession:
    async def test_recall_uses_session(self, mock_simple_api: respx.MockRouter) -> None:
        """recall() uses current session_id when no session_id provided."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        # First create a session via record
        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )
        await simple_mod.record("first")

        session_id = simple_mod._default_session.id

        atlas = make_atlas_response()
        mock_simple_api.get(f"/context/{session_id}").mock(
            return_value=httpx.Response(200, json=atlas)
        )

        result = await simple_mod.recall(query="test")
        assert result.meta.query_ms == 42


class TestRecallExplicitSession:
    async def test_recall_explicit_session(self, mock_simple_api: respx.MockRouter) -> None:
        """recall(session_id=...) uses the provided session_id."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        atlas = make_atlas_response()
        mock_simple_api.get("/context/custom-session-123").mock(
            return_value=httpx.Response(200, json=atlas)
        )

        result = await simple_mod.recall(query="hello", session_id="custom-session-123")
        assert result.meta.query_ms == 42


class TestTraceDelegates:
    async def test_trace_delegates(self, mock_simple_api: respx.MockRouter) -> None:
        """trace() calls client.get_lineage."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        atlas = make_atlas_response()
        mock_simple_api.get("/nodes/node-abc/lineage").mock(
            return_value=httpx.Response(200, json=atlas)
        )

        result = await simple_mod.trace("node-abc", max_depth=5, intent="when")
        assert result.meta.query_ms == 42

        request = mock_simple_api.calls.last.request
        assert "max_depth=5" in str(request.url)
        assert "intent=when" in str(request.url)


class TestConfigureResets:
    async def test_configure_resets(self, mock_simple_api: respx.MockRouter) -> None:
        """configure() resets client and session."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        await simple_mod.record("first")
        assert simple_mod._default_client is not None
        assert simple_mod._default_session is not None

        # Now reconfigure
        simple_mod.configure(base_url="http://test:8000", api_key="new-key")
        assert simple_mod._default_client is None
        assert simple_mod._default_session is None
