"""G01 real HTTP + worker loops + reserved real Spanner PR acceptance demo.

No artifact insertion; SQL reads observe results, exact-key cleanup removes only
registered fixtures. Test operator activates only the known empty reserved DB.
Token credentials bootstrap SDK clients; actual providers are otherwise intact.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import fcntl
import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid5

import httpx
import uvicorn
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
from context_graph.api.routes.webhooks import WEBHOOK_NAMESPACE, build_events
from context_graph.api.tenant_responses import TenantResponseGuard
from context_graph.domain.pack_projection import make_node_id
from context_graph.sources import github, jira
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
SECRET = "g01-local-demo-signing-secret"  # noqa: S105 - isolated test signing key
OLD = [
    "compat-control",
    RESOURCE,
    "compat-control-binding",
    10,
    "sha256:d137c3bfce7254569c2783a2719c9cd0161ecec325f54c36b12a8f943f223eaa",
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
            (binding,), (CredentialGrant.from_token(principal, "g01-local-query-key"),)
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


def fixtures(run_id):
    source = RECORDS / "public-payload-corpus/pull_requests.json"
    public = json.loads(source.read_text())[0]
    repo = "g01/" + run_id + "-payments"
    other = "g01/" + run_id + "-billing"
    number = public["number"]
    title = public["title"]
    now = datetime.now(UTC) - timedelta(minutes=5)

    def pr(action, offset, *, repository=repo, num=number, label=title, body=""):
        record = copy.deepcopy(public)
        moment = (now + timedelta(seconds=offset)).isoformat()
        record.update(
            number=num,
            title=label,
            body=body,
            created_at=now.isoformat(),
            updated_at=moment,
            merged=action == "closed",
            merged_at=moment if action == "closed" else None,
            merge_commit_sha="d" * 40 if action == "closed" else None,
        )
        return {
            "action": action,
            "number": num,
            "repository": {"full_name": repository},
            "pull_request": record,
        }

    opened = pr("opened", 0)
    edited = pr("edited", 1, label=title + " [updated]")
    invalid = copy.deepcopy(opened)
    invalid.pop("repository")
    ticket = json.loads((ROOT / "tests/fixtures/webhooks/jira_issue_created.json").read_text())
    ticket["timestamp"] = int(now.timestamp() * 1000)
    ticket["issue"]["key"] = "APP-42"
    ticket["issue"]["fields"].pop("parent", None)
    return {
        "source": {
            "file": str(source.relative_to(ROOT)),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "url": "https://api.github.com/repos/apache/opendal/pulls?state=closed&per_page=2",
            "kind": (
                "public REST record reconstructed into webhook fixtures; repository, timestamps "
                "and lifecycle fields modified for isolation; not captured native deliveries"
            ),
        },
        "repo": repo,
        "other_repo": other,
        "number": number,
        "title": title,
        "deliveries": [
            ("PR01", "github", opened),
            ("PR02", "github", edited),
            ("PR03", "github", edited),
            ("PR04", "github", invalid),
            ("PR05-ticket", "jira", ticket),
            ("PR05", "github", pr("closed", 3, label=title + " [updated]", body="Closes APP-42")),
            ("PR06-open", "github", pr("opened", 4, num=number + 1)),
            ("PR06", "github", pr("closed", 5, num=number + 1)),
            ("PR07", "github", pr("opened", 6, repository=other)),
            ("PR08", "github", pr("edited", 2, label=title + " [older edit]")),
        ],
    }


def encode(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def normalized(source, body):
    payload = json.loads(body)
    translated = (
        github.translate("pull_request", payload) if source == "github" else jira.translate(payload)
    )
    return build_events(
        source, "expected-delivery", hashlib.sha256(body).hexdigest(), translated, datetime.now(UTC)
    )


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
        "goal": "G01",
        "scenarios": [],
        "checks": [],
        "ordering_policy": (
            "Declared PDLC rules: delivery order governs title updates; edited does not "
            "transition lifecycle, so an older edit preserves merged status. "
            "No claim of timestamp-based property ordering."
        ),
        "runtime": (
            "Single database-bound ordinary app, HMAC authenticated sources, real TCP HTTP "
            "and all five actual worker loops. Public tenant dispatcher not enabled or proved."
        ),
        "providers": (
            "Unmodified LLM client and sentence-transformer embedder. PR/ticket events do not "
            "trigger session-end or domain LLM extraction. Structured artifact responses."
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
    settings = runtime_settings(values)
    settings.ontology.packs = ["pdlc"]
    settings.ontology.trusted_source_ids = ["webhook.github", "webhook.jira"]
    settings.ontology.serve_unevaluated = True
    settings.intent.use_llm = False
    settings.webhooks.github_secret = SECRET
    settings.webhooks.jira_secret = SECRET
    settings.consumer.projection_batch_size = 1
    settings.consumer.block_timeout_ms = 100
    settings.consumer.projection_batch_timeout_ms = 100
    settings.query.default_timeout_ms = 30000
    settings.auth.api_key = "g01-local-query-key"
    settings.rate_limit.enabled = False
    kinds = ("projection", "extraction", "enrichment", "pack_extraction", "consolidation")
    groups = []
    for kind in kinds:
        group = "g01-" + run_id + "-" + kind
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
        str(e.event_id): (e, p)
        for sid, source, payload in data["deliveries"]
        if sid != "PR04"
        for e, p in normalized(source, encode(payload))
    }
    change_ids = [
        make_node_id("Change", [r, n])
        for r, n in (
            (data["repo"], data["number"]),
            (data["repo"], data["number"] + 1),
            (data["other_repo"], data["number"]),
        )
    ]
    work_id = make_node_id("WorkItem", ["jira", "APP-42"])
    allowed = {name: [] for name in KEYS}
    allowed["Events"] = [[eid] for eid in all_events]
    allowed["GraphNodes"] = (
        [["Event", eid] for eid in all_events]
        + [["Change", nid] for nid in change_ids]
        + [["WorkItem", work_id], ["OntologyState", "OntologyState:active"]]
    )
    allowed["GraphEdges"] = [["Change", change_ids[0], "IMPLEMENTS", "WorkItem", work_id]]
    for eid, (event, payload) in all_events.items():
        kind = "WorkItem" if event.event_type.startswith("pdlc.ticket.") else "Change"
        nid = (
            work_id
            if kind == "WorkItem"
            else make_node_id("Change", [payload["repo"], payload["number"]])
        )
        allowed["GraphEdges"].append([kind, nid, "DERIVED_FROM", "Event", eid])
    allowed["GraphEdges"] += [
        ["Event", a, edge, "Event", b]
        for a in all_events
        for b in all_events
        if a != b
        for edge in ("FOLLOWS", "SIMILAR_TO")
    ]
    allowed["ConsumerGroups"] = [[g] for g in groups]
    allowed["ConsumerCursors"] = [[g, s] for g in groups for s in range(settings.spanner.shards)]
    for table in ("ConsumerDeliveries", "ConsumerDeadLetters"):
        allowed[table] = [[g, e] for g in groups for e in all_events]
    evidence["intent"] = {
        "predecessor": OLD,
        "active": owner,
        "restore": restoration,
        "allowed_cleanup_keys": allowed,
        "packs": binding.bundle.pack_identities,
        "processing": binding.bundle.processing,
        "expected_change_ids": change_ids,
        "expected_work_id": work_id,
        "no_ddl": True,
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
        accepted = set()
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=40) as http:
            for sid, source, payload in data["deliveries"]:
                body = encode(payload)
                previous = await asyncio.to_thread(snapshot, database)
                expected_ids = (
                    []
                    if sid == "PR04"
                    else [
                        str(
                            uuid5(
                                WEBHOOK_NAMESPACE, f"{source}:{hashlib.sha256(body).hexdigest()}:0"
                            )
                        )
                    ]
                )
                headers = {
                    "X-Hub-Signature-256" if source == "github" else "X-Hub-Signature": "sha256="
                    + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest(),
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": run_id + "-" + sid,
                }
                item = {
                    "scenario": sid,
                    "source": source,
                    "input_sha256": hashlib.sha256(body).hexdigest(),
                    "expected_status": 422 if sid == "PR04" else 202,
                }
                evidence["scenarios"].append(item)
                durable_json(directory / "observations.json", evidence)
                response = await http.post("/v1/webhooks/" + source, content=body, headers=headers)
                item["response"] = {"status": response.status_code, "body": response.json()}
                durable_json(directory / "observations.json", evidence)
                assert response.status_code == item["expected_status"], (sid, item["response"])
                received = response.json().get("event_ids", [])
                assert received == expected_ids, "Source delivery returned wrong event identity"
                accepted.update(expected_ids)
                completed = False
                for _ in range(300):
                    state = await asyncio.to_thread(snapshot, database)
                    if any(t.done() for t in tasks):
                        for t in tasks:
                            if t.done():
                                await t
                        raise AssertionError("Worker stopped")
                    projected = {n[1] for n in state["nodes"] if n[0] == "Event"}
                    lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
                    if (
                        accepted <= projected
                        and not state["pending"]
                        and all(lag == 0 for lag in lags)
                    ):
                        completed = True
                        break
                    await asyncio.sleep(0.2)
                item["storage"] = state
                item["worker_lags"] = lags
                durable_json(directory / "observations.json", evidence)
                assert completed, "Timed out before every worker finished"
                assert not state["pending"] and not state["dead_letters"], (
                    "Worker completion failed"
                )
                assert {e[0] for e in state["events"]} == accepted, (
                    "Ledger identity/duplicate mismatch"
                )
                assert accepted <= {n[1] for n in state["nodes"] if n[0] == "Event"}
                expected_domain = set()
                expected_domain_edges = set()
                artifact_events = {}
                for eid in accepted:
                    event, event_payload = all_events[eid]
                    label = "WorkItem" if event.event_type.startswith("pdlc.ticket.") else "Change"
                    nid = (
                        work_id
                        if label == "WorkItem"
                        else make_node_id(
                            "Change", [event_payload["repo"], event_payload["number"]]
                        )
                    )
                    expected_domain.add((label, nid))
                    artifact_events.setdefault(nid, []).append(eid)
                    expected_domain_edges.add((label, nid, "DERIVED_FROM", "Event", eid))
                    if (
                        event.event_type == "pdlc.change.merged"
                        and "Closes APP-42" in event_payload["body"]
                    ):
                        expected_domain_edges.add(
                            ("Change", nid, "IMPLEMENTS", "WorkItem", work_id)
                        )
                actual_domain = {
                    (n[0], n[1]) for n in state["nodes"] if n[0] in {"Change", "WorkItem"}
                }
                assert actual_domain == expected_domain, "Unexpected or missing domain artifacts"
                for label, nid, props in state["nodes"]:
                    if label == "Change":
                        observed_events = artifact_events[nid]
                        source_payload = all_events[observed_events[0]][1]
                        assert (props.get("repo"), props.get("number")) == (
                            source_payload["repo"],
                            source_payload["number"],
                        ), "Wrong stored Change identity properties"
                assert {
                    tuple(e[:5]) for e in state["edges"] if e[0] != "Event"
                } == expected_domain_edges, "Unexpected or missing domain/evidence links"
                for eid, document, acceptance in state["events"]:
                    event, expected_payload = all_events[eid]
                    for key, value in event.model_dump(
                        mode="json", exclude={"global_position"}
                    ).items():
                        assert document.get(key) == value, ("Ledger envelope mismatch", eid, key)
                    assert document["payload"] == expected_payload, "Ledger payload mismatch"
                    expected_source = (
                        "webhook.jira"
                        if event.event_type.startswith("pdlc.ticket.")
                        else "webhook.github"
                    )
                    assert acceptance["source_id"] == expected_source
                    assert acceptance["bundle_digest"] == binding.bundle_digest
                if sid in {"PR03", "PR04"}:
                    for section in ("events", "nodes", "edges"):

                        def stable(rows):
                            return sorted(json.dumps(r, sort_keys=True, default=str) for r in rows)

                        assert stable(previous[section]) == stable(state[section]), (
                            "Duplicate/rejection changed stored state"
                        )
                assert not {n[0] for n in state["nodes"]} - {
                    "Event",
                    "Change",
                    "WorkItem",
                    "OntologyState",
                }, "Unexpected optional/domain output"
                nodes = {n[1]: n[2] for n in state["nodes"]}
                if sid in {"PR01", "PR02", "PR03", "PR04", "PR05", "PR08"}:
                    assert change_ids[0] in nodes
                    expected_title = (
                        data["title"]
                        if sid == "PR01"
                        else data["title"] + (" [older edit]" if sid == "PR08" else " [updated]")
                    )
                    assert nodes[change_ids[0]]["title"] == expected_title
                    assert nodes[change_ids[0]]["status"] == (
                        "merged" if sid in {"PR05", "PR08"} else "open"
                    )
                if sid == "PR05":
                    edge = ["Change", change_ids[0], "IMPLEMENTS", "WorkItem", work_id]
                    assert any(
                        e[:5] == edge
                        and e[5].get("method") == "declared"
                        and e[5].get("link_status") == "confirmed"
                        for e in state["edges"]
                    )
                if sid == "PR06":
                    assert nodes[change_ids[1]]["status"] == "merged"
                    assert not any(
                        e[1] == change_ids[1] and e[2] == "IMPLEMENTS" for e in state["edges"]
                    )
                if sid == "PR07":
                    assert all(cid in nodes for cid in change_ids)
                    assert nodes[change_ids[0]]["repo"] != nodes[change_ids[2]]["repo"]
                for eid in accepted:
                    expected_event, expected_payload = all_events[eid]
                    typ = (
                        "WorkItem"
                        if expected_event.event_type.startswith("pdlc.ticket.")
                        else "Change"
                    )
                    nid = (
                        work_id
                        if typ == "WorkItem"
                        else make_node_id(
                            "Change", [expected_payload["repo"], expected_payload["number"]]
                        )
                    )
                    assert any(
                        e[:5] == [typ, nid, "DERIVED_FROM", "Event", eid] for e in state["edges"]
                    ), "Missing event evidence"
                seed = (
                    work_id
                    if source == "jira"
                    else change_ids[2]
                    if sid == "PR07"
                    else change_ids[1]
                    if sid.startswith("PR06")
                    else change_ids[0]
                )
                query = {
                    "query": "trace " + seed,
                    "seed_node_ids": [seed],
                    "intent": "trace",
                    "max_nodes": 20,
                }
                answer = await http.post(
                    "/v1/query/artifacts",
                    json=query,
                    headers={"Authorization": "Bearer g01-local-query-key"},
                )
                item["retrieval"] = {
                    "request": query,
                    "status": answer.status_code,
                    "body": answer.json(),
                }
                durable_json(directory / "observations.json", evidence)
                assert answer.status_code == 200, item["retrieval"]
                returned_nodes = answer.json()["nodes"]
                assert isinstance(returned_nodes, dict), "Unexpected Atlas node response shape"
                matches = [n for n in returned_nodes.values() if n["node_id"] == seed]
                assert matches and matches[0].get("provenance"), (
                    "Artifact missing from retrieval or lacks provenance"
                )
                attributes = matches[0]["attributes"]
                for key in ("title", "status", "repo", "number"):
                    if key in nodes[seed]:
                        assert attributes.get(key) == nodes[seed][key], (
                            "Stale retrieved field",
                            key,
                        )
                newest = max(artifact_events[seed], key=lambda eid: all_events[eid][0].occurred_at)
                assert matches[0]["provenance"]["event_id"] == newest, "Wrong retrieved evidence"
                assert matches[0]["provenance"]["source"] == "spanner"
                assert matches[0]["provenance"]["global_position"], "Missing evidence position"
                assert not [
                    n
                    for n in returned_nodes.values()
                    if n["node_type"] == "Change" and n["node_id"] != seed
                ], "Cross-PR retrieval contamination"
                if sid in {"PR05", "PR08"}:
                    assert any(
                        e["source"] == seed
                        and e["target"] == work_id
                        and e["edge_type"] == "IMPLEMENTS"
                        for e in answer.json()["edges"]
                    ), "Ticket link missing from answer"
                item["verdict"] = "passed"
                evidence["checks"].append({"name": sid, "passed": True, "scenarios": []})
                durable_json(directory / "observations.json", evidence)
                print(sid + " passed", flush=True)
                if first_only:
                    break
    except BaseException as exc:
        evidence["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        evidence["checks"].append(
            {"name": "goal01_required_path", "passed": False, "scenarios": []}
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
        await asyncio.to_thread(close_database, database)
        spanner.Client = original_client
        assert not shutdown_errors, ("Shutdown errors", shutdown_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--first-only", action="store_true")
    parser.add_argument("--expected-epoch", type=int, default=10)
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
        "goal": "G01",
        "phase": "PR01 full-path checkpoint" if args.first_only else "eight PR scenarios",
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
        manifest_path = Path("/private/tmp/engram-g01-run-manifest.json")
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
            print("G01 run failed: " + type(exc).__name__, flush=True)
            code = 1
        finally:
            results = {
                "scenarios": [],
                "summary": "G01: individual scenarios in observations. No baseline promotion.",
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
