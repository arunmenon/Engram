"""PDLC end to end: webhooks to a PDLC graph with no hand-written queries (ADR-0018 phase 1).

Signed GitHub and Jira deliveries go through the real API into the ledger;
the real projection worker, with the configured ontology, projects them;
the graph is read back through the PackGraph port only.

- ``memory`` always runs;
- ``spanner`` runs against the emulator (``CG_SPANNER_EMULATOR_HOST``,
  marked ``integration``) in a fresh database dropped afterwards;
- ``neo4j`` keeps the ledger in memory and the graph in Neo4j
  (``CG_NEO4J_*``, marked ``integration``), emptied before and after.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import os
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
import pytest

from context_graph.adapters.registry import Stores, open_stores
from context_graph.api.app import create_app, lifespan
from context_graph.ontology.runtime import configured_projector
from context_graph.ports.pack_graph import NodeRef
from context_graph.settings import Settings
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "webhooks"
SECRET = "e2e-secret"  # noqa: S105 - test value, not a credential
STORAGE_PORTS = ("EVENT_LOG", "SUBSCRIPTION", "GRAPH", "KEYWORD_INDEX", "VECTOR_INDEX")

DELIVERIES = [
    ("github", "pull_request", "github_pull_request_opened"),
    ("github", "check_run", "github_check_run_completed"),
    ("github", "pull_request_review", "github_pull_request_review_submitted"),
    ("github", "pull_request", "github_pull_request_merged"),
    ("jira", None, "jira_issue_created"),
    ("github", "release", "github_release_published"),
    ("github", "deployment_status", "github_deployment_status_success"),
    ("jira", None, "jira_issue_updated_done"),
]


def _headers(source: str, event_name: str | None, body: bytes, delivery: str) -> dict[str, str]:
    signature = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    if source == "github":
        return {
            "X-GitHub-Event": event_name or "",
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": signature,
        }
    return {"X-Hub-Signature": signature, "X-Atlassian-Webhook-Identifier": delivery}


async def _drain(consumer: ProjectionConsumer, stores: Stores, group: str) -> None:
    probe = stores.subscription(group, "drain-probe")
    task = asyncio.create_task(consumer.run())
    for _ in range(400):
        await asyncio.sleep(0.02)
        if await probe.lag() == 0 and not await consumer._subscription.delivery_counts(100):
            break
    consumer.stop()
    await asyncio.wait_for(task, timeout=10)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "backend",
    [
        "memory",
        pytest.param("spanner", marks=pytest.mark.integration),
        pytest.param("neo4j", marks=pytest.mark.integration),
    ],
)
async def test_webhooks_build_a_pdlc_graph(monkeypatch: pytest.MonkeyPatch, backend: str) -> None:
    for port in STORAGE_PORTS:
        monkeypatch.setenv(f"CG_STORAGE_{port}", backend)
    if backend == "neo4j":
        for port in ("EVENT_LOG", "SUBSCRIPTION", "KEYWORD_INDEX"):
            monkeypatch.setenv(f"CG_STORAGE_{port}", "memory")
    if backend == "spanner":
        emulator = os.environ.get("CG_SPANNER_EMULATOR_HOST")
        if not emulator:
            pytest.skip("Spanner emulator not configured (CG_SPANNER_EMULATOR_HOST)")
        pytest.importorskip("google.cloud.spanner")
        monkeypatch.setenv("CG_SPANNER_DATABASE", f"pdlc{uuid4().hex[:12]}")
        monkeypatch.setenv("CG_SPANNER_CREATE_IF_MISSING", "true")
    monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
    monkeypatch.setenv("CG_WEBHOOK_GITHUB_SECRET", SECRET)
    monkeypatch.setenv("CG_WEBHOOK_JIRA_SECRET", SECRET)
    monkeypatch.delenv("CG_AUTH_API_KEY", raising=False)
    monkeypatch.delenv("CG_ONTOLOGY_PACKS", raising=False)
    settings = Settings()

    try:
        stores = await asyncio.wait_for(open_stores(settings, prepare_ingest=True), timeout=15)
    except Exception as exc:  # noqa: BLE001
        if backend == "memory":
            raise
        pytest.skip(f"{backend} unreachable: {exc}")
    if backend == "neo4j":
        await stores.graph.delete_all(confirm=True)  # type: ignore[attr-defined]
    close = stores.close

    async def keep_open() -> None:
        """The app's shutdown must not close stores the worker still uses."""

    monkeypatch.setattr(stores, "close", keep_open)
    try:
        await _run(monkeypatch, settings, stores)
    finally:
        if backend == "spanner":
            with contextlib.suppress(Exception):
                await asyncio.to_thread(stores.event_log.database.drop)  # type: ignore[attr-defined]
        if backend == "neo4j":
            await stores.graph.delete_all(confirm=True)  # type: ignore[attr-defined]
        await close()


