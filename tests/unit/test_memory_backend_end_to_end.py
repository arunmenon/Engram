"""End-to-end run on the in-memory backend (ADR-0019 §6).

Proof that nothing above the ports depends on Redis or Neo4j: with every
``CG_STORAGE_*`` set to ``memory``, events go in through the real API,
the real projection and enrichment workers drain their subscriptions,
and context, lineage, subgraph and health answer through the real routes
and retrieval engine.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
import pytest

from context_graph.adapters.registry import Stores, open_stores
from context_graph.api.app import create_app, lifespan
from context_graph.settings import Settings
from context_graph.worker.enrichment import EnrichmentConsumer
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from context_graph.worker.consumer import BaseConsumer

STORAGE_PORTS = ("EVENT_LOG", "SUBSCRIPTION", "GRAPH", "KEYWORD_INDEX", "VECTOR_INDEX")


async def _drain(consumer: BaseConsumer, stores: Stores, group: str) -> None:
    """Run a consumer until its group has nothing undelivered or pending."""
    probe = stores.subscription(group, "drain-probe")
    task = asyncio.create_task(consumer.run())
    for _ in range(200):
        await asyncio.sleep(0.02)
        if await probe.lag() == 0 and not await consumer._subscription.delivery_counts(100):
            break
    consumer.stop()
    await asyncio.wait_for(task, timeout=5)


def _event(event_id: str, session_id: str, minutes_ago: int, **extra: object) -> dict:
    return {
        "event_id": event_id,
        "event_type": "tool.execute",
        "occurred_at": (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat(),
        "session_id": session_id,
        "agent_id": "agent-1",
        "trace_id": "trace-1",
        "payload_ref": "payload:1",
        "tool_name": "grep",
        **extra,
    }


@pytest.mark.asyncio()
async def test_api_and_workers_run_on_memory_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    for port in STORAGE_PORTS:
        monkeypatch.setenv(f"CG_STORAGE_{port}", "memory")
    monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
    monkeypatch.delenv("CG_AUTH_API_KEY", raising=False)
    settings = Settings()

    # One process: the API and the workers share the same in-memory stores.
    stores = await open_stores(settings, prepare_ingest=True)

    async def shared_stores(*_args: object, **_kwargs: object) -> Stores:
        return stores

    monkeypatch.setattr("context_graph.api.app.open_stores", shared_stores)

    session_id = f"session-{uuid4().hex[:8]}"
    root, child, grandchild = (str(uuid4()) for _ in range(3))

    app = create_app()
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # -- ingest through the API ---------------------------------------
            for body in (
                _event(root, session_id, 3),
                _event(child, session_id, 2, parent_event_id=root),
                _event(grandchild, session_id, 1, parent_event_id=child),
            ):
                response = await client.post("/v1/events", json=body)
                assert response.status_code == 201, response.text
            duplicate = await client.post("/v1/events", json=_event(root, session_id, 3))
            assert duplicate.status_code == 201
            assert await stores.event_log.stream_length() == 3  # type: ignore[attr-defined]

            # -- workers drain their subscriptions ----------------------------
            projection = ProjectionConsumer(
                subscription=stores.subscription(
                    settings.consumer.group_projection, "projection-1"
                ),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
            )
            await _drain(projection, stores, settings.consumer.group_projection)
            enrichment = EnrichmentConsumer(
                subscription=stores.subscription(
                    settings.consumer.group_enrichment, "enrichment-1"
                ),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
            )
            await _drain(enrichment, stores, settings.consumer.group_enrichment)

            stats = await stores.graph.get_graph_stats()
            assert stats["nodes"]["Event"] == 3
            assert stats["edges"]["CAUSED_BY"] == 2
            assert stats["edges"]["FOLLOWS"] == 2

            # -- retrieval through the API ------------------------------------
            context = (await client.get(f"/v1/context/{session_id}")).json()
            assert set(context["nodes"]) == {root, child, grandchild}
            node = context["nodes"][root]
            assert node["provenance"]["source"] == "memory"
            assert node["provenance"]["global_position"]
            assert node["attributes"]["keywords"] == ["tool", "execute", "grep"]

            lineage = (await client.get(f"/v1/nodes/{grandchild}/lineage")).json()
            assert set(lineage["nodes"]) == {root, child, grandchild}
            assert {e["edge_type"] for e in lineage["edges"]} == {"CAUSED_BY"}

            subgraph = (
                await client.post(
                    "/v1/query/subgraph",
                    json={"query": "what did grep do", "session_id": session_id, "agent_id": "a"},
                )
            ).json()
            assert set(subgraph["nodes"]) >= {root, child, grandchild}
            assert subgraph["meta"]["retrieval_channels"]["graph"] == 3

            health = (await client.get("/v1/health")).json()
            assert health["event_log"] == {"backend": "memory", "ok": True}
            assert health["graph"] == {"backend": "memory", "ok": True}
