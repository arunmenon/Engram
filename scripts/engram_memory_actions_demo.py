"""Belief/Goal acceptance through real HTTP, five workers and assessment Spanner.

Uses the Episode runner's verified-export/reset/shutdown safeguards unchanged.
Structured producer assertions only; no natural-language inference claim.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import socket
import sys
import time
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

import engram_memory_episodes_demo as harness
import httpx
import uvicorn
from engram_experiment_support import (
    DemoAuthentication,
    durable_json,
    fingerprint,
    snapshot,
    stop_demo,
)

from context_graph.adapters.spanner.log import json_value
from context_graph.api.app import create_app
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

PARALLEL_PROBE = False


def identity(family, agent, scope, session, key):
    return (
        family.lower()
        + "-"
        + hashlib.sha256(
            json.dumps(
                [family, agent, scope, session if scope == "session" else "", key],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )


async def run_config(config, bound, db):
    run, directory = harness.RUN, harness.DIRECTORY
    path = directory / (config + ".json")
    session, agent = run + ":" + config, "memory-action-agent"
    record = dict(
        config=config,
        state="running",
        requests=[],
        checks=[],
        session=session,
        expected=dict(
            belief_confirmations=2,
            belief_revision=2,
            goal_completed="completed",
            goal_abandoned="abandoned",
            goal_superseded="superseded",
        ),
        limitations=[
            "Private bound tenant, sequential configurations",
            "Structured producer assertions, not autonomous LLM belief inference",
            "No concurrent tenant isolation claim",
        ],
    )
    consumers, tasks, stores = [], [], []
    server = server_task = None
    start = datetime.now(UTC) - timedelta(hours=2)

    def save():
        durable_json(path, record)

    def check(name, passed, detail=None):
        record["checks"].append(dict(name=name, status="PASS" if passed else "FAIL", detail=detail))
        save()
        if not passed:
            raise AssertionError(name)

    def event(key, kind, payload, *, sid=session, owner=agent):
        return dict(
            event_id=str(uuid5(NAMESPACE_URL, session + ":" + key)),
            event_type=kind,
            occurred_at=start.isoformat(),
            session_id=sid,
            agent_id=owner,
            trace_id=run,
            payload_ref="memory-actions:" + key,
            payload=payload,
        )

    def belief(key, **extra):
        return dict(
            key=key,
            belief_text="Reset tokens expire in fifteen minutes.",
            confidence=0.7,
            category="world_model",
            **extra,
        )

    async def state():
        return await asyncio.to_thread(snapshot, db)

    try:
        check("empty owned starting dataset", not any(v["count"] for v in fingerprint(db).values()))
        app = create_app(bound.settings(), bundle=bound.bundle)
        app.state.tenant_binding = bound
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                DemoAuthentication(app, bound, token=harness.AUTH),
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
            headers={"Authorization": "Bearer " + harness.AUTH},
            timeout=40,
        ) as http:

            async def request(route, body):
                response = await http.post(route, json=body)
                answer = response.json()
                record["requests"].append(
                    dict(route=route, input=body, status=response.status_code, answer=answer)
                )
                save()
                return response.status_code, answer

            async def send(body, expected=201):
                status, answer = await request("/v1/events", body)
                check(
                    "admission " + body["payload_ref"],
                    status == expected,
                    answer if status != expected else None,
                )
                return answer

            async def wait_event(body, expected="applied"):
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    for task in tasks:
                        if task.done():
                            await task
                            raise RuntimeError("Worker stopped")
                    current = await state()
                    source = next(
                        (
                            p
                            for label, k, p in current["nodes"]
                            if label == "Event" and k == body["event_id"]
                        ),
                        {},
                    )
                    if source.get("memory_status") == expected:
                        return current
                    await asyncio.sleep(0.5)
                raise TimeoutError("Memory outcome missing: " + body["payload_ref"])

            async def query(intent, *, sid=session, owner=agent, max_nodes=100):
                status, answer = await request(
                    "/v1/query/subgraph",
                    dict(
                        query="Show " + intent,
                        session_id=sid,
                        agent_id=owner,
                        intent=intent,
                        max_nodes=max_nodes,
                        timeout_ms=30000,
                    ),
                )
                check("retrieval HTTP " + intent, status == 200)
                return answer

            first = event("stated", "memory.belief.stated", belief("expiry"))
            if config == "core":
                await send(first, 422)
                check(
                    "Memory disabled leaves ledger and typed graph empty",
                    not (await state())["events"] and not (await state())["nodes"],
                )
                record["state"] = "passed selected live scenarios"
                return
            await send(first)
            for kind in VALID_CONSUMERS:
                consumer, store = await _build_consumer(
                    kind, bound.settings(), tenant_binding=bound
                )
                consumers.append(consumer)
                stores.append(store)
                tasks.append(asyncio.create_task(consumer.run()))
            await wait_event(first)
            belief_id = identity("Belief", agent, "session", session, "expiry")
            answer = await query("beliefs")
            node = answer["nodes"].get(belief_id, {})
            check(
                "stated Belief source, confidence and count",
                node.get("attributes", {}).get("confirmation_count") == 1
                and node.get("provenance", {}).get("event_id") == first["event_id"]
                and node.get("attributes", {}).get("confidence") == 0.7,
            )
            before = await state()
            status, _ = await request("/v1/events", first)
            check("exact HTTP retry admitted idempotently", status in (200, 201))
            after = await state()
            check("retry no new ledger identity", len(before["events"]) == len(after["events"]))

            confirmations = [
                event(
                    "confirm-" + str(i),
                    "memory.belief.confirmed",
                    dict(key="expiry", expected_revision=0),
                )
                for i in (1, 2)
            ]
            await asyncio.gather(*(send(body) for body in confirmations))
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                current = await state()
                outcomes = {
                    k: p.get("memory_status")
                    for label, k, p in current["nodes"]
                    if label == "Event" and k in {b["event_id"] for b in confirmations}
                }
                if len(outcomes) == 2 and set(outcomes.values()) == {"applied", "conflict"}:
                    break
                await asyncio.sleep(0.5)
            check(
                "same-revision updates have one winner and one explicit conflict",
                len(outcomes) == 2 and set(outcomes.values()) == {"applied", "conflict"},
            )
            winner = next(k for k, v in outcomes.items() if v == "applied")
            answer = await query("beliefs")
            attrs = answer["nodes"].get(belief_id, {}).get("attributes", {})
            check(
                "confirmation counted once with exact support",
                attrs.get("confirmation_count") == 2
                and attrs.get("state_revision") == 1
                and set(attrs.get("supporting_event_ids", [])) == {first["event_id"], winner},
            )

            conflict_losers = {body["event_id"] for body in confirmations} - {winner}
            if PARALLEL_PROBE:
                import context_graph.worker.__main__ as worker_factory

                original_projection = next(
                    c
                    for c in consumers
                    if c._group_name == bound.settings().consumer.group_projection
                )
                projection_index = consumers.index(original_projection)
                original_projection.stop()
                await tasks[projection_index]
                tasks.pop(projection_index)
                original_registration = worker_factory.CONSUMER_SUBSCRIPTIONS["projection"]
                parallel = []
                try:
                    for name in ("memory-cas-a", "memory-cas-b"):
                        worker_factory.CONSUMER_SUBSCRIPTIONS["projection"] = (
                            original_registration[0],
                            name,
                        )
                        worker, store = await _build_consumer(
                            "projection", bound.settings(), tenant_binding=bound
                        )
                        parallel.append(worker)
                        consumers.append(worker)
                        stores.append(store)
                finally:
                    worker_factory.CONSUMER_SUBSCRIPTIONS["projection"] = original_registration
                competing = [
                    event(
                        "parallel-" + str(i),
                        "memory.belief.confirmed",
                        dict(key="expiry", expected_revision=1),
                    )
                    for i in (1, 2)
                ]
                await asyncio.gather(*(send(body) for body in competing))
                deliveries = await asyncio.gather(
                    *(worker._subscription.read_new(1, 0) for worker in parallel)
                )
                check(
                    "parallel consumers own distinct admitted deliveries",
                    all(len(batch) == 1 for batch in deliveries)
                    and {batch[0].fields["event_id"] for batch in deliveries}
                    == {body["event_id"] for body in competing},
                )
                record["parallel_handlers"] = []

                async def handle(worker, delivery):
                    evidence = dict(
                        consumer=worker._subscription.consumer_name,
                        group=worker._group_name,
                        event_id=delivery.fields["event_id"],
                        started_at=datetime.now(UTC).isoformat(),
                        started_monotonic=time.monotonic(),
                    )
                    record["parallel_handlers"].append(evidence)
                    save()
                    await worker.process_message(delivery.position, delivery.fields)
                    evidence.update(
                        ended_at=datetime.now(UTC).isoformat(), ended_monotonic=time.monotonic()
                    )
                    save()

                await asyncio.gather(
                    *(
                        handle(worker, batch[0])
                        for worker, batch in zip(parallel, deliveries, strict=True)
                    )
                )
                current = await state()
                parallel_outcomes = {
                    key: props.get("memory_status")
                    for label, key, props in current["nodes"]
                    if label == "Event" and key in {body["event_id"] for body in competing}
                }
                check(
                    "parallel projection CAS one winner one conflict",
                    len(parallel_outcomes) == 2
                    and set(parallel_outcomes.values()) == {"applied", "conflict"},
                    parallel_outcomes,
                )
                parallel_winner = next(
                    key for key, status in parallel_outcomes.items() if status == "applied"
                )
                conflict_losers |= {
                    key for key, status in parallel_outcomes.items() if status == "conflict"
                }
                answer = await query("beliefs")
                attrs = answer["nodes"].get(belief_id, {}).get("attributes", {})
                check(
                    "parallel CAS exact winner-only support and revision",
                    attrs.get("state_revision") == 2
                    and attrs.get("confirmation_count") == 3
                    and set(attrs.get("supporting_event_ids", []))
                    == {first["event_id"], winner, parallel_winner},
                )
                tasks.append(asyncio.create_task(parallel[0].run()))

            inferred = event("inferred", "memory.belief.inferred", belief("replacement"))
            await send(inferred)
            await wait_event(inferred)
            replacement_id = identity("Belief", agent, "session", session, "replacement")
            answer = await query("beliefs")
            attrs = answer["nodes"].get(replacement_id, {}).get("attributes", {})
            check(
                "inferred belief has no invented confirmation",
                attrs.get("origin") == "inferred"
                and attrs.get("confirmation_count") == 0
                and not attrs.get("supporting_event_ids")
                and attrs.get("last_confirmed_at") is None,
            )
            correction = event(
                "corrected",
                "memory.belief.corrected",
                dict(
                    key="expiry",
                    replacement_key="replacement",
                    expected_revision=2 if PARALLEL_PROBE else 1,
                    contradicts=True,
                ),
            )
            await send(correction)
            await wait_event(correction)
            answer = await query("beliefs")
            check(
                "current recall excludes superseded belief",
                belief_id not in answer["nodes"] and replacement_id in answer["nodes"],
            )
            answer = await query("when")
            edges = {(e["source"], e["edge_type"], e["target"]) for e in answer["edges"]}
            check(
                "history preserves both beliefs and declared correction",
                belief_id in answer["nodes"]
                and replacement_id in answer["nodes"]
                and {(replacement_id, k, belief_id) for k in ("SUPERSEDES", "CONTRADICTS")}
                <= edges,
            )
            check(
                "correction retains exact source evidence",
                (belief_id, "DERIVED_FROM", correction["event_id"]) in edges,
            )

            for key, terminal in [
                ("complete", "completed"),
                ("abandon", "abandoned"),
                ("old", "superseded"),
            ]:
                created = event(
                    key,
                    "memory.goal.created",
                    dict(key=key, description="Implement reset expiry.", priority=5),
                )
                await send(created)
                await wait_event(created)
                if terminal == "superseded":
                    replacement = event(
                        "new",
                        "memory.goal.created",
                        dict(key="new", description="Implement improved reset expiry."),
                    )
                    await send(replacement)
                    await wait_event(replacement)
                update = event(
                    key + "-terminal",
                    "memory.goal." + terminal,
                    dict(
                        key=key,
                        expected_revision=0,
                        **({"replacement_key": "new"} if terminal == "superseded" else {}),
                    ),
                )
                await send(update)
                await wait_event(update)
            answer = await query("when")
            for key, status in [
                ("complete", "completed"),
                ("abandon", "abandoned"),
                ("old", "superseded"),
                ("new", "active"),
            ]:
                goal_id = identity("Goal", agent, "session", session, key)
                node = answer["nodes"].get(goal_id, {})
                check(
                    "Goal lifecycle " + status,
                    node.get("attributes", {}).get("status") == status
                    and node.get("attributes", {}).get("evidence_count")
                    == (1 if key == "new" else 2),
                )

            scoped = event(
                "agent-wide", "memory.belief.stated", belief("agent-wide", scope="agent")
            )
            other = event(
                "other-owner", "memory.belief.stated", belief("expiry"), owner="other-agent"
            )
            await send(scoped)
            await wait_event(scoped)
            await send(other)
            await wait_event(other)
            scoped_id = identity("Belief", agent, "agent", session, "agent-wide")
            answer = await query("beliefs", sid=session + ":another")
            check(
                "explicit agent scope crosses sessions, session scope does not",
                scoped_id in answer["nodes"] and replacement_id not in answer["nodes"],
            )
            answer = await query("beliefs")
            other_id = identity("Belief", "other-agent", "session", session, "expiry")
            check("other owner excluded from Memory recall", other_id not in answer["nodes"])
            answer = await query("beliefs", owner="other-agent")
            check(
                "other owner positively retrievable",
                other_id in answer["nodes"] and replacement_id not in answer["nodes"],
            )

            deferred = event(
                "early-confirm",
                "memory.belief.confirmed",
                dict(key="late-parent", expected_revision=0),
            )
            await send(deferred)
            await wait_event(deferred, "deferred")
            parent = event("late-parent", "memory.belief.stated", belief("late-parent"))
            await send(parent)
            await wait_event(parent)
            await wait_event(deferred)
            answer = await query("beliefs")
            late_id = identity("Belief", agent, "session", session, "late-parent")
            check(
                "missing parent recovered by pending worker retry",
                answer["nodes"].get(late_id, {}).get("attributes", {}).get("confirmation_count")
                == 2,
            )

            for bad in [
                dict(key="invalid", expected_revision=-1),
                dict(key="invalid", expected_revision=0, extra=True),
            ]:
                before = await state()
                body = event(
                    "invalid-" + str(len(record["requests"])), "memory.belief.confirmed", bad
                )
                await send(body, 422)
                after = await state()
                check("invalid contract no ledger write", before["events"] == after["events"])
            if config == "pdlc-memory":
                pr = event(
                    "pdlc",
                    "pdlc.change.created",
                    dict(repo="memory/demo", number=7, title="Memory coexistence"),
                )
                await send(pr)
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    current = await state()
                    if any(
                        label == "Change" and k == "Change:memory/demo|7"
                        for label, k, p in current["nodes"]
                    ):
                        break
                    await asyncio.sleep(0.5)
                status, answer = await request(
                    "/v1/query/artifacts",
                    dict(query="trace this change", seed_node_ids=["Change:memory/demo|7"]),
                )
                check(
                    "PDLC remains independently retrievable",
                    status == 200
                    and answer.get("nodes", {})
                    .get("Change:memory/demo|7", {})
                    .get("provenance", {})
                    .get("event_id")
                    == pr["event_id"],
                )
                answer = await query("goals")
                check(
                    "PDLC event invents no Goal",
                    len([n for n in answer["nodes"].values() if n["node_type"] == "Goal"]) == 3,
                )
            answer = await query("when", max_nodes=1)
            check(
                "read budget honest with no dangling edges",
                len(answer["nodes"]) <= 1
                and answer["meta"]["truncated"]
                and all(
                    e["source"] in answer["nodes"] and e["target"] in answer["nodes"]
                    for e in answer["edges"]
                ),
            )
            # Predeclared semantics reconstructed from submitted bodies, never from returned state.
            bodies = {}
            for request_record in record["requests"]:
                body = request_record["input"]
                if request_record["route"] == "/v1/events" and request_record["status"] in (
                    200,
                    201,
                ):
                    bodies.setdefault(body["event_id"], body)
            losing = conflict_losers
            expected = {}
            expected_edges = set()
            for event_id, body in sorted(
                bodies.items(),
                key=lambda pair: (
                    -1
                    if pair[1]["event_type"].endswith((".stated", ".inferred", ".created"))
                    else pair[1]["payload"].get("expected_revision", 0)
                ),
            ):
                kind, payload = body["event_type"], body["payload"]
                if not kind.startswith("memory.") or event_id in losing:
                    continue
                family = "Belief" if kind.startswith("memory.belief.") else "Goal"
                scope = payload.get("scope", "session")
                key = identity(family, body["agent_id"], scope, body["session_id"], payload["key"])
                if kind.endswith((".stated", ".inferred", ".created")):
                    expected[key] = dict(
                        family=family,
                        agent_id=body["agent_id"],
                        session_id=body["session_id"],
                        scope=scope,
                        local_key=payload["key"],
                        complete=True,
                        state_revision=0,
                        events=[],
                        source=event_id,
                        created_at=body["occurred_at"],
                    )
                    if family == "Belief":
                        expected[key].update(
                            belief_text=payload["belief_text"],
                            category=payload["category"],
                            confidence=payload["confidence"],
                            origin=kind.rsplit(".", 1)[1],
                            supporting_event_ids=[],
                        )
                    else:
                        expected[key].update(description=payload["description"], status="active")
                item = expected[key]
                item["events"].append(event_id)
                item["state_revision"] = len(item["events"]) - 1
                if family == "Belief" and kind.endswith((".stated", ".confirmed")):
                    item["supporting_event_ids"].append(event_id)
                if kind.endswith((".completed", ".abandoned", ".superseded")):
                    item["status"] = kind.rsplit(".", 1)[1]
                if kind.endswith((".corrected", ".superseded")):
                    replacement = identity(
                        family,
                        body["agent_id"],
                        scope,
                        body["session_id"],
                        payload["replacement_key"],
                    )
                    item["superseded_by"] = replacement
                    expected_edges.add((replacement, "SUPERSEDES", key))
                    if payload.get("contradicts"):
                        expected_edges.add((replacement, "CONTRADICTS", key))
                expected_edges.add((key, "DERIVED_FROM", event_id))

            def exact_memory(answer, expected_ids, *, api):
                actual = {
                    key: node
                    for key, node in answer["nodes"].items()
                    if node["node_type"] in ("Belief", "Goal")
                }
                if set(actual) != expected_ids:
                    return False
                for key, node in actual.items():
                    item, attrs = expected[key], node["attributes"]
                    for field in (
                        "agent_id",
                        "session_id",
                        "scope",
                        "local_key",
                        "complete",
                        "state_revision",
                        "superseded_by",
                    ):
                        if attrs.get(field) != item.get(field):
                            return False
                    if datetime.fromisoformat(attrs["created_at"]) != datetime.fromisoformat(
                        item["created_at"]
                    ):
                        return False
                    if set(attrs.get("evidence_event_ids", [])) != set(item["events"]):
                        return False
                    fields = (
                        ("belief_text", "category", "confidence", "origin")
                        if item["family"] == "Belief"
                        else ("description", "status")
                    )
                    if any(attrs.get(field) != item[field] for field in fields):
                        return False
                    if item["family"] == "Belief":
                        if attrs.get("confirmation_count") != len(
                            item["supporting_event_ids"]
                        ) or set(attrs.get("supporting_event_ids", [])) != set(
                            item["supporting_event_ids"]
                        ):
                            return False
                    elif attrs.get("evidence_count") != len(item["events"]):
                        return False
                    if api and node.get("provenance", {}).get("event_id") != item["source"]:
                        return False
                    for event_id in item["events"]:
                        source = answer["nodes"].get(event_id, {})
                        props = {
                            **source.get("attributes", {}),
                            **(source.get("provenance", {}) if api else {}),
                        }
                        body = bodies[event_id]
                        if source.get("node_type") != "Event" or any(
                            props.get(k) != body[k]
                            for k in ("agent_id", "session_id", "event_type")
                        ):
                            return False
                        if (
                            props.get("memory_subject_id") != key
                            or props.get("memory_subject_label") != item["family"]
                            or props.get("memory_expected_revision")
                            != body["payload"].get("expected_revision")
                        ):
                            return False
                observed = {
                    (edge["source"], edge["edge_type"], edge["target"])
                    for edge in answer["edges"]
                    if edge["edge_type"] in ("DERIVED_FROM", "SUPERSEDES", "CONTRADICTS")
                    and (edge["source"] in actual or edge["target"] in actual)
                }
                wanted = {
                    edge
                    for edge in expected_edges
                    if edge[0] in expected_ids
                    and (edge[1] == "DERIVED_FROM" or edge[2] in expected_ids)
                }
                return observed == wanted

            for owner in (agent, "other-agent"):
                answer = await query("when", owner=owner)
                expected_ids = {key for key, item in expected.items() if item["agent_id"] == owner}
                check(
                    "exact Memory state, sources, receipts and edges via API " + owner,
                    exact_memory(answer, expected_ids, api=True),
                )
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                final = await state()
                lags = [await consumer._subscription.lag() for consumer in consumers]
                if all(lag == 0 for lag in lags) and not final["pending"]:
                    break
                await asyncio.sleep(1)
            check(
                "all five groups settled",
                all(lag == 0 for lag in lags) and not final["pending"],
                lags,
            )
            record["expected_state"] = expected
            record["expected_edges"] = sorted(expected_edges)
            audit = dict(
                nodes={
                    key: dict(node_type=label, attributes=json_value(props))
                    for label, key, props in final["nodes"]
                },
                edges=[
                    dict(source=edge[1], edge_type=edge[2], target=edge[4])
                    for edge in final["edges"]
                ],
            )
            check(
                "independent final Spanner Memory row audit",
                exact_memory(audit, set(expected), api=False),
            )

            def dead_letter_fields():
                with db.snapshot() as snap:
                    return [
                        dict(row[0])
                        for row in snap.execute_sql("SELECT fields FROM ConsumerDeadLetters")
                    ]

            dead = await asyncio.to_thread(dead_letter_fields)
            record["dead_letters_inspected"] = dead
            check(
                "exact expected conflict DLQ only",
                len(dead) == len(losing)
                and {row.get("event_id") for row in dead} == losing
                and all(
                    row.get("group") == bound.settings().consumer.group_projection
                    and row.get("disposition_epoch") == str(bound.epoch)
                    for row in dead
                ),
                dead,
            )
            check(
                "losing action conflict diagnostic retained",
                all(
                    audit["nodes"].get(event_id, {}).get("attributes", {}).get("memory_status")
                    == "conflict"
                    and audit["nodes"].get(event_id, {}).get("attributes", {}).get("memory_reason")
                    == "state_conflict"
                    for event_id in losing
                ),
            )
            record["state"] = "passed selected live scenarios"
    except Exception as exc:
        record.update(state="failed", error=type(exc).__name__ + ": " + str(exc))
        raise
    finally:
        record["shutdown_errors"] = await stop_demo(consumers, tasks, stores, server, server_task)
        record["retained_snapshot"] = await state()
        save()
        if record["shutdown_errors"]:
            record["state"] = "failed shutdown; database retained, no reuse"
            save()
            raise RuntimeError("Shutdown incomplete; refuse next reset")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--parallel-probe", action="store_true")
    options, remaining = parser.parse_known_args()
    PARALLEL_PROBE = options.parallel_probe
    sys.argv = [sys.argv[0], *remaining]
    if PARALLEL_PROBE:
        original_binding = harness.binding

        def parallel_binding(config, epoch):
            base = original_binding(config, epoch)
            settings = base.settings()
            settings.consumer.projection_batch_size = 1
            return harness.TenantBinding.from_settings(
                base.tenant_id,
                base.binding_id,
                epoch,
                settings,
                engine_revision="memory-actions-v1",
            )

        harness.binding = parallel_binding
    harness.run_config = run_config
    asyncio.run(harness.main())
