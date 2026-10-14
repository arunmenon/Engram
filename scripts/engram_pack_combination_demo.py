"""Post-remediation five-pack-combination acceptance on the assessment database.

Authenticated HTTP ingress/reads, five actual workers, real Spanner. External
extraction/summary providers return frozen outputs; this is not model evaluation.
No application artifacts are inserted/repaired. Sequential tenants, final data retained.
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
from context_graph.adapters.spanner.log import json_value
from context_graph.api.app import create_app
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

CONFIGURATIONS = ["core", "user", "user-memory", "pdlc", "pdlc-memory"]
DECISION = "Expire reset tokens after fifteen minutes."
SUMMARY = "Accepted activity describes reset token work and Alice's preference correction."
SCENARIOS = {
    "PC01": "common Event, extracted Entity, enrichment and core summaries",
    "PC02": "User profile/preference; overlapping trigger and explicit correction",
    "PC03": "structured Belief confirmation and Goal completion with exact evidence",
    "PC04": "PDLC PR created/merged; same PR number in unrelated repo stays separate",
    "PC05": "PDLC prose extraction Decision; no implicit Belief/Goal conversion",
    "PC06": "Memory Episodes over user and (with PDLC) domain activity",
    "PC07": "HTTP duplicates and fresh User worker receipt replay do not double-count",
    "PC08": "disabled capabilities and malformed enabled contracts reject without writes",
    "PC09": "read APIs return expected artifacts, lifecycle and source evidence",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def preference_id(polarity):
    values = [
        "user:alice",
        "communication",
        "answer-length",
        "global",
        None,
        "support",
        polarity,
        None,
    ]
    return (
        "preference:"
        + hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def extraction(polarity):
    return dict(
        entities=[
            dict(
                name="ResetToken", entity_type="concept", confidence=1.0, source_quote="ResetToken"
            )
        ],
        persona=dict(name="Alice", source_quote="My name is Alice")
        if polarity == "positive"
        else None,
        preferences=[
            dict(
                category="communication",
                key="answer-length",
                polarity=polarity,
                strength=0.8,
                confidence=0.9,
                source="explicit",
                context="support",
                source_quote="I no longer prefer short answers"
                if polarity == "negative"
                else "short answers",
            )
        ],
    )


def fixtures(run_id, config):
    start = datetime.now(UTC) - timedelta(minutes=5)
    sid = run_id + ":" + config
    events = {}

    def event(key, kind="observation.input", payload=None, *, session="user", owner="alice"):
        value = dict(
            event_id=str(uuid5(NAMESPACE_URL, sid + key)),
            event_type=kind,
            occurred_at=(start + timedelta(seconds=len(events))).isoformat(),
            session_id=sid + ":" + session,
            agent_id=owner,
            trace_id=run_id,
            payload_ref="pack-combination:" + key,
            importance_hint=7,
            payload=payload or {},
        )
        events[key] = value
        return value

    event(
        "preference",
        payload={
            "content": "My name is Alice. I use ResetToken. I prefer short answers. We decide: "
            + DECISION
        },
    )
    event("end", "system.session_end")
    event("overlap", "system.session_end")
    event(
        "correction",
        payload={
            "content": "My name is Alice. I use ResetToken. I no longer prefer short answers.",
            "preference_corrections": [
                dict(
                    previous_preference_id=preference_id("positive"),
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="support",
                )
            ],
        },
    )
    event("correction-end", "system.session_end")
    event(
        "belief",
        "memory.belief.stated",
        dict(
            key="expiry",
            belief_text="Reset tokens expire in fifteen minutes.",
            confidence=0.7,
            category="world_model",
        ),
        session="memory",
    )
    event(
        "confirmation",
        "memory.belief.confirmed",
        dict(key="expiry", expected_revision=0),
        session="memory",
    )
    event(
        "goal",
        "memory.goal.created",
        dict(key="implement", description="Implement reset expiry.", priority=5),
        session="memory",
    )
    event(
        "completion",
        "memory.goal.completed",
        dict(key="implement", expected_revision=0),
        session="memory",
    )
    event(
        "pr",
        "pdlc.change.created",
        dict(repo="packmatrix/main", number=7, title="Reset expiry"),
        session="pdlc",
    )
    event(
        "merge",
        "pdlc.change.merged",
        dict(repo="packmatrix/main", number=7, title="Reset expiry", merge_sha="abc123"),
        session="pdlc",
    )
    event(
        "unrelated-pr",
        "pdlc.change.created",
        dict(repo="packmatrix/unrelated", number=7, title="Newsletter"),
        session="unrelated",
        owner="bob",
    )
    event(
        "bad-memory",
        "memory.belief.confirmed",
        dict(key="expiry", expected_revision="bad"),
        session="memory",
    )
    event("bad-pdlc", "pdlc.change.created", dict(repo="packmatrix/main"), session="pdlc")
    memory = "memory" in config
    user = config.startswith("user")
    pdlc = config.startswith("pdlc")
    accepted = ["preference", "end", "overlap", "correction", "correction-end"]
    if memory:
        accepted += ["belief", "confirmation", "goal", "completion"]
    if pdlc:
        accepted += ["pr", "merge", "unrelated-pr"]
    user_members = [events[k]["event_id"] for k in accepted[:5]]
    pdlc_members = [events[k]["event_id"] for k in ["pr", "merge"]]
    return dict(
        events=events,
        accepted=accepted,
        user=user,
        memory=memory,
        pdlc=pdlc,
        user_session=sid + ":user",
        memory_session=sid + ":memory",
        pdlc_session=sid + ":pdlc",
        ids=dict(
            profile="profile:user:alice",
            positive=preference_id("positive"),
            negative=preference_id("negative"),
            entity="entity:ResetToken",
            belief="belief-" + digest(["Belief", "alice", "session", sid + ":memory", "expiry"]),
            goal="goal-" + digest(["Goal", "alice", "session", sid + ":memory", "implement"]),
            user_summary=(
                "summary-"
                + sid
                + ":user-"
                + hashlib.sha256("|".join(sorted(user_members)).encode()).hexdigest()[:12]
            ),
            user_episode="episode-" + digest([sid + ":user", sorted(user_members)]),
            pdlc_episode="episode-" + digest([sid + ":pdlc", sorted(pdlc_members)]),
            change="Change:packmatrix/main|7",
            unrelated="Change:packmatrix/unrelated|7",
            decision="Decision:" + hashlib.sha256(DECISION.encode()).hexdigest(),
        ),
    )


class Providers:
    """Only external model boundaries; no graph/storage writes or worker replacement."""

    def __init__(self, plan):
        self.plan = plan
        self.calls = dict(extraction=[], pack=[], summary=0)

    async def extract_from_session(self, **kwargs):
        self.calls["extraction"].append(
            dict(
                session=kwargs["session_id"], event_ids=[str(e.event_id) for e in kwargs["events"]]
            )
        )
        docs = kwargs["event_payloads"]
        polarity = (
            "negative"
            if any("no longer prefer" in (d.get("payload") or {}).get("content", "") for d in docs)
            else "positive"
        )
        return extraction(polarity)

    async def generate_text(self, prompt):
        self.calls["summary"] += 1
        return SUMMARY


class PackProvider:
    def __init__(self, providers):
        self.providers = providers

    async def generate_text(self, prompt):
        text = prompt.rpartition("<<<\n")[2].removesuffix("\n>>>")
        self.providers.calls["pack"].append(text)
        if "We decide: " + DECISION not in text:
            return json.dumps(dict(nodes=[], links=[]))
        return json.dumps(
            dict(
                nodes=[
                    dict(
                        ref="n1",
                        type="Decision",
                        statement=DECISION,
                        rationale="Bound reset-token lifetime",
                        confidence=0.7,
                        evidence=DECISION,
                    )
                ],
                links=[],
            )
        )


async def run(directory, bound, db, plan, config):
    path = directory / (config + ".json")
    record = dict(
        packs=bound.bundle.pack_identities,
        bundle_identity=bound.bundle.identity,
        processing=bound.bundle.processing,
        state="running",
        checks=[],
        requests=[],
        fixtures=plan,
        limitations=[
            "private sequential bound configurations; not concurrent tenant isolation",
            "frozen external provider outputs, not prose/model quality evaluation",
            "HTTP duplicates and User receipt replay, not general pending-retry recovery",
        ],
    )
    consumers, tasks, stores = [], [], []
    workers = {}
    server = server_task = None
    providers = Providers(plan)

    def save():
        record["providers"] = providers.calls
        durable_json(path, record)

    def check(name, passed, actual=None):
        record["checks"].append(dict(name=name, passed=bool(passed), actual=actual))
        save()
        if not passed:
            raise AssertionError(name)

    async def state():
        return await asyncio.to_thread(snapshot, db)

    def nodes(value):
        return {(label, key): json_value(props) for label, key, props in value["nodes"]}

    def physical_nodes():
        with db.snapshot() as snap:
            return [
                list(row[:2]) + list(row[3:])
                for row in snap.execute_sql("SELECT * FROM GraphNodes ORDER BY label, node_id")
            ]

    def edges(value):
        return {tuple(row[:5]) for row in value["edges"]}

    async def wait(predicate, description):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done():
                    await task
                    raise RuntimeError("worker exited before shutdown")
            value = await predicate()
            if value:
                return value
            await asyncio.sleep(0.3)
        raise TimeoutError(description)

    async def settled():
        async def ready():
            value = await state()
            lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
            return value if not value["pending"] and not any(lags) else None

        value = await wait(ready, "all five workers settle")
        check("five groups zero lag/pending/no DLQ", not value["dead_letters"])
        return value

    try:
        check(
            "verified empty application tables",
            not any(v["count"] for v in fingerprint(db).values()),
        )
        app = create_app(bound.settings(), bundle=bound.bundle)
        app.state.tenant_binding = bound
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                DemoAuthentication(app, bound, token=AUTH, roles=frozenset({"api", "admin"})),
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
                worker._llm_client = providers
            if kind == "pack_extraction":
                worker._model = PackProvider(providers)
            workers[kind] = worker
            consumers.append(worker)
            stores.append(store)
            tasks.append(asyncio.create_task(worker.run()))
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=45,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(route, payload=None, method="POST"):
                row = dict(method=method, route=route, input=payload, status=None)
                record["requests"].append(row)
                save()
                try:
                    response = await http.request(method, route, json=payload)
                    row.update(status=response.status_code, output=response.json())
                except BaseException as exc:
                    row["error"] = repr(exc)
                    save()
                    raise
                save()
                return response.status_code, row["output"]

            events, ids = plan["events"], plan["ids"]
            for key in plan["accepted"]:
                status, answer = await request("/v1/events", events[key])
                check("admitted " + key, status == 201, answer)
                # Keep explicit lifecycle phases, not race the correction with its predecessor.
                if key in {
                    "end",
                    "overlap",
                    "correction-end",
                    "belief",
                    "confirmation",
                    "goal",
                    "completion",
                    "merge",
                }:
                    await settled()
                    value = nodes(await state())
                    if key in {"end", "overlap"} and plan["user"]:
                        pref = value.get(("Preference", ids["positive"]), {})
                        check(
                            key + " preference distinct support once",
                            pref.get("observation_count") == 1
                            and pref.get("support_event_ids") == [events["preference"]["event_id"]],
                            pref,
                        )
            await settled()

            async def produced():
                value = await state()
                found = nodes(value)
                required = {("Entity", ids["entity"]), ("Summary", ids["user_summary"])}
                if plan["memory"]:
                    required |= {
                        ("Episode", ids["user_episode"]),
                        ("Belief", ids["belief"]),
                        ("Goal", ids["goal"]),
                    }
                    if plan["pdlc"]:
                        required.add(("Episode", ids["pdlc_episode"]))
                if plan["pdlc"]:
                    required |= {("Change", ids["change"]), ("Decision", ids["decision"])}
                return (
                    value
                    if required <= found.keys() and any(label == "Summary" for label, key in found)
                    else None
                )

            await wait(produced, "expected Entity/Summary and selected pack outputs")
            await settled()
            for worker in consumers:
                worker.stop()
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            check(
                "five actual workers join normally",
                not any(isinstance(x, BaseException) for x in outcomes),
                [repr(x) for x in outcomes],
            )
            if plan["user"]:
                before_replay = await state()
                prior = nodes(before_replay)
                replay, store = await _build_consumer(
                    "extraction", bound.settings(), tenant_binding=bound
                )
                stores.append(store)
                replay._llm_client = providers
                before_calls = len(providers.calls["extraction"])
                replay_before_fp = await asyncio.to_thread(fingerprint, db)
                await replay.process_message(
                    "receipt-replay", {"event_id": events["correction-end"]["event_id"]}
                )
                replay_after_fp = await asyncio.to_thread(fingerprint, db)
                after = nodes(await state())
                check(
                    "fresh applied receipt replay leaves every table unchanged",
                    replay_before_fp == replay_after_fp,
                    [replay_before_fp, replay_after_fp],
                )
                check(
                    "fresh User worker reuses frozen applied receipt",
                    len(providers.calls["extraction"]) == before_calls,
                )
                check(
                    "User receipt replay preserves all User outputs",
                    {
                        k: v
                        for k, v in prior.items()
                        if k[0] in {"UserProfile", "Preference", "Skill"}
                    }
                    == {
                        k: v
                        for k, v in after.items()
                        if k[0] in {"UserProfile", "Preference", "Skill"}
                    },
                )
            baseline = await state()
            record["processed_baseline"] = baseline
            values, relationships = nodes(baseline), edges(baseline)
            check(
                "exact accepted ledger IDs",
                {row[0] for row in baseline["events"]}
                == {events[key]["event_id"] for key in plan["accepted"]},
            )
            check(
                "one Event projection per accepted identity",
                {key for label, key in values if label == "Event"}
                == {events[key]["event_id"] for key in plan["accepted"]},
            )
            for key in plan["accepted"]:
                props = values[("Event", events[key]["event_id"])]
                check(
                    "accepted Event identity " + key,
                    all(
                        props.get(field) == events[key][field]
                        for field in [
                            "event_id",
                            "event_type",
                            "occurred_at",
                            "session_id",
                            "agent_id",
                            "trace_id",
                        ]
                    ),
                    props,
                )
                check(
                    "exact enrichment " + key,
                    props.get("keywords") == events[key]["event_type"].split(".")
                    and props.get("importance_score") in {6, 7, 8, 10},
                    dict(keywords=props.get("keywords"), importance=props.get("importance_score")),
                )
            for enabled, labels in [
                (plan["user"], {"UserProfile", "Preference", "Skill"}),
                (plan["memory"], {"Belief", "Goal", "Episode"}),
                (plan["pdlc"], {"Change", "Decision", "Constraint", "Lesson"}),
            ]:
                if not enabled:
                    check(
                        "disabled types absent " + str(sorted(labels)),
                        not (labels & {label for label, key in values}),
                    )
            if plan["user"]:
                check(
                    "exact User artifact identities",
                    {key for label, key in values if label == "UserProfile"} == {ids["profile"]}
                    and {key for label, key in values if label == "Preference"}
                    == {ids["positive"], ids["negative"]}
                    and not any(label == "Skill" for label, key in values),
                )
            if plan["pdlc"]:
                check(
                    "exact PDLC artifact identities",
                    {key for label, key in values if label == "Change"}
                    == {ids["change"], ids["unrelated"]}
                    and {key for label, key in values if label == "Decision"} == {ids["decision"]}
                    and not any(label in {"Constraint", "Lesson"} for label, key in values),
                )
            if not plan["user"]:
                check(
                    "User-off no receipts",
                    not any("user_extraction_receipt" in props for props in values.values()),
                )
            check(
                "pack model applicability",
                bool(providers.calls["pack"]) == plan["pdlc"],
                providers.calls["pack"],
            )
            if plan["user"]:
                positive, negative = (
                    values[("Preference", ids["positive"])],
                    values[("Preference", ids["negative"])],
                )
                check(
                    "correction exact old/new support",
                    positive["support_event_ids"] == [events["preference"]["event_id"]]
                    and negative["support_event_ids"] == [events["correction"]["event_id"]]
                    and positive["observation_count"] == negative["observation_count"] == 1,
                )
                check(
                    "correction predecessor and typed edge",
                    positive.get("superseded_by") == ids["negative"]
                    and ("Preference", ids["negative"], "SUPERSEDES", "Preference", ids["positive"])
                    in relationships,
                )
            if plan["memory"]:
                belief, goal = values[("Belief", ids["belief"])], values[("Goal", ids["goal"])]
                check(
                    "Belief exact confirmation count/revision/support",
                    belief.get("confirmation_count") == 2
                    and belief.get("state_revision") == 1
                    and set(belief.get("supporting_event_ids", []))
                    == {events[k]["event_id"] for k in ["belief", "confirmation"]},
                    belief,
                )
                check(
                    "Goal completed with exact support",
                    goal.get("status") == "completed"
                    and goal.get("state_revision") == 1
                    and set(goal.get("evidence_event_ids", []))
                    == {events[k]["event_id"] for k in ["goal", "completion"]},
                    goal,
                )
                check(
                    "no automatic Belief/Goal conversion",
                    {key for label, key in values if label == "Belief"} == {ids["belief"]}
                    and {key for label, key in values if label == "Goal"} == {ids["goal"]},
                )
                for kind, members in [("user", plan["accepted"][:5])] + (
                    [("pdlc", ["pr", "merge"])] if plan["pdlc"] else []
                ):
                    episode = values[("Episode", ids[kind + "_episode"])]
                    members = {events[k]["event_id"] for k in members}
                    check(
                        kind + " Episode exact membership and stored Summary",
                        episode.get("complete") is True
                        and set(episode.get("source_event_ids", [])) == members
                        and ("Summary", episode.get("summary_id")) in values,
                        episode,
                    )
                    check(
                        kind + " Episode typed membership/evidence",
                        all(
                            ("Episode", ids[kind + "_episode"], edge, "Event", eid) in relationships
                            for eid in members
                            for edge in ["CONTAINS", "DERIVED_FROM"]
                        ),
                    )
            if plan["pdlc"]:
                change = values[("Change", ids["change"])]
                check(
                    "PDLC merged state distinct from other repo",
                    change.get("status") == "merged"
                    and values[("Change", ids["unrelated"])].get("status") == "open",
                    change,
                )
                check(
                    "PDLC Change exact source evidence",
                    {
                        e[4]
                        for e in relationships
                        if e[:4] == ("Change", ids["change"], "DERIVED_FROM", "Event")
                    }
                    == {events[k]["event_id"] for k in ["pr", "merge"]},
                )
                check(
                    "pack Decision exact prose source",
                    (
                        "Decision",
                        ids["decision"],
                        "DERIVED_FROM",
                        "Event",
                        events["preference"]["event_id"],
                    )
                    in relationships,
                )
            expected_entity_sources = {events[k]["event_id"] for k in plan["accepted"][:5]}
            actual_entity_sources = {
                edge[1]
                for edge in relationships
                if edge[0] == "Event" and edge[2:] == ("REFERENCES", "Entity", ids["entity"])
            }
            check(
                "Entity exact session REFERENCES after repeated extraction",
                actual_entity_sources == expected_entity_sources,
                dict(
                    expected=sorted(expected_entity_sources), actual=sorted(actual_entity_sources)
                ),
            )
            check(
                "exact Entity IDs without normalized-name duplicate",
                {key for label, key in values if label == "Entity"}
                == ({ids["entity"], "user:alice"} if plan["user"] else {ids["entity"]}),
            )
            accepted_by_id = {events[k]["event_id"]: events[k] for k in plan["accepted"]}

            def outgoing(label, key, kind, target_label="Event"):
                return {e[4] for e in relationships if e[:4] == (label, key, kind, target_label)}

            def exact_evidence(label, key, sources):
                check(
                    label + " exact typed source set " + key,
                    outgoing(label, key, "DERIVED_FROM") == set(sources),
                    sorted(outgoing(label, key, "DERIVED_FROM")),
                )

            if plan["user"]:
                exact_evidence("UserProfile", ids["profile"], [events["preference"]["event_id"]])
                exact_evidence(
                    "Preference",
                    ids["positive"],
                    [events[k]["event_id"] for k in ["preference", "correction"]],
                )
                exact_evidence("Preference", ids["negative"], [events["correction"]["event_id"]])
                for key in ["end", "overlap", "correction-end"]:
                    props = values[("Event", events[key]["event_id"])]
                    receipt = props.get("user_extraction_receipt", {})
                    check(
                        "applied User receipt " + key,
                        receipt.get("status") == "applied"
                        and props.get("user_extraction_owner") == "user:alice",
                        receipt,
                    )
            if plan["memory"]:
                for label, key, sources in [
                    ("Belief", "belief", ["belief", "confirmation"]),
                    ("Goal", "goal", ["goal", "completion"]),
                ]:
                    exact_evidence(label, ids[key], [events[k]["event_id"] for k in sources])
                    artifact = values[(label, ids[key])]
                    check(
                        label + " stored owner/session/complete",
                        artifact.get("agent_id") == "alice"
                        and artifact.get("session_id") == plan["memory_session"]
                        and artifact.get("complete") is True,
                    )
                    for source_key in sources:
                        props = values[("Event", events[source_key]["event_id"])]
                        check(
                            "Memory source receipt " + source_key,
                            props.get("memory_status") == "applied"
                            and props.get("memory_subject_label") == label
                            and props.get("memory_subject_id") == ids[key]
                            and props.get("memory_expected_revision")
                            == (0 if source_key in {"confirmation", "completion"} else None),
                            props,
                        )
            if plan["pdlc"]:
                exact_evidence("Decision", ids["decision"], [events["preference"]["event_id"]])
            # Validate all legitimate intermediate Summary/Episode snapshots too.
            for (label, key), props in values.items():
                if label != "Summary":
                    continue
                members = outgoing("Summary", key, "SUMMARIZES")
                source_rows = [accepted_by_id[eid] for eid in members if eid in accepted_by_id]
                check(
                    "Summary accepted nonempty membership " + key,
                    bool(members) and len(source_rows) == len(members),
                )
                bounds = [
                    min(datetime.fromisoformat(e["occurred_at"]) for e in source_rows),
                    max(datetime.fromisoformat(e["occurred_at"]) for e in source_rows),
                ]
                scope, scope_id = props.get("scope"), props.get("scope_id")
                expected_id = (
                    "summary-"
                    + scope_id
                    + "-"
                    + hashlib.sha256("|".join(sorted(members)).encode()).hexdigest()[:12]
                )
                event_types = ", ".join(sorted({e["event_type"] for e in source_rows}))
                expected_content = (
                    f"{len(members)} events ({event_types}) from "
                    f"{bounds[0].isoformat()} to {bounds[-1].isoformat()}"
                    if scope == "agent"
                    else SUMMARY
                )
                check(
                    "Summary exact identity/count/range/content " + key,
                    key == expected_id
                    and props.get("event_count") == len(members)
                    and [datetime.fromisoformat(v) for v in props.get("time_range", [])] == bounds
                    and props.get("content") == expected_content,
                    props,
                )
                sessions = {e["session_id"] for e in source_rows}
                check(
                    "Summary scope owns its sources " + key,
                    (scope == "agent" and {e["agent_id"] for e in source_rows} == {scope_id})
                    or (scope == "session" and sessions == {scope_id})
                    or (
                        scope == "episode"
                        and len(sessions) == 1
                        and scope_id
                        == (
                            "episode-" + digest([next(iter(sessions)), sorted(members)])
                            if plan["memory"]
                            else next(iter(sessions)) + "-ep0"
                        )
                    ),
                )
            for (label, key), props in values.items():
                if label != "Episode":
                    continue
                members = set(props.get("source_event_ids", []))
                source_rows = [accepted_by_id[eid] for eid in members if eid in accepted_by_id]
                check(
                    "Episode accepted nonempty membership " + key,
                    bool(members) and len(source_rows) == len(members),
                )
                session = props.get("session_id")
                summary_id = (
                    "summary-"
                    + key
                    + "-"
                    + hashlib.sha256("|".join(sorted(members)).encode()).hexdigest()[:12]
                )
                summary = values.get(("Summary", summary_id), {})
                bounds = [
                    min(datetime.fromisoformat(e["occurred_at"]) for e in source_rows),
                    max(datetime.fromisoformat(e["occurred_at"]) for e in source_rows),
                ]
                check(
                    "Episode full stored snapshot valid " + key,
                    props.get("complete") is True
                    and key == "episode-" + digest([session, sorted(members)])
                    and props.get("event_count") == len(members)
                    and {e["session_id"] for e in source_rows} == {session}
                    and props.get("summary_id") == summary_id
                    and summary.get("scope") == "episode"
                    and summary.get("scope_id") == key
                    and [datetime.fromisoformat(props[f]) for f in ["start_time", "end_time"]]
                    == bounds,
                )
                for edge in ["CONTAINS", "DERIVED_FROM"]:
                    check(
                        "Episode exact " + edge + " " + key,
                        outgoing("Episode", key, edge) == members,
                    )
                check(
                    "Episode stored Summary exact membership " + key,
                    outgoing("Summary", summary_id, "SUMMARIZES") == members
                    and outgoing("Summary", summary_id, "SUMMARIZES", "Episode") == {key},
                )
            # After workers join, rejection and idempotency compare every application table.
            rejected = ["bad-memory", "bad-pdlc"]
            if not plan["memory"]:
                rejected += ["belief", "goal"]
            if not plan["pdlc"]:
                rejected += ["pr"]
            for key in rejected:
                before = await asyncio.to_thread(fingerprint, db)
                status, answer = await request("/v1/events", events[key])
                after = await asyncio.to_thread(fingerprint, db)
                check(
                    "reject " + key + " with no writes",
                    status == 422 and before == after,
                    dict(status=status, answer=answer, before=before, after=after),
                )
            for key in (
                ["end"]
                + (["confirmation"] if plan["memory"] else [])
                + (["merge"] if plan["pdlc"] else [])
            ):
                before = await asyncio.to_thread(fingerprint, db)
                status, answer = await request("/v1/events", events[key])
                after = await asyncio.to_thread(fingerprint, db)
                check(
                    "duplicate " + key + " leaves all tables unchanged",
                    status in {200, 201} and before == after,
                    dict(status=status, answer=answer),
                )

            accessed_ids = set()

            async def subgraph(intent, session, *, seed=None):
                status, answer = await request(
                    "/v1/query/subgraph",
                    dict(
                        query="Show " + intent + " for reset expiry",
                        intent=intent,
                        session_id=session,
                        agent_id="alice",
                        seed_nodes=seed,
                        max_nodes=100,
                        timeout_ms=30000,
                    ),
                )
                check("subgraph " + intent + " success", status == 200, answer)
                for node_id, node in answer.get("nodes", {}).items():
                    if node["node_type"] == "Event":
                        source = accepted_by_id.get(node_id, {})
                        provenance = node.get("provenance") or {}
                        check(
                            "public Event source identity " + node_id,
                            bool(source)
                            and all(
                                provenance.get(field) == source[field]
                                for field in ["event_id", "agent_id", "session_id", "trace_id"]
                            )
                            and node.get("attributes", {}).get("event_type")
                            == source.get("event_type"),
                        )
                        accessed_ids.add(node_id)
                check(
                    "subgraph receipts hidden",
                    "user_extraction_receipt" not in json.dumps(answer)
                    and "user_extraction_owner" not in json.dumps(answer),
                )
                check(
                    "no unrelated owner evidence in answer",
                    all(
                        n["provenance"].get("agent_id") == "alice"
                        for n in answer.get("nodes", {}).values()
                        if n.get("provenance")
                    ),
                    answer.get("meta"),
                )
                check(
                    "subgraph " + intent + " untruncated",
                    answer.get("meta", {}).get("truncated") is False,
                )
                return answer

            def public_evidence(answer, label, identity, sources, *, artifact_api=False):
                node = answer.get("nodes", {}).get(identity, {})
                provenance = node.get("provenance") or {}
                check(
                    "public " + label + " exact source binding " + identity,
                    provenance.get("event_id") in sources
                    and provenance.get("agent_id") == "alice"
                    and provenance.get("session_id")
                    == accepted_by_id[provenance["event_id"]]["session_id"],
                    node,
                )
                if artifact_api:
                    newest = max(
                        sources,
                        key=lambda eid: datetime.fromisoformat(accepted_by_id[eid]["occurred_at"]),
                    )
                    check(
                        "artifact API latest source provenance " + identity,
                        provenance.get("event_id") == newest
                        and provenance.get("source") == "spanner"
                        and provenance.get("trace_id") == accepted_by_id[newest]["trace_id"]
                        and provenance.get("global_position")
                        == values[("Event", newest)].get("global_position")
                        and datetime.fromisoformat(provenance["occurred_at"])
                        == datetime.fromisoformat(accepted_by_id[newest]["occurred_at"]),
                        provenance,
                    )
                    return
                actual = {
                    edge["target"]
                    for edge in answer.get("edges", [])
                    if edge["source"] == identity and edge["edge_type"] == "DERIVED_FROM"
                }
                check(
                    "public " + label + " exact evidence edges " + identity,
                    actual == set(sources),
                    sorted(actual),
                )

            before_reads_fp = await asyncio.to_thread(fingerprint, db)
            before_reads_physical = await asyncio.to_thread(physical_nodes)
            common = await subgraph(
                "what", plan["user_session"], seed=[events["preference"]["event_id"]]
            )
            check(
                "common Event and Entity retrievable",
                events["preference"]["event_id"] in common["nodes"]
                and ids["entity"] in common["nodes"],
            )
            status, profile = await request("/v1/users/user:alice/profile", method="GET")
            check("User API selection", status == (200 if plan["user"] else 404), profile)
            if plan["user"]:
                check(
                    "canonical profile",
                    profile.get("profile_id") == ids["profile"]
                    and profile.get("display_name") == "Alice",
                    profile,
                )
                status, prefs = await request("/v1/users/user:alice/preferences", method="GET")
                check(
                    "User API active correction only",
                    status == 200 and {p["preference_id"] for p in prefs} == {ids["negative"]},
                    prefs,
                )
                answer = await subgraph("personalize", plan["user_session"])
                check(
                    "personalization profile/current preference",
                    {ids["profile"], ids["negative"]} <= answer["nodes"].keys()
                    and ids["positive"] not in answer["nodes"],
                )
            if plan["memory"]:
                answer = await subgraph("beliefs", plan["memory_session"])
                check(
                    "retrieved Belief count/support",
                    answer["nodes"]
                    .get(ids["belief"], {})
                    .get("attributes", {})
                    .get("confirmation_count")
                    == 2,
                )
                public_evidence(
                    answer,
                    "Belief",
                    ids["belief"],
                    {events[k]["event_id"] for k in ["belief", "confirmation"]},
                )
                answer = await subgraph("when", plan["memory_session"])
                check(
                    "retrieved Goal completion",
                    answer["nodes"].get(ids["goal"], {}).get("attributes", {}).get("status")
                    == "completed",
                )
                public_evidence(
                    answer,
                    "Goal",
                    ids["goal"],
                    {events[k]["event_id"] for k in ["goal", "completion"]},
                )
                for kind, session in [("user", plan["user_session"])] + (
                    [("pdlc", plan["pdlc_session"])] if plan["pdlc"] else []
                ):
                    answer = await subgraph("when", session)
                    episode = ids[kind + "_episode"]
                    public_evidence(
                        answer,
                        "Episode",
                        episode,
                        set(values[("Episode", episode)]["source_event_ids"]),
                    )
                    check(
                        kind + " Episode and Summary retrievable",
                        episode in answer["nodes"]
                        and values[("Episode", episode)]["summary_id"] in answer["nodes"],
                    )
            if plan["pdlc"]:
                for label, key in [("Change", "change"), ("Decision", "decision")]:
                    status, answer = await request(
                        "/v1/query/artifacts",
                        dict(
                            query="trace this " + label.lower(),
                            intent="trace",
                            seed_node_ids=[ids[key]],
                        ),
                    )
                    check(
                        "artifact " + label + " retrieval",
                        status == 200
                        and ids[key] in answer.get("nodes", {})
                        and ids["unrelated"] not in answer.get("nodes", {}),
                        answer,
                    )
                    public_evidence(
                        answer,
                        label,
                        ids[key],
                        {
                            events[k]["event_id"]
                            for k in (["pr", "merge"] if label == "Change" else ["preference"])
                        },
                        artifact_api=True,
                    )
                    check(
                        "artifact " + label + " provenance retained",
                        bool(answer.get("nodes", {}).get(ids[key], {}).get("provenance")),
                        answer.get("nodes", {}).get(ids[key]),
                    )
            # Read effects are restricted to access metadata on returned Event nodes.
            final = await state()
            after_reads_fp = await asyncio.to_thread(fingerprint, db)
            after_reads_physical = await asyncio.to_thread(physical_nodes)
            check(
                "read physical node columns unchanged",
                before_reads_physical == after_reads_physical,
                [before_reads_physical, after_reads_physical],
            )
            check(
                "all six non-node tables unchanged by reads",
                {k: v for k, v in before_reads_fp.items() if k != "GraphNodes"}
                == {k: v for k, v in after_reads_fp.items() if k != "GraphNodes"},
                [before_reads_fp, after_reads_fp],
            )
            final_nodes = nodes(final)
            check("read membership stable", values.keys() == final_nodes.keys())
            for key, props in values.items():
                actual = final_nodes[key]
                ignored = (
                    {"access_count", "last_accessed_at"}
                    if key[0] == "Event" and key[1] in accessed_ids
                    else set()
                )
                check(
                    "reads preserve " + str(key),
                    {k: v for k, v in props.items() if k not in ignored}
                    == {k: v for k, v in actual.items() if k not in ignored},
                )
            check(
                "read ledger/edges/deliveries unchanged",
                {k: v for k, v in baseline.items() if k != "nodes"}
                == {k: v for k, v in final.items() if k != "nodes"},
            )
            record["final_snapshot"] = final
            before = await asyncio.to_thread(fingerprint, db)
            await asyncio.sleep(1)
            after = await asyncio.to_thread(fingerprint, db)
            check("all tables stable after joins and reads", before == after, [before, after])
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
        if errors:
            record["state"] = "failed: uncertain shutdown"
        save()
        if errors:
            raise RuntimeError("uncertain shutdown; reuse prohibited")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-record", type=Path, required=True)
    parser.add_argument(
        "--configurations", nargs="+", choices=CONFIGURATIONS, default=CONFIGURATIONS
    )
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
    plans = {config: fixtures(args.run_id, config) for config in args.configurations}
    durable_json(
        directory / "manifest.json",
        dict(
            scenarios=SCENARIOS,
            fixtures=plans,
            target=TARGET,
            configurations=args.configurations,
            providers=dict(
                positive=extraction("positive"),
                negative=extraction("negative"),
                summary=SUMMARY,
                decision=DECISION,
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
        for config in args.configurations:
            settings = settings_for(args.run_id, config, target_database=TARGET.rsplit("/", 1)[1])
            settings.decay.reflection_threshold = 5
            settings.decay.reconsolidation_interval_hours = 20 / 3600
            bound = TenantBinding.from_settings(
                "combination-" + config,
                args.run_id + config,
                previous["owner"][0][3] + 1,
                settings,
                engine_revision="pack-combination-v1",
            )
            export = directory / (config + "-previous-export.json")
            frozen, exported, digest_value = await asyncio.to_thread(
                freeze_and_export, db, previous["owner"][0], previous["fingerprints"], export
            )
            await asyncio.to_thread(reset_to, db, frozen, exported, digest_value, export, bound)
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
