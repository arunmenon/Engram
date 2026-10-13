"""Bounded User acceptance on the authorized assessment database.

Real authenticated HTTP, all five real workers, and Spanner storage/read APIs.
Primary prose uses the real configured LLM. Deterministic correction/restart
probes replace only the external extraction provider and label that boundary.
No application data is inserted or repaired outside Engram. Final data retained.
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
from context_graph.api.routes.artifacts import ArtifactQueryRequest
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer
from context_graph.worker.consolidation import ConsolidationConsumer

DB = TARGET.rsplit("/", 1)[1]


def preference_id(owner, polarity, context="support"):
    # Independent public identity oracle, never derived from a response.
    values = [
        "user:" + owner,
        "communication",
        "answer-length",
        "global",
        None,
        context,
        polarity,
        None,
    ]
    return (
        "preference:"
        + hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def preference(polarity="positive", context="support"):
    return dict(
        category="communication",
        key="answer-length",
        polarity=polarity,
        strength=0.8,
        confidence=0.9,
        source="explicit",
        context=context,
        source_quote="I no longer prefer short answers"
        if polarity == "negative"
        else "short answers",
    )


class ProbeProvider:
    """Only controlled sessions use fixed provider output; real sessions delegate."""

    def __init__(self, real, calls):
        self.real, self.calls = real, calls

    async def extract_from_session(self, **kwargs):
        sid = kwargs["session_id"]
        self.calls[sid] = self.calls.get(sid, 0) + 1
        if ":probe:" not in sid:
            return await self.real.extract_from_session(**kwargs)
        documents = kwargs["event_payloads"]
        return next(
            (
                doc["payload"]["probe_result"]
                for doc in reversed(documents)
                if "probe_result" in (doc.get("payload") or {})
            ),
            {},
        )


class InterruptApply:
    """External fault injection around the real transaction, never a repair."""

    def __init__(self, actual, faults, hits):
        self.actual, self.faults, self.hits = actual, faults, hits

    async def get_user_extraction(self, trigger):
        return await self.actual.get_user_extraction(trigger)

    async def prepare_user_extraction(self, trigger, candidate):
        return await self.actual.prepare_user_extraction(trigger, candidate)

    async def apply_user_extraction(self, trigger):
        key = str(trigger.event_id)
        mode = self.faults.pop(key, None)
        if mode == "before":
            self.hits[key] = mode
            raise RuntimeError("controlled interruption after prepare, before apply")
        result = await self.actual.apply_user_extraction(trigger)
        if mode == "after":
            self.hits[key] = mode
            raise RuntimeError("controlled interruption after commit, before ACK")
        return result


async def run_config(run, directory, config, bound, db):
    path = directory / (config + ".json")
    record = dict(
        config=config,
        state="running",
        checks=[],
        requests=[],
        provider_calls={},
        fault_hits={},
        limitations=[
            "private bound tenant; no concurrent tenant isolation claim",
            "development unevaluated gate",
            "fixed provider only for labeled correction/restart probes",
            "enrichment ordering is separate scope",
        ],
    )
    consumers, tasks, stores, faults = [], [], [], {}
    server = server_task = None

    def save():
        durable_json(path, record)

    def check(name, ok, detail=None):
        record["checks"].append(dict(name=name, status="PASS" if ok else "FAIL", detail=detail))
        save()
        if not ok:
            raise AssertionError(name)

    def event(key, kind="observation.input", *, owner="alice", sid=None, payload=None):
        return dict(
            event_id=str(uuid5(NAMESPACE_URL, run + config + key)),
            event_type=kind,
            occurred_at=datetime.now(UTC).isoformat(),
            session_id=sid or run + ":real:" + owner,
            agent_id=owner,
            trace_id=run,
            payload_ref="user-demo:" + key,
            payload=payload or {},
        )

    def nodes(state):
        return {(label, key): json_value(props) for label, key, props in state["nodes"]}

    def edges(state):
        return {(a, b, rel, c, d): json_value(props) for a, b, rel, c, d, props in state["edges"]}

    async def start_extractor():
        worker, store = await _build_consumer("extraction", bound.settings(), tenant_binding=bound)
        worker._llm_client = ProbeProvider(worker._llm_client, record["provider_calls"])
        worker._user_extraction_store = InterruptApply(
            worker._user_extraction_store, faults, record["fault_hits"]
        )
        consumers.append(worker)
        stores.append(store)
        tasks.append(asyncio.create_task(worker.run()))
        return worker, store, tasks[-1]

    async def quiesce():
        # Healthy-path coordination only: wait for a complete timer cycle, then
        # prevent a new one while real workers stop. Never cancel an SDK await.
        lock = next(
            (
                worker._consolidation_lock
                for worker in consumers
                if isinstance(worker, ConsolidationConsumer)
            ),
            None,
        )
        if lock is not None:
            await lock.acquire()
        try:
            for worker in consumers:
                worker.stop()
            joined = await asyncio.gather(*tasks, return_exceptions=True)
            return [type(result).__name__ for result in joined if isinstance(result, BaseException)]
        finally:
            if lock is not None:
                lock.release()

    async def settled():
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done() and not task.cancelled():
                    await task
            active = [c for c in consumers if not c._stopped]
            lags = await asyncio.gather(*(c._subscription.lag() for c in active))
            state = await asyncio.to_thread(snapshot, db)
            if len(active) == 5 and not state["pending"] and all(lag == 0 for lag in lags):
                check("five workers settled without dead letters", not state["dead_letters"], lags)
                return state
            await asyncio.sleep(0.5)
        raise TimeoutError("all five workers did not settle within 180 seconds")

    save()
    try:
        check("empty verified starting data", not any(v["count"] for v in fingerprint(db).values()))
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
        check("authenticated HTTP app ready", server.started)
        for kind in VALID_CONSUMERS:
            if kind == "extraction" and config != "pdlc":
                extractor, extraction_store, extraction_task = await start_extractor()
                continue
            worker, store = await _build_consumer(kind, bound.settings(), tenant_binding=bound)
            consumers.append(worker)
            stores.append(store)
            tasks.append(asyncio.create_task(worker.run()))
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=40,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(method, route, body=None):
                entry = dict(method=method, route=route, input=body, status=None)
                record["requests"].append(entry)
                save()
                try:
                    response = await http.request(method, route, json=body)
                    answer = response.json()
                except BaseException as exc:
                    entry["error"] = repr(exc)
                    save()
                    raise
                entry.update(status=response.status_code, answer=answer)
                save()
                return response.status_code, answer

            async def send(body):
                status, answer = await request("POST", "/v1/events", body)
                check("admitted " + body["payload_ref"], status == 201, answer)

            async def user_read(owner, family):
                status, answer = await request("GET", f"/v1/users/user:{owner}/{family}")
                check("User API " + owner + " " + family, status == 200, answer)
                return answer

            async def query(body):
                status, answer = await request("POST", "/v1/query/subgraph", body)
                check("retrieval API responds", status == 200, answer)
                check(
                    "private receipts hidden from retrieval",
                    "user_extraction_receipt" not in json.dumps(answer)
                    and "user_extraction_owner" not in json.dumps(answer),
                )
                return answer

            if config == "pdlc":
                observation = event(
                    "disabled",
                    payload={
                        "content": (
                            "My name is Alice. I prefer short answers. "
                            "I am interested in Rust development."
                        )
                    },
                )
                end = event("disabled-end", "system.session_end")
                pr = event(
                    "pdlc",
                    "pdlc.change.created",
                    payload={"repo": "user/control", "number": 7, "title": "User-off control"},
                )
                for body in (observation, end, pr):
                    await send(body)
                state = await settled()
                values = nodes(state)
                check(
                    "User disabled produces no User artifacts or receipts",
                    not ({"UserProfile", "Preference", "Skill"} & {label for label, _ in values})
                    and not any("user_extraction_receipt" in p for p in values.values()),
                )
                check("domain Change preserved", ("Change", "Change:user/control|7") in values)
                artifact_status, artifacts = await request(
                    "POST",
                    "/v1/query/artifacts",
                    dict(
                        query="trace user/control#7",
                        intent="trace",
                        seed_node_ids=["Change:user/control|7"],
                    ),
                )
                check(
                    "User-off Change retrievable through artifact API",
                    artifact_status == 200
                    and "Change:user/control|7" in artifacts.get("nodes", {}),
                    artifacts,
                )
                answer = await query(
                    dict(
                        query="event " + observation["event_id"],
                        session_id=observation["session_id"],
                        agent_id="alice",
                        seed_nodes=[observation["event_id"]],
                        intent="what",
                        timeout_ms=30000,
                    )
                )
                check(
                    "core Event still retrievable with User off",
                    observation["event_id"] in answer["nodes"],
                )
            else:
                # Real model: semantic expectations declared here before sending any input.
                primary = event(
                    "real-alice",
                    payload={
                        "content": (
                            "My name is Alice. I am a software engineer. "
                            "I prefer short answers. I am interested in Rust language development."
                        )
                    },
                )
                end = event("real-alice-end", "system.session_end")
                await send(primary)
                await send(end)
                state = await settled()
                values = nodes(state)
                relationships = edges(state)
                check(
                    "User writes preserve shared Entity timestamp chronology",
                    all(
                        datetime.fromisoformat(p["last_seen"])
                        >= datetime.fromisoformat(p["first_seen"])
                        for (label, key), p in values.items()
                        if label == "Entity" and p.get("first_seen") and p.get("last_seen")
                    ),
                )
                profile = await user_read("alice", "profile")
                check(
                    "real LLM canonical Alice profile",
                    profile.get("profile_id") == "profile:user:alice"
                    and profile.get("display_name", "").startswith("Alice"),
                )
                receipt = values[("Event", end["event_id"])]["user_extraction_receipt"]
                quoted_short_ids = {
                    p["preference_id"]
                    for p in receipt["result"]["preferences"]
                    if "short answers" in p["source_quote"].lower() and p["polarity"] == "positive"
                }
                prefs = await user_read("alice", "preferences")
                check(
                    "real LLM produces quoted short-answer preference",
                    any(
                        p["preference_id"] in quoted_short_ids
                        and p.get("category") == "communication"
                        and p.get("support_event_ids") == [primary["event_id"]]
                        for p in prefs
                    ),
                    prefs,
                )
                interests = await user_read("alice", "interests")
                check(
                    "real LLM attaches Rust interest",
                    any("rust" in p.get("name", "").lower() for p in interests),
                    interests,
                )
                rust = [p["entity_id"] for p in interests if "rust" in p.get("name", "").lower()]
                check(
                    "interest evidence references only actual observation",
                    all(
                        {
                            edge[4]
                            for edge in relationships
                            if edge[:3] == ("Entity", key, "DERIVED_FROM")
                        }
                        == {primary["event_id"]}
                        for key in rust
                    ),
                )
                check(
                    "profile same identity through composed graph read",
                    await app.state.stores.pack_reads.get_user_profile("user:alice") == profile,
                )
                answer = await query(
                    dict(
                        query="How does Alice prefer answers?",
                        session_id=primary["session_id"],
                        agent_id="alice",
                        intent="personalize",
                        max_depth=3,
                        timeout_ms=30000,
                    )
                )
                check(
                    "personalization includes canonical profile and preference",
                    "profile:user:alice" in answer["nodes"]
                    and any(p["preference_id"] in answer["nodes"] for p in prefs),
                )
                before = {
                    k: p
                    for k, p in values.items()
                    if k[0] in {"UserProfile", "Preference", "Skill"}
                }
                status, _ = await request("POST", "/v1/events", end)
                check("exact accepted trigger redelivery", status in (200, 201))
                state = await settled()
                check(
                    "exact retry changes no User artifacts",
                    {
                        k: p
                        for k, p in nodes(state).items()
                        if k[0] in {"UserProfile", "Preference", "Skill"}
                    }
                    == before,
                )
                # Controlled sessions isolate storage/worker correctness from model variability.
                owner = "probe-alice"
                sid = run + ":probe:alice"
                source = event(
                    "probe-first",
                    owner=owner,
                    sid=sid,
                    payload={
                        "content": (
                            "I prefer short answers. I know Python. "
                            "I am interested in RetryTopic development."
                        ),
                        "probe_result": {
                            "preferences": [preference()],
                            "skills": [
                                dict(
                                    category="programming_language",
                                    name="Python",
                                    proficiency=0.8,
                                    confidence=0.9,
                                    source="declared",
                                    source_quote="I know Python",
                                )
                            ],
                            "interests": [
                                dict(
                                    entity_name="RetryTopic",
                                    entity_type="concept",
                                    weight=0.8,
                                    source="explicit",
                                    source_quote="interested in RetryTopic development",
                                )
                            ],
                        },
                    },
                )
                trigger = event("probe-first-end", "system.session_end", owner=owner, sid=sid)
                faults[trigger["event_id"]] = "before"
                await send(source)
                await send(trigger)

                async def interrupted(body, status):
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        state = await asyncio.to_thread(snapshot, db)
                        props = nodes(state).get(("Event", body["event_id"]), {})
                        receipt = props.get("user_extraction_receipt", {})
                        if (
                            body["event_id"] in record["fault_hits"]
                            and receipt.get("status") == status
                            and any(row[1] == body["event_id"] for row in state["pending"])
                        ):
                            return state
                        await asyncio.sleep(0.5)
                    raise TimeoutError("injected checkpoint was not observed")

                async def restart():
                    nonlocal extractor, extraction_store, extraction_task
                    extractor.stop()
                    await extraction_task
                    await extraction_store.close()
                    extractor, extraction_store, extraction_task = await start_extractor()

                state = await interrupted(trigger, "prepared")
                positive = preference_id(owner, "positive")
                check(
                    "prepared interruption has no User preference",
                    ("Preference", positive) not in nodes(state),
                )
                record["prepared_checkpoint"] = state
                save()
                await restart()
                state = await settled()
                check(
                    "restart uses first provider result exactly once",
                    record["provider_calls"][sid] == 1,
                )
                first = await user_read(owner, "preferences")
                check(
                    "prepared restart has exact preference and source count",
                    len(first) == 1
                    and first[0]["preference_id"] == positive
                    and first[0]["observation_count"] == 1
                    and first[0]["support_event_ids"] == [source["event_id"]],
                )
                overlap = event("overlap-end", "system.session_end", owner=owner, sid=sid)
                faults[overlap["event_id"]] = "after"
                await send(overlap)
                state = await interrupted(overlap, "applied")
                check(
                    "committed before ACK still has one distinct support",
                    nodes(state)[("Preference", positive)]["observation_count"] == 1,
                )
                record["committed_checkpoint"] = state
                save()
                await restart()
                await settled()
                check(
                    "after-commit restart makes no new provider call",
                    record["provider_calls"][sid] == 2,
                )
                current = await user_read(owner, "preferences")
                check(
                    "overlapping extraction prefix counts support once",
                    current[0]["observation_count"] == 1
                    and current[0]["support_event_ids"] == [source["event_id"]],
                )
                retry_interests = await user_read(owner, "interests")
                retry_skills = await user_read(owner, "skills")
                check(
                    "worker replay preserves one attached interest and one owned Skill",
                    len(retry_interests) == 1
                    and retry_interests[0]["entity_id"] == "entity:RetryTopic"
                    and len(retry_skills) == 1
                    and retry_skills[0]["support_event_ids"] == [source["event_id"]],
                )
                state = await asyncio.to_thread(snapshot, db)
                check(
                    "replayed interest exact provenance",
                    {
                        edge[4]
                        for edge in edges(state)
                        if edge[:3] == ("Entity", "entity:RetryTopic", "DERIVED_FROM")
                    }
                    == {source["event_id"]},
                )
                other_context = event(
                    "reviews",
                    owner=owner,
                    sid=run + ":probe:reviews",
                    payload={
                        "content": "short answers",
                        "probe_result": {"preferences": [preference(context="reviews")]},
                    },
                )
                await send(other_context)
                await send(
                    event(
                        "reviews-end",
                        "system.session_end",
                        owner=owner,
                        sid=other_context["session_id"],
                    )
                )
                await settled()
                correction = event(
                    "correction",
                    owner=owner,
                    sid=sid,
                    payload={
                        "content": "I no longer prefer short answers",
                        "probe_result": {"preferences": [preference("negative")]},
                        "preference_corrections": [
                            dict(
                                previous_preference_id=positive,
                                replacement_key="answer-length",
                                replacement_polarity="negative",
                                context="support",
                            )
                        ],
                    },
                )
                await send(correction)
                await send(event("correction-end", "system.session_end", owner=owner, sid=sid))
                state = await settled()
                negative = preference_id(owner, "negative")
                review = preference_id(owner, "positive", "reviews")
                current = await user_read(owner, "preferences")
                check(
                    "explicit correction preserves unrelated context",
                    {p["preference_id"] for p in current} == {negative, review},
                )
                values = nodes(state)
                relationships = edges(state)
                check(
                    "predecessor history and correction evidence retained",
                    values[("Preference", positive)]["superseded_by"] == negative
                    and ("Preference", negative, "SUPERSEDES", "Preference", positive)
                    in relationships
                    and ("Preference", positive, "DERIVED_FROM", "Event", correction["event_id"])
                    in relationships,
                )
                check(
                    "correction exact support and preserved predecessor support",
                    values[("Preference", negative)]["support_event_ids"]
                    == [correction["event_id"]]
                    and values[("Preference", positive)]["support_event_ids"]
                    == [source["event_id"]]
                    and values[("Preference", review)]["support_event_ids"]
                    == [other_context["event_id"]],
                )
                check(
                    "one declared correction successor edge",
                    {
                        e
                        for e in relationships
                        if e[2] == "SUPERSEDES" and e[3:] == ("Preference", positive)
                    }
                    == {("Preference", negative, "SUPERSEDES", "Preference", positive)},
                )
                later = event(
                    "later",
                    owner=owner,
                    sid=sid,
                    payload={"content": "No new preference today.", "probe_result": {}},
                )
                await send(later)
                await send(event("later-end", "system.session_end", owner=owner, sid=sid))
                await settled()
                check(
                    "later trigger does not reinterpret prior correction",
                    {p["preference_id"] for p in await user_read(owner, "preferences")}
                    == {negative, review},
                )
                bob = event(
                    "probe-bob",
                    owner="probe-bob",
                    sid=run + ":probe:bob",
                    payload={
                        "content": "My name is Bob. I prefer short answers.",
                        "probe_result": {
                            "preferences": [preference()],
                            "persona": {"name": "Bob", "source_quote": "My name is Bob"},
                        },
                    },
                )
                await send(bob)
                await send(
                    event(
                        "probe-bob-end",
                        "system.session_end",
                        owner="probe-bob",
                        sid=bob["session_id"],
                    )
                )
                await settled()
                bob_prefs = await user_read("probe-bob", "preferences")
                check(
                    "other owner positively retrievable and excluded from Alice",
                    {p["preference_id"] for p in bob_prefs}
                    == {preference_id("probe-bob", "positive")}
                    and all(
                        p.get("user_id") == "user:" + owner
                        for p in await user_read(owner, "preferences")
                    ),
                )
                bob_profile = await user_read("probe-bob", "profile")
                check(
                    "second owner canonical profile",
                    bob_profile["profile_id"] == "profile:user:probe-bob"
                    and bob_profile["display_name"] == "Bob",
                )
                bob_answer = await query(
                    dict(
                        query="How does Bob prefer answers?",
                        session_id=bob["session_id"],
                        agent_id="probe-bob",
                        intent="personalize",
                        max_depth=3,
                        timeout_ms=30000,
                    )
                )
                check(
                    "second owner personalization positive",
                    "profile:user:probe-bob" in bob_answer["nodes"]
                    and preference_id("probe-bob", "positive") in bob_answer["nodes"],
                )
                alice_answer = await query(
                    dict(
                        query="How does Alice prefer answers?",
                        session_id=primary["session_id"],
                        agent_id="alice",
                        intent="personalize",
                        max_depth=3,
                        timeout_ms=30000,
                    )
                )
                check(
                    "second owner excluded from Alice personalization",
                    "profile:user:probe-bob" not in alice_answer["nodes"]
                    and preference_id("probe-bob", "positive") not in alice_answer["nodes"],
                )
                export = await user_read(owner, "data-export")
                check(
                    "User export includes applied frozen receipts",
                    bool(export.get("extraction_receipts"))
                    and all(r["status"] == "applied" for r in export["extraction_receipts"]),
                )
                state = await settled()
                values = nodes(state)
                check(
                    "every extraction trigger receipt is applied",
                    all(
                        p["user_extraction_receipt"]["status"] == "applied"
                        for p in values.values()
                        if "user_extraction_receipt" in p
                    ),
                )
                submitted = {
                    r["input"]["event_id"]: r["input"]
                    for r in record["requests"]
                    if r["route"] == "/v1/events" and r["status"] in (200, 201)
                }
                expected_artifacts = {}
                for (label, trigger_id), props in values.items():
                    if label != "Event" or "user_extraction_receipt" not in props:
                        continue
                    receipt = props["user_extraction_receipt"]
                    owner_id = "user:" + submitted[trigger_id]["agent_id"]
                    check(
                        "receipt owner matches submitted trigger " + trigger_id,
                        receipt["owner"] == owner_id,
                    )
                    outputs = [("Preference", p) for p in receipt["result"]["preferences"]]
                    outputs += [("Skill", p) for p in receipt["result"]["skills"]]
                    if receipt["result"]["persona"]:
                        outputs.append(("UserProfile", receipt["result"]["persona"]))
                    for family, item in outputs:
                        quote = " ".join(item["source_quote"].lower().split())
                        supports = {
                            source_id
                            for source_id in receipt["input_event_ids"]
                            if quote
                            and quote
                            in " ".join(
                                " ".join(
                                    str(submitted[source_id]["payload"].get(field) or "")
                                    for field in ("content", "input", "output")
                                )
                                .lower()
                                .split()
                            )
                        }
                        check(
                            "receipt quoted support independently resolved " + trigger_id + family,
                            bool(supports) and supports == set(item["support_event_ids"]),
                        )
                        if family == "UserProfile":
                            key = "profile:" + owner_id
                        else:
                            fields = (
                                [
                                    "category",
                                    "key",
                                    "scope",
                                    "scope_id",
                                    "context",
                                    "polarity",
                                    "about_entity",
                                ]
                                if family == "Preference"
                                else ["category", "name"]
                            )
                            encoded = json.dumps(
                                [owner_id, *[item.get(field) for field in fields]],
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode()
                            key = family.lower() + ":" + hashlib.sha256(encoded).hexdigest()
                            check(
                                "receipt identity independently resolved " + key,
                                item[family.lower() + "_id"] == key,
                            )
                        expected = expected_artifacts.setdefault(
                            (family, key), {"owner": owner_id, "sources": set()}
                        )
                        expected["sources"].update(supports)
                actual_artifacts = {
                    key: props
                    for key, props in values.items()
                    if key[0] in {"UserProfile", "Preference", "Skill"}
                }
                check(
                    "exact artifact set from frozen receipts and submitted inputs",
                    set(actual_artifacts) == set(expected_artifacts),
                )
                relationships = edges(state)
                for (family, key), expected in expected_artifacts.items():
                    props = actual_artifacts[(family, key)]
                    expected_sources = expected["sources"]
                    actual_sources = {
                        edge[4]
                        for edge in relationships
                        if edge[:3] == (family, key, "DERIVED_FROM")
                        and relationships[edge].get("method") != "declared_correction"
                    }
                    check(
                        "independent exact support/count audit " + key,
                        actual_sources == expected_sources == set(props["support_event_ids"])
                        and (
                            family != "Preference"
                            or props["observation_count"] == len(expected_sources)
                        ),
                    )
                    owner_edge = {
                        "UserProfile": "HAS_PROFILE",
                        "Preference": "HAS_PREFERENCE",
                        "Skill": "HAS_SKILL",
                    }[family]
                    actual_owners = {
                        edge[1] for edge in relationships if edge[2:] == (owner_edge, family, key)
                    }
                    check(
                        "independent exact owner audit " + key,
                        actual_owners == {expected["owner"]}
                        and props["user_id"] == expected["owner"],
                    )
                record["expected_user_artifacts"] = {
                    family + ":" + key: {
                        "owner": expected["owner"],
                        "sources": sorted(expected["sources"]),
                    }
                    for (family, key), expected in expected_artifacts.items()
                }
                admitted = {
                    r["input"]["event_id"]
                    for r in record["requests"]
                    if r["route"] == "/v1/events" and r["status"] in (200, 201)
                }
                check(
                    "exact admitted ledger membership",
                    {row[0] for row in state["events"]} == admitted,
                )
                expected_triggers = {
                    r["input"]["event_id"]
                    for r in record["requests"]
                    if r["route"] == "/v1/events"
                    and r["status"] in (200, 201)
                    and r["input"]["event_type"] == "system.session_end"
                }
                check(
                    "exact complete trigger receipt coverage",
                    {
                        key
                        for (label, key), props in values.items()
                        if label == "Event" and "user_extraction_receipt" in props
                    }
                    == expected_triggers,
                )
                if config == "user-memory":
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        state = await asyncio.to_thread(snapshot, db)
                        values = nodes(state)
                        if any(
                            label == "Episode" and p.get("session_id") == sid and p.get("complete")
                            for (label, key), p in values.items()
                        ):
                            break
                        await asyncio.sleep(1)
                    check(
                        "core Summary and Memory Episode coexist with User",
                        "Summary" in {label for label, _ in values}
                        and any(
                            label == "Episode" and p.get("session_id") == sid and p.get("complete")
                            for (label, key), p in values.items()
                        ),
                    )
                # Quiesce real workers before the whole-database rejection oracle.
                # Timed consolidation is otherwise allowed to write unrelated rows.
                await settled()
                errors = await quiesce()
                check("healthy workers quiesced without canceled SDK work", not errors, errors)
                invalid = event("invalid")
                invalid.pop("session_id")
                before_invalid = await asyncio.to_thread(fingerprint, db)
                status, _ = await request("POST", "/v1/events", invalid)
                after_invalid = await asyncio.to_thread(fingerprint, db)
                record["invalid_before_fingerprints"] = before_invalid
                record["invalid_after_fingerprints"] = after_invalid
                check(
                    "invalid envelope produces no writes with workers quiesced",
                    status == 422 and before_invalid == after_invalid,
                )
            record["final_snapshot"] = await asyncio.to_thread(snapshot, db)
            record["state"] = "passed"
            save()
    except BaseException as exc:
        record.update(state="failed", error=repr(exc))
        save()
        raise
    finally:
        quiesce_errors = await quiesce()
        record["shutdown_errors"] = quiesce_errors + await stop_demo(
            consumers, tasks, stores, server, server_task
        )
        record["retained_snapshot"] = await asyncio.to_thread(snapshot, db)
        save()
        if record["shutdown_errors"]:
            record["state"] = "failed shutdown; no reset permitted"
            save()
            raise RuntimeError("Unclean shutdown; refuse reset")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--previous-record", type=Path, required=True)
    parser.add_argument(
        "--configurations",
        nargs="+",
        choices=["user", "user-memory", "pdlc"],
        default=["user", "user-memory", "pdlc"],
    )
    args = parser.parse_args()
    # Validate the fixture against the real public contract before any cloud work.
    ArtifactQueryRequest.model_validate(
        dict(query="trace user/control#7", intent="trace", seed_node_ids=["Change:user/control|7"])
    )
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("Unsafe run id")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    if directory.exists():
        raise ValueError("Refuse evidence overwrite")
    previous = json.loads(args.previous_record.read_text())
    if previous["database"] != TARGET:
        raise ValueError("Wrong database")
    directory.mkdir()
    sources = [*ROOT.glob("src/**/*.py"), *ROOT.glob("src/**/*.yaml"), *ROOT.glob("scripts/*.py")]
    durable_json(
        directory / "source-hashes.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(sources)
        },
    )
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
            settings = settings_for(args.run_id, config, target_database=DB)
            settings.decay.reflection_threshold = 5
            settings.decay.reconsolidation_interval_hours = 20 / 3600
            durable_json(
                directory / (config + "-test-settings.json"),
                {
                    "reflection_threshold": 5,
                    "reconsolidation_interval_seconds": 20,
                    "extraction_mid_session_interval": (
                        settings.consumer.extraction_mid_session_interval
                    ),
                },
            )
            bound = TenantBinding.from_settings(
                "user-" + config,
                args.run_id + "-" + config,
                previous["owner"][0][3] + 1,
                settings,
                engine_revision="user-attachment-v1",
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
                    owner=await asyncio.to_thread(read_owner, db),
                    fingerprints=await asyncio.to_thread(fingerprint, db),
                    database=TARGET,
                )
                durable_json(directory / (config + "-retained.json"), previous)
    finally:
        await asyncio.to_thread(close_database, db)
        spanner.Client = original


if __name__ == "__main__":
    asyncio.run(main())
