"""G03 real HTTP + worker loops + reserved real Spanner planning acceptance demo.

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
import tarfile
import traceback
from pathlib import Path

import httpx
import structlog
import uvicorn
from engram_experiment_support import (
    DemoAuthentication,
    await_settled,
    durable_json,
    fingerprint,
    load_credentials,
    read_owner,
    runtime_settings,
    snapshot,
    stop_demo,
)
from engram_goal03_fixtures import fixtures
from engram_spanner_empty_activation import (
    KEYS,
    RESOURCE,
    activate_empty_target,
    clean_registered_target,
    freeze_target,
)
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.api.app import create_app
from context_graph.domain.models import Event
from context_graph.tenancy import (
    TenantBinding,
)
from context_graph.worker.__main__ import _build_consumer

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility"
SECRET = "g03-local-demo-signing-secret"  # noqa: S105 - isolated test signing key
OLD = [
    "compat-control",
    RESOURCE,
    "compat-control-binding",
    28,
    "sha256:f57ffb649f7ab0197d21f45b9397203887f8cb103e32efd784f4e52ce4c3f7b1",
    "active",
]


async def execute(
    values,
    run_id,
    directory,
    *,
    first_only=False,
    goal="G03",
    fixture_factory=fixtures,
    retain_success=False,
    target_database="engram-compat-target",
):
    data = fixture_factory(run_id)
    journey_passed = False
    durable_json(directory / "fixtures.json", data)
    evidence = {
        "goal": goal,
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
    database = client.instance(values["SPANNER_INSTANCE_ID"]).database(target_database, pool=pool)
    prepare_cleanup(database, client, pool)
    consumers, stores, tasks = [], [], []
    server = server_task = None
    active_owner = None
    mutation_attempted = False
    extraction_outcomes = []
    old_logging = None
    settings = runtime_settings(values, database=target_database)
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
    settings.auth.api_key = "g03-local-query-key"
    settings.rate_limit.enabled = False
    kinds = ("projection", "extraction", "enrichment", "pack_extraction", "consolidation")
    groups = []
    for kind in kinds:
        group = goal.lower() + "-" + run_id + "-" + kind
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
        runtime_settings(values, database=target_database),
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
                DemoAuthentication(app, binding, token="g03-local-query-key"),
                host="127.0.0.1",
                port=port,
                log_level="warning",
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
        expected_edge_properties = {}
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            timeout=40,
            headers={"Authorization": "Bearer g03-local-query-key"},
        ) as http:

            async def retrieve(query, required, forbidden, *, exact=False):
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
                if exact:
                    assert set(returned) == set(required), (
                        "Unexpected retrieval identities",
                        set(returned) ^ set(required),
                    )
                assert not (set(forbidden) & set(returned)), ("Cross-feature contamination", result)
                assert not answer["meta"].get("truncated"), (
                    "Truncated result is not complete acceptance"
                )
                returned_edges = {
                    (edge["edge_type"], edge["source"], edge["target"]) for edge in answer["edges"]
                }
                required_edges = {
                    edge
                    for edge in expected_edges
                    if edge[1] in required
                    and edge[2] in required
                    and expected_edge_properties.get(edge, {}).get("link_status") != "rejected"
                }
                assert required_edges <= returned_edges, (
                    "Missing required retrieval edges",
                    required_edges - returned_edges,
                )
                if goal in {"G04", "G05", "G06"} and exact:
                    assert returned_edges == required_edges, (
                        "Unexpected retrieval edges",
                        returned_edges ^ required_edges,
                    )
                for edge in answer["edges"]:
                    edge_key = (edge["edge_type"], edge["source"], edge["target"])
                    if goal in {"G04", "G05", "G06"} and edge_key in expected_edge_properties:
                        for name, value in expected_edge_properties[edge_key].items():
                            assert edge.get("properties", {}).get(name) == value, (
                                "Wrong retrieval edge property",
                                edge_key,
                                name,
                            )

                    if edge["edge_type"] == "RAN_AGAINST" and edge["source"] in required:
                        assert (
                            edge.get("properties", {}).get("commit_sha")
                            == returned[edge["source"]]["attributes"]["commit_sha"]
                        ), edge
                for nid in required:
                    if nid not in artifact_events:
                        continue
                    provenance = returned[nid].get("provenance")
                    assert (
                        provenance
                        and provenance.get("source") == "spanner"
                        and provenance.get("event_id") in artifact_events[nid]
                    ), ("Wrong evidence", nid, provenance)
                    if goal in {"G04", "G05", "G06"}:
                        newest = max(
                            artifact_events[nid],
                            key=lambda event_id: all_events[event_id][0].occurred_at,
                        )
                        assert provenance["event_id"] == newest, (
                            "Wrong latest source",
                            nid,
                            provenance,
                            newest,
                        )
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
                negative = fixture["expected_status"] != 201 or fixture.get(
                    "duplicate", sid == "IM11-duplicate"
                )
                before_fingerprint = (
                    await asyncio.to_thread(fingerprint, database)
                    if goal in {"G04", "G05", "G06"} and negative
                    else None
                )
                response = await http.post("/v1/events", json=request)
                item["response"] = {"status": response.status_code, "body": response.json()}
                durable_json(directory / "observations.json", evidence)
                assert response.status_code == fixture["expected_status"], item["response"]
                if fixture["expected_status"] == 201:
                    assert response.json()["event_id"] == eid and response.json()["global_position"]
                    is_duplicate = fixture.get("duplicate", sid == "IM11-duplicate")
                    expected_outcome = "duplicate" if is_duplicate else "created"
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
                if fixture["expected_status"] != 201 or fixture.get(
                    "duplicate", sid == "IM11-duplicate"
                ):
                    assert state == previous, "Rejected/duplicate request changed persistent state"
                    if goal in {"G04", "G05", "G06"}:
                        after_fingerprint = await asyncio.to_thread(fingerprint, database)
                        item["no_write_fingerprints"] = {
                            "before": before_fingerprint,
                            "after": after_fingerprint,
                        }
                        assert before_fingerprint == after_fingerprint, (
                            "Rejected/duplicate request changed full persistent state"
                        )
                nid = fixture["expected_node"]
                nodes = {row[1]: row[2] for row in state["nodes"]}
                if nid:
                    expected_nodes[nid] = fixture["expected_props"]
                    if fixture.get("observes_node", True):
                        artifact_events.setdefault(nid, set()).add(eid)
                for extra_id, extra_props in fixture.get("extra_nodes", {}).items():
                    expected_nodes[extra_id] = extra_props
                    if extra_id not in fixture.get("placeholders", []):
                        artifact_events.setdefault(extra_id, set()).add(eid)
                for existing_id, properties in fixture.get("node_assertions", {}).items():
                    assert existing_id in expected_nodes, "Assertion references an unobserved node"
                    expected_nodes[existing_id] = {**expected_nodes[existing_id], **properties}
                for placeholder in fixture.get("placeholders", []):
                    assert not any(
                        r[1] == placeholder and r[2] == "DERIVED_FROM" for r in state["edges"]
                    ), ("Placeholder falsely has event evidence", placeholder)
                expected_edges.update(tuple(e) for e in fixture["expected_edges"])
                for kind, source, target, properties in fixture.get("expected_edge_properties", []):
                    expected_edge_properties[(kind, source, target)] = {
                        name: response.json()["global_position"] if value == "$receipt" else value
                        for name, value in properties.items()
                    }
                domain = {
                    n[1]
                    for n in state["nodes"]
                    if n[0] != "Lesson" or n[1].endswith(":authored")
                    if n[0]
                    in (
                        {
                            "Spec",
                            "Requirement",
                            "DesignElement",
                            "DesignApproval",
                            "WorkItem",
                            "Change",
                            "Review",
                            "TestCase",
                            "TestRun",
                            "Release",
                            "Deployment",
                            "Component",
                        }
                        | ({"Incident", "Lesson"} if goal == "G06" else set())
                    )
                }
                expected_domain = set(expected_nodes)
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
                    if r[2]
                    in (
                        {
                            "REFINES",
                            "APPROVES",
                            "SUPERSEDES",
                            "IMPLEMENTS",
                            "REVIEWS",
                            "VERIFIES",
                            "EXECUTES",
                            "RAN_AGAINST",
                            "INCLUDES",
                            "DEPLOYS",
                            "DEPLOYED_TO",
                        }
                        | (
                            {"AFFECTS", "OCCURRED_ON", "REMEDIATES", "LEARNED_FROM", "CITES"}
                            if goal == "G06"
                            else set()
                        )
                    )
                }
                assert actual_edges == expected_edges, (
                    "Wrong declared planning links",
                    actual_edges ^ expected_edges,
                )
                for edge in state["edges"]:
                    if goal in {"G04", "G05", "G06"} and edge[2] == "DEPLOYED_TO":
                        assert edge[5].get("environment") == nodes[edge[1]].get("environment")
                    if goal in {"G04", "G05", "G06"}:
                        for name, value in expected_edge_properties.get(
                            (edge[2], edge[1], edge[4]), {}
                        ).items():
                            assert edge[5].get(name) == value, (
                                "Wrong stored edge property",
                                edge,
                                name,
                            )
                    if edge[2] == "RAN_AGAINST":
                        run_props = nodes[edge[1]]
                        assert edge[5].get("commit_sha") == run_props.get("commit_sha"), (
                            "Missing/wrong RAN_AGAINST commit",
                            edge,
                            run_props,
                        )
                for key, events in artifact_events.items():
                    assert {(key, event) for event in events} <= {
                        (r[1], r[4]) for r in state["edges"] if r[2] == "DERIVED_FROM"
                    }
                if goal in {"G04", "G05", "G06"}:
                    actual_sources = {
                        (r[1], r[4])
                        for r in state["edges"]
                        if r[2] == "DERIVED_FROM" and r[1] in expected_nodes
                    }
                    required_sources = {
                        (key, event_id)
                        for key, events in artifact_events.items()
                        for event_id in events
                    }
                    assert actual_sources == required_sources, (
                        "Unexpected artifact provenance",
                        actual_sources ^ required_sources,
                    )
                    if fixture.get("absence_id"):
                        item["absence_retrieval"] = await retrieve(
                            {
                                "query": "absence-check-" + eid,
                                "seed_node_ids": [fixture["absence_id"]],
                                "intent": "status",
                                "max_nodes": 50,
                            },
                            [],
                            [fixture["absence_id"]],
                            exact=True,
                        )
                assert not any(
                    r[0] in {"UserProfile", "Preference", "Skill", "Belief", "Goal", "Episode"}
                    for r in state["nodes"]
                )
                if nid:
                    query = {
                        "query": "status " + nid,
                        "seed_node_ids": [nid],
                        "intent": "status",
                        "max_nodes": 50,
                    }
                    item["retrieval"] = await retrieve(query, [nid], [])
                    if goal in {"G04", "G05", "G06"}:
                        for placeholder in fixture.get("placeholders", []):
                            result = await retrieve(
                                {
                                    "query": "status " + placeholder,
                                    "seed_node_ids": [placeholder],
                                    "intent": "status",
                                    "max_nodes": 50,
                                },
                                [placeholder],
                                [],
                            )
                            assert not result["body"]["nodes"][placeholder].get("provenance"), (
                                "Placeholder API falsely claims provenance"
                            )
                            item.setdefault("placeholder_retrieval", []).append(result)

                else:
                    seed = data["fallback_seed"] if "fallback_seed" in data else data["ids"]["spec"]
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
                        "seed_node_ids": fixture.get(
                            "seeds", [fixture["seed"]] if fixture["seed"] else []
                        ),
                        "intent": fixture["intent"],
                        "max_nodes": 50,
                        "max_depth": fixture.get("max_depth", 5),
                    }
                    item = {
                        "scenario": sid,
                        "retrieval": await retrieve(
                            query,
                            fixture["required"],
                            fixture["forbidden"],
                            exact=fixture.get("exact", False),
                        ),
                        "verdict": "passed",
                    }
                    evidence["scenarios"].append(item)
                    evidence["checks"].append({"name": sid, "passed": True, "scenarios": []})
                    durable_json(directory / "observations.json", evidence)
                    print(sid + " passed", flush=True)
            journey_passed = not first_only and len(evidence["checks"]) == len(data["steps"]) + len(
                data["queries"]
            )
    except BaseException as exc:
        evidence["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        evidence["checks"].append(
            {"name": goal.lower() + "_required_path", "passed": False, "scenarios": []}
        )
        durable_json(directory / "observations.json", evidence)
        raise
    finally:
        shutdown_errors = await stop_demo(consumers, tasks, stores, server, server_task)
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
        keep_dataset = retain_success and journey_passed and not shutdown_errors
        if keep_dataset:
            assert active_owner == owner, "Retained owner changed"
            evidence["retention"] = {
                "status": "retained_pending_stakeholder_cleanup_approval",
                "owner": active_owner,
                "run_id": run_id,
                "packs": binding.bundle.pack_identities,
                "fingerprints": await asyncio.to_thread(fingerprint, database),
                "registered_cleanup_keys": allowed,
                "workers_and_HTTP": "stopped and settled; no unattended process",
                "cleanup": "Explicit approval required before deleting or reusing dataset",
            }
            durable_json(directory / "retained-dataset.json", evidence["retention"])
            durable_json(directory / "observations.json", evidence)
        else:
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
                        runtime_settings(values, database=target_database),
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


def main(
    *,
    goal="G03",
    fixture_factory=fixtures,
    driver_path=None,
    retain_success=False,
    target_database="engram-compat-target",
):
    global RESOURCE
    if (goal == "G06") != (target_database == "engram-g06-target"):
        raise ValueError("G06 requires its separate reserved database")
    RESOURCE = "projects/portiq-mvp/instances/engram-experiment/databases/" + target_database
    OLD[1] = RESOURCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--first-only", action="store_true")
    parser.add_argument("--expected-epoch", type=int, default=OLD[3])
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
        "goal": goal,
        "phase": goal + " first-input checkpoint"
        if args.first_only
        else goal + " full journey scenarios",
        "target": RESOURCE,
        "scope": "one ordinary bound app; no tenant dispatcher sign-off",
        "source_sha256": hashlib.sha256((driver_path or Path(__file__)).read_bytes()).hexdigest(),
        "runtime_sources": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src").rglob("*"))
            if p.is_file() and p.suffix in {".py", ".yaml"}
        },
        "harness_sources": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (
                Path(__file__),
                ROOT / "scripts/engram_experiment_support.py",
                ROOT / ("scripts/engram_" + goal.lower().replace("g", "goal", 1) + "_fixtures.py"),
            )
        },
        "code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "dirty_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "--binary"])
        ).hexdigest(),
        "credential_handling": "Token SDK bootstrap; token never persisted in evidence",
    }
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = Path("/private/tmp/engram-" + goal.lower() + "-run-manifest.json")
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
        if goal in {"G04", "G05", "G06"}:
            # Freeze contents before the first cloud read/write, not just after execution.
            paths = sorted(
                set(manifest["runtime_sources"])
                | {str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("engram*.py")}
                | {
                    "scripts/track_spanner_compatibility.py",
                    "pyproject.toml",
                    "uv.lock",
                    "tests/unit/test_goal04_release_journey.py",
                    *(["tests/unit/test_goal05_connected_journey.py"] if goal == "G05" else []),
                    *(
                        [
                            str(p.relative_to(ROOT))
                            for p in (ROOT / "tests/unit").glob("test_goal06*.py")
                        ]
                        if goal == "G06"
                        else []
                    ),
                    "tests/fixtures/pack_contracts/pdlc.json",
                }
            )
            hashes = {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths
            }
            with tarfile.open(directory / "executed-source.tar.gz", "w:gz") as archive:
                for name in paths:
                    archive.add(ROOT / name, arcname=name)
            durable_json(directory / "executed-source-sha256.json", hashes)
        code = 0
        try:
            asyncio.run(
                await_settled(
                    execute(
                        values,
                        args.run_id,
                        directory,
                        first_only=args.first_only,
                        goal=goal,
                        fixture_factory=fixture_factory,
                        retain_success=retain_success,
                        target_database=target_database,
                    )
                )
            )
        except BaseException as exc:
            print(goal + " run failed: " + type(exc).__name__, flush=True)
            code = 1
        finally:
            results = {
                "scenarios": [],
                "summary": goal + ": individual scenarios in observations. No baseline promotion.",
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
