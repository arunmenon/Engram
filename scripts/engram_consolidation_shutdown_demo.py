"""Issue60: hold actual Spanner SDK transactions while production workers stop.

Authenticated HTTP inputs, five real workers, real Spanner, public timeline read.
Only the optional summary provider and explicitly labeled fault seams are scripted.
No graph inserts/repairs or external lock workaround. Final assessment data retained.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import socket
import threading
import time
from copy import deepcopy
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
from context_graph.ports.errors import RuntimeFencedError, UnavailableError
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

SUMMARY_TEXT = "Two accepted events describe bounded shutdown verification."
SCENARIOS = {
    "SS01": "stop inside a real SDK Summary transaction; wait for the entire cycle",
    "SS02": "stop a sleeping timer promptly, without admitting a cycle",
    "SS03": "three parent cancellations during SDK work; drain then propagate cancellation",
    "SS04": "SDK callback storage failure rolls back under existing logged-cycle policy",
    "SS05": "SDK callback fencing rolls back; fatal fence escapes only after both children join",
    "SS06": "subscription fencing while timer writes; admitted cycle drains before fence escapes",
    "SS07": "fresh worker retry/restart retains exact summary/Episode identities and evidence",
}


class SummaryProvider:
    async def generate_text(self, prompt):
        return SUMMARY_TEXT


class SDKGate:
    """Hold after scheduling a Summary mutation INSIDE the real SDK callback."""

    def __init__(self, database, mode):
        self.database, self.mode = database, mode
        self.entered, self.release = threading.Event(), threading.Event()
        self.lock = threading.Lock()
        self.used = False
        self.active = 0
        self.record = dict(
            mode=mode,
            sdk_calls=0,
            returned_calls=0,
            gated_outcome=None,
            summary_commits=[],
            summary_rollbacks=[],
        )

    def __getattr__(self, name):
        return getattr(self.database, name)

    def evidence(self):
        with self.lock:
            return dict(
                deepcopy(self.record), active_calls=self.active, entered=self.entered.is_set()
            )

    def run_in_transaction(self, operation, *args, **kwargs):
        gate = self
        tagged = False
        attempt_summaries = []
        with self.lock:
            self.active += 1
            self.record["sdk_calls"] += 1

        class Transaction:
            def __init__(self, actual):
                self.actual = actual

            def __getattr__(self, name):
                return getattr(self.actual, name)

            def insert_or_update(self, table, columns, values):
                nonlocal tagged
                rows = list(values)
                self.actual.insert_or_update(table, columns, rows)
                if table != "GraphNodes" or "label" not in columns:
                    return
                labels = columns.index("label")
                summaries = [
                    row[columns.index("node_id")] for row in rows if row[labels] == "Summary"
                ]
                if not summaries:
                    return
                for row in rows:
                    if row[labels] == "Summary":
                        props = json_value(row[columns.index("props")])
                        attempt_summaries.append(
                            {
                                key: props.get(key)
                                for key in [
                                    "summary_id",
                                    "scope",
                                    "scope_id",
                                    "event_count",
                                    "time_range",
                                ]
                            }
                        )
                with gate.lock:
                    if gate.used:
                        return
                    gate.used = tagged = True
                    gate.record.update(
                        scheduled_summary_ids=summaries,
                        inside_sdk_callback=True,
                        entered_at=datetime.now(UTC).isoformat(),
                    )
                gate.entered.set()
                if not gate.release.wait(30):
                    raise TimeoutError("Harness did not release its real SDK transaction")
                if gate.mode == "storage-failure":
                    raise UnavailableError("controlled SDK callback storage failure")
                if gate.mode == "timer-fence":
                    raise RuntimeFencedError("controlled SDK callback fence")

        def wrapped(tx, *a, **kw):
            nonlocal attempt_summaries
            # The SDK can retry an aborted callback. Only its final attempt
            # belongs to the committed transaction's write set.
            attempt_summaries = []
            return operation(Transaction(tx), *a, **kw)

        try:
            result = self.database.run_in_transaction(wrapped, *args, **kwargs)
            with self.lock:
                self.record["summary_commits"].extend(attempt_summaries)
                if tagged:
                    self.record["gated_outcome"] = "committed"
            return result
        except BaseException as exc:
            with self.lock:
                self.record["summary_rollbacks"].extend(attempt_summaries)
                if tagged:
                    self.record["gated_outcome"] = type(exc).__name__
            raise
        finally:
            with self.lock:
                self.active -= 1
                self.record["returned_calls"] += 1


class SubscriptionFence:
    def __init__(self, actual, gate):
        self.actual, self.gate, self.hits = actual, gate, 0

    def __getattr__(self, name):
        return getattr(self.actual, name)

    async def read_new(self, count, block_ms):
        result = await self.actual.read_new(count, block_ms)
        if self.gate.entered.is_set():
            self.hits += 1
            raise RuntimeFencedError("controlled subscription fence")
        return result


def fixtures(run):
    sid, owner = run + "-session", "shutdown-owner"
    now = datetime.now(UTC)
    events = [
        dict(
            event_id=str(uuid5(NAMESPACE_URL, run + str(i))),
            event_type="observation.input",
            occurred_at=(now + timedelta(seconds=i)).isoformat(),
            session_id=sid,
            agent_id=owner,
            trace_id=run,
            payload_ref="shutdown:" + str(i),
            tool_name="shutdown-tool",
            importance_hint=7,
            payload={"content": "Shutdown verification source " + str(i)},
        )
        for i in range(2)
    ]
    members = sorted(event["event_id"] for event in events)
    episode = (
        "episode-"
        + hashlib.sha256(json.dumps([sid, members], separators=(",", ":")).encode()).hexdigest()
    )
    digest = hashlib.sha256("|".join(members).encode()).hexdigest()[:12]
    summaries = {
        scope: "summary-" + scope_id + "-" + digest
        for scope, scope_id in [("episode", episode), ("session", sid), ("agent", owner)]
    }
    expected_edges = {(events[1]["event_id"], "FOLLOWS", events[0]["event_id"])}
    expected_edges |= {
        (summary, "SUMMARIZES", member) for summary in summaries.values() for member in members
    }
    expected_edges |= {
        (episode, kind, member) for kind in ["CONTAINS", "DERIVED_FROM"] for member in members
    }
    expected_edges.add((summaries["episode"], "SUMMARIZES", episode))
    return dict(
        events=events,
        session_id=sid,
        owner=owner,
        episode=episode,
        summaries=summaries,
        expected_edges=sorted(expected_edges),
        summary_provider=SUMMARY_TEXT,
    )


async def run(run_id, directory, bound, db, plan):
    path = directory / "verification.json"
    record = dict(
        state="running",
        checks=[],
        requests=[],
        scenarios={},
        inputs=plan,
        limitations=[
            "private bound Core+PDLC+Memory configuration, not concurrent tenancy",
            "scripted optional summary provider; no prose/model quality claim",
            "faults inside real SDK callback; controlled fence, not actual tenant revocation",
            "ordinary cycle errors remain logged/swallowed, not fatal supervisor errors",
            "no process-kill, directly cancelled child or retroactive detached-work guarantee",
        ],
    )
    consumers, tasks, stores, gates = [], [], [], []
    other_workers = []
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

    async def wait_for(predicate, description, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done():
                    result = task.exception() if not task.cancelled() else asyncio.CancelledError()
                    if result:
                        raise result
            result = predicate()
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return result
            await asyncio.sleep(0.1)
        raise TimeoutError(description)

    async def settled_others():
        async def ready():
            values = await state()
            lags = await asyncio.gather(*(c._subscription.lag() for c in other_workers))
            return values if not values["pending"] and all(v == 0 for v in lags) else None

        values = await wait_for(ready, "four non-consolidation workers settle")
        check("other workers zero lag/pending/DLQ", not values["dead_letters"])
        return values

    async def start_consolidation(mode):
        worker, store = await _build_consumer(
            "consolidation", bound.settings(), tenant_binding=bound
        )
        worker._llm_client = SummaryProvider()
        gate = SDKGate(store.graph._database, mode)
        store.graph._database = gate
        fence = None
        if mode == "subscription-fence":
            fence = SubscriptionFence(worker._subscription, gate)
            worker._subscription = fence
        consumers.append(worker)
        stores.append(store)
        gates.append(gate)
        task = asyncio.create_task(worker.run())
        tasks.append(task)
        return worker, task, gate, fence

    async def join(worker, task, expected=None):
        worker.stop()
        outcome = None
        try:
            await asyncio.wait_for(asyncio.shield(task), 30)
        except (asyncio.CancelledError, RuntimeFencedError) as exc:
            outcome = type(exc)
        check(
            "joined outcome matches declared expectation",
            outcome is expected,
            dict(
                expected=expected.__name__ if expected else None,
                actual=outcome.__name__ if outcome else None,
            ),
        )
        tasks.remove(task)

    async def no_late_business_writes(case):
        before = await asyncio.to_thread(fingerprint, db)
        await asyncio.sleep(0.5)
        after = await asyncio.to_thread(fingerprint, db)
        record["scenarios"][case]["postjoin_fingerprints"] = [before, after]
        check(
            case + " no postjoin ledger/graph writes",
            all(before[k] == after[k] for k in ["Events", "GraphNodes", "GraphEdges"]),
        )

    def business(values):
        return {
            key: sorted(json.dumps(row, sort_keys=True) for row in values[key])
            for key in ["events", "nodes", "edges"]
        }

    async def exact_graph():
        values = await state()
        nodes = {(label, key): json_value(props) for label, key, props in values["nodes"]}
        ids = {e["event_id"] for e in plan["events"]}
        expected = (
            {("Event", eid) for eid in ids}
            | {("Summary", key) for key in plan["summaries"].values()}
            | {("Episode", plan["episode"]), ("OntologyState", "OntologyState:active")}
        )
        check(
            "exact ledger and graph identities",
            {r[0] for r in values["events"]} == ids
            and len(values["events"]) == 2
            and set(nodes) == expected
            and len(values["nodes"]) == 7,
        )
        labels = {key: label for label, key in expected}
        expected_edges = {(labels[a], a, rel, labels[b], b) for a, rel, b in plan["expected_edges"]}
        edges = {(al, a, rel, bl, b) for al, a, rel, bl, b, props in values["edges"]}
        check(
            "exact twelve directed graph edges",
            edges == expected_edges and len(values["edges"]) == 12,
            values["edges"],
        )
        for scope, key in plan["summaries"].items():
            props = nodes[("Summary", key)]
            scope_id = {
                "episode": plan["episode"],
                "session": plan["session_id"],
                "agent": plan["owner"],
            }[scope]
            bounds = [event["occurred_at"] for event in plan["events"]]
            check(
                "summary exact scope/membership " + scope,
                props.get("scope") == scope
                and props.get("scope_id") == scope_id
                and props.get("time_range") == bounds
                and props.get("event_count") == 2
                and (
                    props.get("content") == SUMMARY_TEXT
                    if scope != "agent"
                    else bool(props.get("content"))
                ),
                props,
            )
        episode = nodes[("Episode", plan["episode"])]
        check(
            "complete Episode retains exact evidence",
            episode.get("complete") is True
            and episode.get("event_count") == 2
            and episode.get("session_id") == plan["session_id"]
            and set(episode.get("source_event_ids", [])) == ids
            and episode.get("summary_id") == plan["summaries"]["episode"],
            episode,
        )
        for event in plan["events"]:
            props = nodes[("Event", event["event_id"])]
            check(
                "source Event identity/owner " + event["event_id"],
                all(
                    props.get(key) == event[key]
                    for key in [
                        "event_id",
                        "event_type",
                        "occurred_at",
                        "session_id",
                        "agent_id",
                        "trace_id",
                        "tool_name",
                    ]
                )
                and props.get("keywords") == ["observation", "input", "shutdown-tool"],
                props,
            )
        check(
            "Episode temporal bounds",
            [episode.get("start_time"), episode.get("end_time")]
            == [event["occurred_at"] for event in plan["events"]],
        )
        ontology = nodes[("OntologyState", "OntologyState:active")]
        check(
            "ontology metadata matches bound packs",
            ontology.get("version") == bound.bundle.schema_version
            and set(ontology.get("packs", []))
            == {name + "@" + version for name, version in bound.bundle.pack_identities},
        )
        check(
            "no pending/dead letter after joined cycle",
            not values["pending"] and not values["dead_letters"],
        )
        return values

    save()
    try:
        check(
            "verified empty starting dataset", not any(v["count"] for v in fingerprint(db).values())
        )
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
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=40,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(route, body):
                entry = dict(route=route, input=body, status=None)
                record["requests"].append(entry)
                save()
                try:
                    result = await http.post(route, json=body)
                    entry.update(status=result.status_code, answer=result.json())
                    save()
                    return result
                except BaseException as exc:
                    entry["error"] = repr(exc)
                    save()
                    raise

            for kind in VALID_CONSUMERS:
                if kind == "consolidation":
                    continue
                worker, store = await _build_consumer(kind, bound.settings(), tenant_binding=bound)
                consumers.append(worker)
                stores.append(store)
                other_workers.append(worker)
                tasks.append(asyncio.create_task(worker.run()))
            for event in plan["events"]:
                response = await request("/v1/events", event)
                check(
                    "accepted source event " + event["event_id"],
                    response.status_code == 201,
                    response.json(),
                )
            await settled_others()

            # Sleeping timer: no acquisition of consolidation lock by harness.
            worker, task, gate, _ = await start_consolidation("sleeping")
            await asyncio.sleep(0.05)
            began = time.monotonic()
            await join(worker, task)
            elapsed = time.monotonic() - began
            record["scenarios"]["SS02"] = dict(sdk=gate.evidence(), stop_seconds=elapsed)
            check(
                "SS02 sleeping timer wakes without a cycle",
                not gate.entered.is_set() and elapsed < 3,
                record["scenarios"]["SS02"],
            )
            await no_late_business_writes("SS02")

            for case, mode in [
                ("SS01", "stop"),
                ("SS03", "cancel"),
                ("SS04", "storage-failure"),
                ("SS05", "timer-fence"),
                ("SS06", "subscription-fence"),
                ("SS07", "restart"),
            ]:
                before = await state()
                worker, task, gate, fence = await start_consolidation(mode)
                # Expected errors cannot happen until this transaction is released.
                await wait_for(gate.entered.is_set, "SDK Summary mutation held")
                observed = dict(sdk_held=gate.evidence(), before_release=before)
                record["scenarios"][case] = observed
                if mode == "cancel":
                    for number in range(3):
                        task.cancel()
                        await asyncio.sleep(0.1)
                        check(
                            "SS03 repeated cancellation keeps run unfinished " + str(number),
                            not task.done(),
                        )
                elif mode == "subscription-fence":
                    await wait_for(lambda fence=fence: fence.hits, "subscription fence observed")
                    await asyncio.sleep(0.1)
                else:
                    worker.stop()
                    await asyncio.sleep(0.2)
                check(
                    case + " shutdown cannot finish while real SDK callback is held",
                    not task.done() and gate.evidence()["active_calls"] > 0,
                    gate.evidence(),
                )
                gate.release.set()
                expected = (
                    asyncio.CancelledError
                    if mode == "cancel"
                    else (
                        RuntimeFencedError
                        if mode in {"timer-fence", "subscription-fence"}
                        else None
                    )
                )
                await join(worker, task, expected)
                observed["sdk_returned"] = gate.evidence()
                check(
                    case + " every tracked SDK call returned",
                    gate.evidence()["active_calls"] == 0
                    and gate.evidence()["sdk_calls"] == gate.evidence()["returned_calls"],
                    gate.evidence(),
                )
                if mode in {"storage-failure", "timer-fence"}:
                    after = await state()
                    observed["after_failed_cycle"] = after
                    check(
                        case + " scheduled Summary mutation rolled back",
                        business(before) == business(after),
                        gate.evidence(),
                    )
                    check(
                        case + " actual SDK failure matches mode",
                        gate.evidence()["gated_outcome"]
                        == (
                            "UnavailableError"
                            if mode == "storage-failure"
                            else "RuntimeFencedError"
                        ),
                    )
                else:
                    check(
                        case + " actual gated SDK transaction committed",
                        gate.evidence()["gated_outcome"] == "committed",
                    )
                    commits = gate.evidence()["summary_commits"]
                    check(
                        case + " this admitted cycle committed all three summaries",
                        len(commits) == 3
                        and {(entry["scope"], entry["summary_id"]) for entry in commits}
                        == set(plan["summaries"].items()),
                        commits,
                    )
                    await exact_graph()
                if fence:
                    observed["subscription_fence_hits"] = fence.hits
                await no_late_business_writes(case)
                save()

            response = await request(
                "/v1/query/subgraph",
                dict(
                    query="Show the session timeline",
                    session_id=plan["session_id"],
                    agent_id=plan["owner"],
                    intent="when",
                    max_nodes=100,
                    timeout_ms=30000,
                ),
            )
            answer = response.json()
            check(
                "public timeline read succeeds without truncation",
                response.status_code == 200 and answer.get("meta", {}).get("truncated") is False,
                answer,
            )
            minimum = {e["event_id"] for e in plan["events"]} | {
                plan["episode"],
                plan["summaries"]["episode"],
            }
            allowed = minimum | set(plan["summaries"].values())
            check(
                "public timeline retrieves sources/Episode/Summary without unrelated nodes",
                minimum <= set(answer.get("nodes", {})) <= allowed,
            )
            attrs = answer.get("nodes", {}).get(plan["episode"], {}).get("attributes", {})
            check(
                "public Episode exact membership",
                attrs.get("complete") is True
                and attrs.get("summary_id") == plan["summaries"]["episode"]
                and set(attrs.get("source_event_ids", []))
                == {e["event_id"] for e in plan["events"]},
                attrs,
            )
            await settled_others()
            for c in consumers:
                c.stop()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            check(
                "all remaining workers join without cancellation workaround",
                not any(isinstance(x, BaseException) for x in results),
            )
            check("all SDK gates drained", all(g.evidence()["active_calls"] == 0 for g in gates))
            record["final_snapshot"] = await exact_graph()
            before = await asyncio.to_thread(fingerprint, db)
            await asyncio.sleep(1)
            after = await asyncio.to_thread(fingerprint, db)
            record["final_no_late_write_fingerprints"] = [before, after]
            check("all application tables stable after every worker joins", before == after)
            record["state"] = "passed"
            save()
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        save()
        raise
    finally:
        # Release every controlled SDK callback before joining; never cancel it.
        for gate in gates:
            gate.release.set()
        errors = await stop_demo(consumers, tasks, stores, server, server_task)
        record["shutdown_errors"] = errors
        record["retained_snapshot"] = await state()
        save()
        if errors or any(g.evidence()["active_calls"] for g in gates):
            record["state"] = "uncertain shutdown; reuse prohibited"
            save()
            raise RuntimeError("Uncertain shutdown; refuse database reuse")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-record", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("Unsafe run ID")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    if directory.exists():
        raise ValueError("Refuse evidence overwrite")
    previous = json.loads(args.previous_record.read_text())
    if previous["database"] != TARGET:
        raise ValueError("Only the authorized assessment DB may be reused")
    directory.mkdir()
    plan = fixtures(args.run_id)
    durable_json(
        directory / "manifest.json",
        dict(
            scenarios=SCENARIOS,
            fixtures=plan,
            target=TARGET,
            timer_seconds=5,
            threshold=5,
            packs=["core", "pdlc", "memory"],
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
        settings = settings_for(
            args.run_id, "pdlc-memory", target_database=TARGET.rsplit("/", 1)[1]
        )
        settings.decay.reflection_threshold = 5
        settings.decay.reconsolidation_interval_hours = 5 / 3600
        bound = TenantBinding.from_settings(
            "shutdown-assessment",
            args.run_id,
            previous["owner"][0][3] + 1,
            settings,
            engine_revision="consolidation-shutdown-v1",
        )
        export = directory / "previous-export.json"
        frozen, exported, digest = await asyncio.to_thread(
            freeze_and_export, db, previous["owner"][0], previous["fingerprints"], export
        )
        await asyncio.to_thread(reset_to, db, frozen, exported, digest, export, bound)
        try:
            await run(args.run_id, directory, bound, db, plan)
        finally:
            durable_json(
                directory / "retained.json",
                dict(
                    database=TARGET,
                    owner=await asyncio.to_thread(read_owner, db),
                    fingerprints=await asyncio.to_thread(fingerprint, db),
                ),
            )
    finally:
        await asyncio.to_thread(close_database, db)
        spanner.Client = original


if __name__ == "__main__":
    asyncio.run(main())
