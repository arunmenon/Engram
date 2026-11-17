"""Control-plane behavior with a simulated durable runner, not live Spanner."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from context_graph.workbench.api import create_app


@pytest.mark.asyncio
async def test_capacity_auth_and_cancel_remains_running_until_cleanup(tmp_path, monkeypatch):
    started = asyncio.Event()
    cleaning = asyncio.Event()
    release = asyncio.Event()
    execution = SimpleNamespace(
        pool=SimpleNamespace(
            status=lambda: {"backend": "spanner", "capacity": 1, "available": 0, "slots": []}
        )
    )

    async def run(_journey, *, execution: object, progress):
        assert execution is not None
        progress({"backend": "spanner", "phase": "running", "cleanup": "pending"})
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            progress({"backend": "spanner", "phase": "cleaning", "cleanup": "pending"})
            cleaning.set()
            await release.wait()
            progress({"backend": "spanner", "phase": "released", "cleanup": "verified"})

    monkeypatch.setattr("context_graph.workbench.api.run_journey", run)
    app = create_app(database=tmp_path / "drafts.db", operators={"a": "alice"}, execution=execution)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.get("/admin/sandbox-capacity")).status_code == 401
        client.headers["Authorization"] = "Bearer a"
        assert (await client.get("/admin/capabilities")).json()["sandbox"] == "spanner"
        assert (await client.get("/admin/sandbox-capacity")).json()["available"] == 0
        draft = (await client.post("/admin/journeys/implementation")).json()
        root = f"/admin/tenants/{draft['id']}"
        response = await client.post(root + "/journey-run", json={"revision": draft["revision"]})
        assert response.status_code == 202
        await asyncio.wait_for(started.wait(), 2)
        draft = (await client.get(root)).json()
        response = await client.post(root + "/cancel", json={"revision": draft["revision"]})
        assert response.json()["job"]["status"] == "running"
        assert response.json()["job"]["cancelling"]
        await asyncio.wait_for(cleaning.wait(), 2)
        draft = (await client.get(root)).json()
        assert draft["storage_run"]["phase"] == "cleaning"
        assert (
            await client.post(root + "/journey-run", json={"revision": draft["revision"]})
        ).status_code == 409
        release.set()
        for _ in range(100):
            await asyncio.sleep(0.01)
            draft = (await client.get(root)).json()
            if draft["job"]["status"] != "running":
                break
        assert draft["job"]["status"] == "cancelled"
        assert draft["storage_run"]["cleanup"] == "verified"
        assert not draft.get("journey_result")
