"""Issue29: real API/worker/Spanner enrichment convergence, retained assessment data.

Only the external embedding provider and one storage-fault boundary are scripted.
No graph inserts or repair. Sequential pack configurations do not prove tenancy.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import socket
import time
from datetime import UTC, datetime
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
from context_graph.ports.errors import UnavailableError
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer
from context_graph.worker.consolidation import ConsolidationConsumer

VECTOR = [0.25] * 384
SCENARIOS = {
    "EN01": "enrichment first: pending without Event, then projection restores exact annotations",
    "EN02": "stop while projection absent; fresh enrichment worker recovers same pending delivery",
    "EN03": "projection first then enrichment, with exact vector and supplied importance7",
    "EN04": "duplicate ingestion and stale projection A/B/A preserve annotations and access state",
    "EN05": "absent embedding provider: keywords/default5, no invented vector",
    "EN06": "failed provider: keywords/default5, existing vector preserved on replay",
    "EN07": "vector storage outage after keyword commit: pending, one provider call, recovery",
}


class EmbeddingProbe:
    def __init__(self, *, fail=False):
        self.fail, self.calls = fail, 0

    async def embed_text(self, text):
        self.calls += 1
        if self.fail:
            raise RuntimeError("controlled external embedding provider failure")
        return list(VECTOR)


class VectorStorageFault:
    """Hold a transient storage outage; delegate all real graph operations."""

    def __init__(self, graph):
        self.graph, self.blocked, self.hits = graph, True, 0

    def __getattr__(self, name):
        return getattr(self.graph, name)

    async def store_event_embedding(self, event_id, vector):
        if self.blocked:
            self.hits += 1
            raise UnavailableError("controlled vector storage outage after keyword commit")
        await self.graph.store_event_embedding(event_id, vector)


async def run_config(run, directory, config, bound, db):
    path = directory / (config + ".json")
    record = dict(
        state="running",
        config=config,
        scenarios=SCENARIOS,
        requests=[],
        checks=[],
        limitations=[
            "private bound tenant; sequential configurations only",
            "scripted external embedding provider; no model quality claim",
            "existing retry bounds delay, not total wait or repeated-restart DLQ",
            "healthy quiescence avoids #60; does not fix shutdown",
        ],
    )
    consumers, tasks, stores = [], [], []
    workers, running = {}, {}
    server = server_task = None

    def save():
        durable_json(path, record)

    def check(name, passed, actual=None):
        record["checks"].append(dict(name=name, passed=bool(passed), actual=actual))
        save()
        if not passed:
            raise AssertionError(name)

    async def wait(predicate, description):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done():
                    await task
            value = await predicate()
            if value:
                return value
            await asyncio.sleep(0.2)
        raise TimeoutError(description)

    async def start(kind, *, launch=True):
        worker, store = await _build_consumer(kind, bound.settings(), tenant_binding=bound)
        workers[kind] = worker
        consumers.append(worker)
        stores.append(store)
        if kind == "enrichment":
            worker._embedding_service = EmbeddingProbe()
        if launch:
            task = asyncio.create_task(worker.run())
            tasks.append(task)
            running[kind] = task
        return worker

    async def stop(kind):
        workers[kind].stop()
        # Cooperative stop; shield prevents timeout from cancelling SDK work.
        await asyncio.wait_for(asyncio.shield(running[kind]), 30)
        tasks.remove(running.pop(kind))

    async def quiesce():
        lock = next(
            (c._consolidation_lock for c in consumers if isinstance(c, ConsolidationConsumer)), None
        )
        if lock:
            await lock.acquire()
        try:
            for c in consumers:
                c.stop()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [repr(x) for x in results if isinstance(x, BaseException)]
        finally:
            if lock:
                lock.release()

    async def state():
        return await asyncio.to_thread(snapshot, db)

    async def properties(eid):
        values = await state()
        return next(
            (json_value(p) for label, key, p in values["nodes"] if label == "Event" and key == eid),
            None,
        )

    async def pending(eid):
        values = await state()
        group = workers["enrichment"]._group_name
        exact = [row for row in values["pending"] if row == [group, eid]]
        if exact:
            record.setdefault("pending_observations", []).append(
                dict(event_id=eid, group=group, rows=exact, dead_letters=values["dead_letters"])
            )
            save()
        return exact or None

    async def settled():
        async def ready():
            active = [c for c in consumers if not c._stopped]
            lags = await asyncio.gather(*(c._subscription.lag() for c in active))
            values = await state()
            return (
                values
                if len(active) == 5 and not values["pending"] and all(v == 0 for v in lags)
                else None
            )

        result = await wait(ready, "five workers settle")
        check("five workers zero lag/pending and no DLQ", not result["dead_letters"])
        return result

    def body(key, hint=7):
        result = dict(
            event_id=str(uuid5(NAMESPACE_URL, run + config + key)),
            event_type="observation.input",
            occurred_at=datetime.now(UTC).isoformat(),
            session_id=run + config + key,
            agent_id="enrichment-owner",
            trace_id=run,
            payload_ref="enrichment:" + key,
            tool_name="race-tool",
            payload={"content": "ordering probe " + key},
        )
        if hint is not None:
            result["importance_hint"] = hint
        return result

    save()
    try:
        check("verified empty start", not any(v["count"] for v in fingerprint(db).values()))
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
        check("authenticated HTTP ready", server.started)
        for kind in VALID_CONSUMERS:
            await start(kind, launch=kind != "projection")
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=40,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(route, payload=None, *, method="POST"):
                row = dict(route=route, method=method, input=payload, status=None)
                record["requests"].append(row)
                save()
                try:
                    response = await http.request(method, route, json=payload)
                    row.update(status=response.status_code, output=response.json())
                    save()
                    return response
                except BaseException as exc:
                    row["error"] = repr(exc)
                    save()
                    raise

            async def send(event):
                response = await request("/v1/events", event)
                check(
                    "accepted " + event["event_id"],
                    response.status_code in (200, 201),
                    response.json(),
                )
                return response.json()

            async def verify(event, *, vector=True, importance=7):
                props = await properties(event["event_id"])
                check(
                    "exact annotations " + event["event_id"],
                    props is not None
                    and props.get("keywords") == ["observation", "input", "race-tool"]
                    and props.get("importance_score") == importance
                    and (
                        props.get("embedding") == VECTOR if vector else not props.get("embedding")
                    ),
                    props,
                )
                answer = await request(
                    "/v1/query/subgraph",
                    dict(
                        query="event " + event["event_id"],
                        intent="what",
                        seed_nodes=[event["event_id"]],
                        session_id=event["session_id"],
                        agent_id=event["agent_id"],
                        timeout_ms=30000,
                    ),
                )
                result = answer.json()
                check(
                    "Event retrieved through HTTP " + event["event_id"],
                    answer.status_code == 200 and event["event_id"] in result.get("nodes", {}),
                    result,
                )
                node = result.get("nodes", {}).get(event["event_id"], {})
                check(
                    "public annotation values/owner " + event["event_id"],
                    node.get("attributes", {}).get("keywords")
                    == ["observation", "input", "race-tool"]
                    and node.get("attributes", {}).get("importance_score") == importance
                    and node.get("provenance", {}).get("agent_id") == event["agent_id"]
                    and node.get("provenance", {}).get("session_id") == event["session_id"]
                    and result.get("meta", {}).get("truncated") is False,
                    node,
                )
                return props

            first = body("EN01")
            await send(first)
            await wait(lambda: pending(first["event_id"]), "enrichment takes delivery")
            await asyncio.sleep(0.5)
            check(
                "EN01 no projection, still pending, no partial Event",
                await pending(first["event_id"]) and await properties(first["event_id"]) is None,
                await state(),
            )
            await stop("enrichment")
            check("EN02 stop retains pending delivery", bool(await pending(first["event_id"])))
            await start("enrichment")
            await asyncio.sleep(0.5)
            check(
                "EN02 fresh worker still waits for projection",
                bool(await pending(first["event_id"])),
            )
            task = asyncio.create_task(workers["projection"].run())
            tasks.append(task)
            running["projection"] = task
            await settled()
            await verify(first)

            second = body("EN03")
            await stop("enrichment")
            await send(second)

            async def projected():
                return await properties(second["event_id"])

            await wait(projected, "projection first")
            check(
                "EN03 projected before enrichment",
                (await properties(second["event_id"])).get("keywords") == [],
            )
            await start("enrichment")
            await settled()
            await verify(second)

            # Stop projection while manually redelivering to its public worker seam.
            # This invokes actual projection code, never direct graph insertion.
            await stop("projection")
            context = await request("/v1/context/" + second["session_id"], method="GET")
            check(
                "EN04 session-context read returns Event and records access",
                context.status_code == 200
                and second["event_id"] in context.json().get("nodes", {}),
                context.json(),
            )
            check(
                "EN04 graph-port importance adjustment applied",
                await workers["enrichment"]._graph_store.adjust_node_importance(
                    second["event_id"], 1
                ),
            )
            before = await properties(second["event_id"])
            check(
                "EN04 positive access and adjusted importance before replay",
                before.get("access_count", 0) > 0 and before.get("importance_score") == 8,
                before,
            )
            ledger_before = len((await state())["events"])
            await send(second)
            await start("projection", launch=False)
            records = await workers["projection"]._event_log.get_documents([second["event_id"]])
            position = records[0]["global_position"]
            await workers["projection"].process_message(position, {"event_id": second["event_id"]})
            await workers["projection"].on_idle()
            await workers["enrichment"].process_message(position, {"event_id": second["event_id"]})
            after = await properties(second["event_id"])
            check(
                "EN04 replay preserves owned annotations/access state",
                all(
                    before.get(k) == after.get(k)
                    for k in (
                        "keywords",
                        "importance_score",
                        "embedding",
                        "summary",
                        "access_count",
                        "last_accessed_at",
                    )
                ),
            )
            check(
                "EN04 duplicate creates no new ledger event",
                len((await state())["events"]) == ledger_before,
            )
            task = asyncio.create_task(workers["projection"].run())
            tasks.append(task)
            running["projection"] = task
            await settled()
            await verify(second, importance=8)

            workers["enrichment"]._embedding_service = None
            absent = body("EN05", None)
            await send(absent)
            await settled()
            await verify(absent, vector=False, importance=5)

            provider = EmbeddingProbe(fail=True)
            workers["enrichment"]._embedding_service = provider
            failed = body("EN06", None)
            await send(failed)
            await settled()
            await verify(failed, vector=False, importance=5)
            records = await workers["enrichment"]._event_log.get_documents([second["event_id"]])
            await workers["enrichment"].process_message(
                records[0]["global_position"], {"event_id": second["event_id"]}
            )
            await verify(second, importance=8)
            check("EN06 external provider failure exercised", provider.calls == 2, provider.calls)

            provider = EmbeddingProbe()
            enrichment = workers["enrichment"]
            enrichment._embedding_service = provider
            original_graph = enrichment._graph_store
            fault = VectorStorageFault(original_graph)
            enrichment._graph_store = fault
            recovery = body("EN07")
            await send(recovery)

            async def attempted():
                return fault.hits

            await wait(attempted, "vector storage outage observed")
            partial = await properties(recovery["event_id"])
            check(
                "EN07 keywords committed, vector pending",
                partial.get("keywords") == ["observation", "input", "race-tool"]
                and not partial.get("embedding")
                and bool(await pending(recovery["event_id"])),
                partial,
            )
            fault.blocked = False
            await settled()
            await verify(recovery)
            check(
                "EN07 storage retries do not repeat embedding provider",
                provider.calls == 1,
                provider.calls,
            )
            enrichment._graph_store = original_graph
            errors = await quiesce()
            check("healthy worker quiescence", not errors, errors)
            final = await state()
            fixtures = [first, second, absent, failed, recovery]
            expected_ids = {event["event_id"] for event in fixtures}
            check(
                "exact accepted ledger identities",
                {row[0] for row in final["events"]} == expected_ids and len(final["events"]) == 5,
            )
            check(
                "exact Event node identities; no extra artifacts",
                {(row[0], row[1]) for row in final["nodes"]}
                == (
                    {("Event", eid) for eid in expected_ids}
                    | {("OntologyState", "OntologyState:active")}
                )
                and len(final["nodes"]) == 6,
            )
            ontology = next(
                json_value(p) for label, key, p in final["nodes"] if label == "OntologyState"
            )
            check(
                "exact active ontology metadata matches selected bundle",
                ontology.get("version") == bound.bundle.schema_version
                and set(ontology.get("packs", []))
                == {name + "@" + version for name, version in bound.bundle.pack_identities},
                ontology,
            )
            check(
                "exact empty edge set for separate single-event sessions",
                final["edges"] == [],
                final["edges"],
            )
            for event in fixtures:
                props = await properties(event["event_id"])
                expected_importance = (
                    8 if event is second else (7 if event in (first, recovery) else 5)
                )
                expected_vector = VECTOR if event in (first, second, recovery) else None
                check(
                    "final exact fields " + event["event_id"],
                    all(
                        props.get(k) == event[k]
                        for k in (
                            "event_type",
                            "session_id",
                            "agent_id",
                            "trace_id",
                            "tool_name",
                            "occurred_at",
                        )
                    )
                    and props.get("keywords") == ["observation", "input", "race-tool"]
                    and props.get("importance_score") == expected_importance
                    and (
                        props.get("embedding") == expected_vector
                        if expected_vector
                        else not props.get("embedding")
                    ),
                    props,
                )

            def physical_vectors():
                with db.snapshot() as snap:
                    return [
                        list(row)
                        for row in snap.execute_sql(
                            "SELECT label, node_id, embedding FROM GraphNodes"
                        )
                    ]

            columns = await asyncio.to_thread(physical_vectors)
            record["physical_embedding_columns"] = columns
            check(
                "Event vectors are JSON properties, excluded from Entity ANN column",
                len(columns) == 6
                and all(row[0] in {"Event", "OntologyState"} and row[2] is None for row in columns),
                columns,
            )
            record["final_snapshot"] = final
            record["state"] = "passed"
            save()
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        save()
        raise
    finally:
        errors = await quiesce()
        errors += await stop_demo(consumers, tasks, stores, server, server_task)
        record["shutdown_errors"] = errors
        record["retained_snapshot"] = await state()
        save()
        if errors:
            record["state"] = "failed shutdown; reset prohibited"
            save()
            raise RuntimeError("Unclean shutdown; refuse reset")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-record", type=Path, required=True)
    parser.add_argument(
        "--configurations",
        nargs="+",
        default=["core", "user", "user-memory", "pdlc", "pdlc-memory"],
        choices=["core", "user", "user-memory", "pdlc", "pdlc-memory"],
    )
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("Unsafe run id")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    if directory.exists():
        raise ValueError("Refuse evidence overwrite")
    previous = json.loads(args.previous_record.read_text())
    if previous["database"] != TARGET:
        raise ValueError("Wrong target")
    directory.mkdir()
    durable_json(
        directory / "manifest.json",
        dict(
            scenarios=SCENARIOS,
            vector=VECTOR,
            configurations=args.configurations,
            target=TARGET,
            provider="scripted external embedding only",
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
        for config in args.configurations:
            settings = settings_for(args.run_id, config, target_database=TARGET.rsplit("/", 1)[1])
            bound = TenantBinding.from_settings(
                "enrichment-" + config,
                args.run_id + config,
                previous["owner"][0][3] + 1,
                settings,
                engine_revision="enrichment-ordering-v1",
            )
            export = directory / (config + "-previous-export.json")
            frozen, exported, digest = await asyncio.to_thread(
                freeze_and_export, db, previous["owner"][0], previous["fingerprints"], export
            )
            await asyncio.to_thread(reset_to, db, frozen, exported, digest, export, bound)
            try:
                await run_config(args.run_id, directory, config, bound, db)
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
