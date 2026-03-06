from __future__ import annotations

import uuid

import httpx
import pytest
import respx

from engram import EngramClient, EngramConfig
from engram.sessions import SessionManager
from tests.conftest import make_atlas_response, make_ingest_response


@pytest.fixture
def session_config() -> EngramConfig:
    return EngramConfig(base_url="http://test:8000", api_key="test-key")


@pytest.fixture
def session_client(session_config: EngramConfig) -> EngramClient:
    return EngramClient(config=session_config)


@pytest.fixture
def mock_session_api():
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


class TestSessionAutoIds:
    def test_session_auto_ids(self, session_client: EngramClient) -> None:
        """session_id and trace_id are auto-generated UUIDs."""
        session = SessionManager(client=session_client, agent_id="test-agent")
        # Verify they are valid UUID4 strings
        parsed_session = uuid.UUID(session.id)
        parsed_trace = uuid.UUID(session.trace_id)
        assert parsed_session.version == 4
        assert parsed_trace.version == 4
        assert session.id != session.trace_id


class TestSessionRecord:
    async def test_session_record(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """record() creates event with correct fields."""
        ingest_resp = make_ingest_response()
        mock_session_api.post("/events").mock(return_value=httpx.Response(200, json=ingest_resp))

        session = SessionManager(client=session_client, agent_id="agent-x")
        result = await session.record("hello world", event_type="tool.execute", importance=7)

        assert result.event_id == ingest_resp["event_id"]
        assert result.global_position == ingest_resp["global_position"]

        # Verify the request payload
        request = mock_session_api.calls.last.request
        import json

        body = json.loads(request.content)
        assert body["event_type"] == "tool.execute"
        assert body["session_id"] == session.id
        assert body["agent_id"] == "agent-x"
        assert body["trace_id"] == session.trace_id
        assert body["payload_ref"] == "hello world"
        assert body["importance_hint"] == 7


class TestSessionEventChaining:
    async def test_session_event_chaining(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """parent_event_id set to previous event's event_id."""
        resp1 = make_ingest_response()
        resp2 = make_ingest_response()
        mock_session_api.post("/events").mock(
            side_effect=[
                httpx.Response(200, json=resp1),
                httpx.Response(200, json=resp2),
            ]
        )

        session = SessionManager(client=session_client, agent_id="agent-x")

        # First event — no parent
        await session.record("first")
        import json

        body1 = json.loads(mock_session_api.calls[0].request.content)
        assert "parent_event_id" not in body1

        # Second event — parent should be first event's id
        await session.record("second")
        body2 = json.loads(mock_session_api.calls[1].request.content)
        assert body2["parent_event_id"] == body1["event_id"]


class TestSessionEventCount:
    async def test_session_event_count(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """event_count increments after each record."""
        mock_session_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        session = SessionManager(client=session_client, agent_id="agent-x")
        assert session.event_count == 0

        await session.record("one")
        assert session.event_count == 1

        await session.record("two")
        assert session.event_count == 2


class TestSessionContext:
    async def test_session_context(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """context() delegates to client.get_context with session id."""
        atlas = make_atlas_response()
        session = SessionManager(client=session_client, agent_id="agent-x")

        mock_session_api.get(f"/context/{session.id}").mock(
            return_value=httpx.Response(200, json=atlas)
        )

        result = await session.context(query="test query", max_nodes=50)
        assert result.meta.query_ms == 42

        request = mock_session_api.calls.last.request
        assert "query=test+query" in str(request.url) or "query=test%20query" in str(request.url)


class TestSessionStartEvent:
    async def test_session_start_event(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """__aenter__ sends system.session_start event."""
        mock_session_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        session = SessionManager(client=session_client, agent_id="agent-x")
        await session.__aenter__()

        import json

        body = json.loads(mock_session_api.calls.last.request.content)
        assert body["event_type"] == "system.session_start"
        assert body["payload_ref"] == "Session started"


class TestSessionEndEvent:
    async def test_session_end_event(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """__aexit__ sends system.session_end event."""
        mock_session_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        session = SessionManager(client=session_client, agent_id="agent-x")
        await session.__aenter__()
        await session.__aexit__(None, None, None)

        import json

        # Last call should be session_end
        body = json.loads(mock_session_api.calls.last.request.content)
        assert body["event_type"] == "system.session_end"
        assert body["payload_ref"] == "Session ended"


class TestSessionEndIdempotent:
    async def test_session_end_idempotent(
        self, mock_session_api: respx.MockRouter, session_client: EngramClient
    ) -> None:
        """Calling end() twice only sends one session_end event."""
        mock_session_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response())
        )

        session = SessionManager(client=session_client, agent_id="agent-x")
        await session.__aenter__()  # 1 call (session_start)

        result1 = await session.end()  # 2nd call (session_end)
        assert result1 is not None

        result2 = await session.end()  # Should be no-op
        assert result2 is None

        # Only 2 calls total: session_start + session_end
        assert len(mock_session_api.calls) == 2


class TestSessionProperties:
    def test_session_properties(self, session_client: EngramClient) -> None:
        """.id, .trace_id, .event_count are accessible."""
        session = SessionManager(client=session_client, agent_id="test-agent")
        assert isinstance(session.id, str)
        assert isinstance(session.trace_id, str)
        assert session.event_count == 0
        assert len(session.id) == 36  # UUID string length
        assert len(session.trace_id) == 36
