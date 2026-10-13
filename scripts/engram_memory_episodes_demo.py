"""Memory-only acceptance through HTTP, five workers and the authorized Spanner DB.

Sequential configurations; no public dispatcher or concurrent isolation claim.
Exports and verifies each retained dataset before exact-key reset. Never inserts
application artifacts or repairs them. Final dataset remains retained.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import socket
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import uvicorn
from engram_composition_assessment import AUTH, INSTANCE, PROJECT, ROOT, settings_for, token
from engram_composition_reuse import TARGET, freeze_and_export, reset_to
from engram_experiment_support import (
    DemoAuthentication,
    durable_json,
    fingerprint,
    read_owner,
    snapshot,
    stop_demo,
)
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.api.app import create_app
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

RUN = "memory-episodes-1013-01"
DB = TARGET.rsplit("/", 1)[1]
DIRECTORY = ROOT / "docs/review/spanner-compatibility/runs" / RUN


def binding(config, epoch):
    settings = settings_for(RUN, "core" if config != "pdlc-memory" else config, target_database=DB)
    settings.ontology.builtin_packs = [] if config == "core" else ["memory"]
    settings.decay.reflection_threshold = 5
    settings.decay.reconsolidation_interval_hours = 20 / 3600
    return TenantBinding.from_settings(
        "memory-" + config, RUN + "-" + config, epoch, settings, engine_revision="memory-episode-v1"
    )


def identity(session, members):
    # Independent oracle implementing the predeclared public identity convention.
    encoded = json.dumps([session, sorted(members)], separators=(",", ":")).encode()
    return "episode-" + hashlib.sha256(encoded).hexdigest()


async def run_config(config, bound, db):
    path = DIRECTORY / (config + ".json")
    record = {"config": config, "checks": [], "requests": [], "state": "running"}
    consumers, tasks, stores = [], [], []
    server = server_task = None

    def save():
        durable_json(path, record)

    def check(name, passed, detail=None):
        record["checks"].append(
            {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}
        )
        save()
        if not passed:
            raise AssertionError(name)

    session = RUN + ":" + config
    start = datetime.now(UTC) - timedelta(hours=2)

    def event(key, minute, *, other=False, pdlc=False):
        return dict(
            event_id=str(uuid5(NAMESPACE_URL, session + ":" + key)),
            event_type="pdlc.change.created" if pdlc else "observation.input",
            occurred_at=(start + timedelta(minutes=minute)).isoformat(),
            session_id=session + ":other" if other else session,
            agent_id="memory-demo-agent",
            trace_id=RUN,
            payload_ref="memory-demo:" + key,
            payload={"repo": "memory/demo", "number": 7, "title": "Episode coexistence"}
            if pdlc
            else {"content": "Observed system activity " + key},
        )

    first, second, late, bridge = [
        event(k, m) for k, m in [("a", 0), ("b", 5), ("late", 40), ("bridge", 20)]
    ]
    pair = [first["event_id"], second["event_id"]]
    expected = [pair, [late["event_id"]], [*pair, late["event_id"], bridge["event_id"]]]
    record.update(
        expected_memberships=expected,
        session=session,
        limitations=[
            "Private bound authenticated app",
            "Development unevaluated-bundle gate",
            "Sequential reuse does not prove concurrent tenant isolation",
        ],
    )
    inputs = {p["event_id"]: p for p in (first, second, late, bridge)}
    audit_memberships = [(session, members) for members in expected]
    save()
    try:
        check("empty owned starting dataset", not any(v["count"] for v in fingerprint(db).values()))
        app = create_app(bound.settings(), bundle=bound.bundle)
        app.state.tenant_binding = bound
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                DemoAuthentication(app, bound, token=AUTH),
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
                raise RuntimeError("HTTP startup failed")
            await asyncio.sleep(0.1)
        check("HTTP startup", server.started)
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=40,
        ) as http:

            async def request(route, body):
                response = await http.post(route, json=body)
                answer = response.json()
                record["requests"].append(
                    {
                        "route": route,
                        "input": body,
                        "status": response.status_code,
                        "answer": answer,
                    }
                )
                save()
                return response.status_code, answer

            async def query(max_nodes=100, sid=session):
                return await request(
                    "/v1/query/subgraph",
                    dict(
                        query="Show the session timeline",
                        session_id=sid,
                        agent_id="memory-demo-agent",
                        intent="when",
                        max_nodes=max_nodes,
                        timeout_ms=30000,
                    ),
                )

            async def wait_for(members=None, sid=session):
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    for task in tasks:
                        if task.done():
                            await task
                            raise RuntimeError("Worker stopped")
                    state = await asyncio.to_thread(snapshot, db)
                    if members is None:
                        ready = any(
                            label == "Summary" and p.get("scope") == "episode"
                            for label, _, p in state["nodes"]
                        )
                    else:
                        ready = any(
                            label == "Episode"
                            and key == identity(sid, members)
                            and p.get("complete")
                            for label, key, p in state["nodes"]
                        )
                    source_count = sum(
                        label == "Event" and props.get("session_id") == sid
                        for label, key, props in state["nodes"]
                    )
                    session_done = any(
                        label == "Summary"
                        and props.get("scope") == "session"
                        and props.get("scope_id") == sid
                        and props.get("event_count") == source_count
                        for label, key, props in state["nodes"]
                    )
                    if ready and session_done and not state["pending"]:
                        return state
                    await asyncio.sleep(1)
                raise TimeoutError("Expected output not observed within 180 seconds")

            for payload in (first, second):
                status, _ = await request("/v1/events", payload)
                check("initial admission " + payload["event_id"], status == 201)
            for kind in VALID_CONSUMERS:
                consumer, store = await _build_consumer(
                    kind, bound.settings(), tenant_binding=bound
                )
                consumers.append(consumer)
                stores.append(store)
                tasks.append(asyncio.create_task(consumer.run()))
            state = await wait_for(None if config == "core" else pair)
            status, answer = await query()
            check("timeline HTTP success", status == 200)
            if config == "core":
                check(
                    "M01 core summaries, no Episodes",
                    {p.get("scope") for label, _, p in state["nodes"] if label == "Summary"}
                    >= {"episode", "session"}
                    and not any(e[2] == "CONTAINS" for e in state["edges"])
                    and not any(label == "Episode" for label, _, _ in state["nodes"])
                    and not any(n["node_type"] == "Episode" for n in answer["nodes"].values()),
                )
            else:

                def exact_snapshot(answer, members, sid=session):
                    key = identity(sid, members)
                    summary_id = (
                        "summary-"
                        + key
                        + "-"
                        + hashlib.sha256("|".join(sorted(members)).encode()).hexdigest()[:12]
                    )
                    node = answer.get("nodes", {}).get(key, {})
                    attrs = node.get("attributes", {})
                    summary = answer.get("nodes", {}).get(summary_id, {})
                    summary_attrs = summary.get("attributes", {})
                    bounds = sorted(inputs[member]["occurred_at"] for member in members)
                    edges = {
                        (e["source"], e["edge_type"], e["target"]) for e in answer.get("edges", [])
                    }
                    expected_edges = {
                        (key, kind, member)
                        for member in members
                        for kind in ("CONTAINS", "DERIVED_FROM")
                    }
                    expected_edges |= {
                        (summary_id, "SUMMARIZES", member) for member in [*members, key]
                    }
                    observed_edges = {
                        edge for edge in edges if edge[0] == key or edge[0] == summary_id
                    }
                    return (
                        node.get("node_type") == "Episode"
                        and attrs.get("complete")
                        and attrs.get("session_id") == sid
                        and attrs.get("snapshot_kind") == "membership"
                        and attrs.get("event_count") == len(members)
                        and set(attrs.get("source_event_ids", [])) == set(members)
                        and attrs.get("summary_id") == summary_id
                        and [attrs.get("start_time"), attrs.get("end_time")]
                        == [bounds[0], bounds[-1]]
                        and summary.get("node_type") == "Summary"
                        and summary_attrs.get("scope") == "episode"
                        and summary_attrs.get("scope_id") == key
                        and summary_attrs.get("event_count") == len(members)
                        and summary_attrs.get("time_range") == [bounds[0], bounds[-1]]
                        and observed_edges == expected_edges
                        and all(
                            answer["nodes"].get(member, {}).get("node_type") == "Event"
                            and answer["nodes"][member]["provenance"].get("session_id") == sid
                            and answer["nodes"][member].get("provenance", {}).get("event_id")
                            == member
                            for member in members
                        )
                        and node.get("provenance", {}).get("event_id")
                        == min(members, key=lambda member: (inputs[member]["occurred_at"], member))
                    )

                check(
                    "M02 exact Episode, Summary, members and evidence via API",
                    exact_snapshot(answer, pair),
                )
                for payload, members, name in [
                    (late, [late["event_id"]], "M03 temporal split"),
                    (bridge, expected[2], "M05 late bridge membership"),
                ]:
                    status, _ = await request("/v1/events", payload)
                    check(name + " admission", status == 201)
                    await wait_for(members)
                    status, answer = await query()
                    check(name, status == 200 and exact_snapshot(answer, members))
                check(
                    "M06 old snapshots retained as membership history",
                    all(exact_snapshot(answer, members) for members in expected),
                )
                before = await asyncio.to_thread(snapshot, db)
                record["M04_before"] = before
                save()
                status, _ = await request("/v1/events", bridge)
                prior_created = {
                    k: p.get("created_at")
                    for label, k, p in before["nodes"]
                    if label == "Summary" and p.get("scope") == "session"
                }
                deadline = time.monotonic() + 180
                while True:
                    current = await asyncio.to_thread(snapshot, db)
                    if any(
                        label == "Summary"
                        and k in prior_created
                        and p.get("created_at") != prior_created[k]
                        for label, k, p in current["nodes"]
                    ):
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("No subsequent consolidation output observed")
                    await asyncio.sleep(1)
                after = await asyncio.to_thread(snapshot, db)
                record["M04_after"] = after
                save()
                check(
                    "M04 retry and repeated cycles do not duplicate membership snapshots",
                    status in (200, 201)
                    and len(before["events"]) == len(after["events"])
                    and {(label, k) for label, k, p in before["nodes"] if label == "Episode"}
                    == {(label, k) for label, k, p in after["nodes"] if label == "Episode"}
                    and {
                        tuple(e[:5])
                        for e in before["edges"]
                        if e[0] == "Episode" or e[3] == "Episode"
                    }
                    == {
                        tuple(e[:5])
                        for e in after["edges"]
                        if e[0] == "Episode" or e[3] == "Episode"
                    },
                )
                unrelated = event("unrelated", 0, other=True)
                status, _ = await request("/v1/events", unrelated)
                check("other session admitted", status == 201)
                inputs[unrelated["event_id"]] = unrelated
                other_members = [unrelated["event_id"]]
                audit_memberships.append((unrelated["session_id"], other_members))
                await wait_for(other_members, unrelated["session_id"])
                status, own = await query(sid=unrelated["session_id"])
                check(
                    "M07 other session positively retrievable",
                    status == 200 and exact_snapshot(own, other_members, unrelated["session_id"]),
                )
                status, answer = await query()
                check(
                    "M07 other session excluded",
                    status == 200 and unrelated["event_id"] not in answer["nodes"],
                )
                status, limited = await query(1)
                check(
                    "M10 explicit bound without dangling edges",
                    status == 200
                    and len(limited["nodes"]) <= 1
                    and limited["meta"]["truncated"]
                    and all(
                        e["source"] in limited["nodes"] and e["target"] in limited["nodes"]
                        for e in limited["edges"]
                    ),
                )
                if config == "pdlc-memory":
                    pr = event("pr", 10, pdlc=True)
                    status, _ = await request("/v1/events", pr)
                    check("PDLC admission", status == 201)
                    await wait_for([*pair, late["event_id"], bridge["event_id"], pr["event_id"]])
                    inputs[pr["event_id"]] = pr
                    pr_members = [*pair, late["event_id"], bridge["event_id"], pr["event_id"]]
                    audit_memberships.append((session, pr_members))
                    status, timeline = await query()
                    check(
                        "M11 PDLC-containing Episode through API",
                        status == 200
                        and exact_snapshot(timeline, pr_members)
                        and not any(
                            e["target"] == "Change:memory/demo|7"
                            and e["source"].startswith("episode-")
                            for e in timeline["edges"]
                        ),
                    )
                    status, artifact = await request(
                        "/v1/query/artifacts",
                        {"query": "trace this change", "seed_node_ids": ["Change:memory/demo|7"]},
                    )
                    node = artifact.get("nodes", {}).get("Change:memory/demo|7", {})
                    check(
                        "M11 PDLC artifact coexistence",
                        status == 200
                        and node.get("attributes", {}).get("title") == "Episode coexistence"
                        and node.get("provenance", {}).get("event_id") == pr["event_id"],
                    )
            before = await asyncio.to_thread(snapshot, db)
            invalid = event("invalid", 0)
            invalid.pop("session_id")
            status, _ = await request("/v1/events", invalid)
            after = await asyncio.to_thread(snapshot, db)
            check(
                "M12 invalid envelope no ledger write",
                status == 422
                and before["events"] == after["events"]
                and not any(
                    k == invalid["event_id"] or invalid["event_id"] in p.get("source_event_ids", [])
                    for label, k, p in after["nodes"]
                ),
            )
            check("no dead letters", not after["dead_letters"])
            if config != "core":
                audit_answer = {
                    "nodes": {
                        k: {
                            "node_type": label,
                            "attributes": p,
                            "provenance": {"event_id": k, "session_id": p.get("session_id")},
                        }
                        for label, k, p in after["nodes"]
                    },
                    "edges": [
                        {"source": e[1], "edge_type": e[2], "target": e[4]} for e in after["edges"]
                    ],
                }
                expected_ids = {identity(sid, members) for sid, members in audit_memberships}
                check(
                    "independent final exact Episode identity audit",
                    {k for label, k, p in after["nodes"] if label == "Episode"} == expected_ids,
                )
                for sid, members in audit_memberships:
                    key = identity(sid, members)
                    # Provenance is checked through HTTP above; storage has actual evidence edges.
                    audit_answer["nodes"][key]["provenance"] = {
                        "event_id": min(members, key=lambda m: (inputs[m]["occurred_at"], m))
                    }
                    check(
                        "final stored membership and Summary audit " + key,
                        exact_snapshot(audit_answer, members, sid),
                    )
            record["state"] = "passed selected live scenarios"
    except Exception as exc:
        record.update(state="failed", error=type(exc).__name__ + ": " + str(exc))
        raise
    finally:
        record["shutdown_errors"] = await stop_demo(consumers, tasks, stores, server, server_task)
        record["retained_snapshot"] = await asyncio.to_thread(snapshot, db)
        save()
        if record["shutdown_errors"]:
            record["state"] = "failed shutdown; database retained, no reuse"
            save()
            raise RuntimeError("Shutdown did not complete cleanly; refuse next reset")


async def main():
    global RUN, DIRECTORY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=RUN)
    parser.add_argument(
        "--previous-record",
        type=Path,
        default=ROOT
        / "docs/review/spanner-compatibility/runs/composition-1010r/pdlc-memory-retained.json",
    )
    parser.add_argument(
        "--configurations",
        nargs="+",
        choices=["core", "memory", "pdlc-memory"],
        default=["core", "memory", "pdlc-memory"],
    )
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("Run ID must be alphanumeric with hyphens")
    RUN = args.run_id
    DIRECTORY = ROOT / "docs/review/spanner-compatibility/runs" / RUN
    if DIRECTORY.exists():
        raise ValueError("Refuse evidence overwrite; inspect previous attempt first")
    previous = json.loads(args.previous_record.read_text())
    if previous["database"] != TARGET:
        raise ValueError("Previous retained record targets another database")
    DIRECTORY.mkdir()
    credentials = Credentials(token=token(impersonate=True))
    original = spanner.Client

    def authenticated(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original(*args, **kwargs)

    spanner.Client = authenticated
    client = authenticated(project=PROJECT)
    pool = BurstyPool()
    db = client.instance(INSTANCE).database(DB, pool=pool)
    prepare_cleanup(db, client, pool)
    try:
        for config in args.configurations:
            bound = binding(config, previous["owner"][0][3] + 1)
            export = DIRECTORY / (config + "-previous-export.json")
            frozen, exported, digest = await asyncio.to_thread(
                freeze_and_export, db, previous["owner"][0], previous["fingerprints"], export
            )
            await asyncio.to_thread(reset_to, db, frozen, exported, digest, export, bound)
            try:
                await run_config(config, bound, db)
            finally:
                previous = {
                    "owner": await asyncio.to_thread(read_owner, db),
                    "fingerprints": await asyncio.to_thread(fingerprint, db),
                    "database": TARGET,
                }
                durable_json(DIRECTORY / (config + "-retained.json"), previous)
    finally:
        await asyncio.to_thread(close_database, db)
        spanner.Client = original


if __name__ == "__main__":
    asyncio.run(main())
