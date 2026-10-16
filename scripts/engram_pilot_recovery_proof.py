"""P10 labeled scheduling probes; business writes still use public HTTP."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import time
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from engram_memory_actions_demo import identity
from engram_pilot_completion_fixtures import decoded_snapshot_cell as decode
from engram_pilot_completion_fixtures import p04_negative_proof

PROVIDER_REJECTION = ContextVar("p10_actual_provider_rejection", default=None)


def freeze(run_id):
    now = datetime.now(UTC) - timedelta(minutes=3)

    def step(t, key, kind, payload, session):
        return dict(
            scenario=key,
            expected_status=201,
            expected_edges=[],
            request=dict(
                event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + t + ":" + key)),
                event_type=kind,
                occurred_at=now.isoformat(),
                session_id=run_id + ":" + session,
                agent_id=run_id + ":" + t + ":owner",
                trace_id=run_id,
                payload_ref="pilot-p10:" + key,
                payload=payload,
            ),
        )

    delay = step(
        "a",
        "delay",
        "observation.input",
        dict(content="Processing delay probe, not a personal preference."),
        "delay",
    )
    delay["request"]["importance_hint"] = 9
    prose = step(
        "a",
        "provider-source",
        "observation.input",
        dict(content="I prefer concise explanations with concrete examples."),
        "provider",
    )
    end = step("a", "provider-end", "system.session_end", {}, "provider")
    parent = step(
        "b",
        "parent",
        "memory.goal.created",
        dict(key="recover", description="Complete the deferred deployment review"),
        "memory",
    )
    child = step(
        "b", "child", "memory.goal.completed", dict(key="recover", expected_revision=0), "memory"
    )
    child["request"]["occurred_at"] = (now + timedelta(seconds=1)).isoformat()
    positive = step(
        "b",
        "positive",
        "memory.goal.created",
        dict(
            key="available", description="Tenant B remains usable during Tenant A provider failure"
        ),
        "positive",
    )
    goal = identity(
        "Goal", parent["request"]["agent_id"], "session", parent["request"]["session_id"], "recover"
    )
    positive_goal = identity(
        "Goal",
        positive["request"]["agent_id"],
        "session",
        positive["request"]["session_id"],
        "available",
    )
    return dict(
        run_id=run_id,
        coverage=(
            "P10 cooperative recovery with labeled instance-only barriers; "
            "no forced crash/network partition"
        ),
        groups=[
            dict(
                name="p10-a",
                tenant="a",
                recovery_proof=True,
                steps=[delay, prose, end],
                queries=[],
                retained_negative_proofs=[p04_negative_proof()],
            ),
            dict(
                name="p10-b",
                tenant="b",
                recovery_proof=True,
                steps=[child, parent, positive],
                queries=[],
                goal=goal,
                positive_goal=positive_goal,
            ),
        ],
    )


class RecoveryHooks:
    """Test-only scheduling controls attached to individual worker instances."""

    def __init__(self, plan, record, save):
        self.plan, self.record, self.save = plan, record, save
        self.delay_id = plan["groups"][0]["steps"][0]["request"]["event_id"]
        self.failed_session = plan["groups"][0]["steps"][1]["request"]["session_id"]
        self.child_id = plan["groups"][1]["steps"][0]["request"]["event_id"]
        self.projection_release = asyncio.Event()
        self.projection_entered = asyncio.Event()
        self.child_deferred = asyncio.Event()
        self.skip_memory_retries = True
        self.provider_injected = False
        self.arm_stop = False
        self.held_session = asyncio.Event()
        self.session_release = asyncio.Event()
        self.held_worker = None
        self.held_finished = False
        self.later_sessions = []
        self.generation = 0
        record["recovery_interventions"] = []

    def note(self, name, **data):
        self.record["recovery_interventions"].append(dict(name=name, **data))
        self.save()

    def release_all(self):
        self.projection_release.set()
        self.session_release.set()
        self.skip_memory_retries = False

    def install(self, tenant, kind, worker):
        if tenant == "a" and kind == "projection":
            original = worker.process_message

            async def projection(entry_id, data):
                if data.get("event_id") == self.delay_id and not self.projection_release.is_set():
                    self.note("projection-held-before-processing", event_id=self.delay_id)
                    self.projection_entered.set()
                    await self.projection_release.wait()
                return await original(entry_id, data)

            worker.process_message = projection
        if tenant == "b" and kind == "projection":
            diagnostic = worker._memory_diagnostic

            async def observe_deferred(event, status, reason=None):
                await diagnostic(event, status, reason)
                if str(event.event_id) == self.child_id and status == "deferred":
                    self.note("child-deferred", event_id=self.child_id, reason=reason)
                    self.child_deferred.set()

            worker._memory_diagnostic = observe_deferred
            retry = worker._retry_pending_memory

            async def pending():
                # Return to normal reads so the parent can project. Never ack or alter counts.
                if self.skip_memory_retries and self.child_deferred.is_set():
                    return
                return await retry()

            worker._retry_pending_memory = pending
        if tenant == "a" and kind == "extraction":
            extract = worker._llm_client.extract_from_session
            installed_generation = self.generation

            async def marked_extract(*args, **kwargs):
                marker = None
                if kwargs.get("session_id") == self.failed_session:
                    inject = not self.provider_injected
                    self.provider_injected = True
                    marker = dict(
                        session_id=self.failed_session,
                        generation=installed_generation,
                        inject=inject,
                    )
                    if inject:
                        self.note("real-provider-test-credential-selected", **marker)
                token = PROVIDER_REJECTION.set(marker)
                try:
                    return await extract(*args, **kwargs)
                finally:
                    PROVIDER_REJECTION.reset(token)

            worker._llm_client.extract_from_session = marked_extract
        if tenant == "a" and kind == "consolidation":
            consolidate = worker._consolidate_session

            async def held(session_id, count):
                if self.arm_stop and self.held_worker is None:
                    self.held_worker = worker
                    self.note(
                        "consolidation-session-held", session_id=session_id, event_count=count
                    )
                    self.held_session.set()
                    await self.session_release.wait()
                    await consolidate(session_id, count)
                    self.held_finished = True
                    self.note("consolidation-held-session-finished", session_id=session_id)
                    return
                if self.held_worker is worker and worker._stopped:
                    self.later_sessions.append(session_id)
                return await consolidate(session_id, count)

            worker._consolidate_session = held


async def execute(
    plan,
    *,
    request,
    check,
    record,
    save,
    databases,
    evidence_directory,
    hooks,
    restart,
    stale_probe,
    settle,
):
    from engram_experiment_support import read_owner, snapshot
    from engram_pilot_completion_fixtures import (
        recovery_documents,
        recovery_input_hash,
        verified_recovered_user_receipt,
    )
    from engram_pilot_retrieval_proof import closed_response
    from engram_pilot_tenant_proof import memory_read_request

    a, b = plan["groups"]
    delay, prose, end = a["steps"]
    child, parent, positive = b["steps"]
    saved = record.setdefault("recovery_proof", [])
    receipts = {}

    async def capture(name):
        states = {t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()}
        for tenant, db in databases.items():
            states[tenant]["owner"] = await asyncio.to_thread(read_owner, db)
        raw = json.dumps(states, sort_keys=True, default=str).encode()
        p = Path(evidence_directory) / (name + "-state.json.gz")
        p.write_bytes(gzip.compress(raw))
        assert gzip.decompress(p.read_bytes()) == raw
        saved.append(dict(name=name, file=p.name, sha256=hashlib.sha256(raw).hexdigest()))
        save()
        return states

    async def wait_state(name, predicate, seconds=180):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            states = {t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()}
            if predicate(states):
                return await capture(name)
            await asyncio.sleep(0.3)
        raise TimeoutError("P10 observation missing: " + name)

    def nodes(state):
        return {(r[0], r[1]): decode(r[2]) for r in state["nodes"]}

    def pending(state, eid, group):
        # Snapshot field order is pinned by the normal support adapter.
        return any(row[:2] == [group, eid] for row in state["pending"])

    async def admit(t, s):
        code, out = await request(t, "/v1/events", s["request"])
        check(
            s["scenario"] + " public created", code == 201 and out.get("status") == "created", out
        )
        receipts[(t, s["request"]["event_id"])] = out["global_position"]
        return out

    await admit("a", delay)
    await asyncio.wait_for(hooks.projection_entered.wait(), 60)
    states = await wait_state(
        "enrichment-pending-before-event",
        lambda ss: (
            pending(ss["a"], hooks.delay_id, "assessment-enrichment")
            and ("Event", hooks.delay_id) not in nodes(ss["a"])
        ),
    )
    check(
        "delayed Event accepted in ledger",
        any(r[0] == hooks.delay_id for r in states["a"]["events"]),
    )
    hooks.note("projection-barrier-released", event_id=hooks.delay_id)
    hooks.projection_release.set()
    await wait_state(
        "event-projects-after-release", lambda ss: ("Event", hooks.delay_id) in nodes(ss["a"])
    )
    await admit("b", child)
    await asyncio.wait_for(hooks.child_deferred.wait(), 60)
    states = await capture("child-deferred-before-parent")
    check(
        "child actual deferred pending and no subject",
        pending(states["b"], hooks.child_id, "assessment-projection")
        and nodes(states["b"])[("Event", hooks.child_id)].get("memory_status") == "deferred"
        and nodes(states["b"])[("Event", hooks.child_id)].get("memory_reason")
        == "reference_missing"
        and ("Goal", b["goal"]) not in nodes(states["b"]),
    )
    await admit("b", parent)
    await wait_state(
        "parent-projected-with-child-still-pending",
        lambda ss: (
            ("Goal", b["goal"]) in nodes(ss["b"])
            and nodes(ss["b"])[("Goal", b["goal"])].get("status") == "active"
            and pending(ss["b"], hooks.child_id, "assessment-projection")
        ),
    )
    hooks.skip_memory_retries = False
    hooks.note("pending-memory-retry-skip-released")
    await wait_state(
        "child-converged-after-parent",
        lambda ss: (
            nodes(ss["b"]).get(("Goal", b["goal"]), {}).get("status") == "completed"
            and not pending(ss["b"], hooks.child_id, "assessment-projection")
        ),
    )
    await admit("a", prose)
    await admit("a", end)
    marked = end["request"]["event_id"]
    states = await wait_state(
        "real-provider-rejection-pending",
        lambda ss: (
            any(
                c.get("test_injection") == "p10-known-invalid-credential"
                and c.get("error_type") == "AuthenticationError"
                for c in record["provider_calls"]
            )
            and pending(ss["a"], marked, "assessment-extraction")
        ),
    )
    check(
        "failed extraction has no applied receipt",
        ("Event", marked) in nodes(states["a"])
        and nodes(states["a"])[("Event", marked)].get("user_extraction_status") != "applied",
    )
    await admit("b", positive)
    states = await wait_state(
        "B-positive-during-A-failure", lambda ss: ("Goal", b["positive_goal"]) in nodes(ss["b"])
    )
    code, out = await request(
        "b",
        "/v1/query/subgraph",
        memory_read_request({"steps": [positive]}),
    )
    check(
        "B public available during A failure",
        code == 200
        and b["positive_goal"] in out.get("nodes", {})
        and closed_response(out, states["b"]),
    )
    hooks.arm_stop = True
    await asyncio.wait_for(hooks.held_session.wait(), 90)
    stopping = asyncio.create_task(restart())
    try:
        await asyncio.sleep(0.1)
        check(
            "cooperative stop waits for held session",
            not stopping.done() and hooks.held_worker._stopped,
        )
    finally:
        # No orphan callback may create workers after outer cleanup completes.
        hooks.session_release.set()
        await stopping
    check(
        "held session finishes without subsequent stopped-session work",
        hooks.held_finished and hooks.later_sessions == [],
        hooks.later_sessions,
    )
    states = await settle()
    await capture("after-normal-restart")
    event = nodes(states["a"])[("Event", hooks.delay_id)]
    check(
        "delayed enrichment eventually applied", event.get("keywords") == ["observation", "input"]
    )
    docs = recovery_documents(states["a"], [prose["request"], end["request"]])
    receipt = verified_recovered_user_receipt(
        states["a"],
        dict(
            recover_user_inputs=[prose["request"], end["request"]],
            recovery_input_hash=recovery_input_hash(
                states["a"], [prose["request"], end["request"]]
            ),
        ),
    )
    check(
        "restart applies exact accepted extraction source window",
        receipt["input_event_ids"] == [d["event_id"] for d in docs],
    )
    user_path = "/v1/users/user:" + end["request"]["agent_id"] + "/data-export"
    code, user_export = await request("a", user_path, method="GET", role="admin")
    check(
        "recovered receipt visible through public User API",
        code == 200 and receipt in user_export.get("extraction_receipts", []),
    )
    check(
        "single marked real rejection only",
        len(
            [
                c
                for c in record["provider_calls"]
                if c.get("test_injection") == "p10-known-invalid-credential"
            ]
        )
        == 1,
    )
    for t, step, required in [("a", end, marked), ("b", parent, b["goal"])]:
        body = memory_read_request({"steps": [step]})
        if t == "a":
            body["seed_nodes"] = [marked]
        code, out = await request(t, "/v1/query/subgraph", body)
        node = out.get("nodes", {}).get(required, {})
        check(
            t + " recovered public read expected identity and source closure",
            code == 200 and required in out.get("nodes", {}) and closed_response(out, states[t]),
        )
        check(
            t + " recovered exact admission provenance",
            node.get("provenance", {}).get("event_id") == step["request"]["event_id"]
            and node.get("provenance", {}).get("global_position")
            == receipts[(t, step["request"]["event_id"])],
        )
        if t == "b":
            check(
                "B completed Goal reports actual terminal state",
                node.get("attributes", {}).get("status") == "completed",
            )
    check(
        "successful marked extraction belongs to restarted generation",
        any(
            c.get("recovery_extraction_session") == hooks.failed_session
            and c.get("worker_generation") == 1
            and c.get("state") == "returned"
            for c in record["provider_calls"]
        ),
    )
    await stale_probe()

    from engram_pilot_tenant_proof import retained_state_preserved

    for tenant, step in (("a", end), ("b", child)):
        before = await capture("replay-before-" + tenant)
        code, out = await request(tenant, "/v1/events", step["request"])
        after = await capture("replay-after-" + tenant)
        check(
            "recovered replay preserves exact receipt-" + tenant,
            code == 201
            and out.get("status") == "duplicate"
            and out.get("global_position") == receipts[(tenant, step["request"]["event_id"])],
        )
        check(
            "recovered replay preserves both tenants-" + tenant,
            all(retained_state_preserved(before[t], after[t]) for t in before),
        )

    code, final_export = await request("a", user_path, method="GET", role="admin")

    def normalized_export(value):
        return {
            k: sorted(json.dumps(row, sort_keys=True) for row in v) if isinstance(v, list) else v
            for k, v in value.items()
        }

    check(
        "recovered public User outputs and receipts stable across replays",
        code == 200 and normalized_export(final_export) == normalized_export(user_export),
    )
