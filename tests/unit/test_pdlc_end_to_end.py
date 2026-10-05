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
import orjson
import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.registry import Stores, open_stores
from context_graph.api.app import create_app, lifespan
from context_graph.domain.models import Event
from context_graph.domain.pack_extraction import extraction_profiles
from context_graph.domain.projection import event_to_node
from context_graph.migration.compare import compare_graphs
from context_graph.ontology.__main__ import evaluate_graph, same_graph, target_settings
from context_graph.ontology.rebuild import RebuildRefusedError, rebuild
from context_graph.ontology.runtime import configured_projector
from context_graph.ontology.versioning import reconcile
from context_graph.ports.pack_graph import NodeRef
from context_graph.settings import Settings
from context_graph.worker.pack_extraction import PackExtractionConsumer
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "webhooks"
EVAL_SETS = Path(__file__).resolve().parents[1] / "fixtures" / "ontology"
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
    monkeypatch.setenv("CG_ONTOLOGY_EVAL_STATE_TTL_S", "0")  # see each recorded change at once
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
        await _run(monkeypatch, settings, stores, backend)
    finally:
        if backend == "spanner":
            with contextlib.suppress(Exception):
                await asyncio.to_thread(stores.event_log.database.drop)  # type: ignore[attr-defined]
        if backend == "neo4j":
            await stores.graph.delete_all(confirm=True)  # type: ignore[attr-defined]
        await close()


async def _run(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    stores: Stores,
    backend: str,
) -> None:
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
                subscription=stores.subscription(
                    settings.consumer.group_projection, "projection-1"
                ),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
                pack_projector=configured_projector(settings.ontology),
                pack_lookup_limit=settings.ontology.lookup_limit,
            )
            await _drain(projection, stores, settings.consumer.group_projection)
            await _check_graph(stores.graph)
            await _check_eval_gate(client, settings, stores)
            await _check_queries(client)
            await _check_versioning(client, settings, stores, backend)
            await _check_extraction(client, settings, stores)


async def _check_eval_gate(client: httpx.AsyncClient, settings: Settings, stores: Stores) -> None:
    """Decision 10: PDLC's weights wait on its evaluation set, from the first deploy."""
    # Before the worker records the ontology, and after: PDLC is pending either way
    question = {"query": "Where is PAY-341 deployed? Trace it."}
    unrecorded = (await client.post("/v1/query/artifacts", json=question)).json()
    assert unrecorded["meta"]["eval_pending"] == ["pdlc"]
    projector = configured_projector(settings.ontology)
    plan = await reconcile(
        stores.graph,
        stores.event_log,
        projector,
        allow_breaking=False,
        batch_size=100,
        lookup_limit=settings.ontology.lookup_limit,
    )
    assert plan.kind == "initial"
    assert plan.eval_required == {"pdlc"}
    pending = (await client.post("/v1/query/artifacts", json=question)).json()
    assert pending["meta"]["eval_pending"] == ["pdlc"]
    assert pending["meta"]["inferred_intents"] == {}  # trace is PDLC's: not used yet
    asked = await client.post("/v1/query/artifacts", json={**question, "intent": "trace"})
    assert asked.status_code == 409, asked.text
    assert "evaluate --record" in asked.json()["detail"]

    reports = await evaluate_graph(
        settings, stores.graph, projector.registry, [EVAL_SETS], record=True
    )
    assert [(r.pack, r.passed) for r in reports] == [("pdlc", True)]


async def _check_queries(client: httpx.AsyncClient) -> None:
    """Artifact questions through the API (ADR-0018 phase 2)."""
    trace = await client.post(
        "/v1/query/artifacts", json={"query": "Where is PAY-341 deployed? Trace it."}
    )
    assert trace.status_code == 200, trace.text
    body = trace.json()
    assert body["meta"]["eval_pending"] == []
    assert body["meta"]["inferred_intents"] == {"trace": 1.0}
    assert body["meta"]["seed_nodes"][0] == "WorkItem:jira|PAY-341"
    assert "Change:acme/payments|7" in body["nodes"]
    change = body["nodes"]["Change:acme/payments|7"]
    assert change["provenance"]["agent_id"] == "webhook:github"

    unreviewed = await client.post(
        "/v1/query/artifacts",
        json={"query": "Which pull requests were merged without an approving review?"},
    )
    assert unreviewed.status_code == 200, unreviewed.text
    assert unreviewed.json()["nodes"] == {}  # PR 7 was approved
    assert unreviewed.json()["meta"]["retrieval_channels"]["completeness.REVIEWS.confirmed"] == 1

    bad = await client.post("/v1/query/artifacts", json={"query": "x", "intent": "nope"})
    assert bad.status_code == 422


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


