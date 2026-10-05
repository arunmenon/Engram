"""Spanner behaviour probes for ``scripts/engram_trial.py`` (phases gql, search, vector, retrieval).

Each probe records what it observes instead of asserting, so the same run
on the emulator and on a real instance can be compared side by side:
``python scripts/engram_trial.py --phases gql,search,vector,retrieval``.

- **gql:** Spanner Graph semantics on a small labelled graph: dynamic
  label filters against key-column predicates, dynamic properties of each
  JSON type (floats are stored tagged, see ``adapters/spanner/log.py``),
  path modes (TRAIL, ACYCLIC, WALK) over a cycle, directions, shortest
  path, path functions.
- **search:** the keyword channel. The same documents go to Spanner
  (``SEARCH``/``SCORE``) and to the memory backend (BM25); each query
  reports both rankings and their top-5 overlap.
- **vector:** approximate nearest neighbours (``APPROX_COSINE_DISTANCE``
  over the vector index) against exact cosine over the same rows:
  recall@10, and whether a stored vector finds itself.
- **retrieval:** the OpenDAL PDLC ledger and the CRM ledger are projected
  into the memory backend and into Spanner; the artifact evaluation sets
  run on both (F1 and latency per question), and the core engine
  (lineage, context, subgraph) answers the same queries on both.

Writes go to rows tagged with a per-run id; nothing is deleted.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import random
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENDAL = ROOT / "tests" / "fixtures" / "opendal"
CRM = ROOT / "tests" / "fixtures" / "packs" / "crm"
DIMENSIONS = 384


def _ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _plain(value: Any) -> Any:
    """Query results as JSON-friendly values for the report."""
    serialize = getattr(value, "serialize", None)  # a JSON cell: its text
    if serialize is not None:
        return serialize()
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ---------------------------------------------------------------------------
# gql
# ---------------------------------------------------------------------------


async def phase_gql(database: Any) -> dict[str, Any]:
    from google.cloud.spanner_v1 import param_types

    from context_graph.adapters.spanner.graph import SpannerGraphStore

    graph = SpannerGraphStore(database)
    run = uuid.uuid4().hex[:8]
    a = [f"probe-{run}-a{i}" for i in range(4)]
    b = f"probe-{run}-b0"
    await graph._upsert_nodes(
        [
            (
                ("ProbeA", node_id),
                {
                    "name": f"a{i}",
                    "n": i,
                    "f": i + 0.5,
                    "flag": i % 2 == 0,
                    "tags": ["x", "y"],
                    "obj": {"k": i},
                },
            )
            for i, node_id in enumerate(a)
        ]
        + [(("ProbeB", b), {"name": "b0"})]
    )
    links = [(a[i], a[(i + 1) % 4]) for i in range(4)]  # a0 -> a1 -> a2 -> a3 -> a0
    await graph._upsert_edges(
        [((("ProbeA", s), "PROBE_LINK", ("ProbeA", d)), {"w": 1, "x": 0.25}) for s, d in links]
        + [((("ProbeA", a[1]), "PROBE_OTHER", ("ProbeB", b)), {"w": 2})]
    )

    start = "a.node_id = @a0"
    probes: list[tuple[str, str, Any]] = [
        # name, GQL after "GRAPH EngramGraph", expected (for the report only)
        ("node label filter", f"MATCH (a:ProbeA) WHERE {start} RETURN COUNT(*) AS c", 1),
        ("node label, lower case", f"MATCH (a:probea) WHERE {start} RETURN COUNT(*) AS c", 1),
        (
            "node label as column",
            f"MATCH (a) WHERE {start} AND a.label = 'ProbeA' RETURN COUNT(*) AS c",
            1,
        ),
        ("static table label", f"MATCH (a:GraphNodes) WHERE {start} RETURN COUNT(*) AS c", 1),
        ("LABELS()", f"MATCH (a) WHERE {start} RETURN LABELS(a) AS l", "ProbeA"),
        (
            "edge label filter",
            f"MATCH (a)-[e:PROBE_LINK]->(b) WHERE {start} RETURN COUNT(*) AS c",
            1,
        ),
        (
            "edge label as column",
            f"MATCH (a)-[e]->(b) WHERE {start} AND e.edge_type = 'PROBE_LINK' RETURN COUNT(*) AS c",
            1,
        ),
        ("string property =", f"MATCH (a) WHERE {start} AND a.name = 'a0' RETURN COUNT(*) AS c", 1),
        (
            "string property, STRING()",
            f"MATCH (a) WHERE {start} AND STRING(a.name) = 'a0' RETURN COUNT(*) AS c",
            1,
        ),
        ("int property =", f"MATCH (a) WHERE {start} AND a.n = 0 RETURN COUNT(*) AS c", 1),
        (
            "int property, INT64()",
            f"MATCH (a) WHERE {start} AND INT64(a.n) = 0 RETURN COUNT(*) AS c",
            1,
        ),
        (
            "bool property, BOOL()",
            f"MATCH (a) WHERE {start} AND BOOL(a.flag) RETURN COUNT(*) AS c",
            1,
        ),
        ("float property (tagged)", f"MATCH (a) WHERE {start} RETURN a.f AS f", '{"$float":"0.5"}'),
        (
            "float property, FLOAT64()",
            f"MATCH (a) WHERE {start} RETURN SAFE.FLOAT64(a.f) AS f",
            "NULL: floats are tagged objects",
        ),
        ("list property", f"MATCH (a) WHERE {start} RETURN a.tags AS t", '["x","y"]'),
        ("nested property", f"MATCH (a) WHERE {start} RETURN a.obj.k AS k", 0),
        ("missing property", f"MATCH (a) WHERE {start} RETURN a.nope IS NULL AS missing", True),
        (
            "PROPERTY_EXISTS",
            f"MATCH (a) WHERE {start} RETURN PROPERTY_EXISTS(a, name) AS has_name",
            True,
        ),
        (
            "edge property",
            f"MATCH (a)-[e]->(b) WHERE {start} RETURN e.w AS w, e.x AS x",
            "1 and tagged 0.25",
        ),
        (
            "TRAIL {1,5} over a 4-cycle",
            f"MATCH p = TRAIL (a)-[e WHERE e.edge_type = 'PROBE_LINK']->{{1,5}}(b) "
            f"WHERE {start} RETURN COUNT(*) AS c",
            4,
        ),
        (
            "ACYCLIC {1,5} over a 4-cycle",
            f"MATCH p = ACYCLIC (a)-[e WHERE e.edge_type = 'PROBE_LINK']->{{1,5}}(b) "
            f"WHERE {start} RETURN COUNT(*) AS c",
            3,
        ),
        (
            "WALK {1,5} over a 4-cycle",
            f"MATCH p = WALK (a)-[e WHERE e.edge_type = 'PROBE_LINK']->{{1,5}}(b) "
            f"WHERE {start} RETURN COUNT(*) AS c",
            5,
        ),
        (
            "quantified edge label filter",
            f"MATCH p = TRAIL (a)-[e:PROBE_LINK]->{{1,5}}(b) WHERE {start} RETURN COUNT(*) AS c",
            4,
        ),
        (
            "inbound",
            f"MATCH (a)<-[e]-(b) WHERE {start} RETURN ARRAY_AGG(b.node_id) AS ids",
            "a3",
        ),
        ("any direction", f"MATCH (a)-[e]-(b) WHERE {start} RETURN COUNT(*) AS c", 2),
        (
            "ANY SHORTEST a0 to a3",
            "MATCH p = ANY SHORTEST (a)-[e]->{1,5}(b) "
            f"WHERE {start} AND b.node_id = @a3 RETURN PATH_LENGTH(p) AS hops",
            3,
        ),
        (
            "NODES(p) along a path",
            "MATCH p = TRAIL (a)-[e]->{3}(b) "
            f"WHERE {start} RETURN ARRAY(SELECT n.node_id FROM UNNEST(NODES(p)) AS n "
            "WITH OFFSET o ORDER BY o) AS ids",
            "a0, a1, a2, a3",
        ),
        (
            "two hops to another label",
            "MATCH (a)-[]->(m)-[e2]->(b) "
            f"WHERE {start} AND b.label = 'ProbeB' RETURN b.node_id AS id",
            "b0",
        ),
    ]
    results = []
    for name, query, expected in probes:
        started = time.monotonic()
        try:
            with database.snapshot() as snapshot:
                rows = list(
                    snapshot.execute_sql(
                        "GRAPH EngramGraph " + query,
                        params={"a0": a[0], "a3": a[3]},
                        param_types={"a0": param_types.STRING, "a3": param_types.STRING},
                    )
                )
            outcome: dict[str, Any] = {"rows": _plain(rows)[:5]}
        except Exception as exc:  # noqa: BLE001 - the probe records it
            outcome = {"error": f"{type(exc).__name__}: {str(exc).splitlines()[0][:240]}"}
        results.append({"probe": name, "expected": expected, **outcome, "ms": _ms(started)})
    return {"run": run, "probes": results}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

SEARCH_DOCUMENTS = [
    ("d1", {"title": "Deploy S3 express support", "body": "adds the s3 express one zone service"}),
    ("d2", {"title": "Deploying rollback for PAY-341", "body": "rollback after the incident"}),
    ("d3", {"title": "Incident: deploy failed", "body": "the deploy of 0.59.1 failed with 429"}),
    ("d4", {"title": "GCS gRPC client", "body": "gcs grpc support behind a feature flag"}),
    ("d5", {"title": "HTTP 429 retries", "body": "retry on 429 too many requests for s3 and gcs"}),
    ("d6", {"title": "Docs typo", "body": "fix a typo in the readme"}),
    ("d7", {"title": "S3 restoration", "body": "restore archived s3 objects; s3 s3 s3"}),
    ("d8", {"title": "Release 0.59.1", "body": "release notes for deploy 0.59.1"}),
]
SEARCH_QUERIES = [
    "deploy",
    "deploying",
    "Deploy S3",
    "PAY-341",
    "s3 express",
    "rollback incident",
    "429",
    "0.59.1",
    "grpc",
    "the",
    "zzzunknown",
]


async def phase_search(database: Any) -> dict[str, Any]:
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.spanner.log import SpannerEventLog
    from context_graph.domain.models import Event

    run = uuid.uuid4().hex[:8]
    session = f"probe-search-{run}"
    spanner_log = SpannerEventLog(database)
    memory_log = MemoryEventLog()
    events, payloads, names = [], [], {}
    start = datetime.now(UTC)
    for minute, (name, payload) in enumerate(SEARCH_DOCUMENTS):
        event = Event(
            event_id=uuid.uuid4(),
            event_type="tool.execute",
            occurred_at=start + timedelta(seconds=minute),
            session_id=session,
            agent_id="probe-agent",
            trace_id=f"probe-{run}",
            payload_ref=f"probe:{name}",
            tool_name="probe",
        )
        events.append(event)
        payloads.append(payload)
        names[str(event.event_id)] = name
    await spanner_log.append_batch(events, payloads)
    await memory_log.append_batch(events, payloads)

    results = []
    for query in SEARCH_QUERIES:
        started = time.monotonic()
        try:
            scored = await spanner_log.search_scored(query, session_id=session, limit=8)
            spanner_ranked = [(names[str(e.event_id)], round(s, 3)) for e, s in scored]
            spanner_error = None
        except Exception as exc:  # noqa: BLE001 - the probe records it
            spanner_ranked, spanner_error = [], f"{type(exc).__name__}: {exc}"[:240]
        spanner_ms = _ms(started)
        memory_ranked = [
            names[str(e.event_id)]
            for e in await memory_log.search_bm25(query, session_id=session, limit=8)
        ]
        spanner_ids = [name for name, _score in spanner_ranked]
        results.append(
            {
                "query": query,
                "spanner": spanner_ranked,
                "spanner_error": spanner_error,
                "memory_bm25": memory_ranked,
                "same_set": set(spanner_ids) == set(memory_ranked),
                "same_top1": spanner_ids[:1] == memory_ranked[:1],
                "top5_overlap": len(set(spanner_ids[:5]) & set(memory_ranked[:5])),
                "ms": spanner_ms,
            }
        )
    return {
        "run": run,
        "documents": {name: payload["title"] for name, payload in SEARCH_DOCUMENTS},
        "queries": results,
        "same_set": sum(r["same_set"] for r in results),
        "same_top1": sum(r["same_top1"] for r in results),
        "of": len(results),
    }


# ---------------------------------------------------------------------------
# vector
# ---------------------------------------------------------------------------


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(x * y for x, y in zip(left, right, strict=True))


async def phase_vector(database: Any, count: int = 500, queries: int = 20) -> dict[str, Any]:
    from context_graph.adapters.spanner.graph import SpannerGraphStore

    graph = SpannerGraphStore(database)
    rng = random.Random(41)
    run = uuid.uuid4().hex[:8]
    # Clustered vectors, closer to real embeddings than uniform noise
    centres = [_unit([rng.gauss(0, 1) for _ in range(DIMENSIONS)]) for _ in range(20)]
    vectors = {
        f"probe-{run}-v{i}": _unit([c + rng.gauss(0, 0.35) for c in centres[i % len(centres)]])
        for i in range(count)
    }
    items = [(("Entity", key), {"name": key, "embedding": v}) for key, v in vectors.items()]
    started = time.monotonic()
    for offset in range(0, len(items), 100):
        await graph._upsert_nodes(items[offset : offset + 100])
    write_ms = _ms(started)

    # Exact neighbours over every embedded row, including earlier runs'
    with database.snapshot() as snapshot:
        stored = {
            node_id: [float(v) for v in embedding]
            for node_id, embedding in snapshot.execute_sql(
                "SELECT node_id, embedding FROM GraphNodes "
                "WHERE label = 'Entity' AND embedding IS NOT NULL"
            )
        }
    keys = list(vectors)
    recalls, self_hits, latencies = [], 0, []
    for number in range(queries):
        if number % 2 == 0:  # a stored vector: it should find itself first
            own = keys[rng.randrange(len(keys))]
            query = vectors[own]
        else:  # a new point near a cluster
            own = None
            query = _unit([c + rng.gauss(0, 0.35) for c in centres[rng.randrange(20)]])
        exact = sorted(stored, key=lambda k: _cosine(query, _unit(stored[k])), reverse=True)[:10]
        started = time.monotonic()
        found = await graph.search_similar_entities(query, top_k=10, threshold=0.0)
        latencies.append(_ms(started))
        found_ids = [hit["entity_id"] for hit in found]
        recalls.append(len(set(found_ids) & set(exact)) / 10)
        if own is not None and found_ids[:1] == [own]:
            self_hits += 1
    return {
        "run": run,
        "stored_vectors": len(stored),
        "written": count,
        "write_ms": write_ms,
        "recall_at_10_mean": round(sum(recalls) / len(recalls), 3),
        "recall_at_10_min": min(recalls),
        "self_hit": f"{self_hits} of {(queries + 1) // 2}",
        "query_ms_p50": sorted(latencies)[len(latencies) // 2],
        "query_ms_max": max(latencies),
    }


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------


async def _opendal_ledger() -> tuple[Any, Any]:
    """The OpenDAL deliveries through the real GitHub webhook route into a memory ledger."""
    import os

    import httpx
    import orjson
    from fastapi import FastAPI

    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.api.routes.webhooks import router
    from context_graph.ontology import load_registry
    from context_graph.settings import Settings

    secret = "opendal-eval"  # noqa: S105 - the fixture's signing value, not a credential
    os.environ["CG_WEBHOOK_GITHUB_SECRET"] = secret
    os.environ.pop("CG_ONTOLOGY_PACKS", None)
    settings = Settings()
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    log = MemoryEventLog()
    app.state.settings = settings
    app.state.event_store = log
    app.state.ontology = load_registry(["pdlc"])
    deliveries = orjson.loads((OPENDAL / "deliveries.json").read_bytes())["deliveries"]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://probe") as client:
        for delivery in deliveries:
            body = orjson.dumps(delivery["body"])
            signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            response = await client.post(
                "/v1/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": delivery["event"],
                    "X-GitHub-Delivery": delivery["delivery"],
                    "X-Hub-Signature-256": signature,
                },
            )
            response.raise_for_status()
    return log, settings


async def _crm_ledger() -> tuple[Any, Any]:
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.models import Event
    from context_graph.settings import Settings

    history = [
        ("crm.account.created", {"account_id": "acme", "name": "Acme", "industry": "retail"}),
        ("crm.account.created", {"account_id": "globex", "name": "Globex", "industry": "energy"}),
        ("crm.account.created", {"account_id": "initech", "name": "Initech"}),
        ("crm.contact.added", {"email": "ann@acme.com", "name": "Ann", "account_id": "acme"}),
        ("crm.contact.added", {"email": "bo@globex.com", "name": "Bo", "account_id": "globex"}),
        ("crm.deal.created", {"deal_id": "D-1", "title": "Pilot", "account_id": "acme"}),
        ("crm.deal.created", {"deal_id": "D-2", "title": "Rollout", "account_id": "acme"}),
        ("crm.deal.replaced", {"deal_id": "D-1", "replaced_by": "D-2"}),
        ("crm.deal.created", {"deal_id": "D-7", "title": "Renewal", "account_id": "acme"}),
        ("crm.deal.won", {"deal_id": "D-7"}),
        ("crm.deal.created", {"deal_id": "D-8", "title": "Trial", "account_id": "globex"}),
    ]
    log = MemoryEventLog()
    start = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
    run = uuid.uuid4().hex[:8]
    for minute, (event_type, payload) in enumerate(history):
        event = Event(
            event_id=uuid.uuid4(),
            event_type=event_type,
            occurred_at=start + timedelta(minutes=minute),
            session_id=f"crm:probe-{run}",
            agent_id="importer:crm",
            trace_id="crm-probe",
            payload_ref=f"crm:{minute}",
        )
        await log.append(event, payload)
    return log, Settings()


def _retriever(graph: Any, registry: Any, settings: Any) -> Any:
    from context_graph.retrieval.artifacts import ArtifactRetriever

    ontology = settings.ontology
    return ArtifactRetriever(
        graph,
        registry,
        default_max_depth=settings.query.default_max_depth,
        seed_limit=ontology.retrieval_seed_limit,
        neighbor_limit=ontology.retrieval_neighbor_limit,
        provenance_source="probe",
        seed_min_ratio=ontology.retrieval_seed_min_ratio,
        max_terms=ontology.retrieval_max_terms,
        max_graph_calls=ontology.retrieval_max_graph_calls,
        scan_limit=ontology.retrieval_scan_limit,
        word_scan_limit=ontology.retrieval_word_scan_limit,
    )


async def _eval(graph: Any, registry: Any, settings: Any, eval_file: Path) -> dict[str, Any]:
    from context_graph.ontology.evaluation import _reading, f1_score, load_eval_set
    from context_graph.retrieval.artifacts import ArtifactQuery

    eval_set = load_eval_set(eval_file)
    retriever = _retriever(graph, registry, settings)
    rows = {}
    for question in eval_set.questions:
        started = time.monotonic()
        response = await retriever.retrieve(
            ArtifactQuery(
                question.query,
                seed_node_ids=tuple(question.seed_node_ids),
                intent=question.intent,
                max_nodes=settings.query.default_max_nodes,
            )
        )
        found = _reading(response, question.answer)
        rows[question.id] = {
            "f1": round(f1_score(found, set(question.expected)), 2),
            "ms": _ms(started),
            "found": sorted(found),
        }
    return rows


def _engine_call(graph: Any, name: str, document: dict[str, Any]) -> Any:
    """The coroutine for one core engine query about ``document``'s event."""
    from context_graph.domain.models import LineageQuery, SubgraphQuery

    if name == "lineage":
        return graph.get_lineage(LineageQuery(node_id=document["event_id"]))
    if name == "context":
        return graph.get_context(document["session_id"], max_nodes=50)
    return graph.get_subgraph(
        SubgraphQuery(
            query="why did this change fail",
            session_id=document["session_id"],
            agent_id=document["agent_id"],
            max_nodes=50,
        )
    )


