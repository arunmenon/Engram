"""Authentication and shutdown guarantees for shared experiment plumbing."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from scripts.engram_experiment_support import DemoAuthentication, await_settled, stop_demo

from tests.unit.test_tenant_catalog import bind


class App:
    def __init__(self):
        self.check = AsyncMock()
        self.state = SimpleNamespace(stores=SimpleNamespace(tenant_read_check=self.check))
        self.principals = []

    async def __call__(self, scope, receive, send):
        self.principals.append(scope["engram.principal"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"private answer"})


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [("Authorization", "Bearer wrong")],
        [("Authorization", "Basic demo-test-credential-key")],
        [
            ("Authorization", "Bearer demo-test-credential-key"),
            ("Authorization", "Bearer demo-test-credential-key"),
        ],
    ],
)
async def test_demo_rejects_missing_invalid_and_ambiguous_credentials(headers):
    app = App()
    entry = DemoAuthentication(app, bind("a"), token="demo-test-credential-key")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=entry), base_url="http://demo"
    ) as client:
        response = await client.get("/v1/probe", headers=headers)
    assert response.status_code == 401
    assert not app.principals
    app.check.assert_not_awaited()


async def test_demo_authenticates_tenant_and_checks_before_response_release():
    app = App()
    entry = DemoAuthentication(app, bind("a"), token="demo-test-credential-key")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=entry), base_url="http://demo"
    ) as client:
        response = await client.get(
            "/v1/probe", headers={"Authorization": "Bearer demo-test-credential-key"}
        )
    assert response.status_code == 200
    assert app.principals[0].tenant_id == "a"
    assert app.check.await_count == 2


async def test_cancellation_waits_for_inflight_operation_before_propagating():
    entered, release = asyncio.Event(), asyncio.Event()
    settled = []

    async def operation():
        entered.set()
        await release.wait()
        settled.append(True)

    task = asyncio.create_task(await_settled(operation()))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled == [True]


async def test_shutdown_settles_workers_before_closing_stores():
    stopped, release = asyncio.Event(), asyncio.Event()
    order = []

    async def worker():
        await release.wait()
        order.append("worker settled")

    async def close():
        order.append("store closed")

    worker_task = asyncio.create_task(worker())
    shutdown = asyncio.create_task(
        stop_demo(
            [SimpleNamespace(stop=stopped.set)],
            [worker_task],
            [SimpleNamespace(close=close)],
            None,
            None,
        )
    )
    await stopped.wait()
    assert not shutdown.done() and order == []
    assert not worker_task.cancelled()
    release.set()
    assert await shutdown == []
    assert order == ["worker settled", "store closed"]


async def test_shutdown_retains_errors_and_still_closes_other_stores_and_server():
    closed = []

    async def failed_worker():
        raise RuntimeError("worker failed")

    async def failed_close():
        raise ValueError("close failed")

    async def good_close():
        closed.append(True)

    server = SimpleNamespace(should_exit=False)
    errors = await stop_demo(
        [],
        [asyncio.create_task(failed_worker())],
        [SimpleNamespace(close=failed_close), SimpleNamespace(close=good_close)],
        server,
        asyncio.create_task(asyncio.sleep(0)),
    )
    assert errors == ["RuntimeError", "ValueError"]
    assert closed == [True] and server.should_exit
