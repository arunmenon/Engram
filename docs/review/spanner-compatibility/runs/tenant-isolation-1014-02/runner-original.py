"""Two approved databases, one public dispatcher, ten real workers; retain evidence.

Only external model outputs are scripted. Acceptance artifacts are written/read
through authenticated HTTP. Operator export/epoch transitions are explicit.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import socket
import time
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import uvicorn
from engram_composition_assessment import INSTANCE, PROJECT, ROOT, settings_for, token
from engram_composition_reuse import TARGET, freeze_and_export, reset_to
from engram_experiment_support import (
    CONTROL_COLUMNS,
    durable_json,
    fingerprint,
    read_owner,
    snapshot,
    stop_demo,
)
from engram_pack_combination_demo import PackProvider, Providers, fixtures
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.log import json_value
from context_graph.api.tenants import create_tenant_app
from context_graph.ports.errors import RuntimeFencedError
from context_graph.retrieval.engine import RetrievalEngine
from context_graph.tenancy import CredentialGrant, Principal, TenantBinding, TenantCatalog
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

TARGETS = {"a": TARGET, "b": TARGET.rsplit("/", 1)[0] + "/engram-g07-target"}
TOKENS = {t: "isolation-local-fixture-" + t + "-credential-1014" for t in TARGETS}


def plans_for(run_id):
    a = fixtures(run_id, "user-memory")
    b = copy.deepcopy(a)
    b.update(user=False, pdlc=True)
    b["accepted"] += ["pr", "merge", "unrelated-pr"]
    b["events"]["belief"]["payload"]["belief_text"] = "Tenant B tokens expire in thirty minutes."
    b["events"]["goal"]["payload"]["description"] = "Tenant B implements thirty-minute expiry."
    for t, plan in [("a", a), ("b", b)]:
        event = copy.deepcopy(plan["events"]["preference"])
        event.update(
            event_id=str(uuid5(NAMESPACE_URL, run_id + ":restart:" + t)),
            occurred_at=(
                datetime.fromisoformat(plan["events"]["bad-pdlc"]["occurred_at"])
                + timedelta(seconds=1)
            ).isoformat(),
            payload={"content": "Fresh restarted tenant " + t + " event"},
        )
        plan["restart_event"] = event
    return {"a": a, "b": b}


async def execute(directory, bindings, databases, plans):
    record = {
        "state": "running",
        "checks": [],
        "requests": [],
        "limitations": [
            "Scripted external model outputs; no model quality claim",
            "Hierarchy policies, pilot, native webhooks and streaming cursors excluded",
        ],
    }
    consumers = []
    tasks = []
    stores = []
    by_tenant = {}
    server = None
    server_task = None
    providers = {t: Providers(plans[t]) for t in bindings}
    retrieved, release = asyncio.Event(), asyncio.Event()
    original_retrieve = RetrievalEngine.get_subgraph

    async def observed_retrieval(engine, query):
        result = await original_retrieve(engine, query)
        if query.query == "hold this response for ownership transition":
            retrieved.set()
            await release.wait()
        return result

    RetrievalEngine.get_subgraph = observed_retrieval

    def save():
        record["providers"] = {t: p.calls for t, p in providers.items()}
        durable_json(directory / "results.json", record)

    def check(name, ok, actual=None):
        record["checks"].append({"name": name, "passed": bool(ok), "actual": actual})
        save()
        if not ok:
            raise AssertionError(name)

    async def state(t):
        return await asyncio.to_thread(snapshot, databases[t])

    async def settle():
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done():
                    await task
                    raise RuntimeError("worker exited before shutdown")
            lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
            snapshots = await asyncio.gather(*(state(t) for t in bindings))
            if not any(lags) and all(not s["pending"] for s in snapshots):
                check(
                    "ten workers settled; zero DLQ", all(not s["dead_letters"] for s in snapshots)
                )
                return dict(zip(bindings, snapshots, strict=True))
            await asyncio.sleep(0.3)
        raise TimeoutError("ten workers did not settle")

    async def fingerprints():
        return dict(
            zip(
                databases,
                await asyncio.gather(
                    *(asyncio.to_thread(fingerprint, d) for d in databases.values())
                ),
                strict=True,
            )
        )

    try:
        grants = []
        for t, binding in bindings.items():
            for suffix, roles in [("", {"api", "admin"}), ("-api", {"api"})]:
                grants.append(
                    CredentialGrant.from_token(
                        Principal(
                            "credential-" + t + suffix,
                            binding.tenant_id,
                            frozenset(roles),
                            source_id="demo.query",
                        ),
                        TOKENS[t] + suffix,
                    )
                )
        app = create_tenant_app(TenantCatalog(tuple(bindings.values()), tuple(grants)))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        server_task = asyncio.create_task(server.serve())
        for _ in range(300):
            if server.started:
                break
            if server_task.done():
                await server_task
            await asyncio.sleep(0.1)
        check("public dispatcher ready", server.started)
        for t, binding in bindings.items():
            by_tenant[t] = []
            for kind in VALID_CONSUMERS:
                worker, store = await _build_consumer(
                    kind, binding.settings(), tenant_binding=binding
                )
                if kind in {"extraction", "consolidation"}:
                    worker._llm_client = providers[t]
                if kind == "pack_extraction":
                    worker._model = PackProvider(providers[t])
                consumers.append(worker)
                stores.append(store)
                by_tenant[t].append(worker)
                tasks.append(asyncio.create_task(worker.run()))
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            timeout=45,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(t, path, body=None, method="POST", headers=None):
                hdr = {"Authorization": "Bearer " + TOKENS[t]} if t else {}
                if headers is not None:
                    hdr = headers
                row = {"tenant": t, "method": method, "path": path, "input": body}
                record["requests"].append(row)
                save()
                try:
                    response = await http.request(method, path, json=body, headers=hdr)
                except BaseException as exc:
                    row["error"] = repr(exc)
                    save()
                    raise
                try:
                    output = response.json()
                except ValueError:
                    output = response.text
                row.update(status=response.status_code, output=output)
                save()
                return response.status_code, output

            async def query(
                t, intent, session, seed=None, cursor=None, text="retrieve supported evidence"
            ):
                payload = {
                    "query": text,
                    "intent": intent,
                    "agent_id": "alice",
                    "session_id": session,
                    "max_nodes": 100,
                    "max_depth": 5,
                }
                if seed:
                    payload["seed_nodes"] = seed
                if cursor is not None:
                    payload["cursor"] = cursor
                status, answer = await request(t, "/v1/query/subgraph", payload)
                if status == 200:
                    check(
                        t + " subgraph untruncated " + intent,
                        answer.get("meta", {}).get("truncated") is False,
                        answer.get("meta"),
                    )
                return status, answer

            for key in plans["b"]["accepted"]:
                selected = [t for t in bindings if key in plans[t]["accepted"]]
                responses = await asyncio.gather(
                    *(request(t, "/v1/events", plans[t]["events"][key]) for t in selected)
                )
                for t, (status, answer) in zip(selected, responses, strict=True):
                    check(t + " admits " + key, status == 201, answer)
                await settle()
            observed = await settle()
            for t, s in observed.items():
                nodes = {(label, key): json_value(props) for label, key, props in s["nodes"]}
                events = {row[0] for row in s["events"]}
                expected_keys = plans[t]["accepted"]
                check(
                    t + " exact accepted ledger IDs",
                    events == {plans[t]["events"][k]["event_id"] for k in expected_keys},
                )
                for event_id, raw_document, raw_acceptance in s["events"]:
                    document, acceptance = json_value(raw_document), json_value(raw_acceptance)
                    key = next(
                        k for k in expected_keys if plans[t]["events"][k]["event_id"] == event_id
                    )
                    expected = plans[t]["events"][key]
                    check(
                        t + " exact ledger content " + key,
                        all(
                            (
                                datetime.fromisoformat(document[field])
                                == datetime.fromisoformat(value)
                                if field == "occurred_at"
                                else document.get(field) == value
                            )
                            for field, value in expected.items()
                        ),
                        document,
                    )
                    binding = bindings[t]
                    check(
                        t + " ledger authority " + key,
                        all(
                            acceptance.get(field) == value
                            for field, value in {
                                "tenant_id": binding.tenant_id,
                                "database_resource": binding.database_resource,
                                "binding_id": binding.binding_id,
                                "accepted_epoch": binding.epoch,
                                "bundle_digest": binding.bundle_digest,
                                "engine_revision": binding.engine_revision,
                                "source_id": "demo.query",
                            }.items()
                        ),
                        acceptance,
                    )
                    event_props = nodes[("Event", event_id)]
                    check(
                        t + " projected Event identity " + key,
                        all(
                            (
                                datetime.fromisoformat(event_props[field])
                                == datetime.fromisoformat(expected[field])
                                if field == "occurred_at"
                                else event_props.get(field) == expected[field]
                            )
                            for field in [
                                "event_id",
                                "event_type",
                                "occurred_at",
                                "session_id",
                                "agent_id",
                                "trace_id",
                            ]
                        ),
                        event_props,
                    )
                check(
                    t + " exact belief content",
                    nodes[("Belief", plans[t]["ids"]["belief"])]["belief_text"]
                    == plans[t]["events"]["belief"]["payload"]["belief_text"],
                )
                check(
                    t + " exact goal content",
                    nodes[("Goal", plans[t]["ids"]["goal"])]["description"]
                    == plans[t]["events"]["goal"]["payload"]["description"],
                )
                check(
                    t + " User selection",
                    any(label == "UserProfile" for label, key in nodes) == (t == "a"),
                )
                check(
                    t + " PDLC selection",
                    any(label == "Change" for label, key in nodes) == (t == "b"),
                )
                check(
                    t + " memory source evidence",
                    all(
                        {
                            edge[4]
                            for edge in s["edges"]
                            if edge[0] == label
                            and edge[1] == plans[t]["ids"][kind]
                            and edge[2] == "DERIVED_FROM"
                            and edge[3] == "Event"
                        }
                        == {plans[t]["events"][k]["event_id"] for k in keys}
                        for label, kind, keys in [
                            ("Belief", "belief", ["belief", "confirmation"]),
                            ("Goal", "goal", ["goal", "completion"]),
                        ]
                    ),
                )
            # Drain background consolidation before full-table no-effect assertions.
            for consumer in consumers:
                consumer.stop()
            joined = await asyncio.gather(*tasks, return_exceptions=True)
            check(
                "all ten worker loops drained normally",
                all(not isinstance(value, BaseException) for value in joined),
                [type(value).__name__ for value in joined],
            )
            record["processed_snapshots"] = observed
            save()
            # Same replay identity is isolated per database; disabled contract refuses.
            before = await fingerprints()
            for t in bindings:
                status, answer = await request(t, "/v1/events", plans[t]["events"]["belief"])
                check(t + " duplicate status", status == 201, answer)
                conflict = copy.deepcopy(plans[t]["events"]["belief"])
                conflict["payload"]["belief_text"] = "conflicting content"
                status, answer = await request(t, "/v1/events", conflict)
                check(t + " conflict refused", status == 409, answer)
            status, answer = await request("a", "/v1/events", plans["a"]["events"]["pr"])
            check("a disabled PDLC refused", status == 422, answer)
            check("duplicates/conflicts/disabled writes unchanged", await fingerprints() == before)
            # Body cursor and denied auth must not even increment access counters.
            before = await fingerprints()
            attempts = [
                (None, {}, 401),
                ("a", {"Authorization": "Bearer unknown"}, 401),
                (
                    "a",
                    {
                        "Authorization": "Bearer " + TOKENS["a"],
                        "X-Tenant-ID": bindings["b"].tenant_id,
                    },
                    401,
                ),
            ]
            for t, hdr, expected in attempts:
                status, answer = await request(
                    t, "/v1/events", plans["a"]["events"]["belief"], headers=hdr
                )
                check("unauthorized ingress refused", status == expected, answer)
            status, answer = await request(
                "a",
                "/v1/events",
                plans["a"]["events"]["belief"],
                headers=[
                    ("Authorization", "Bearer " + TOKENS["a"]),
                    ("Authorization", "Bearer " + TOKENS["b"]),
                ],
            )
            check("duplicate authorization headers refused", status == 401, answer)
            forged = copy.deepcopy(plans["a"]["events"]["belief"])
            forged["tenant_id"] = bindings["b"].tenant_id
            forged["database_resource"] = bindings["b"].database_resource
            status, answer = await request("a", "/v1/events", forged)
            check("forged routing fields cannot switch database", status in {201, 422}, answer)
            status, answer = await query(
                "a", "what", plans["a"]["memory_session"], cursor="foreign-cursor"
            )
            check("JSON cursor refused", status == 400, answer)
            for path, method, body, expected in [
                ("/metrics", "GET", None, 503),
                ("/v1/webhooks/github", "POST", {}, 503),
                ("/v1/events/import", "POST", {}, 503),
                ("/v1/admin/prune", "POST", {}, 503),
                ("/v1/admin/replay", "POST", {}, 503),
                ("/v1/admin/reconsolidate", "POST", {}, 503),
                ("/v1/context/x?cursor=foreign", "GET", None, 400),
                ("/v1/admin/stats", "GET", None, 403),
            ]:
                hdr = {"Authorization": "Bearer " + TOKENS["a"] + "-api"}
                status, answer = await request("a", path, body, method, headers=hdr)
                check("unsupported/role " + path, status == expected, answer)
            check("rejected requests leave both targets unchanged", await fingerprints() == before)
            for t in bindings:
                status, answer = await query(t, "beliefs", plans[t]["memory_session"])
                check(t + " Belief retrieval status", status == 200, answer)
                check(
                    t + " Belief retrieval tenant content",
                    answer.get("nodes", {})
                    .get(plans[t]["ids"]["belief"], {})
                    .get("attributes", {})
                    .get("belief_text")
                    == plans[t]["events"]["belief"]["payload"]["belief_text"],
                    answer,
                )
                provenance = (
                    answer.get("nodes", {}).get(plans[t]["ids"]["belief"], {}).get("provenance", {})
                )
                check(
                    t + " public Belief source authority",
                    provenance.get("event_id") == plans[t]["events"]["belief"]["event_id"]
                    and provenance.get("agent_id") == "alice"
                    and provenance.get("session_id") == plans[t]["memory_session"]
                    and provenance.get("source") == "spanner",
                    provenance,
                )
                expected_source = plans[t]["events"]["belief"]
                expected_position = next(
                    row["output"]["global_position"]
                    for row in record["requests"]
                    if row["tenant"] == t
                    and row["path"] == "/v1/events"
                    and row.get("status") == 201
                    and row["input"]["event_id"] == expected_source["event_id"]
                )
                check(
                    t + " Belief provenance exact own ledger position/time/trace",
                    provenance.get("global_position") == expected_position
                    and datetime.fromisoformat(provenance["occurred_at"])
                    == datetime.fromisoformat(expected_source["occurred_at"])
                    and provenance.get("trace_id") == expected_source["trace_id"],
                    provenance,
                )
                check(
                    t + " public belief evidence exact",
                    {
                        e["target"]
                        for e in answer.get("edges", [])
                        if e["source"] == plans[t]["ids"]["belief"]
                        and e["edge_type"] == "DERIVED_FROM"
                    }
                    == {plans[t]["events"][k]["event_id"] for k in ["belief", "confirmation"]},
                    answer,
                )
                status, answer = await query(t, "when", plans[t]["memory_session"])
                check(
                    t + " Goal retrieval completed",
                    status == 200
                    and answer.get("nodes", {})
                    .get(plans[t]["ids"]["goal"], {})
                    .get("attributes", {})
                    .get("status")
                    == "completed",
                    answer,
                )
                goal = answer.get("nodes", {}).get(plans[t]["ids"]["goal"], {})
                check(
                    t + " public Goal exact description and source",
                    goal.get("attributes", {}).get("description")
                    == plans[t]["events"]["goal"]["payload"]["description"]
                    and goal.get("provenance", {}).get("event_id")
                    == plans[t]["events"]["goal"]["event_id"],
                    goal,
                )
                check(
                    t + " public Goal evidence exact",
                    {
                        e["target"]
                        for e in answer.get("edges", [])
                        if e["source"] == plans[t]["ids"]["goal"]
                        and e["edge_type"] == "DERIVED_FROM"
                    }
                    == {plans[t]["events"][k]["event_id"] for k in ["goal", "completion"]},
                    answer,
                )
                expected_source = plans[t]["events"]["goal"]
                expected_position = next(
                    row["output"]["global_position"]
                    for row in record["requests"]
                    if row["tenant"] == t
                    and row["path"] == "/v1/events"
                    and row.get("status") == 201
                    and row["input"]["event_id"] == expected_source["event_id"]
                )
                provenance = goal.get("provenance", {})
                check(
                    t + " Goal provenance exact own ledger authority",
                    provenance.get("global_position") == expected_position
                    and provenance.get("agent_id") == "alice"
                    and provenance.get("session_id") == plans[t]["memory_session"]
                    and datetime.fromisoformat(provenance["occurred_at"])
                    == datetime.fromisoformat(expected_source["occurred_at"])
                    and provenance.get("trace_id") == expected_source["trace_id"],
                    provenance,
                )
                status, answer = await request(t, "/v1/users/user:alice/profile", method="GET")
                check(t + " profile HTTP selection", status == (200 if t == "a" else 404), answer)
                if t == "a":
                    check(
                        "A profile identity/content",
                        answer.get("profile_id") == plans[t]["ids"]["profile"]
                        and answer.get("display_name") == "Alice",
                        answer,
                    )
                    status, answer = await query(t, "personalize", plans[t]["user_session"])
                    check(
                        "A personalization includes canonical profile and correction",
                        status == 200
                        and {plans[t]["ids"]["profile"], plans[t]["ids"]["negative"]}
                        <= answer.get("nodes", {}).keys()
                        and plans[t]["ids"]["positive"] not in answer.get("nodes", {}),
                        answer,
                    )
                status, answer = await request(
                    t,
                    "/v1/query/artifacts",
                    {
                        "query": "trace this change",
                        "intent": "trace",
                        "seed_node_ids": [plans[t]["ids"]["change"]],
                    },
                )
                check(t + " artifact query status", status == 200, answer)
                check(
                    t + " exact foreign-only Change isolation",
                    (plans[t]["ids"]["change"] in answer.get("nodes", {})) == (t == "b"),
                    answer,
                )
                if t == "b":
                    change = answer.get("nodes", {}).get(plans[t]["ids"]["change"], {})
                    check(
                        "B PDLC exact content and latest source",
                        change.get("attributes", {}).get("status") == "merged"
                        and change.get("attributes", {}).get("title") == "Reset expiry"
                        and change.get("provenance", {}).get("event_id")
                        == plans[t]["events"]["merge"]["event_id"],
                        change,
                    )
                status, answer = await request(t, "/v1/admin/stats", method="GET")
                check(t + " authorized stats", status == 200, answer)
            # One database frozen while other tenant remains usable. Resume by NEW epoch only,
            # after old workers/API have been shut down; leave frozen A if recovery fails.
            held = asyncio.create_task(
                query(
                    "a",
                    "beliefs",
                    plans["a"]["memory_session"],
                    text="hold this response for ownership transition",
                )
            )
            await asyncio.wait_for(retrieved.wait(), 45)
            predecessor = (await asyncio.to_thread(read_owner, databases["a"]))[0]
            frozen = [*predecessor[:-1], "frozen"]
            durable_json(
                directory / "freeze-a-intent.json", {"previous": predecessor, "intended": frozen}
            )

            def freeze(tx):
                from google.cloud.spanner_v1 import KeySet

                rows = list(tx.read("TenantControl", CONTROL_COLUMNS, KeySet(keys=[["active"]])))
                if rows != [predecessor]:
                    raise ValueError("owner drift")
                tx.update("TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *frozen]])

            await asyncio.to_thread(databases["a"].run_in_transaction, freeze)
            for worker in by_tenant["a"]:
                try:
                    await worker._subscription.ack(
                        next(
                            row["output"]["global_position"]
                            for row in record["requests"]
                            if row["tenant"] == "a"
                            and row["path"] == "/v1/events"
                            and row.get("status") == 201
                            and row["input"]["event_id"]
                            == plans["a"]["events"]["belief"]["event_id"]
                        )
                    )
                except RuntimeFencedError:
                    check(
                        "stale A acknowledgement refused " + worker._subscription.group_name, True
                    )
                else:
                    check(
                        "stale A acknowledgement refused " + worker._subscription.group_name, False
                    )
            before = await fingerprints()
            release.set()
            status, answer = await held
            check(
                "already retrieved A response fenced before release",
                status == 503 and answer == {"detail": "Tenant runtime unavailable"},
                answer,
            )
            status, answer = await query("a", "beliefs", plans["a"]["memory_session"])
            check("frozen A read refused", status == 503, answer)
            status, answer = await request("a", "/v1/events", plans["a"]["events"]["belief"])
            check("frozen A write refused", status == 503, answer)
            status, answer = await query("b", "beliefs", plans["b"]["memory_session"])
            check("B remains usable when A frozen", status == 200, answer)
            after = await fingerprints()
            check("frozen A application state unchanged", after["a"] == before["a"])
            record["state"] = "scenarios-passed-awaiting-fenced-restart-verification"
            save()
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        save()
        raise
    finally:
        release.set()
        RetrievalEngine.get_subgraph = original_retrieve
        errors = await stop_demo(consumers, tasks, stores, server, server_task)
        record["shutdown_errors"] = errors
        for t, db in databases.items():
            durable_json(
                directory / (t + "-retained.json"),
                {
                    "database": db.name,
                    "owner": await asyncio.to_thread(read_owner, db),
                    "fingerprints": await asyncio.to_thread(fingerprint, db),
                },
            )
        if errors:
            record["state"] = "failed"
        save()
        if errors:
            raise RuntimeError("unexpected shutdown errors: " + repr(errors))


async def verify_restart(directory, bindings, databases, plans):
    record = {"state": "running", "checks": [], "requests": []}
    consumers, tasks, stores = [], [], []
    server = server_task = None

    def check(name, passed, actual=None):
        record["checks"].append({"name": name, "passed": bool(passed), "actual": actual})
        durable_json(directory / "restart-results.json", record)
        if not passed:
            raise AssertionError(name)

    try:
        catalog = TenantCatalog(
            tuple(bindings.values()),
            tuple(
                CredentialGrant.from_token(
                    Principal(
                        "restart-" + t,
                        b.tenant_id,
                        frozenset({"api", "admin"}),
                        source_id="demo.query",
                    ),
                    TOKENS[t],
                )
                for t, b in bindings.items()
            ),
        )
        app = create_tenant_app(catalog)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        server_task = asyncio.create_task(server.serve())
        for _ in range(300):
            if server.started:
                break
            if server_task.done():
                await server_task
            await asyncio.sleep(0.1)
        check("new epoch public dispatcher startup", server.started)
        for t, binding in bindings.items():
            provider = Providers(plans[t])
            for kind in VALID_CONSUMERS:
                worker, store = await _build_consumer(
                    kind, binding.settings(), tenant_binding=binding
                )
                if kind in {"extraction", "consolidation"}:
                    worker._llm_client = provider
                if kind == "pack_extraction":
                    worker._model = PackProvider(provider)
                consumers.append(worker)
                stores.append(store)
                tasks.append(asyncio.create_task(worker.run()))
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=45) as http:
            for t in bindings:
                payload = {
                    "query": "retrieve belief",
                    "intent": "beliefs",
                    "session_id": plans[t]["memory_session"],
                    "agent_id": "alice",
                    "max_nodes": 100,
                }
                response = await http.post(
                    "/v1/query/subgraph",
                    json=payload,
                    headers={"Authorization": "Bearer " + TOKENS[t]},
                )
                answer = response.json()
                record["requests"].append(
                    {
                        "tenant": t,
                        "input": payload,
                        "status": response.status_code,
                        "output": answer,
                    }
                )
                check(
                    t + " restart retrieves original tenant Belief",
                    response.status_code == 200
                    and answer.get("nodes", {})
                    .get(plans[t]["ids"]["belief"], {})
                    .get("attributes", {})
                    .get("belief_text")
                    == plans[t]["events"]["belief"]["payload"]["belief_text"],
                    answer,
                )
                response = await http.post(
                    "/v1/events",
                    json=plans[t]["events"]["belief"],
                    headers={"Authorization": "Bearer " + TOKENS[t]},
                )
                check(
                    t + " duplicate replay across API restart",
                    response.status_code == 201,
                    response.json(),
                )
            for t in bindings:
                event = plans[t]["restart_event"]
                response = await http.post(
                    "/v1/events", json=event, headers={"Authorization": "Bearer " + TOKENS[t]}
                )
                record["requests"].append(
                    {
                        "tenant": t,
                        "input": event,
                        "status": response.status_code,
                        "output": response.json(),
                    }
                )
                check(
                    t + " fresh event admitted after restart",
                    response.status_code == 201,
                    response.json(),
                )
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                for task in tasks:
                    if task.done():
                        await task
                        raise RuntimeError("restarted worker exited")
                if not any(await asyncio.gather(*(w._subscription.lag() for w in consumers))):
                    break
                await asyncio.sleep(0.3)
            else:
                raise TimeoutError("restart workers did not settle")
            check(
                "all ten restarted worker loops active",
                len(tasks) == 10 and all(not task.done() for task in tasks),
            )
            for t, db in databases.items():
                observed = await asyncio.to_thread(snapshot, db)
                event = plans[t]["restart_event"]
                check(
                    t + " fresh restart Event projected",
                    any(
                        label == "Event" and identity == event["event_id"]
                        for label, identity, props in observed["nodes"]
                    ),
                )
                check(
                    t + " restart delivery queues empty",
                    not observed["pending"] and not observed["dead_letters"],
                )
        record["state"] = "passed"
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        raise
    finally:
        errors = await stop_demo(consumers, tasks, stores, server, server_task)
        record["shutdown_errors"] = errors
        if errors:
            record["state"] = "failed"
        for t, db in databases.items():
            durable_json(
                directory / (t + "-final-retained.json"),
                {
                    "database": db.name,
                    "owner": await asyncio.to_thread(read_owner, db),
                    "fingerprints": await asyncio.to_thread(fingerprint, db),
                    "snapshot": await asyncio.to_thread(snapshot, db),
                },
            )
        durable_json(directory / "restart-results.json", record)
        if errors:
            raise RuntimeError("restart shutdown failed: " + repr(errors))


async def verify_mismatched_startup(directory, bindings, databases):
    before = {t: await asyncio.to_thread(fingerprint, db) for t, db in databases.items()}
    invalid = dict(bindings)
    invalid["b"] = replace(bindings["b"], epoch=bindings["b"].epoch + 100)
    catalog = TenantCatalog(
        tuple(invalid.values()),
        tuple(
            CredentialGrant.from_token(
                Principal("startup-" + t, b.tenant_id, frozenset({"api"}), source_id="demo.query"),
                TOKENS[t],
            )
            for t, b in invalid.items()
        ),
    )
    messages = []
    incoming = iter([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    async def receive():
        return next(incoming)

    async def send(message):
        messages.append(message)

    await create_tenant_app(catalog)(
        {"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send
    )
    after = {t: await asyncio.to_thread(fingerprint, db) for t, db in databases.items()}
    passed = (
        messages == [{"type": "lifespan.startup.failed", "message": "Tenant startup failed"}]
        and before == after
    )
    durable_json(
        directory / "mismatched-startup.json",
        {"passed": passed, "messages": messages, "before": before, "after": after},
    )
    if not passed:
        raise AssertionError("mismatched owner startup must fail without effects")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-directory", type=Path)
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("unsafe run ID")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    directory.mkdir()
    plans = plans_for(args.run_id)
    durable_json(
        directory / "manifest.json",
        {
            "targets": TARGETS,
            "plans": plans,
            "scope": "public dispatcher, ten workers; no direct artifact writes",
        },
    )
    durable_json(
        directory / "source-hashes.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(
                [*ROOT.glob("src/**/*.py"), *ROOT.glob("src/**/*.yaml"), *ROOT.glob("scripts/*.py")]
            )
        },
    )
    credentials = Credentials(token(impersonate=True))
    original = spanner.Client

    def authenticated(*a, **kw):
        kw["credentials"] = credentials
        return original(*a, **kw)

    spanner.Client = authenticated
    client = authenticated(project=PROJECT)
    databases = {}
    bindings = {}
    try:
        for t, target in TARGETS.items():
            pool = BurstyPool()
            db = client.instance(INSTANCE).database(target.rsplit("/", 1)[1], pool=pool)
            prepare_cleanup(db, client, pool)
            databases[t] = db
            prior_path = (
                args.previous_directory / (t + "-attempt-final-state.json")
                if args.previous_directory
                else ROOT
                / "docs/review/spanner-compatibility/runs/tenant-isolation-1014-preflight"
                / ("runtime-" + target.rsplit("/", 1)[1] + ".json")
            )
            previous = json.loads(prior_path.read_text())
            durable_json(
                directory / (t + "-previous-evidence.json"),
                {
                    "path": str(prior_path),
                    "sha256": hashlib.sha256(prior_path.read_bytes()).hexdigest(),
                    "owner": previous["owner"],
                    "fingerprints": previous["fingerprints"],
                },
            )
            if previous["database"] != target:
                raise ValueError("wrong expected target")
            settings = settings_for(
                args.run_id,
                "user-memory" if t == "a" else "pdlc-memory",
                target_database=target.rsplit("/", 1)[1],
            )
            settings.decay.reflection_threshold = 5
            settings.decay.reconsolidation_interval_hours = 20 / 3600
            bound = TenantBinding.from_settings(
                "isolation-" + t,
                args.run_id + "-" + t,
                previous["owner"][0][3] + 1,
                settings,
                engine_revision="tenant-isolation-v1",
            )
            bindings[t] = bound
            await asyncio.to_thread(db.reload)
            durable_json(directory / (t + "-schema-before.json"), list(db.ddl_statements))
            durable_json(
                directory / (t + "-binding.json"),
                {
                    "tenant_id": bound.tenant_id,
                    "database_resource": bound.database_resource,
                    "binding_id": bound.binding_id,
                    "epoch": bound.epoch,
                    "bundle_digest": bound.bundle_digest,
                    "engine_revision": bound.engine_revision,
                    "packs": bound.bundle.pack_identities,
                },
            )
            export = directory / (t + "-previous-export.json")
            frozen, exported, digest = await asyncio.to_thread(
                freeze_and_export,
                db,
                previous["owner"][0],
                previous["fingerprints"],
                export,
                authorized_target=target,
            )
            await asyncio.to_thread(
                reset_to, db, frozen, exported, digest, export, bound, authorized_target=target
            )
        await verify_mismatched_startup(directory, bindings, databases)
        await execute(directory, bindings, databases, plans)
        previous = (await asyncio.to_thread(read_owner, databases["a"]))[0]
        new_a = replace(bindings["a"], epoch=bindings["a"].epoch + 1)
        intended = [
            new_a.tenant_id,
            new_a.database_resource,
            new_a.binding_id,
            new_a.epoch,
            new_a.bundle_digest,
            "active",
        ]
        durable_json(
            directory / "restart-a-intent.json", {"previous": previous, "intended": intended}
        )

        def reactivate(tx):
            from google.cloud.spanner_v1 import KeySet

            rows = list(tx.read("TenantControl", CONTROL_COLUMNS, KeySet(keys=[["active"]])))
            if rows != [previous] or previous[-1] != "frozen":
                raise ValueError("unexpected predecessor for restart")
            tx.update("TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *intended]])

        await asyncio.to_thread(databases["a"].run_in_transaction, reactivate)
        before_stale = {t: await asyncio.to_thread(fingerprint, db) for t, db in databases.items()}
        try:
            stale, stale_stores = await _build_consumer(
                "projection", bindings["a"].settings(), tenant_binding=bindings["a"]
            )
        except RuntimeFencedError:
            stale_refused = True
        else:
            await stale_stores.close()
            stale_refused = False
        after_stale = {t: await asyncio.to_thread(fingerprint, db) for t, db in databases.items()}
        durable_json(
            directory / "old-epoch-startup-refused.json",
            {
                "passed": stale_refused and before_stale == after_stale,
                "before": before_stale,
                "after": after_stale,
            },
        )
        if not stale_refused or before_stale != after_stale:
            raise AssertionError("old epoch worker was not safely refused")
        bindings["a"] = new_a
        await verify_restart(directory, bindings, databases, plans)
    except BaseException as exc:
        durable_json(
            directory / "attempt-failure.json",
            {
                "error": repr(exc),
                "disposition": "No acceptance claim; retain state and exports",
            },
        )
        raise
    finally:
        for t, db in databases.items():
            try:
                durable_json(
                    directory / (t + "-attempt-final-state.json"),
                    {
                        "database": db.name,
                        "owner": await asyncio.to_thread(read_owner, db),
                        "fingerprints": await asyncio.to_thread(fingerprint, db),
                    },
                )
            except Exception as exc:
                durable_json(
                    directory / (t + "-attempt-final-state-failed.json"), {"error": repr(exc)}
                )
        for db in databases.values():
            await asyncio.to_thread(close_database, db)
        spanner.Client = original


if __name__ == "__main__":
    asyncio.run(main())
