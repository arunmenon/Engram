"""G02 real HTTP + worker loops + reserved real Spanner planning acceptance demo.

No artifact insertion; SQL reads observe results, exact-key cleanup removes only
registered fixtures. Test operator activates only the known empty reserved DB.
Token credentials bootstrap SDK clients; actual providers are otherwise intact.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import os
import socket
import subprocess
import sys
import traceback
from pathlib import Path

import httpx
import structlog
import uvicorn
from engram_goal02_fixtures import fixtures
from engram_spanner_acceptance_cases import await_settled
from engram_spanner_compat import load_credentials
from engram_spanner_empty_activation import (
    KEYS,
    RESOURCE,
    activate_empty_target,
    clean_registered_target,
    freeze_target,
)
from engram_spanner_tenant_control import durable_json, fingerprint
from engram_spanner_tenant_control_cases import read_owner
from engram_spanner_tenant_runtime_cases import runtime_settings
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials
from starlette.responses import JSONResponse

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.api.app import create_app
from context_graph.api.tenant_responses import TenantResponseGuard
from context_graph.domain.models import Event
from context_graph.tenancy import (
    CredentialGrant,
    Principal,
    TenantAuthorizationError,
    TenantBinding,
    TenantCatalog,
)
from context_graph.worker.__main__ import _build_consumer

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility"
SECRET = "g02-local-demo-signing-secret"  # noqa: S105 - isolated test signing key
OLD = [
    "compat-control",
    RESOURCE,
    "compat-control-binding",
    18,
    "sha256:f57ffb649f7ab0197d21f45b9397203887f8cb103e32efd784f4e52ce4c3f7b1",
    "active",
]


class DemoAuthentication:
    """Single-bound test entrypoint using actual catalog credential verification.

    HMAC routes authenticate in Engram's handler. Other requests authenticate
    against the actual immutable catalog before Engram's tenant role/response
    guards. This is not the disabled public multi-tenant dispatcher.
    """

    def __init__(self, app, binding):
        self.app = app
        principal = Principal("demo.query", binding.tenant_id, frozenset({"api"}), "demo.query")
        self.catalog = TenantCatalog(
            (binding,), (CredentialGrant.from_token(principal, "g02-local-query-key"),)
        )
        self.guarded = TenantResponseGuard(app, child=app, binding=binding)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith("/v1/webhooks/"):
            await self.app(scope, receive, send)
            return
        headers = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
        try:
            if len(headers) != 1 or not headers[0].startswith(b"Bearer "):
                raise TenantAuthorizationError
            principal = self.catalog.authenticate(headers[0][7:].decode("ascii"))
        except (TenantAuthorizationError, UnicodeError):
            await JSONResponse({"detail": "Unauthorized"}, 401)(scope, receive, send)
            return
        scope = dict(scope)
        scope["engram.principal"] = principal
        await self.guarded(scope, receive, send)


def snapshot(database):
    with database.snapshot(multi_use=True) as snap:
        return {
            "events": [
                list(r)
                for r in snap.execute_sql("SELECT event_id, document, acceptance FROM Events")
            ],
            "nodes": [
                list(r) for r in snap.execute_sql("SELECT label, node_id, props FROM GraphNodes")
            ],
            "edges": [
                list(r)
                for r in snap.execute_sql(
                    "SELECT src_label, src_id, edge_type, dst_label, dst_id, props FROM GraphEdges"
                )
            ],
            "pending": [
                list(r)
                for r in snap.execute_sql("SELECT group_name, event_id FROM ConsumerDeliveries")
            ],
            "dead_letters": [
                list(r)
                for r in snap.execute_sql("SELECT group_name, event_id FROM ConsumerDeadLetters")
            ],
        }


async def execute(values, run_id, directory, *, first_only=False):
    data = fixtures(run_id)
    durable_json(directory / "fixtures.json", data)
    evidence = {
        "goal": "G02",
        "scenarios": [],
        "checks": [],
        "reference_policy": (
            "Explicit typed revision keys create visible placeholders; actual arrival "
            "fills same node."
        ),
        "runtime": (
            "Single bound app, real Bearer catalog verification, real TCP HTTP and all "
            "five workers; no public dispatcher sign-off."
        ),
        "providers": (
            "Actual configured LLM and cached embedder. LLM proposals retained and "
            "recorded separately from declared planning links."
        ),
        "cleanup_policy": (
            "Only predeclared node identities/events or generated nodes with "
            "DERIVED_FROM to this run's accepted Event, plus edges between those owned "
            "endpoints. Verify active fence, stop workers before cleanup; otherwise "
            "refuse."
        ),
        "eval_gate": (
            "serve_unevaluated explicitly enabled for disposable experiment; "
            "no full-pack evaluation claim"
        ),
    }
    durable_json(directory / "observations.json", evidence)
    original_client = spanner.Client
    credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

    def authenticated_client(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original_client(*args, **kwargs)

    spanner.Client = authenticated_client
    client = authenticated_client(project=values["GOOGLE_CLOUD_PROJECT"])
    pool = BurstyPool()
    database = client.instance(values["SPANNER_INSTANCE_ID"]).database(
        "engram-compat-target", pool=pool
    )
    prepare_cleanup(database, client, pool)
    consumers, stores, tasks = [], [], []
    server = server_task = None
    active_owner = None
    mutation_attempted = False
    extraction_outcomes = []
    old_logging = None
    settings = runtime_settings(values)
    settings.ontology.packs = ["pdlc"]
    settings.ontology.trusted_source_ids = ["demo.query"]
    settings.ontology.serve_unevaluated = True
    settings.intent.use_llm = False
    settings.webhooks.github_secret = SECRET
    settings.webhooks.jira_secret = SECRET
    settings.consumer.projection_batch_size = 1
    settings.consumer.block_timeout_ms = 100
    settings.consumer.projection_batch_timeout_ms = 100
    settings.query.default_timeout_ms = 30000
    settings.llm.timeout_seconds = 30
    settings.llm.max_retries = 0
    settings.llm.max_tokens = 1024
    settings.auth.api_key = "g02-local-query-key"
    settings.rate_limit.enabled = False
    kinds = ("projection", "extraction", "enrichment", "pack_extraction", "consolidation")
    groups = []
    for kind in kinds:
        group = "g02-" + run_id + "-" + kind
        setattr(settings.consumer, "group_" + kind, group)
        groups.append(group)
    binding = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        OLD[3] + 1,
        settings,
        engine_revision="tenant-control-conformance-v1",
    )
    restore = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        OLD[3] + 2,
        runtime_settings(values),
        engine_revision="tenant-control-conformance-v1",
    )
    owner = [*TenantFence.from_binding(binding)._identity(), "active"]
    restoration = [*TenantFence.from_binding(restore)._identity(), "active"]
    all_events = {
        item["request"]["event_id"]: (
            Event.model_validate(item["request"], strict=False),
            item["request"]["payload"],
        )
        for item in data["steps"]
        if item["expected_status"] == 201
    }
    allowed = {name: [] for name in KEYS}
    allowed["Events"] = [[eid] for eid in all_events]
    allowed["GraphNodes"] = (
        [["Event", eid] for eid in all_events]
        + [[nid.split(":")[0], nid] for nid in data["ids"].values()]
        + [["OntologyState", "OntologyState:active"]]
    )
    allowed["ConsumerGroups"] = [[g] for g in groups]
    allowed["ConsumerCursors"] = [
        [g, shard] for g in groups for shard in range(settings.spanner.shards)
    ]
    for table in ("ConsumerDeliveries", "ConsumerDeadLetters"):
        allowed[table] = [[g, e] for g in groups for e in all_events]
    evidence["intent"] = {
        "predecessor": OLD,
        "active": owner,
        "restore": restoration,
        "initial_cleanup_keys": allowed,
        "packs": binding.bundle.pack_identities,
        "processing": binding.bundle.processing,
        "expected_normalized": {
            k: {"event": e.model_dump(mode="json"), "payload": p}
            for k, (e, p) in all_events.items()
        },
    }
    durable_json(directory / "observations.json", evidence)
    try:
        assert await asyncio.to_thread(read_owner, database) == [OLD], "Predecessor changed"
        before = await asyncio.to_thread(fingerprint, database)
        assert not any(v["count"] for v in before.values()), "Target is not empty"
        evidence["before"] = before
        durable_json(directory / "observations.json", evidence)
        mutation_attempted = True
        await asyncio.to_thread(freeze_target, database, OLD)
        active_owner = [*OLD[:-1], "frozen"]
        await asyncio.to_thread(activate_empty_target, database, active_owner, binding)
        active_owner = owner
        evidence["activation"] = "verified"
        durable_json(directory / "observations.json", evidence)
        app = create_app(binding.settings(), bundle=binding.bundle)
        app.state.tenant_binding = binding
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                DemoAuthentication(app, binding), host="127.0.0.1", port=port, log_level="warning"
            )
        )
        server_task = asyncio.create_task(server.serve())
        for _ in range(300):
            if server.started:
                break
            if server_task.done():
                await server_task
                raise AssertionError("HTTP server stopped before startup")
            await asyncio.sleep(0.1)
        assert server.started, "HTTP server startup timeout"
        for kind in kinds:
            consumer, store = await _build_consumer(
                kind, binding.settings(), tenant_binding=binding
            )
            consumers.append(consumer)
            stores.append(store)
            tasks.append(asyncio.create_task(consumer.run()))
        evidence["worker_loops"] = list(kinds)
        durable_json(directory / "observations.json", evidence)
        old_logging = structlog.get_config()

        def record_extraction(logger, method, event_dict):
            if event_dict.get("event") in {
                "pack_extraction_applied",
                "pack_extraction_answer_invalid",
            }:
                extraction_outcomes.append(
                    {
                        k: v
                        for k, v in event_dict.items()
                        if k
                        in {
                            "event",
                            "event_id",
                            "pack",
                            "nodes",
                            "links",
                            "rejected",
                            "edges_written",
                            "error",
                        }
                    }
                )
            return event_dict

        structlog.configure(processors=[record_extraction, *old_logging["processors"]])
        accepted = set()
        expected_nodes = {}
        expected_edges = set()
        artifact_events = {}
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            timeout=40,
            headers={"Authorization": "Bearer g02-local-query-key"},
        ) as http:

            async def retrieve(query, required, forbidden):
                response = await http.post("/v1/query/artifacts", json=query)
                result = {"request": query, "status": response.status_code, "body": response.json()}
                evidence.setdefault("retrieval_attempts", []).append(result)
                durable_json(directory / "observations.json", evidence)
                assert response.status_code == 200, result
                answer = response.json()
                returned = answer["nodes"]
                assert set(required) <= set(returned), (
                    "Missing retrieval nodes",
                    set(required) - set(returned),
                    result,
                )
                assert not (set(forbidden) & set(returned)), ("Cross-feature contamination", result)
                assert not answer["meta"].get("truncated"), (
                    "Truncated result is not complete acceptance"
                )
                returned_edges = {
                    (edge["edge_type"], edge["source"], edge["target"]) for edge in answer["edges"]
                }
                required_edges = {
                    edge for edge in expected_edges if edge[1] in required and edge[2] in required
                }
                assert required_edges <= returned_edges, (
                    "Missing required retrieval edges",
                    required_edges - returned_edges,
                )
                for nid in required:
                    if nid not in artifact_events:
                        continue
                    provenance = returned[nid].get("provenance")
                    assert (
                        provenance
                        and provenance.get("source") == "spanner"
                        and provenance.get("event_id") in artifact_events[nid]
                    ), ("Wrong evidence", nid, provenance)
                    for key, value in expected_nodes.get(nid, {}).items():
                        assert returned[nid]["attributes"].get(key) == value, (
                            "Stale artifact",
                            nid,
                            key,
                        )
                return result

            for fixture in data["steps"]:
                sid = fixture["scenario"]
                request = fixture["request"]
                eid = request["event_id"]
                item = {
                    "scenario": sid,
                    "request": request,
                    "expected_status": fixture["expected_status"],
                }
                evidence["scenarios"].append(item)
                durable_json(directory / "observations.json", evidence)
                previous = await asyncio.to_thread(snapshot, database)
                response = await http.post("/v1/events", json=request)
                item["response"] = {"status": response.status_code, "body": response.json()}
                durable_json(directory / "observations.json", evidence)
                assert response.status_code == fixture["expected_status"], item["response"]
                if fixture["expected_status"] == 201:
                    assert response.json()["event_id"] == eid and response.json()["global_position"]
                    expected_outcome = "duplicate" if sid == "PL07-duplicate" else "created"
                    assert response.json()["status"] == expected_outcome
                    accepted.add(eid)
                completed = False
                for _ in range(600):
                    state = await asyncio.to_thread(snapshot, database)
                    if any(t.done() for t in tasks):
                        for t in tasks:
                            if t.done():
                                await t
                        raise AssertionError("Worker stopped")
                    lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
                    projected = {n[1] for n in state["nodes"] if n[0] == "Event"}
                    assert not state["dead_letters"], "Worker dead-lettered event"
                    if (
                        accepted <= projected
                        and not state["pending"]
                        and all(lag == 0 for lag in lags)
                    ):
                        completed = True
                        break
                    await asyncio.sleep(0.2)
                evidence["extraction_outcomes"] = extraction_outcomes
                matching = [
                    outcome
                    for outcome in extraction_outcomes
                    if outcome.get("event_id") == eid and outcome.get("pack") == "pdlc"
                ]
                if (
                    fixture["expected_status"] == 201
                    and request["event_type"] == "pdlc.design.section_changed"
                ):
                    assert matching and all(
                        o["event"] == "pack_extraction_applied" for o in matching
                    ), ("No successful real extraction outcome", eid, matching)
                item["storage"] = state
                item["worker_lags"] = lags
                durable_json(directory / "observations.json", evidence)
                assert completed, "Workers did not complete"
                assert {row[0] for row in state["events"]} == accepted, "Unexpected ledger events"
                for key, doc, authority in state["events"]:
                    expected = all_events[key]
                    assert (
                        doc["payload"] == expected[1]
                        and doc["event_type"] == expected[0].event_type
                    )
                    assert (
                        authority["tenant_id"] == "compat-control"
                        and authority["database_resource"] == RESOURCE
                    )
                    assert (
                        authority["bundle_digest"] == binding.bundle_digest
                        and authority["accepted_epoch"] == owner[3]
                        and authority["source_id"] == "demo.query"
                    )
                if fixture["expected_status"] != 201 or sid == "PL07-duplicate":
                    assert state == previous, "Rejected/duplicate request changed persistent state"
                nid = fixture["expected_node"]
                nodes = {row[1]: row[2] for row in state["nodes"]}
                if nid:
                    expected_nodes[nid] = fixture["expected_props"]
                    artifact_events.setdefault(nid, set()).add(eid)
                expected_edges.update(tuple(e) for e in fixture["expected_edges"])
                domain = {
                    n[1]
                    for n in state["nodes"]
                    if n[0] in {"Spec", "Requirement", "DesignElement", "DesignApproval"}
                }
                expected_domain = set(expected_nodes)
                if sid == "PL09-before":
                    expected_domain.add(data["ids"]["late"])
                assert domain == expected_domain, (
                    "Unexpected planning identities",
                    domain ^ expected_domain,
                )
                for key, props in expected_nodes.items():
                    for name, value in props.items():
                        assert nodes[key].get(name) == value, (sid, key, name)
                actual_edges = {
                    (r[2], r[1], r[4])
                    for r in state["edges"]
                    if r[2] in {"REFINES", "APPROVES", "SUPERSEDES"}
                }
                assert actual_edges == expected_edges, (
                    "Wrong declared planning links",
                    actual_edges ^ expected_edges,
                )
                for key, events in artifact_events.items():
                    assert {(key, event) for event in events} <= {
                        (r[1], r[4]) for r in state["edges"] if r[2] == "DERIVED_FROM"
                    }
                assert not any(
                    r[0] in {"UserProfile", "Preference", "Skill", "Belief", "Goal", "Episode"}
                    for r in state["nodes"]
                )
                if sid == "PL09-before":
                    late = data["ids"]["late"]
                    assert "body" not in nodes[late]
                    assert not any(r[1] == late and r[2] == "DERIVED_FROM" for r in state["edges"])
                    item["placeholder"] = {
                        "node_id": late,
                        "properties": nodes[late],
                        "content_evidence": False,
                    }
                if sid == "PL06":
                    assert (
                        "APPROVES",
                        data["ids"]["approval"],
                        data["ids"]["hld2"],
                    ) not in actual_edges
                if nid:
                    query = {
                        "query": "status " + nid,
                        "seed_node_ids": [nid],
                        "intent": "status",
                        "max_nodes": 50,
                    }
                    item["retrieval"] = await retrieve(query, [nid], [])
                    if sid in {"PL03", "PL04"}:
                        chain = [
                            data["ids"][k]
                            for k in (
                                ["hld1", "expiry", "single", "spec"]
                                if sid == "PL03"
                                else ["lld", "hld1", "expiry", "single", "spec"]
                            )
                        ]
                        item["connected_retrieval"] = await retrieve(
                            {
                                "query": "trace " + nid,
                                "seed_node_ids": [nid],
                                "intent": "trace",
                                "max_nodes": 50,
                                "max_depth": 5,
                            },
                            chain,
                            [],
                        )
                        pairs = {
                            (e["edge_type"], e["source"], e["target"])
                            for e in item["connected_retrieval"]["body"]["edges"]
                        }
                        if sid == "PL04":
                            assert ("REFINES", data["ids"]["lld"], data["ids"]["hld1"]) in pairs

                else:
                    seed = data["ids"]["spec"]
                    item["retrieval"] = await retrieve(
                        {
                            "query": "status " + seed,
                            "seed_node_ids": [seed],
                            "intent": "status",
                            "max_nodes": 50,
                        },
                        [seed],
                        [],
                    )
                item["verdict"] = "passed"
                evidence["checks"].append({"name": sid, "passed": True, "scenarios": []})
                durable_json(directory / "observations.json", evidence)
                print(sid + " passed", flush=True)
                if first_only:
                    break
            if not first_only:
                for fixture in data["queries"]:
                    sid = fixture["scenario"]
                    query = {
                        "query": fixture.get("text") or fixture["intent"] + " " + fixture["seed"],
                        "seed_node_ids": [fixture["seed"]] if fixture["seed"] else [],
                        "intent": fixture["intent"],
                        "max_nodes": 50,
                        "max_depth": 5,
                    }
                    item = {
                        "scenario": sid,
                        "retrieval": await retrieve(
                            query, fixture["required"], fixture["forbidden"]
                        ),
                        "verdict": "passed",
                    }
                    if sid == "PL11-history":
                        pairs = {
                            (e["edge_type"], e["source"], e["target"])
                            for e in item["retrieval"]["body"]["edges"]
                        }
                        assert ("APPROVES", data["ids"]["approval"], data["ids"]["hld1"]) in pairs
                        assert ("SUPERSEDES", data["ids"]["hld2"], data["ids"]["hld1"]) in pairs
                        assert (
                            "APPROVES",
                            data["ids"]["approval"],
                            data["ids"]["hld2"],
                        ) not in pairs
                    evidence["scenarios"].append(item)
                    evidence["checks"].append({"name": sid, "passed": True, "scenarios": []})
                    durable_json(directory / "observations.json", evidence)
                    print(sid + " passed", flush=True)
    except BaseException as exc:
        evidence["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        evidence["checks"].append(
            {"name": "goal02_required_path", "passed": False, "scenarios": []}
        )
        durable_json(directory / "observations.json", evidence)
        raise
    finally:
        for consumer in consumers:
            consumer.stop()
        # stop() lets in-flight SDK calls finish; cancelling a to_thread await
        # would not terminate its transaction and could race fixture cleanup.
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        shutdown_errors = [type(r).__name__ for r in task_results if isinstance(r, BaseException)]
        for store in stores:
            try:
                await store.close()
            except Exception as exc:
                shutdown_errors.append(type(exc).__name__)
        if server is not None:
            server.should_exit = True
        if server_task is not None:
            try:
                await asyncio.wait_for(server_task, 15)
            except Exception as exc:
                shutdown_errors.append(type(exc).__name__)
        evidence["shutdown_errors"] = shutdown_errors
        durable_json(directory / "observations.json", evidence)
        if mutation_attempted and active_owner is not None and active_owner[3] == OLD[3] + 1:
            final = await asyncio.to_thread(snapshot, database)
            owned = {(r[0], r[1]) for r in allowed["GraphNodes"]}
            owned |= {
                (r[0], r[1])
                for r in final["edges"]
                if r[2] == "DERIVED_FROM" and r[3] == "Event" and r[4] in all_events
            }
            assert len(owned) <= 300, "Generated artifact bound exceeded"
            assert all((label, nid) in owned for label, nid, _ in final["nodes"]), (
                "Unattributed node; refuse cleanup"
            )
            assert all((r[0], r[1]) in owned and (r[3], r[4]) in owned for r in final["edges"]), (
                "Unowned edge; refuse cleanup"
            )
            allowed["GraphNodes"] = [list(pair) for pair in sorted(owned)]
            allowed["GraphEdges"] = [r[:5] for r in final["edges"]]
            evidence["generated_cleanup_proof"] = {
                "ownership": "DERIVED_FROM to predeclared run event or predeclared identity",
                "final_state": final,
                "resolved_keys": allowed,
            }
            durable_json(directory / "observations.json", evidence)
        if mutation_attempted:
            observed_owner = await asyncio.to_thread(read_owner, database)
            known = [OLD, [*OLD[:-1], "frozen"], owner, [*owner[:-1], "frozen"]]
            assert len(observed_owner) == 1 and observed_owner[0] in known, (
                "Unknown ownership during cleanup; refuse mutation"
            )
            # Reconcile only exact previously persisted operation intents.
            active_owner = observed_owner[0]
        if active_owner is not None:
            if active_owner[-1] == "active":
                evidence["cleanup_intent"] = {
                    "freeze": active_owner,
                    "keys": allowed,
                    "restore": restoration,
                }
                durable_json(directory / "observations.json", evidence)
                await asyncio.to_thread(freeze_target, database, active_owner)
                active_owner = [*active_owner[:-1], "frozen"]
            if active_owner[3] == OLD[3] + 1:
                evidence["cleanup_counts"] = await asyncio.to_thread(
                    clean_registered_target, database, active_owner, allowed
                )
                await asyncio.to_thread(activate_empty_target, database, active_owner, restore)
                evidence["restored_owner"] = await asyncio.to_thread(read_owner, database)
                evidence["after"] = await asyncio.to_thread(fingerprint, database)
                assert evidence["restored_owner"] == [restoration]
                assert not any(v["count"] for v in evidence["after"].values())
                durable_json(directory / "observations.json", evidence)
            elif active_owner == [*OLD[:-1], "frozen"]:
                recovery = TenantBinding.from_settings(
                    "compat-control",
                    "compat-control-binding",
                    OLD[3] + 1,
                    runtime_settings(values),
                    engine_revision="tenant-control-conformance-v1",
                )
                evidence["preactivation_recovery_intent"] = [
                    *TenantFence.from_binding(recovery)._identity(),
                    "active",
                ]
                durable_json(directory / "observations.json", evidence)
                await asyncio.to_thread(activate_empty_target, database, active_owner, recovery)
                evidence["restored_owner"] = await asyncio.to_thread(read_owner, database)
                durable_json(directory / "observations.json", evidence)
        if old_logging is not None:
            structlog.configure(**old_logging)
        await asyncio.to_thread(close_database, database)
        spanner.Client = original_client
        assert not shutdown_errors, ("Shutdown errors", shutdown_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--first-only", action="store_true")
    parser.add_argument("--expected-epoch", type=int, default=18)
    parser.add_argument("--expected-digest", default=OLD[4])
    args = parser.parse_args()
    OLD[3] = args.expected_epoch
    OLD[4] = args.expected_digest
    values = load_credentials(args.credentials)
    assert (values["GOOGLE_CLOUD_PROJECT"], values["SPANNER_INSTANCE_ID"]) == (
        "portiq-mvp",
        "engram-experiment",
    )
    os.environ.pop("SPANNER_EMULATOR_HOST", None)
    os.environ["HF_HUB_OFFLINE"] = "1"
    tracker = ROOT / "scripts/track_spanner_compatibility.py"
    manifest = {
        "goal": "G02",
        "phase": "PL01 full-path checkpoint" if args.first_only else "twelve planning scenarios",
        "target": RESOURCE,
        "scope": "one ordinary bound app; no tenant dispatcher sign-off",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime_sources": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src").rglob("*"))
            if p.is_file() and p.suffix in {".py", ".yaml"}
        },
        "code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "dirty_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "--binary"])
        ).hexdigest(),
        "credential_handling": "Token SDK bootstrap; token never persisted in evidence",
    }
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = Path("/private/tmp/engram-g02-run-manifest.json")
        durable_json(manifest_path, manifest)
        subprocess.run(
            [
                sys.executable,
                str(tracker),
                "start",
                "--run-id",
                args.run_id,
                "--manifest",
                str(manifest_path),
            ],
            check=True,
        )
        directory = RECORDS / "runs" / args.run_id
        code = 0
        try:
            asyncio.run(
                await_settled(execute(values, args.run_id, directory, first_only=args.first_only))
            )
        except BaseException as exc:
            print("G02 run failed: " + type(exc).__name__, flush=True)
            code = 1
        finally:
            results = {
                "scenarios": [],
                "summary": "G02: individual scenarios in observations. No baseline promotion.",
                "cleanup": (
                    "See recorded cleanup/restoration evidence; "
                    "absence of evidence is not cleanup success."
                ),
            }
            durable_json(directory / "finish-input.json", results)
            subprocess.run(
                [
                    sys.executable,
                    str(tracker),
                    "finish",
                    "--run-id",
                    args.run_id,
                    "--results",
                    str(directory / "finish-input.json"),
                ],
                check=True,
            )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
