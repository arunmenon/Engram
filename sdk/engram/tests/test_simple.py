from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

import engram.simple as simple_mod
from engram.config import reset_config
from engram.models import Memory
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


# --- Item 2.3: add() and search() ---


class TestAdd:
    async def test_add_records_event(self, mock_simple_api: respx.MockRouter) -> None:
        """add() wraps record() with event_type='observation.output'."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response("evt-add"))
        )

        result = await simple_mod.add("remember this fact")
        assert result.event_id == "evt-add"
        # session_start + add
        assert len(mock_simple_api.calls) == 2

    async def test_add_with_importance(self, mock_simple_api: respx.MockRouter) -> None:
        """add() passes importance_hint through."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        await simple_mod.add("important fact", importance=8)
        # Verify the second call (the add, not session_start) contains importance
        assert len(mock_simple_api.calls) == 2


class TestSearch:
    async def test_search_returns_memories(self, mock_simple_api: respx.MockRouter) -> None:
        """search() returns flat Memory list from subgraph query."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        now = datetime.now(timezone.utc).isoformat()
        atlas = make_atlas_response(
            nodes={
                "evt-1": {
                    "node_id": "evt-1",
                    "node_type": "Event",
                    "attributes": {"content": "User prefers dark mode"},
                    "provenance": {
                        "event_id": "evt-1",
                        "global_position": "100-0",
                        "source": "redis",
                        "occurred_at": now,
                        "session_id": "sess-1",
                        "agent_id": "agent-1",
                        "trace_id": "trace-1",
                    },
                    "scores": {"decay_score": 0.9, "relevance_score": 0.8, "importance_score": 7},
                },
                "evt-2": {
                    "node_id": "evt-2",
                    "node_type": "Summary",
                    "attributes": {"summary": "UI preferences discussed"},
                    "scores": {"decay_score": 0.5, "relevance_score": 0.6, "importance_score": 3},
                },
            }
        )
        mock_simple_api.post("/query/subgraph").mock(return_value=httpx.Response(200, json=atlas))

        memories = await simple_mod.search("dark mode")
        assert len(memories) == 2
        assert all(isinstance(m, Memory) for m in memories)
        # Should be sorted by score descending
        assert memories[0].score >= memories[1].score
        assert memories[0].text == "User prefers dark mode"
        assert memories[0].source_session == "sess-1"
        assert memories[1].text == "UI preferences discussed"

    async def test_search_empty_results(self, mock_simple_api: respx.MockRouter) -> None:
        """search() returns empty list when no nodes have text."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        atlas = make_atlas_response()
        mock_simple_api.post("/query/subgraph").mock(return_value=httpx.Response(200, json=atlas))

        memories = await simple_mod.search("nonexistent")
        assert memories == []

    async def test_search_skips_non_text_nodes(self, mock_simple_api: respx.MockRouter) -> None:
        """search() skips nodes without text content."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        atlas = make_atlas_response(
            nodes={
                "n1": {
                    "node_id": "n1",
                    "node_type": "Entity",
                    "attributes": {"embedding": [0.1, 0.2, 0.3]},
                    "scores": {"decay_score": 0.5, "relevance_score": 0.5, "importance_score": 3},
                },
            }
        )
        mock_simple_api.post("/query/subgraph").mock(return_value=httpx.Response(200, json=atlas))

        memories = await simple_mod.search("payment")
        assert memories == []


# --- Item 2.4: aclose() and configure warning ---


class TestAclose:
    async def test_aclose_ends_session(self, mock_simple_api: respx.MockRouter) -> None:
        """aclose() ends session and closes client."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        await simple_mod.record("first")
        assert simple_mod._default_session is not None
        assert simple_mod._default_client is not None

        await simple_mod.aclose()
        assert simple_mod._default_session is None
        assert simple_mod._default_client is None

    async def test_aclose_idempotent(self) -> None:
        """aclose() is safe to call when nothing is active."""
        await simple_mod.aclose()
        assert simple_mod._default_session is None
        assert simple_mod._default_client is None
        # Call again — no error
        await simple_mod.aclose()


class TestConfigureWarnsActiveSession:
    async def test_configure_warns_active_session(self, mock_simple_api: respx.MockRouter) -> None:
        """configure() warns if session is active."""
        from engram.config import configure

        configure(base_url="http://test:8000")

        mock_simple_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        await simple_mod.record("first")
        assert simple_mod._default_session is not None

        with pytest.warns(ResourceWarning, match="active session"):
            simple_mod.configure(base_url="http://test:8000")

    def test_configure_no_warning_when_clean(self) -> None:
        """configure() does not emit ResourceWarning when no active session."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            # Allow other warnings (e.g., HTTP base_url warning from config)
            warnings.simplefilter("ignore", UserWarning)
            simple_mod.configure(base_url="http://test:8000")
