"""#61: authenticated UUID Event reads on the retained assessment Spanner target.

Five real worker loops; only the external extraction/summary providers are scripted.
Sequential Core and Core+PDLC+Memory configurations; no concurrent-tenant claim.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
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
from context_graph.adapters.spanner.log import json_value
from context_graph.api.app import create_app
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

SCENARIOS = {
    "AC01": "UUID Event read twice: exactly one increment per returned Event per read",
    "AC02": "mixed Entity and optional Episode/Summary: non-Events unchanged",
    "AC03": "one-node page: unreturned Events unchanged",
    "AC04": "empty cursor page: no access writes; unrelated owner/session unchanged",
}


class Providers:
    async def extract_from_session(self, **kwargs):
        return {
            "entities": [
                {
                    "name": "evt-access-probe",
                    "entity_type": "tool",
                    "confidence": 1.0,
                    "source_quote": "evt-access-probe",
                }
            ]
        }

    async def generate_text(self, prompt):
        return "Access probe activity, kept as fixed provider output."


def fixtures(run_id, config):
    sid, owner = run_id + config, "access-owner"
    now = datetime.now(UTC)
    events = [
        dict(
            event_id=str(uuid5(NAMESPACE_URL, sid + str(i))),
            event_type="system.session_end" if i == 2 else "observation.input",
            occurred_at=(now + timedelta(seconds=i)).isoformat(),
            session_id=sid if i < 3 else sid + "-unrelated",
            agent_id=owner if i < 3 else "unrelated-owner",
            trace_id=run_id,
            payload_ref="access:" + str(i),
            importance_hint=7,
            payload={"content": "evt-access-probe"},
        )
        for i in range(4)
    ]
    members = sorted(e["event_id"] for e in events[:3])
    episode = (
        "episode-"
        + hashlib.sha256(json.dumps([sid, members], separators=(",", ":")).encode()).hexdigest()
    )
    return dict(
        events=events, session=sid, owner=owner, entity="entity:evt-access-probe", episode=episode
    )


async def run(directory, bound, db, plan, config):
    path = directory / (config + ".json")
    record = dict(
        state="running",
        checks=[],
        requests=[],
        fixtures=plan,
        limitations=[
            "private sequential tenant; no concurrent/public tenancy proof",
            "scripted external extraction and summary output; no model quality claim",
            "sequential read accounting only; concurrent increment atomicity not tested",
        ],
    )
    consumers, tasks, stores = [], [], []
    server = server_task = None

    def save():
        durable_json(path, record)

    def check(name, passed, actual=None):
        record["checks"].append(dict(name=name, passed=bool(passed), actual=actual))
        save()
        if not passed:
            raise AssertionError(name)

    async def state():
        return await asyncio.to_thread(snapshot, db)

    def physical_nodes():
        with db.snapshot() as snap:
            return [
                list(row[:2]) + list(row[3:])
                for row in snap.execute_sql("SELECT * FROM GraphNodes ORDER BY label, node_id")
            ]

    def nodes(s):
        return {(label, key): json_value(props) for label, key, props in s["nodes"]}

    async def wait(predicate, description):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done():
                    await task
                    raise RuntimeError("worker exited before shutdown")
            value = await predicate()
            if value:
                return value
            await asyncio.sleep(0.2)
        raise TimeoutError(description)

    try:
        check("empty application tables", not any(v["count"] for v in fingerprint(db).values()))
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
            await asyncio.sleep(0.1)
        check("authenticated API ready", server.started)
        for kind in VALID_CONSUMERS:
            worker, store = await _build_consumer(kind, bound.settings(), tenant_binding=bound)
            if kind in {"extraction", "consolidation"}:
                worker._llm_client = Providers()
            consumers.append(worker)
            stores.append(store)
            tasks.append(asyncio.create_task(worker.run()))
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=45,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(route, payload):
                row = dict(route=route, input=payload, status=None)
                record["requests"].append(row)
                save()
                try:
                    response = await http.post(route, json=payload)
                except BaseException as exc:
                    row["error"] = repr(exc)
                    save()
                    raise
                row.update(status=response.status_code, output=response.json())
                save()
                return response

            for event in plan["events"]:
                response = await request("/v1/events", event)
                check(
                    "accepted " + event["event_id"],
                    response.status_code in {200, 201},
                    response.json(),
                )

            async def ready():
                s = await state()
                found = nodes(s)
                required = {("Event", e["event_id"]) for e in plan["events"]} | {
                    ("Entity", plan["entity"])
                }
                if config == "pdlc-memory":
                    required.add(("Episode", plan["episode"]))
                lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
                return (
                    s if required <= found.keys() and not s["pending"] and not any(lags) else None
                )

            await wait(ready, "five workers, Entity and optional Episode materialize")
            for worker in consumers:
                worker.stop()
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            check(
                "all five real workers joined",
                not any(isinstance(x, BaseException) for x in outcomes),
                [repr(x) for x in outcomes],
            )
            baseline = await state()
            record["processed_baseline"] = baseline
            check(
                "exact ledger membership",
                {row[0] for row in baseline["events"]} == {e["event_id"] for e in plan["events"]},
            )
            check("no pending or DLQ", not baseline["pending"] and not baseline["dead_letters"])
            expected_events = {e["event_id"] for e in plan["events"][:3]}
            query = dict(
                query="trace session",
                intent="when",
                session_id=plan["session"],
                agent_id=plan["owner"],
                seed_nodes=[plan["events"][2]["event_id"]],
                max_nodes=100,
                timeout_ms=30000,
            )
            counts = {eid: 0 for eid in expected_events}
            check(
                "baseline Event access counts zero",
                all(
                    nodes(baseline)[("Event", eid)].get("access_count", 0) == 0
                    for eid in expected_events
                ),
            )
            cases = [
                ("AC01-first", {}),
                ("AC01-repeat", {}),
                ("AC03-page-0", {"max_nodes": 1}),
                ("AC04-empty", {"cursor": base64.urlsafe_b64encode(b"10000").decode()}),
            ]
            event_page_seen = False
            for index, (label, overrides) in enumerate(cases):
                before = await state()
                before_fp = await asyncio.to_thread(fingerprint, db)
                physical_before = await asyncio.to_thread(physical_nodes)
                started = datetime.now(UTC)
                response = await request("/v1/query/subgraph", query | overrides)
                ended = datetime.now(UTC)
                answer = response.json()
                check(label + " HTTP success", response.status_code == 200, answer)
                returned = answer.get("nodes", {})
                returned_events = {
                    key for key, value in returned.items() if value["node_type"] == "Event"
                }
                check(
                    label + " allowed Event identities",
                    returned_events <= expected_events,
                    sorted(returned_events),
                )
                check(
                    label + " returned Event owner/session",
                    all(
                        v["provenance"].get("session_id") == plan["session"]
                        and v["provenance"].get("agent_id") == plan["owner"]
                        for k, v in returned.items()
                        if k in returned_events
                    ),
                )
                if label.startswith("AC01"):
                    check(label + " untruncated", answer.get("meta", {}).get("truncated") is False)
                    check(
                        label + " all session Events and Entity returned",
                        expected_events <= returned.keys() and plan["entity"] in returned,
                        sorted(returned),
                    )
                    if config == "pdlc-memory":
                        check(label + " Episode returned", plan["episode"] in returned)
                elif label.startswith("AC03-page"):
                    check(label + " exactly one node", len(returned) == 1)
                    if returned_events:
                        event_page_seen = True
                        check("one-node Event page reached", len(returned_events) == 1)
                    else:
                        cursor = answer.get("pagination", {}).get("cursor")
                        check("bounded next Event page exists", bool(cursor) and index < 10)
                        cases.insert(
                            index + 1,
                            ("AC03-page-" + str(index), {"max_nodes": 1, "cursor": cursor}),
                        )
                else:
                    check("empty cursor page returns no nodes", not returned, returned)
                after = await state()
                after_fp = await asyncio.to_thread(fingerprint, db)
                physical_after = await asyncio.to_thread(physical_nodes)
                check(
                    label + " other six tables unchanged",
                    {k: v for k, v in before_fp.items() if k != "GraphNodes"}
                    == {k: v for k, v in after_fp.items() if k != "GraphNodes"},
                )
                check(label + " physical node columns unchanged", physical_before == physical_after)
                prior, current = nodes(before), nodes(after)
                check(label + " node membership stable", prior.keys() == current.keys())
                for key, props in prior.items():
                    actual = current[key]
                    if key[0] == "Event" and key[1] in returned_events:
                        counts[key[1]] += 1
                        check(
                            label + " exact count " + key[1],
                            actual.get("access_count") == counts[key[1]],
                            actual,
                        )
                        accessed = datetime.fromisoformat(actual["last_accessed_at"])
                        check(
                            label + " timestamp in request interval " + key[1],
                            started <= accessed <= ended,
                        )

                        def strip(p):
                            return {
                                k: v
                                for k, v in p.items()
                                if k not in {"access_count", "last_accessed_at"}
                            }

                        check(
                            label + " other Event properties unchanged " + key[1],
                            strip(actual) == strip(props),
                        )
                    else:
                        check(label + " untouched " + str(key), actual == props)
                check(
                    label + " ledger/edges/delivery state unchanged",
                    {k: v for k, v in before.items() if k != "nodes"}
                    == {k: v for k, v in after.items() if k != "nodes"},
                )
                record.setdefault("read_snapshots", []).append(
                    dict(case=label, before=before, after=after)
                )
                save()
            check("paginated Event increment exercised", event_page_seen)
            record["final_snapshot"] = await state()
            before = await asyncio.to_thread(fingerprint, db)
            await asyncio.sleep(1)
            after = await asyncio.to_thread(fingerprint, db)
            check("post-worker state stable", before == after)
            record["state"] = "passed"
            save()
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        save()
        raise
    finally:
        errors = await stop_demo(consumers, tasks, stores, server, server_task)
        record["shutdown_errors"] = errors
        record["retained_snapshot"] = await state()
        save()
        if errors:
            record["state"] = "failed: uncertain shutdown"
            save()
            raise RuntimeError("uncertain shutdown; refuse reuse")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-record", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("unsafe run ID")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    if directory.exists():
        raise ValueError("refuse evidence overwrite")
    previous = json.loads(args.previous_record.read_text())
    if previous["database"] != TARGET:
        raise ValueError("wrong assessment target")
    directory.mkdir()
    configs = ["core", "pdlc-memory"]
    plans = {config: fixtures(args.run_id, config) for config in configs}
    durable_json(
        directory / "manifest.json",
        dict(
            scenarios=SCENARIOS,
            fixtures=plans,
            target=TARGET,
            configurations=configs,
            expected_effect=(
                "only returned Events access_count +1 and request-time "
                "last_accessed_at; everything else unchanged"
            ),
        ),
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
    credentials = Credentials(token=token(impersonate=True))
    original = spanner.Client

    def authenticated(*a, **kw):
        kw["credentials"] = credentials
        return original(*a, **kw)

    spanner.Client = authenticated
    client = authenticated(project=PROJECT)
    pool = BurstyPool()
    db = client.instance(INSTANCE).database(TARGET.rsplit("/", 1)[1], pool=pool)
    prepare_cleanup(db, client, pool)
    try:
        for config in configs:
            settings = settings_for(args.run_id, config, target_database=TARGET.rsplit("/", 1)[1])
            settings.decay.reflection_threshold = 5
            settings.decay.reconsolidation_interval_hours = 5 / 3600
            bound = TenantBinding.from_settings(
                "access-" + config,
                args.run_id + config,
                previous["owner"][0][3] + 1,
                settings,
                engine_revision="subgraph-access-v1",
            )
            export = directory / (config + "-previous-export.json")
            frozen, exported, digest = await asyncio.to_thread(
                freeze_and_export, db, previous["owner"][0], previous["fingerprints"], export
            )
            await asyncio.to_thread(reset_to, db, frozen, exported, digest, export, bound)
            try:
                await run(directory, bound, db, plans[config], config)
            finally:
                previous = dict(
                    database=TARGET,
                    owner=await asyncio.to_thread(read_owner, db),
                    fingerprints=await asyncio.to_thread(fingerprint, db),
                )
                durable_json(directory / (config + "-retained.json"), previous)
    finally:
        await asyncio.to_thread(close_database, db)
        spanner.Client = original


if __name__ == "__main__":
    asyncio.run(main())
