"""Capture ASGI sends to prove no response data escapes a failed final check."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from context_graph.api.tenant_responses import TenantResponseGuard
from context_graph.api.tenants import _create_bound_child
from context_graph.ports.errors import RuntimeFencedError
from context_graph.tenancy import Principal
from tests.unit.test_tenant_catalog import bind


def scope(**changes):
    return {
        "type": "http",
        "method": "GET",
        "path": "/v1/probe",
        "query_string": b"",
        "headers": [],
        "engram.principal": Principal("credential", "a", frozenset({"api"})),
        **changes,
    }


async def receive():
    return {"type": "http.request", "body": b"", "more_body": False}


def guard(app, check, **kwargs):
    child = SimpleNamespace(state=SimpleNamespace(stores=SimpleNamespace(tenant_read_check=check)))
    return TenantResponseGuard(app, child=child, binding=bind("a"), **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"", b'{"cached":"private answer"}'])
async def test_cached_or_empty_response_checks_before_execution_and_release(body):
    sent = []

    async def check():
        assert not sent

    checked = AsyncMock(side_effect=check)

    async def app(scope, receive, send):
        assert checked.await_count == 1
        await send({"type": "http.response.start", "status": 200, "headers": []})
        assert not sent
        await send({"type": "http.response.body", "body": body})

    await guard(app, checked)(scope(), receive, AsyncMock(side_effect=sent.append))
    assert checked.await_count == 2
    assert sent[0]["status"] == 200 and sent[1]["body"] == body


@pytest.mark.asyncio
@pytest.mark.parametrize("chunked", [False, True])
async def test_transition_after_handler_before_release_discards_every_private_byte(chunked):
    sent = []
    checked = AsyncMock(side_effect=[None, RuntimeFencedError("secret foreign control value")])

    async def app(scope, receive, send):
        await send(
            {"type": "http.response.start", "status": 200, "headers": [(b"x-private", b"secret")]}
        )
        await send({"type": "http.response.body", "body": b"private data", "more_body": chunked})
        if chunked:
            assert not sent
            await send({"type": "http.response.body", "body": b"", "more_body": False})

    await guard(app, checked)(scope(), receive, AsyncMock(side_effect=sent.append))
    assert sent[0]["status"] == 503
    assert b"private" not in sent[1]["body"] and b"secret" not in sent[1]["body"]
    assert (b"x-private", b"secret") not in sent[0]["headers"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [RuntimeFencedError("stale"), RuntimeError("backend unavailable")]
)
async def test_precheck_failure_never_calls_handler(failure):
    app = AsyncMock()
    sent = []
    await guard(app, AsyncMock(side_effect=failure))(
        scope(), receive, AsyncMock(side_effect=sent.append)
    )
    app.assert_not_awaited()
    assert sent[0]["status"] == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes,status",
    [
        ({"engram.principal": None}, 401),
        ({"engram.principal": Principal("other", "b", frozenset({"api"}))}, 403),
        ({"path": "/v1/events/import/"}, 503),
        ({"query_string": b"cursor="}, 400),
        ({"query_string": b"%63ursor=foreign"}, 400),
    ],
)
async def test_unauthorized_or_unfinished_entries_have_no_handler_or_storage_effects(
    changes, status
):
    app = AsyncMock()
    checked = AsyncMock()
    sent = []
    await guard(app, checked)(scope(**changes), receive, AsyncMock(side_effect=sent.append))
    app.assert_not_awaited()
    checked.assert_not_awaited()
    assert sent[0]["status"] == status


@pytest.mark.asyncio
async def test_chunked_response_has_bounded_materialization_before_release():
    sent = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"123", "more_body": True})
        assert not sent
        await send({"type": "http.response.body", "body": b"456", "more_body": False})

    await guard(app, AsyncMock(), max_body_bytes=5)(
        scope(), receive, AsyncMock(side_effect=sent.append)
    )
    assert sent[0]["status"] == 503 and b"123" not in sent[1]["body"]


@pytest.mark.asyncio
async def test_real_bound_fastapi_middleware_chunks_are_materialized_then_authorized():
    child = _create_bound_child(bind("a"))
    checked = AsyncMock()
    child.state.stores = SimpleNamespace(tenant_read_check=checked)

    @child.get("/v1/probe")
    async def probe():
        return {"answer": "cached result"}

    async def authenticated(scope, receive, send):
        scope = dict(scope)
        scope["engram.principal"] = Principal("credential", "a", frozenset({"api"}))
        await child(scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=authenticated), base_url="http://test"
    ) as client:
        response = await client.get("/v1/probe")
    assert response.status_code == 200 and response.json() == {"answer": "cached result"}
    assert checked.await_count == 2


@pytest.mark.asyncio
async def test_many_empty_chunks_preserve_bounded_payload_and_final_check():
    sent = []
    checked = AsyncMock()

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        for _ in range(1000):
            await send({"type": "http.response.body", "body": b"", "more_body": True})
            assert not sent
        await send({"type": "http.response.body", "body": b"ok"})

    await guard(app, checked, max_body_bytes=2)(
        scope(), receive, AsyncMock(side_effect=sent.append)
    )
    assert checked.await_count == 2
    assert sent[1]["body"] == b"ok"


@pytest.mark.asyncio
async def test_bound_route_control_refusal_is_sanitized_503_when_outer_checks_still_pass():
    child = _create_bound_child(bind("a"))
    child.state.stores = SimpleNamespace(tenant_read_check=AsyncMock())

    @child.get("/v1/probe")
    async def probe():
        raise RuntimeFencedError("secret foreign database details")

    async def authenticated(scope, receive, send):
        scope = dict(scope)
        scope["engram.principal"] = Principal("credential", "a", frozenset({"api"}))
        await child(scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=authenticated), base_url="http://test"
    ) as client:
        response = await client.get("/v1/probe")
    assert response.status_code == 503
    assert "secret" not in response.text and "foreign" not in response.text