async def _run(monkeypatch: pytest.MonkeyPatch, settings: Settings, stores: Stores) -> None:
    async def shared_stores(*_args: object, **_kwargs: object) -> Stores:
        return stores

    monkeypatch.setattr("context_graph.api.app.open_stores", shared_stores)
    app = create_app()
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for index, (source, event_name, fixture) in enumerate(DELIVERIES):
                body = (FIXTURES / f"{fixture}.json").read_bytes()
                response = await client.post(
                    f"/v1/webhooks/{source}",
                    content=body,
                    headers=_headers(source, event_name, body, f"delivery-{index}"),
                )
                assert response.status_code == 202, response.text
                assert len(response.json()["event_ids"]) == 1

            # A pack-owned namespace accepts only declared types
            rejected = await client.post(
                "/v1/events",
                json={
                    "event_id": str(uuid4()),
                    "event_type": "pdlc.change.exploded",
                    "occurred_at": "2026-10-01T09:00:00Z",
                    "session_id": "s",
                    "agent_id": "a",
                    "trace_id": "t",
                    "payload_ref": "p",
                },
            )
            assert rejected.status_code == 422, rejected.text

            # Webhook agent ids cannot be claimed through the generic ingest
            spoofed = await client.post(
                "/v1/events",
                json={
                    "event_id": str(uuid4()),
                    "event_type": "pdlc.change.created",
                    "occurred_at": "2026-10-01T09:00:00Z",
                    "session_id": "s",
                    "agent_id": "webhook:github",
                    "trace_id": "t",
                    "payload_ref": "p",
                    "payload": {"repo": "acme/payments", "number": 1, "title": "evil"},
                },
            )
            assert spoofed.status_code == 422, spoofed.text
            assert "reserved" in spoofed.text

    projection = ProjectionConsumer(
        subscription=stores.subscription(settings.consumer.group_projection, "projection-1"),
        event_log=stores.event_log,
        graph_store=stores.graph,
        settings=settings,
        pack_projector=configured_projector(settings.ontology),
        pack_lookup_limit=settings.ontology.lookup_limit,
    )
    await _drain(projection, stores, settings.consumer.group_projection)
    await _check_graph(stores.graph)


async def _check_graph(graph: GraphBackend) -> None:
    change = NodeRef("Change", "Change:acme/payments|7")
    work_item = NodeRef("WorkItem", "WorkItem:jira|PAY-341")
    release = NodeRef("Release", "Release:acme/payments|v1.4.0")
    nodes = await graph.get_nodes([change, work_item, release])

    assert nodes[change]["status"] == "merged"
    assert nodes[change]["merge_sha"] == "def456"
    assert nodes[change]["source_trust"] == "trusted"
    assert nodes[work_item]["status"] == "done"  # created To Do, then closed Done
    assert nodes[work_item]["title"] == "Refund retries"
    assert nodes[release]["node_type"] == "Release"

    def links(rows: list[dict[str, object]]) -> set[tuple[object, ...]]:
        return {(r["edge_type"], r["node_label"]) for r in rows}

    around_change = await graph.neighbors([change], None, "both", 100)
    assert links(around_change) >= {
        ("IMPLEMENTS", "WorkItem"),
        ("REVIEWS", "Review"),
        ("RAN_AGAINST", "TestRun"),
        ("INCLUDES", "Release"),
        ("DERIVED_FROM", "Event"),
    }
    implements = next(r for r in around_change if r["edge_type"] == "IMPLEMENTS")
    assert implements["properties"]["link_status"] == "confirmed"
    parents = await graph.neighbors([work_item], ["DECOMPOSES_INTO"], "in", 10)
    assert [r["source_key"] for r in parents] == ["WorkItem:jira|PAY-300"]
    deployments = await graph.find_nodes("Deployment", {"environment": "production"}, 10)
    assert [d["status"] for d in deployments] == ["succeeded"]