async def _check_versioning(
    client: httpx.AsyncClient,
    settings: Settings,
    stores: Stores,
    backend: str,
) -> None:
    """The graph records its ontology; a gated rebuild from the same ledger (ADR-0018 phase 3)."""
    projector = configured_projector(settings.ontology)
    plan = await reconcile(
        stores.graph,
        stores.event_log,
        projector,
        allow_breaking=False,
        batch_size=100,
        lookup_limit=settings.ontology.lookup_limit,
    )
    assert plan.kind == "none"  # recorded when the evaluation gate was checked
    response = await client.get("/v1/ontology")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["graph"]["version"] == body["version"] == projector.registry.version
    assert body["change"]["kind"] == "none"
    assert body["node_types"]["Change"]["key"] == ["repo", "number"]
    assert body["extraction"][0]["pack"] == "pdlc"
    assert body["extraction"][0]["propose_nodes"] == ["Constraint", "Decision", "Lesson"]

    # Blue/green into a fresh graph of the same kind: a new Spanner database; a
    # memory graph otherwise (Neo4j Community serves one database)
    target_stores: Stores | None = None
    target: GraphBackend = MemoryGraphStore()
    if backend == "spanner":
        green = target_settings(
            [f"CG_SPANNER_DATABASE=green{uuid4().hex[:10]}", "CG_SPANNER_CREATE_IF_MISSING=true"]
        )
        assert not same_graph(settings, green)
        target_stores = await open_stores(green)
        target = target_stores.graph
    try:
        report = await rebuild(stores.event_log, target, projector, settings, eval_dirs=[EVAL_SETS])
        assert report.passed, [r.as_dict() for r in report.gate]
        assert report.events >= len(DELIVERIES)
        # tests/fixtures/ontology/pdlc.eval.yaml: every question is answered exactly;
        # a change in any score fails here
        (gate,) = report.gate
        scores = {r.id: round(r.f1, 2) for r in gate.results}
        assert scores == dict.fromkeys(scores, 1.0), gate.as_dict()
        assert gate.mean_f1 == 1.0
        comparison = await compare_graphs(stores.graph, target, sample_sessions=0)
        assert comparison.ok, comparison.as_dict()
        with pytest.raises(RebuildRefusedError):  # the live graph is never a target
            await rebuild(
                stores.event_log, stores.graph, projector, settings, eval_dirs=[EVAL_SETS]
            )
    finally:
        if target_stores is not None:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(target_stores.event_log.database.drop)  # type: ignore[attr-defined]
            await target_stores.close()


class LinkingModel:
    """Test double for the model: proposes one decision about the first known component."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        components = [
            line[2:].split(" ")[0]
            for line in prompt.splitlines()
            if line.startswith("- Component:")
        ]
        links = (
            [{"type": "APPLIES_TO", "from": "n1", "to": components[0], "confidence": 0.6}]
            if components
            else []
        )
        return orjson.dumps(
            {
                "nodes": [
                    {"ref": "n1", "type": "Decision", "statement": DECIDED, "confidence": 0.9}
                ],
                "links": links,
            }
        ).decode()


DECIDED = "Refund retries use idempotency keys"


async def _check_extraction(client: httpx.AsyncClient, settings: Settings, stores: Stores) -> None:
    """Prose in, a proposed Decision linked to a known component out (ADR-0018 phase 3)."""
    event_id = str(uuid4())
    response = await client.post(
        "/v1/events",
        json={
            "event_id": event_id,
            "event_type": "observation.input",
            "occurred_at": "2026-10-02T09:00:00Z",
            "session_id": "design-review",
            "agent_id": "agent-1",
            "trace_id": "t",
            "payload_ref": "p",
            "payload": {"content": "For acme/payments we decided: " + DECIDED + "."},
        },
    )
    assert response.status_code in (200, 201), response.text
    projector = configured_projector(settings.ontology)
    (profile,) = extraction_profiles(
        projector.registry, max_nodes=5, max_links=5, max_text_chars=2000
    )
    model = LinkingModel()
    consumer = PackExtractionConsumer(
        subscription=stores.subscription("pack-extraction", "e2e"),
        event_log=stores.event_log,
        graph=stores.graph,
        profiles=[profile],
        projector=projector,
        model=model,
        settings=settings,
    )
    (document,) = await stores.event_log.get_documents([event_id])
    assert document is not None
    await stores.graph.merge_event_node(event_to_node(Event.model_validate(document, strict=False)))
    await consumer.process_message("e2e", {"event_id": event_id})
    (prompt,) = model.prompts
    assert "- Component:" in prompt  # found by the words of the text
    decision = NodeRef("Decision", "Decision:" + hashlib.sha256(DECIDED.encode()).hexdigest())
    node = (await stores.graph.get_nodes([decision]))[decision]
    assert node["status"] == "proposed"
    assert node["source_trust"] == "untrusted"
    applies = await stores.graph.neighbors([decision], ["APPLIES_TO"], "out", 10)
    assert len(applies) == 1
    assert applies[0]["properties"]["link_status"] == "proposed"