async def _engine(graph: Any, log: Any, sample: int = 5) -> dict[str, Any]:
    """Core engine answers (node ids) for a fixed sample of the ledger's events."""
    entries = await log.read_after(None, 10_000)
    documents = [e.document for e in entries if e.document][:: max(1, len(entries) // sample)]
    answers: dict[str, Any] = {}
    for document in documents[:sample]:
        for name in ("lineage", "context", "subgraph"):
            key = f"{name}:{document['event_id']}"
            started = time.monotonic()
            try:
                response = await _engine_call(graph, name, document)
                answers[key] = {"nodes": sorted(response.nodes), "ms": _ms(started)}
            except Exception as exc:  # noqa: BLE001 - the probe records it
                answers[key] = {"error": f"{type(exc).__name__}: {exc}"[:240]}
    return answers


async def _compare_backends(
    name: str, log: Any, projector: Any, settings: Any, eval_file: Path, database: Any
) -> dict[str, Any]:
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.ontology.rebuild import rebuild

    out: dict[str, Any] = {}
    graphs = {"memory": MemoryGraphStore(), "spanner": SpannerGraphStore(database)}
    evals, engines = {}, {}
    for backend, graph in graphs.items():
        started = time.monotonic()
        report = await rebuild(
            log, graph, projector, settings, eval_dirs=[], skip_gate=True, force=True
        )
        out[f"{backend}_projection"] = {
            "events": report.events,
            "dead_lettered": len(report.dead_lettered),
            "ms": _ms(started),
        }
        evals[backend] = await _eval(graph, projector.registry, settings, eval_file)
        engines[backend] = await _engine(graph, log)

    questions = []
    for question_id, memory in evals["memory"].items():
        spanner = evals["spanner"][question_id]
        questions.append(
            {
                "id": question_id,
                "memory_f1": memory["f1"],
                "spanner_f1": spanner["f1"],
                "same_answer": memory["found"] == spanner["found"],
                "memory_ms": memory["ms"],
                "spanner_ms": spanner["ms"],
                **(
                    {}
                    if memory["found"] == spanner["found"]
                    else {
                        "only_memory": sorted(set(memory["found"]) - set(spanner["found"])),
                        "only_spanner": sorted(set(spanner["found"]) - set(memory["found"])),
                    }
                ),
            }
        )
    engine_rows = []
    for key, memory in engines["memory"].items():
        spanner = engines["spanner"][key]
        if "error" in memory or "error" in spanner:
            engine_rows.append({"query": key, "memory": memory, "spanner": spanner})
            continue
        left, right = set(memory["nodes"]), set(spanner["nodes"])
        engine_rows.append(
            {
                "query": key,
                "memory_nodes": len(left),
                "spanner_nodes": len(right),
                "jaccard": round(len(left & right) / len(left | right), 2) if left | right else 1.0,
                "spanner_ms": spanner["ms"],
            }
        )

    def mean(key: str) -> float:
        return round(sum(q[key] for q in questions) / len(questions), 3)

    out.update(
        {
            "eval": name,
            "memory_mean_f1": mean("memory_f1"),
            "spanner_mean_f1": mean("spanner_f1"),
            "same_answers": f"{sum(q['same_answer'] for q in questions)} of {len(questions)}",
            "spanner_question_ms_p50": sorted(q["spanner_ms"] for q in questions)[
                len(questions) // 2
            ],
            "questions": questions,
            "engine": engine_rows,
        }
    )
    return out


async def phase_retrieval(database: Any) -> dict[str, Any]:
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology import load_registry

    log, settings = await _opendal_ledger()
    pdlc = PackProjector(load_registry(["pdlc"]), frozenset({"webhook:github"}))
    opendal = await _compare_backends(
        "opendal", log, pdlc, settings, OPENDAL / "pdlc.eval.yaml", database
    )
    crm_log, crm_settings = await _crm_ledger()
    crm = PackProjector(load_registry(["crm"], [CRM]), frozenset({"importer:crm"}))
    crm_result = await _compare_backends(
        "crm", crm_log, crm, crm_settings, CRM / "crm.eval.yaml", database
    )
    return {"opendal": opendal, "crm": crm_result}
