"""A new domain pack, end to end, with no code for it (ADR-0018; review finding 2.8).

``tests/fixtures/packs/crm`` is a small CRM pack the engine knows nothing
about, loaded from ``CG_ONTOLOGY_PACK_DIRS`` with no PDLC pack active. Its
events go through ``POST /v1/events/batch`` from a trusted importer, the
projection worker builds the graph, the evaluation gate holds its intents
back until ``evaluate --record`` passes, and artifact questions are answered
through the API. A blue/green rebuild gated on the pack's evaluation set
reproduces the graph. Runs on every graph backend.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.registry import Stores, open_stores
from context_graph.api.app import create_app, lifespan
from context_graph.ontology.__main__ import evaluate_graph
from context_graph.ontology.rebuild import rebuild
from context_graph.ontology.runtime import configured_projector
from context_graph.ontology.versioning import reconcile
from context_graph.ports.pack_graph import NodeRef
from context_graph.settings import Settings
from context_graph.worker.projection import ProjectionConsumer

CRM = Path(__file__).resolve().parents[1] / "fixtures" / "packs" / "crm"
IMPORTER = "importer:crm"
STORAGE_PORTS = ("EVENT_LOG", "SUBSCRIPTION", "GRAPH", "KEYWORD_INDEX", "VECTOR_INDEX")
START = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)

# (event type, payload): the ledger the evaluation set's answers come from
HISTORY: list[tuple[str, dict[str, Any]]] = [
    ("crm.account.created", {"account_id": "acme", "name": "Acme", "industry": "retail"}),
    ("crm.account.created", {"account_id": "globex", "name": "Globex", "industry": "energy"}),
    ("crm.account.created", {"account_id": "initech", "name": "Initech", "industry": "software"}),
    ("crm.contact.added", {"email": "ann@acme.com", "name": "Ann", "account_id": "acme"}),
    ("crm.contact.added", {"email": "bo@globex.com", "name": "Bo", "account_id": "globex"}),
    ("crm.deal.created", {"deal_id": "D-1", "title": "Pilot", "account_id": "acme", "amount": 10}),
    ("crm.deal.created", {"deal_id": "D-2", "title": "Rollout", "account_id": "acme"}),
    ("crm.deal.replaced", {"deal_id": "D-1", "replaced_by": "D-2"}),
    ("crm.deal.created", {"deal_id": "D-7", "title": "Renewal", "account_id": "acme"}),
    ("crm.deal.won", {"deal_id": "D-7"}),
    ("crm.deal.created", {"deal_id": "D-8", "title": "Trial", "account_id": "globex"}),
]


def _events() -> list[dict[str, Any]]:
    return [
        {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "occurred_at": (START + timedelta(minutes=minute)).isoformat(),
            "session_id": "crm:import",
            "agent_id": IMPORTER,
            "trace_id": "crm-import",
            "payload_ref": f"crm:{minute}",
            "payload": payload,
        }
        for minute, (event_type, payload) in enumerate(HISTORY)
    ]


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
async def test_a_new_pack_needs_no_code(monkeypatch: pytest.MonkeyPatch, backend: str) -> None:
    for port in STORAGE_PORTS:
        monkeypatch.setenv(f"CG_STORAGE_{port}", backend)
    if backend == "neo4j":
        for port in ("EVENT_LOG", "SUBSCRIPTION", "KEYWORD_INDEX"):
            monkeypatch.setenv(f"CG_STORAGE_{port}", "memory")
    if backend == "spanner":
        if not os.environ.get("CG_SPANNER_EMULATOR_HOST"):
            pytest.skip("Spanner emulator not configured (CG_SPANNER_EMULATOR_HOST)")
        pytest.importorskip("google.cloud.spanner")
        monkeypatch.setenv("CG_SPANNER_DATABASE", f"crm{uuid4().hex[:12]}")
        monkeypatch.setenv("CG_SPANNER_CREATE_IF_MISSING", "true")
    monkeypatch.setenv("CG_ONTOLOGY_PACKS", "crm")
    monkeypatch.setenv("CG_ONTOLOGY_PACK_DIRS", str(CRM))
    monkeypatch.setenv("CG_ONTOLOGY_TRUSTED_SOURCES", IMPORTER)
    monkeypatch.setenv("CG_ONTOLOGY_EVAL_STATE_TTL_S", "0")
    monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
    monkeypatch.delenv("CG_AUTH_API_KEY", raising=False)
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
    projector = configured_projector(settings.ontology)
    assert [p.name for p in projector.registry.packs] == ["core", "memory", "user", "crm"]
    app = create_app()
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            ingested = await client.post("/v1/events/batch", json={"events": _events()})
            assert ingested.status_code == 201, ingested.text
            assert ingested.json()["accepted"] == len(HISTORY)
            undeclared = await client.post(
                "/v1/events/batch",
                json={"events": [{**_events()[0], "event_type": "crm.deal.exploded"}]},
            )
            assert undeclared.json()["rejected"] == 1  # the pack owns the crm namespace

            # The worker records the ontology at start, then projects
            plan = await reconcile(
                stores.graph,
                stores.event_log,
                projector,
                allow_breaking=False,
                batch_size=100,
                lookup_limit=settings.ontology.lookup_limit,
            )
            assert plan.kind == "initial"
            assert plan.eval_required == {"crm"}
            consumer = ProjectionConsumer(
                subscription=stores.subscription(
                    settings.consumer.group_projection, "projection-1"
                ),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
                pack_projector=projector,
                pack_lookup_limit=settings.ontology.lookup_limit,
            )
            await _drain(consumer, stores, settings.consumer.group_projection)
            await _check_graph(stores)
            await _check_gate(client, settings, stores, projector)
            await _check_questions(client)
    await _check_rebuild(settings, stores, projector)


async def _check_graph(stores: Stores) -> None:
    """Core's interfaces and provenance, with nothing declared for them in code."""
    deals = {
        ref.key: props
        for ref, props in (
            await stores.graph.get_nodes(
                [NodeRef("Deal", f"Deal:{d}") for d in ("D-1", "D-2", "D-7", "D-8")]
            )
        ).items()
    }
    assert {key: props["status"] for key, props in deals.items()} == {
        "Deal:D-1": "replaced",
        "Deal:D-2": "open",
        "Deal:D-7": "won",
        "Deal:D-8": "open",
    }
    assert {props["source_trust"] for props in deals.values()} == {"trusted"}
    provenance = await stores.graph.neighbors(
        [NodeRef("Deal", "Deal:D-7")], ["DERIVED_FROM"], "out", 10
    )
    assert len(provenance) == 2  # created, won
    replaced = await stores.graph.neighbors([NodeRef("Deal", "Deal:D-1")], ["SUPERSEDES"], "in", 10)
    assert [r["source_key"] for r in replaced] == ["Deal:D-2"]


