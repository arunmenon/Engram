"""Recording-port dispatch/lifecycle conformance, not production isolation."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import Depends, FastAPI, Request

from context_graph.api.dependencies import require_admin_key, require_api_key
from context_graph.api.tenants import (
    TenantServiceNotReadyError,
    _TenantDispatcher,
    create_tenant_app,
)
from context_graph.tenancy import TenantCatalog
from tests.unit.test_tenant_catalog import bind, grant


def catalog():
    return TenantCatalog(
        [bind("a"), bind("b")],
        [
            grant("a"),
            grant("b"),
            grant("a", token="admin-a" * 8, roles={"admin"}, credential_id="admin-a"),
            grant("a", token="rotation-a" * 8, credential_id="rotation-a"),
        ],
    )


def children(events, calls, *, fail=None, gate=None):
    def factory(binding):
        @asynccontextmanager
        async def lifetime(app):
            events.append(("open", binding.tenant_id))
            try:
                if binding.tenant_id == fail:
                    raise RuntimeError("controlled child initialization failure")
                yield
            finally:
                events.append(("close", binding.tenant_id))

        app = FastAPI(lifespan=lifetime)
        # Empty legacy keys must never bypass tenant principal guards.
        app.state.settings = SimpleNamespace(auth=SimpleNamespace(api_key=None, admin_key=None))

        @app.get("/v1/state", dependencies=[Depends(require_api_key)])
        async def state(request: Request):
            calls.append(binding.tenant_id)
            if gate:
                gate[0].set()
                await gate[1].wait()
            return {
                "tenant": binding.tenant_id,
                "database": binding.database_resource,
                "credential": request.scope["engram.principal"].credential_id,
            }

        @app.post("/v1/admin/action", dependencies=[Depends(require_admin_key)])
        async def admin():
            calls.append(binding.tenant_id)
            return {"tenant": binding.tenant_id}

        return app

    return factory


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "missing", "stale"])
async def test_public_factory_requires_all_runtime_checks(monkeypatch, failure):
    from context_graph.ports.errors import RuntimeFencedError

    events, calls, checks = [], [], []
    factory = children(events, calls)

    def bound_child(binding):
        child = factory(binding)
        check = AsyncMock()
        checks.append(check)
        if binding.tenant_id == "b" and failure == "stale":
            check.side_effect = RuntimeFencedError("stale")
        child.state.stores = SimpleNamespace(
            tenant_read_check=None if binding.tenant_id == "b" and failure == "missing" else check
        )
        return child

    monkeypatch.setattr("context_graph.api.tenants._create_bound_child", bound_child)
    gateway = create_tenant_app(catalog())
    if failure:
        with pytest.raises((TenantServiceNotReadyError, RuntimeFencedError)):
            await gateway._start()
        assert not gateway._ready
        assert events[-2:] == [("close", "b"), ("close", "a")]
    else:
        await gateway._start()
        try:
            for check in checks:
                check.assert_awaited_once()
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=gateway), base_url="http://test"
            ) as client:
                for tenant in ("a", "b"):
                    response = await client.get(
                        "/v1/state", headers={"Authorization": "Bearer " + tenant * 32}
                    )
                    assert response.status_code == 200
                    assert response.json()["tenant"] == tenant
        finally:
            await gateway._stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("public", [False, True])
async def test_authentication_routing_roles_rotation_and_rejected_requests_do_not_call_children(
    monkeypatch, public
):
    events, calls = [], []
    factory = children(events, calls)
    if public:
        def bound_child(binding):
            child = factory(binding)
            child.state.stores = SimpleNamespace(tenant_read_check=AsyncMock())
            return child

        monkeypatch.setattr("context_graph.api.tenants._create_bound_child", bound_child)
        gateway = create_tenant_app(catalog())
    else:
        gateway = _TenantDispatcher(catalog(), factory)
    await gateway._start()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=gateway), base_url="http://test"
        ) as client:
            for tenant in ("a", "b"):
                response = await client.get(
                    "/v1/state", headers={"Authorization": "Bearer " + tenant * 32}
                )
                assert response.json()["tenant"] == tenant
                assert response.json()["database"].endswith("/databases/tenant-" + tenant)
            rotation = await client.get(
                "/v1/state", headers={"Authorization": "Bearer " + "rotation-a" * 8}
            )
            assert rotation.json()["credential"] == "rotation-a"
            before = list(calls)
            for headers in (
                {},
                {"Authorization": "Bearer unknown"},
                {"Authorization": "Bearer " + "a" * 32, "X-Tenant-ID": "b"},
                [("Authorization", "Bearer " + "a" * 32), ("Authorization", "Bearer " + "b" * 32)],
            ):
                assert (await client.get("/v1/state", headers=headers)).status_code == 401
            assert (
                await client.post(
                    "/v1/admin/action", headers={"Authorization": "Bearer " + "a" * 32}
                )
            ).status_code == 403
            assert calls == before
            assert (
                await client.post(
                    "/v1/admin/action", headers={"Authorization": "Bearer " + "admin-a" * 8}
                )
            ).json() == {"tenant": "a"}
            before = list(calls)
            for path in ("/metrics", "/v1/webhooks/github"):
                assert (await client.get(path)).status_code == 503
            assert calls == before
            assert (await client.get("/health")).json() == {"status": "ready"}
            # The child cannot bypass role checks when called without dispatcher identity.
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=gateway._children["a"]), base_url="http://direct"
            ) as direct:
                assert (await direct.get("/v1/state")).status_code == 401
    finally:
        await gateway._stop()
    assert events == [("open", "a"), ("open", "b"), ("close", "b"), ("close", "a")]


@pytest.mark.asyncio
async def test_partial_startup_closes_open_children_and_never_serves():
    events, calls = [], []
    gateway = _TenantDispatcher(catalog(), children(events, calls, fail="b"))
    with pytest.raises(RuntimeError, match="controlled"):
        await gateway._start()
    assert events == [("open", "a"), ("open", "b"), ("close", "b"), ("close", "a")]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gateway), base_url="http://test"
    ) as client:
        assert (
            await client.get("/v1/state", headers={"Authorization": "Bearer " + "a" * 32})
        ).status_code == 503
    assert calls == []


@pytest.mark.asyncio
async def test_shutdown_drains_inflight_before_closing_and_refuses_new_requests():
    events, calls = [], []
    entered, release = asyncio.Event(), asyncio.Event()
    gateway = _TenantDispatcher(catalog(), children(events, calls, gate=(entered, release)))
    await gateway._start()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gateway), base_url="http://test"
    ) as client:
        request = asyncio.create_task(
            client.get("/v1/state", headers={"Authorization": "Bearer " + "a" * 32})
        )
        await asyncio.wait_for(entered.wait(), 2)
        shutdown = asyncio.create_task(gateway._stop())
        await asyncio.sleep(0)
        assert not shutdown.done()
        assert not any(kind == "close" for kind, _tenant in events)
        assert (
            await client.get("/v1/state", headers={"Authorization": "Bearer " + "b" * 32})
        ).status_code == 503
        release.set()
        assert (await request).status_code == 200
        await asyncio.wait_for(shutdown, 2)
    assert events[-2:] == [("close", "b"), ("close", "a")]