async def _check_gate(
    client: httpx.AsyncClient, settings: Settings, stores: Stores, projector: Any
) -> None:
    """Decision 10: crm's intents wait on its evaluation set, then serve."""
    question = {"query": "What is in the Acme pipeline?"}
    pending = (await client.post("/v1/query/artifacts", json=question)).json()
    assert pending["meta"]["eval_pending"] == ["crm"]
    assert pending["meta"]["inferred_intents"] == {}
    refused = await client.post("/v1/query/artifacts", json={**question, "intent": "pipeline"})
    assert refused.status_code == 409, refused.text

    reports = await evaluate_graph(settings, stores.graph, projector.registry, [CRM], record=True)
    assert [(r.pack, r.passed) for r in reports] == [("crm", True)], [r.as_dict() for r in reports]


async def _check_questions(client: httpx.AsyncClient) -> None:
    async def ask(query: str) -> dict[str, Any]:
        response = await client.post("/v1/query/artifacts", json={"query": query})
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        assert body["meta"]["eval_pending"] == []
        return body

    pipeline = await ask("What is in the Acme pipeline?")
    assert pipeline["meta"]["inferred_intents"] == {"pipeline": 1.0}
    deals = {k for k, n in pipeline["nodes"].items() if n["node_type"] == "Deal"}
    assert deals == {"Deal:D-2", "Deal:D-7"}  # D-1 was replaced
    assert pipeline["nodes"]["Deal:D-7"]["provenance"]["agent_id"] == IMPORTER

    by_key = await ask("Which account does deal D-7 belong to?")
    assert by_key["meta"]["seed_nodes"] == ["Deal:D-7"]  # the pack's key pattern

    coverage = await ask("Which accounts have no deals?")
    assert {k for k, n in coverage["nodes"].items() if n["retrieval_reason"] == "no_link"} == {
        "Account:initech"
    }


async def _check_rebuild(settings: Settings, stores: Stores, projector: Any) -> None:
    """A gated blue/green rebuild reproduces the graph from the ledger."""
    target = MemoryGraphStore()
    report = await rebuild(stores.event_log, target, projector, settings, eval_dirs=[CRM])
    assert report.passed, [r.as_dict() for r in report.gate]
    assert report.events == len(HISTORY)
    (gate,) = report.gate
    assert (gate.pack, gate.mean_f1) == ("crm", 1.0)
