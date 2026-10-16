"""Real-provider pilot entry checkpoint; append-only, two already-owned databases.

This first stage covers A-01/A-06 and B02/B06 components plus shared routing,
retry and role probes. It does not claim the entire 49-journey pilot passed.
All business writes and reads use authenticated public Engram HTTP. No reset,
rebind, frozen model, direct artifact insert, or cleanup is performed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import litellm
import structlog
import uvicorn
from engram_experiment_support import durable_json, fingerprint, read_owner, snapshot, stop_demo
from engram_pilot_completion_fixtures import declared_dead_letters
from engram_pilot_model_transition import binding_from_baseline
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.api.routes.artifacts import ArtifactQueryRequest
from context_graph.api.tenants import create_tenant_app
from context_graph.domain.models import Event, SubgraphQuery
from context_graph.tenancy import CredentialGrant, Principal, TenantCatalog
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"a": "engram-assess-1010a-pdlc", "b": "engram-g07-target"}


def episode_membership_edges(state, episode_ids):
    """Exact membership, including detection of newly added old-Episode edges."""
    return sorted(
        json.dumps(row, sort_keys=True)
        for row in state["edges"]
        if row[0] == "Episode" and row[1] in episode_ids and row[2] in {"CONTAINS", "DERIVED_FROM"}
    )


def sourced_proposals(state, source_ids):
    """Content-keyed proposals may exist already; evidence belongs to each delivery."""
    keys = {
        (edge[0], edge[1])
        for edge in state["edges"]
        if edge[2] == "DERIVED_FROM" and edge[3] == "Event" and edge[4] in source_ids
    }
    return [
        row
        for row in state["nodes"]
        if row[0] in {"Decision", "Constraint", "Lesson"} and (row[0], row[1]) in keys
    ]


def provider_prompt_text(messages):
    """Observe original message text without JSON transport quote escaping."""
    return "\n".join(str(message.get("content", "")) for message in messages)


def observe_summary_cache(consumer, tenant, record, save, context):
    """Observe the original worker call; never replace its provider or result."""
    from context_graph.domain.consolidation import build_summary_prompt

    original = consumer._summary_text

    async def observed(scope, scope_id, events):
        prompt = build_summary_prompt(events)
        sources = tuple(sorted(str(e["event_id"]) for e in events))
        key = (scope, scope_id, sources, prompt)
        observations = record.setdefault("summary_cache_observations", [])
        row = dict(
            id="summary-" + str(len(observations)),
            tenant=tenant,
            scope=scope,
            scope_id=scope_id,
            source_event_ids=list(sources),
            prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
            cache_present_before=key in consumer._summary_texts,
        )
        observations.append(row)
        token = context.set(row["id"])
        save()
        try:
            text = await original(scope, scope_id, events)
            row.update(
                state="returned",
                output_sha256=hashlib.sha256(text.encode()).hexdigest() if text else None,
                cache_present_after=key in consumer._summary_texts,
            )
            return text
        except Exception as exc:
            row.update(state="failed", error_type=type(exc).__name__)
            raise
        finally:
            context.reset(token)
            save()

    consumer._summary_text = observed


def material_node(row, recovered_user_triggers=frozenset()):
    allowed = {
        "Event": {"access_count", "last_accessed_at", "importance_score"},
        "Entity": {"last_seen", "mention_count"},
        "Summary": {"content", "created_at"},
    }.get(row[0], set())
    if row[0] == "Event" and row[1] in recovered_user_triggers:
        allowed = allowed | {
            "user_extraction_receipt",
            "user_extraction_owner",
            "user_extraction_status",
        }
    return {key: value for key, value in row[2].items() if key not in allowed}


def fixtures(run_id):
    start = datetime.now(UTC) - timedelta(minutes=3)
    rows = []

    def add(t, key, kind="observation.input", payload=None, owner="publisher", session="work"):
        event = dict(
            event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + t + ":" + key)),
            event_type=kind,
            occurred_at=(start + timedelta(seconds=len(rows))).isoformat(),
            session_id=run_id + ":" + session,
            agent_id=run_id + ":" + owner,
            trace_id=run_id,
            payload_ref="pilot:" + key,
            payload=payload or {},
            importance_hint=7,
        )
        Event.model_validate_json(json.dumps(event))
        row = {"tenant": t, "key": key, "event": event, "expected_status": 201}
        rows.append(row)
        return row

    for key, name, style in [
        ("alice", "Alice", "short answers"),
        ("bob", "Bob", "detailed examples"),
    ]:
        add(
            "a",
            key,
            payload={
                "content": (
                    f"My name is {name}. I am a software engineer. I prefer {style}. "
                    "I am interested in Rust language development."
                )
            },
            owner=key,
            session=key,
        )
        add("a", key + "-end", "system.session_end", owner=key, session=key)
    doc = run_id + "-export"
    hld = run_id + "-hld"
    add(
        "b",
        "spec",
        "pdlc.spec.changed",
        dict(
            doc_id=doc,
            version="1",
            title="Audit CSV export",
            scope="Export authorized workspace rows",
            acceptance_criteria="Only workspace-authorized rows",
        ),
    )
    add(
        "b",
        "requirement",
        "pdlc.requirement.changed",
        dict(
            spec_id=doc,
            spec_version="1",
            local_id="authorization",
            statement="Export only workspace-authorized rows",
        ),
    )
    add(
        "b",
        "design",
        "pdlc.design.section_changed",
        dict(
            doc_id=hld,
            section_path="streaming",
            version="1",
            kind="hld",
            title="Bounded export streaming",
            body=(
                "We decide to stream authorized rows in bounded batches because "
                "workspace exports must not exhaust memory. "
                "Constraint: never buffer an entire workspace."
            ),
            requirements=[dict(spec_id=doc, spec_version="1", local_id="authorization")],
        ),
    )
    add(
        "b",
        "prose",
        payload={
            "content": (
                "For export jobs we choose bounded batches because memory is limited; "
                "avoid buffering whole workspaces. This is a proposed design choice, "
                "not evidence of a production deployment."
            )
        },
    )
    add("b", "end", "system.session_end")
    expected = {
        "spec": "Spec:" + doc + "|1",
        "requirement": "Requirement:" + doc + "|1|authorization",
        "design": "DesignElement:" + hld + "|streaming|1",
    }
    queries = {
        "a-alice": dict(
            query="What answer style and interests should this assistant use for Alice?",
            intent="personalize",
            agent_id=run_id + ":alice",
            session_id=run_id + ":alice",
            timeout_ms=30000,
            max_nodes=60,
        ),
        "a-bob": dict(
            query="What answer style and interests should this assistant use for Bob?",
            intent="personalize",
            agent_id=run_id + ":bob",
            session_id=run_id + ":bob",
            timeout_ms=30000,
            max_nodes=60,
        ),
        "b-trace": dict(
            query="Which design refines this export authorization requirement?",
            intent="trace",
            seed_node_ids=[expected["requirement"]],
            max_depth=3,
            max_nodes=60,
        ),
        "b-text": dict(query="Audit CSV export", intent="trace", max_depth=3, max_nodes=60),
    }
    for k in ("a-alice", "a-bob"):
        SubgraphQuery.model_validate_json(json.dumps(queries[k]))
    for k in ("b-trace", "b-text"):
        ArtifactQueryRequest.model_validate(queries[k])
    return {
        "events": rows,
        "expected_artifacts": expected,
        "queries": queries,
        "forbidden": [
            "cross-tenant source Events",
            "cross-owner preferences",
            "invented deployment",
            "duplicate source event",
        ],
        "scope": [
            "A-01",
            "A-06 owner control",
            "B02 declared chain",
            "B06 prose proposals",
            "C02",
            "C06",
            "C07",
            "C17",
        ],
        "provider": "actual configured model, no provider replacement",
        "remaining": (
            "All other candidate journeys/probes remain unexecuted. "
            "This first checkpoint is not complete pilot acceptance."
        ),
    }


def build_plan(args):
    plan = fixtures(args.run_id)
    if getattr(args, "journey_file", None):
        plan["spectrum"] = json.loads(args.journey_file.read_text())
    elif getattr(args, "spectrum", False):
        from engram_pilot_spectrum import freeze

        plan["spectrum"] = freeze(args.run_id)
    groups = plan.get("spectrum", {}).get("groups", [])
    selected_only = getattr(args, "journeys_only", False)
    if selected_only and not groups:
        raise ValueError("--journeys-only requires nonempty selected journey groups")
    from engram_pilot_completion_fixtures import load_retained_negative

    for group in groups:
        if "retained_negative_deliveries" in group:
            raise ValueError("Retained deliveries must be loaded from frozen verified proofs")
        proofs = group.get("retained_negative_proofs", [])
        if proofs:
            group["retained_negative_deliveries"] = [
                load_retained_negative(p, ROOT) for p in proofs
            ]
    names = set()
    for group in groups:
        if group["name"] in names or group["tenant"] not in TARGETS:
            raise ValueError("Journey names must be unique and tenants must be a or b")
        names.add(group["name"])
        if not isinstance(group["steps"], list) or not isinstance(group["queries"], list):
            raise ValueError("Journey steps and queries must be lists")
        correction_inputs = (
            group.get("recover_user_inputs")
            or group.get("verify_user_inputs")
            or [s["request"] for s in group["steps"]]
        )
        if group.get("user_correction") and (
            len(correction_inputs) != 2
            or [r["event_type"] for r in correction_inputs]
            != ["observation.input", "system.session_end"]
            or any(
                r["agent_id"] != group["owner"] or r["session_id"] != group["session"]
                for r in correction_inputs
            )
        ):
            raise ValueError("Correction requires the declared two-input owner/session window")
        recovery = group.get("recover_user_inputs") or group.get("verify_user_inputs", [])
        if group.get("recover_user_inputs") and group.get("verify_user_inputs"):
            raise ValueError("A User group cannot both recover and verify a prior receipt")
        if recovery and (
            not (group.get("user_story") or group.get("user_correction"))
            or group["steps"]
            or len(recovery) != 2
            or [r["event_type"] for r in recovery] != ["observation.input", "system.session_end"]
            or any(r["agent_id"] != group["owner"] for r in recovery)
            or any(r["session_id"] != group["session"] for r in recovery)
        ):
            raise ValueError("User recovery must name its exact two-input owner/session window")
        if not any((group["steps"], group["queries"], group.get("final_queries"), recovery)):
            raise ValueError("Journey group must contain inputs or read checks")
        for request in [*[s["request"] for s in group["steps"]], *recovery]:
            Event.model_validate_json(json.dumps(request))
    plan["execution_mode"] = "selected-journeys" if selected_only else "entry-and-selected"
    if selected_only:
        plan.update(
            events=[],
            expected_artifacts={},
            queries={},
            scope=[plan["spectrum"]["coverage"]],
            remaining=(
                "Selected groups only; entry business paths are not executed "
                "or certified by this attempt."
            ),
        )
        if not any(group["steps"] or group.get("recover_user_inputs") for group in groups):
            plan["execution_mode"] = "selected-retained-reads"
    return plan


async def execute(args):
    plan = build_plan(args)
    directory = Path(args.output).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    spectrum_steps = [
        {"tenant": group["tenant"], **step}
        for group in plan.get("spectrum", {}).get("groups", [])
        for step in group["steps"]
    ]
    selected_groups = plan.get("spectrum", {}).get("groups", [])
    if selected_groups and not getattr(args, "journeys_only", False):
        plan["scope"] = [*plan["scope"], plan["spectrum"]["coverage"]]
    recovery_groups = [g for g in selected_groups if g.get("recover_user_inputs")]
    verified_groups = [g for g in selected_groups if g.get("verify_user_inputs")]
    source_inputs = (
        plan["events"]
        + [{"tenant": step["tenant"], "event": step["request"]} for step in spectrum_steps]
        + [
            {"tenant": g["tenant"], "event": r}
            for g in recovery_groups
            for r in g["recover_user_inputs"]
        ]
    )
    retained_reads_only = plan["execution_mode"] == "selected-retained-reads"
    active_tenants = {r["tenant"] for r in source_inputs}

    durable_json(directory / "fixtures.json", plan)
    source_paths = [*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("src").rglob("*.yaml")]
    source_paths.extend(
        ROOT / "scripts" / name
        for name in (
            "engram_pilot_first_run.py",
            "engram_pilot_model_transition.py",
            "engram_experiment_support.py",
            "engram_composition_assessment.py",
            "engram_pilot_spectrum.py",
            "engram_pilot_completion_fixtures.py",
            "engram_pilot_episode_bridge.py",
            "engram_pilot_summary_proof.py",
            "engram_pilot_episode_history.py",
            "engram_pilot_retrieval_proof.py",
            "engram_pilot_tenant_proof.py",
            "engram_pilot_recovery_proof.py",
        )
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    durable_json(
        directory / "reproduction-manifest.json",
        {
            "git_revision": revision.stdout.strip(),
            "execution_mode": plan["execution_mode"],
            "source_sha256": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in source_paths
            },
            "fixtures_sha256": hashlib.sha256(
                (directory / "fixtures.json").read_bytes()
            ).hexdigest(),
            "provider_mode": "actual; no replacement; no artificial call ceiling",
        },
    )

    record = {
        "state": "preflight",
        "execution_mode": plan["execution_mode"],
        "scope": plan["scope"],
        "checks": [],
        "requests": [],
        "provider_calls": [],
        "worker_outcomes": [],
        "workers": [],
        "limitations": [
            plan["remaining"],
            (
                "Local loopback public-dispatcher path; no external cohort onboarding "
                "or TLS/remote access proof"
            ),
            "Episode/summary/vector claims require corresponding selected-scenario evidence",
            "Unevaluated-pack development gate retained; no full-pack evaluation claim",
        ],
    }

    def save():
        durable_json(directory / "results.json", record)

    def check(name, ok, actual=None):
        record["checks"].append(dict(name=name, passed=bool(ok), actual=actual))
        save()
        if not ok:
            raise AssertionError(name)

    save()
    check("real provider credential present", bool(os.getenv("OPENAI_API_KEY")))
    cloud = shutil.which("gcloud")
    if not cloud:
        raise RuntimeError("gcloud must be on PATH; no private-machine fallback")
    r = subprocess.run(
        [
            cloud,
            "auth",
            "print-access-token",
            "--impersonate-service-account=" + args.service_account,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if r.returncode:
        raise RuntimeError("Credential refresh failed; credential output suppressed")
    credentials = Credentials(token=r.stdout.strip())
    original_client = spanner.Client

    def authenticated(*a, **kw):
        kw["credentials"] = credentials
        return original_client(*a, **kw)

    spanner.Client = authenticated
    client = authenticated(project="portiq-mvp")
    databases = {}
    bindings = {}
    consumers = []
    stores = []
    tasks = []
    server = server_task = None
    original_completion = litellm.acompletion
    summary_context: ContextVar[str | None] = ContextVar("pilot_summary_request", default=None)
    recovery_hooks = None
    if any(g.get("recovery_proof") for g in selected_groups):
        from engram_pilot_recovery_proof import RecoveryHooks

        recovery_hooks = RecoveryHooks(plan["spectrum"], record, save)

    async def observed_completion(*a, **kw):
        row = {"model": kw.get("model"), "started_at": datetime.now(UTC).isoformat()}
        row["prompt_sha256"] = hashlib.sha256(
            provider_prompt_text(kw.get("messages", [])).encode()
        ).hexdigest()
        if summary_context.get() is not None:
            row["summary_request_id"] = summary_context.get()
        if recovery_hooks is not None:
            from engram_pilot_recovery_proof import PROVIDER_REJECTION

            if (marker := PROVIDER_REJECTION.get()) is not None:
                row.update(
                    recovery_extraction_session=marker["session_id"],
                    worker_generation=marker["generation"],
                    input_messages=kw.get("messages", []),
                )
                if marker["inject"]:
                    row["test_injection"] = "p10-known-invalid-credential"
                    kw = {**kw, "api_key": "invalid-pilot-test-credential"}
        record["provider_calls"].append(row)
        save()
        try:
            answer = await original_completion(*a, **kw)
        except Exception as exc:
            row["state"] = "failed"
            row["error_type"] = type(exc).__name__
            save()
            raise
        try:
            row["usage"] = answer.usage.model_dump() if answer.usage else None
            row["output"] = answer.choices[0].message.content
            row["state"] = "returned"
            prompt = provider_prompt_text(kw.get("messages", []))
            probe_ids = {
                step["request"]["event_id"]
                for group in plan.get("spectrum", {}).get("groups", [])
                if group.get("temporal_story")
                for step in group["steps"]
            }
            if "source_content" in prompt and any(eid in prompt for eid in probe_ids):
                row["input_messages"] = kw.get("messages", [])

            row["input_event_candidates"] = [
                r["event"]["event_id"]
                for r in source_inputs
                if any(
                    text and text in prompt
                    for text in (
                        r["event"]["payload"].get("content"),
                        r["event"]["payload"].get("body"),
                    )
                )
            ]
            user_input_ids = {
                r["event_id"]
                for group in selected_groups
                if group.get("user_story") or group.get("user_correction")
                for r in (
                    group.get("recover_user_inputs") or [step["request"] for step in group["steps"]]
                )
            }
            if row["input_event_candidates"] and (
                "Known items:" in prompt
                or user_input_ids.intersection(row["input_event_candidates"])
            ):
                row["input_messages"] = kw.get("messages", [])
            save()
        except Exception as exc:
            record.setdefault("observation_errors", []).append(type(exc).__name__)
        return answer

    litellm.acompletion = observed_completion
    old_config = structlog.get_config().copy()

    def observe(_logger, _method, event):
        if event.get("event", "").startswith(
            (
                "pack_extraction_applied",
                "pack_extraction_answer_invalid",
                "consumer_processing_failed",
                "user_extraction",
                "message_processing_failed",
                "event_enriched",
                "consolidation_cycle_stopped",
            )
        ):
            record["worker_outcomes"].append(dict(event))
            save()
        return event

    structlog.configure(processors=[observe, *old_config["processors"]])
    try:
        for t, dbid in TARGETS.items():
            pool = BurstyPool()
            db = client.instance("engram-experiment").database(dbid, pool=pool)
            prepare_cleanup(db, client, pool)
            databases[t] = db
            previous = json.loads(
                (Path(args.predecessor) / (t + "-read-only-state.json")).read_text()
            )
            check(
                t + " exact retained owner and dataset",
                db.name == previous["database"]
                and read_owner(db) == previous["owner"]
                and fingerprint(db) == previous["fingerprints"],
            )
            check(
                t + " baseline has no undeclared retained dead letters",
                declared_dead_letters(
                    previous["snapshot"],
                    [{**g, "steps": []} for g in selected_groups],
                    t,
                    require_all=True,
                ),
            )
            check(
                t + " inactive tenant has no pending work",
                t in active_tenants or not previous["snapshot"]["pending"],
            )
            durable_json(directory / (t + "-before.json"), previous)
            for group in recovery_groups:
                if group["tenant"] != t:
                    continue
                from engram_pilot_completion_fixtures import recovery_input_hash

                trigger_id = group["recover_user_inputs"][-1]["event_id"]
                trigger_props = next(
                    r[2]
                    for r in previous["snapshot"]["nodes"]
                    if r[0] == "Event" and r[1] == trigger_id
                )
                check(
                    group["name"] + " exact pending source and absent prior receipt",
                    ["assessment-extraction", trigger_id] in previous["snapshot"]["pending"]
                    and not trigger_props.get("user_extraction_receipt")
                    and not trigger_props.get("user_extraction_owner")
                    and not trigger_props.get("user_extraction_status")
                    and recovery_input_hash(previous["snapshot"], group["recover_user_inputs"])
                    == group["recovery_input_hash"],
                )
            for group in verified_groups:
                if group["tenant"] != t:
                    continue
                from engram_pilot_completion_fixtures import verified_recovered_user_receipt

                verified_recovered_user_receipt(previous["snapshot"], group)
                check(group["name"] + " exact already-applied receipt at startup", True)
            existing_ids = {r[0] for r in previous["snapshot"]["events"]}
            fixture_ids = {r["event"]["event_id"] for r in plan["events"] if r["tenant"] == t}
            fixture_ids |= {
                step["request"]["event_id"]
                for step in spectrum_steps
                if step["tenant"] == t and step["expected_status"] < 400
            }
            check(t + " all fixture Event identities fresh", not (existing_ids & fixture_ids))
            if t == "b":
                check(
                    "all fixture artifacts fresh",
                    not (
                        {r[1] for r in previous["snapshot"]["nodes"]}
                        & set(plan["expected_artifacts"].values())
                    ),
                )
            spectrum_artifacts = set()
            for step in spectrum_steps:
                if step["tenant"] == t and step["expected_status"] < 400:
                    spectrum_artifacts.update(step.get("extra_nodes", {}))
                    spectrum_artifacts.update(step.get("node_assertions", {}))
                    if step.get("expected_node"):
                        spectrum_artifacts.add(step["expected_node"])
                    for _, source, target in step.get("expected_edges", []):
                        spectrum_artifacts.update((source, target))
            check(
                t + " spectrum artifact identities fresh",
                not (spectrum_artifacts & {r[1] for r in previous["snapshot"]["nodes"]}),
            )
            with db.snapshot() as view:
                groups = {r[0] for r in view.execute_sql("SELECT group_name FROM ConsumerGroups")}
            check(
                t + " retained worker groups match",
                groups == {"assessment-" + k for k in VALID_CONSUMERS},
            )

            bound = binding_from_baseline(args.run_id, t, previous)
            check(
                t + " selected bundle matches retained owner",
                bound.bundle_digest == previous["owner"][0][4],
            )
            bindings[t] = bound
        record["settings"] = {
            t: {
                "model": b.settings().llm.model_id,
                "packs": b.bundle.pack_identities,
                "epoch": b.epoch,
                "consolidation_hours": b.settings().decay.reconsolidation_interval_hours,
                "reflection_threshold": b.settings().decay.reflection_threshold,
            }
            for t, b in bindings.items()
        }
        save()
        tokens = {t: secrets.token_urlsafe(32) for t in bindings}
        admin = {t: secrets.token_urlsafe(32) for t in bindings}
        untrusted = {t: secrets.token_urlsafe(32) for t in bindings}
        grants = []
        for t, b in bindings.items():
            grants.extend(
                [
                    CredentialGrant.from_token(
                        Principal(
                            "pilot-" + t, b.tenant_id, frozenset({"api"}), source_id="demo.query"
                        ),
                        tokens[t],
                    ),
                    CredentialGrant.from_token(
                        Principal(
                            "pilot-admin-" + t,
                            b.tenant_id,
                            frozenset({"api", "admin"}),
                            source_id="demo.query",
                        ),
                        admin[t],
                    ),
                ]
            )
        if any(g.get("retrieval_proof") for g in selected_groups):
            for t, b in bindings.items():
                grants.append(
                    CredentialGrant.from_token(
                        Principal(
                            "pilot-untrusted-" + t,
                            b.tenant_id,
                            frozenset({"api"}),
                            source_id="demo.untrusted",
                        ),
                        untrusted[t],
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
                raise RuntimeError("API startup failed")
            await asyncio.sleep(0.1)
        check("public dispatcher ready", server.started)
        if any(g.get("retrieval_proof") for g in selected_groups):
            from engram_pilot_retrieval_proof import observe_vectors

            for t, b in bindings.items():
                observe_vectors(app._children[b.tenant_id], t, record, save)
        for _t, b in bindings.items():
            if retained_reads_only or _t not in active_tenants:
                continue
            for kind in VALID_CONSUMERS:
                worker, store = await _build_consumer(kind, b.settings(), tenant_binding=b)
                if kind == "consolidation":
                    observe_summary_cache(worker, _t, record, save, summary_context)
                if recovery_hooks is not None:
                    recovery_hooks.install(_t, kind, worker)
                consumers.append(worker)
                stores.append(store)
                tasks.append(asyncio.create_task(worker.run()))
                record.setdefault("workers", []).append(
                    {"tenant": _t, "type": kind, "group": "assessment-" + kind}
                )

        async def stop_current_workers():
            for worker in consumers:
                worker.stop()
            finished = await asyncio.gather(*tasks, return_exceptions=True)
            check(
                "recovery worker stop completed without errors",
                not any(isinstance(r, BaseException) for r in finished),
            )

        async def restart_workers():
            await stop_current_workers()
            snapshots = {t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()}
            end = plan["spectrum"]["groups"][0]["steps"][-1]["request"]
            props = next(
                (
                    r[2]
                    for r in snapshots["a"]["nodes"]
                    if r[0] == "Event" and r[1] == end["event_id"]
                ),
                {},
            )
            durable_json(directory / "before-restart-pending-proof.json", snapshots)
            check(
                "old workers stopped with marked extraction still pending and unapplied",
                ["assessment-extraction", end["event_id"]] in snapshots["a"]["pending"]
                and props.get("user_extraction_status") != "applied",
            )
            for store in stores:
                await store.close()
            consumers.clear()
            tasks.clear()
            stores.clear()
            recovery_hooks.generation += 1
            generation = []
            for tenant, binding in bindings.items():
                for kind in VALID_CONSUMERS:
                    worker, store = await _build_consumer(
                        kind, binding.settings(), tenant_binding=binding
                    )
                    if kind == "consolidation":
                        observe_summary_cache(worker, tenant, record, save, summary_context)
                    recovery_hooks.install(tenant, kind, worker)
                    consumers.append(worker)
                    stores.append(store)
                    tasks.append(asyncio.create_task(worker.run()))
                    generation.append(
                        dict(
                            tenant=tenant,
                            type=kind,
                            group="assessment-" + kind,
                            epoch=binding.epoch,
                        )
                    )
            record.setdefault("recovery_worker_generations", []).append(generation)
            check(
                "restarted generation has exact tenant worker set and current epochs",
                {(r["tenant"], r["type"], r["epoch"]) for r in generation}
                == {(t, k, b.epoch) for t, b in bindings.items() for k in VALID_CONSUMERS}
                and len(consumers) == len(generation) == 10
                and sorted(w._group_name for w in consumers)
                == sorted(r["group"] for r in generation),
            )
            save()

        async def probe_stale_binding():
            from context_graph.ports.errors import RuntimeFencedError

            await stop_current_workers()
            before = {
                t: dict(
                    owner=await asyncio.to_thread(read_owner, db),
                    fingerprints=await asyncio.to_thread(fingerprint, db),
                )
                for t, db in databases.items()
            }
            for tenant, binding in bindings.items():
                predecessor = binding.predecessor
                check(tenant + " recorded predecessor available", predecessor is not None)
                try:
                    unexpected, opened = await _build_consumer(
                        "projection", predecessor.settings(), tenant_binding=predecessor
                    )
                except RuntimeFencedError:
                    check(tenant + " stale startup fenced before processing", True)
                else:
                    unexpected.stop()
                    await opened.close()
                    check(tenant + " stale startup fenced before processing", False)
            after = {
                t: dict(
                    owner=await asyncio.to_thread(read_owner, db),
                    fingerprints=await asyncio.to_thread(fingerprint, db),
                )
                for t, db in databases.items()
            }
            durable_json(
                directory / "stale-startup-owner-table-proof.json", dict(before=before, after=after)
            )
            check(
                "stale startup leaves exact owners and all table fingerprints unchanged",
                before == after,
            )

        record["state"] = "running"
        save()
        # Each request gets a fresh loopback connection. Long Spanner/model waits
        # must not leave a pooled socket racing Uvicorn's keep-alive expiry.
        # HTTP errors still fail the run; this does not retry/waive responses.
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            timeout=45,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as http:

            async def request(
                t,
                path,
                body=None,
                *,
                method="POST",
                role="api",
                auth_mode="normal",
                tenant_hints=None,
            ):
                if role not in {"api", "admin", "untrusted"}:
                    raise ValueError("Unknown explicit pilot credential role")
                token = {"admin": admin, "api": tokens, "untrusted": untrusted}[role][t]
                if auth_mode not in {"normal", "missing", "invalid", "duplicate"}:
                    raise ValueError("Unknown explicit authentication probe")
                headers = []
                if auth_mode != "missing":
                    headers.append(
                        (
                            "Authorization",
                            "Bearer "
                            + ("invalid-pilot-probe" if auth_mode == "invalid" else token),
                        )
                    )
                if auth_mode == "duplicate":
                    headers.append(("Authorization", "Bearer " + token))
                headers.extend(("X-Tenant-ID", hint) for hint in (tenant_hints or []))
                row = {
                    "tenant": t,
                    "path": path,
                    "method": method,
                    "role": role,
                    "input": body,
                    "auth_mode": auth_mode,
                    "tenant_hints": tenant_hints or [],
                }
                record["requests"].append(row)
                save()
                response = await http.request(method, path, json=body, headers=headers)
                try:
                    out = response.json()
                except ValueError:
                    out = response.text
                row.update(status=response.status_code, output=out)
                save()
                return response.status_code, out

            if not getattr(args, "journeys_only", False):
                for row in plan["events"]:
                    code, out = await request(row["tenant"], "/v1/events", row["event"])
                    check(row["key"] + " admitted", code == row["expected_status"], code)
                # Stable request identity, same input, separately recorded retry result.
                first = plan["events"][0]
                code, out = await request("a", "/v1/events", first["event"])
                check("unchanged retry accepted without new identity", code in (200, 201), code)
                b_prose = {
                    r["event"]["event_id"]
                    for r in plan["events"]
                    if r["key"] in ("design", "prose")
                }
                deadline = time.monotonic() + 240
                states = {}
                required = {(r["tenant"], r["event"]["event_id"]) for r in plan["events"]}
                while time.monotonic() < deadline:
                    invalid = [
                        o
                        for o in record["worker_outcomes"]
                        if o.get("event") == "pack_extraction_answer_invalid"
                        and o.get("event_id") in b_prose
                    ]
                    if invalid:
                        raise AssertionError("Required pack answer invalid; no completed output")
                    for task in tasks:
                        if task.done():
                            await task
                            raise RuntimeError("worker exited before stop")
                    states = {
                        t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()
                    }
                    all_present = all(
                        any(n[0] == "Event" and n[1] == eid for n in states[t]["nodes"])
                        for t, eid in required
                    )
                    a_nodes = {(r[0], r[1]): r[2] for r in states["a"]["nodes"]}
                    receipts = all(
                        ("Event", r["event"]["event_id"]) in a_nodes
                        and "user_extraction_receipt" in a_nodes[("Event", r["event"]["event_id"])]
                        for r in plan["events"]
                        if r["tenant"] == "a" and r["key"].endswith("-end")
                    )
                    applied = {
                        r.get("event_id")
                        for r in record["worker_outcomes"]
                        if r.get("event") == "pack_extraction_applied"
                    }
                    lags = await asyncio.gather(*(w._subscription.lag() for w in consumers))
                    if (
                        all_present
                        and receipts
                        and b_prose <= applied
                        and not any(lags)
                        and all(
                            not s["pending"] and declared_dead_letters(s, selected_groups, t)
                            for t, s in states.items()
                        )
                    ):
                        break
                    await asyncio.sleep(1)
                check(
                    "exact events, extraction receipts, matching pack outcomes and drained work",
                    all_present
                    and receipts
                    and b_prose <= applied
                    and not any(lags)
                    and all(
                        not s["pending"] and declared_dead_letters(s, selected_groups, t)
                        for t, s in states.items()
                    ),
                )
                for t, s in states.items():
                    durable_json(directory / (t + "-processed.json"), s)
                    before = json.loads((directory / (t + "-before.json")).read_text())
                    previous_ids = {row[0] for row in before["snapshot"]["events"]}
                    observed_ids = {row[0] for row in s["events"]}
                    expected_ids = {
                        row["event"]["event_id"] for row in plan["events"] if row["tenant"] == t
                    }
                    check(
                        t + " exact new ledger identities including retry",
                        observed_ids - previous_ids == expected_ids,
                    )
                prior_b = json.loads((directory / "b-before.json").read_text())["snapshot"]
                prior_keys = {(row[0], row[1]) for row in prior_b["nodes"]}
                fresh_b = [
                    row for row in states["b"]["nodes"] if (row[0], row[1]) not in prior_keys
                ]
                check(
                    "B disabled User and unasserted deployment outputs absent",
                    not any(
                        row[0] in {"UserProfile", "Preference", "Skill", "Deployment"}
                        for row in fresh_b
                    ),
                )
                proposals = sourced_proposals(states["b"], b_prose)
                fresh_proposals = [
                    row for row in fresh_b if row[0] in {"Decision", "Constraint", "Lesson"}
                ]
                check(
                    "model proposals stored with actual source evidence",
                    all(sourced_proposals(states["b"], {source}) for source in b_prose)
                    and all(
                        any(
                            edge[:3] == [row[0], row[1], "DERIVED_FROM"]
                            and edge[3] == "Event"
                            and edge[4] in b_prose
                            for edge in states["b"]["edges"]
                        )
                        for row in fresh_proposals
                    ),
                )
                owner_reads = {}
                for owner, name, phrase in [
                    ("alice", "Alice", "short answers"),
                    ("bob", "Bob", "detailed examples"),
                ]:
                    uid = "user:" + args.run_id + ":" + owner
                    code, profile = await request(
                        "a", "/v1/users/" + uid + "/profile", method="GET", role="admin"
                    )
                    check(
                        name + " canonical profile",
                        code == 200
                        and profile.get("profile_id") == "profile:" + uid
                        and profile.get("display_name", "").startswith(name),
                        profile,
                    )
                    code, prefs = await request(
                        "a", "/v1/users/" + uid + "/preferences", method="GET", role="admin"
                    )
                    source = next(
                        r["event"]["event_id"] for r in plan["events"] if r["key"] == owner
                    )
                    a_nodes = {(r[0], r[1]): r[2] for r in states["a"]["nodes"]}
                    end = next(
                        r["event"]["event_id"] for r in plan["events"] if r["key"] == owner + "-end"
                    )
                    receipt = a_nodes[("Event", end)]["user_extraction_receipt"]["result"]
                    supported = {
                        p["preference_id"]
                        for p in receipt["preferences"]
                        if phrase in p.get("source_quote", "").lower()
                        and p["polarity"] == "positive"
                    }
                    check(
                        name + " attributed preference and exact source",
                        code == 200
                        and any(
                            p.get("preference_id") in supported
                            and p.get("support_event_ids") == [source]
                            for p in prefs
                        ),
                        prefs,
                    )
                    code, answer = await request(
                        "a", "/v1/query/subgraph", plan["queries"]["a-" + owner]
                    )
                    ownprefs = supported & {p.get("preference_id") for p in prefs}
                    check(
                        name + " composed read contains preference evidence",
                        code == 200
                        and bool(ownprefs & set(answer.get("nodes", {})))
                        and source in answer.get("nodes", {}),
                        answer,
                    )
                    owner_reads[owner] = {
                        "answer": answer,
                        "prefs": ownprefs,
                        "profile": "profile:" + uid,
                    }
                    other_source = next(
                        r["event"]["event_id"]
                        for r in plan["events"]
                        if r["key"] == ("bob" if owner == "alice" else "alice")
                    )
                    check(
                        name + " read excludes other owner source",
                        other_source not in answer.get("nodes", {}),
                    )
                for owner, other in (("alice", "bob"), ("bob", "alice")):
                    answer = owner_reads[owner]["answer"]
                    forbidden = owner_reads[other]["prefs"] | {owner_reads[other]["profile"]}
                    check(
                        owner + " excludes foreign profile/preferences",
                        not (forbidden & set(answer.get("nodes", {})))
                        and all(
                            n.get("attributes", {}).get("user_id")
                            != "user:" + args.run_id + ":" + other
                            for n in answer.get("nodes", {}).values()
                        ),
                    )
                code, _ = await request(
                    "a", "/v1/users/user:" + args.run_id + ":alice/profile", method="GET"
                )
                check("ordinary API role cannot read admin User endpoint", code == 403, code)
                for key in ("b-trace", "b-text"):
                    code, answer = await request("b", "/v1/query/artifacts", plan["queries"][key])
                    check(
                        key + " declared chain retrievable",
                        code == 200
                        and all(
                            n in answer.get("nodes", {})
                            for n in plan["expected_artifacts"].values()
                        ),
                        answer,
                    )
                    expected = plan["expected_artifacts"]
                    pairs = {
                        (e["edge_type"], e["source"], e["target"]) for e in answer.get("edges", [])
                    }
                    check(
                        key + " declared directed links",
                        {
                            ("REFINES", expected["design"], expected["requirement"]),
                            ("REFINES", expected["requirement"], expected["spec"]),
                        }
                        <= pairs,
                    )
                    source_for = {
                        plan["expected_artifacts"][k]: next(
                            r["event"]["event_id"] for r in plan["events"] if r["key"] == k
                        )
                        for k in ("spec", "requirement", "design")
                    }
                    check(
                        key + " exact artifact source provenance",
                        all(
                            (answer["nodes"][nid].get("provenance") or {}).get("event_id") == eid
                            for nid, eid in source_for.items()
                        ),
                    )
                prose_event = next(
                    r["event"]["event_id"] for r in plan["events"] if r["key"] == "prose"
                )
                prose_proposals = [
                    row
                    for row in proposals
                    if any(
                        edge[:5] == [row[0], row[1], "DERIVED_FROM", "Event", prose_event]
                        for edge in states["b"]["edges"]
                    )
                ]
                initial = {"Decision": "proposed", "Constraint": "active", "Lesson": "tentative"}
                check(
                    "prose specifically produced persisted proposals",
                    bool(prose_proposals)
                    and all(
                        row[2].get("status") == initial[row[0]] and row[2].get("method")
                        for row in prose_proposals
                    ),
                )
                proposal_query = dict(
                    query="status of these proposed export choices",
                    intent="status",
                    seed_node_ids=[r[1] for r in prose_proposals],
                    max_nodes=60,
                )
                ArtifactQueryRequest.model_validate(proposal_query)
                code, proposal_answer = await request("b", "/v1/query/artifacts", proposal_query)
                check(
                    "prose proposals publicly retrievable with provenance",
                    code == 200
                    and all(
                        row[1] in proposal_answer.get("nodes", {})
                        and (proposal_answer["nodes"][row[1]].get("provenance") or {}).get(
                            "event_id"
                        )
                        == prose_event
                        and proposal_answer["nodes"][row[1]]["attributes"].get("status")
                        == initial[row[0]]
                        for row in prose_proposals
                    ),
                )
                design = next(
                    r["event"]["event_id"] for r in plan["events"] if r["key"] == "design"
                )
                foreign_body = dict(
                    query="event " + design,
                    session_id=args.run_id + ":work",
                    agent_id=args.run_id + ":publisher",
                    seed_nodes=[design],
                    intent="what",
                    timeout_ms=30000,
                    max_nodes=30,
                )
                code, positive = await request("b", "/v1/query/subgraph", foreign_body)
                check(
                    "foreign-only positive in B",
                    code == 200 and design in positive.get("nodes", {}),
                )
                code, negative = await request("a", "/v1/query/subgraph", foreign_body)
                check(
                    "foreign-only excluded in A",
                    code == 200 and design not in negative.get("nodes", {}),
                )
                applied = [
                    r
                    for r in record["worker_outcomes"]
                    if r.get("event") == "pack_extraction_applied" and r.get("event_id") in b_prose
                ]
                check(
                    "actual model generated validated PDLC proposals",
                    sum(r.get("nodes", 0) for r in applied) > 0,
                    applied,
                )
            if selected_groups:
                from engram_pilot_spectrum import execute as execute_spectrum

                await execute_spectrum(
                    plan["spectrum"],
                    evidence_directory=directory,
                    recovery_hooks=recovery_hooks,
                    restart=restart_workers,
                    stale_probe=probe_stale_binding,
                    request=request,
                    check=check,
                    databases=databases,
                    record=record,
                    save=save,
                    consumers=consumers,
                    baselines={
                        t: json.loads((directory / (t + "-before.json")).read_text())["snapshot"]
                        for t in databases
                    },
                )
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    lags = await asyncio.gather(*(w._subscription.lag() for w in consumers))
                    states = {
                        t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()
                    }
                    if not any(lags) and all(
                        not s["pending"]
                        and declared_dead_letters(s, selected_groups, t, require_all=True)
                        for t, s in states.items()
                    ):
                        break
                    await asyncio.sleep(0.3)
                check(
                    (
                        "retained reads preserve exactly declared queue/DLQ state"
                        if retained_reads_only
                        else "spectrum work drained with exactly declared negative deliveries"
                    ),
                    not any(lags)
                    and all(
                        not s["pending"]
                        and declared_dead_letters(s, selected_groups, t, require_all=True)
                        for t, s in states.items()
                    ),
                )
        record["final_worker_lags"] = await asyncio.gather(
            *(w._subscription.lag() for w in consumers)
        )
        if retained_reads_only:
            check(
                "retained-read checkpoint submits no inputs or background model work",
                not source_inputs and not record["workers"] and not record["provider_calls"],
            )
        else:
            check(
                "exact selected-tenant worker identities and final zero lag",
                {(w["tenant"], w["type"]) for w in record["workers"]}
                == {(t, kind) for t in active_tenants for kind in VALID_CONSUMERS}
                and len(record["workers"]) == len(active_tenants) * len(VALID_CONSUMERS)
                and not any(record["final_worker_lags"]),
            )
        record["state"] = "pending-final-verification"
        save()
    except BaseException as exc:
        record["state"] = "failed"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)[:600]}
        save()
        raise
    finally:
        try:
            try:
                if recovery_hooks is not None:
                    recovery_hooks.release_all()
                errors = await stop_demo(consumers, tasks, stores, server, server_task)
            except Exception as exc:
                errors = [type(exc).__name__]
            record["shutdown_errors"] = errors
            record["checks"].append(
                {
                    "name": (
                        "actual provider outcomes match declared recovery contract after shutdown"
                        if recovery_hooks is not None
                        else "actual provider calls returned after cooperative shutdown"
                    ),
                    "passed": (
                        bool(record["provider_calls"]) or getattr(args, "journeys_only", False)
                    )
                    and all(
                        (
                            c.get("state") == "failed"
                            and c.get("error_type") == "AuthenticationError"
                        )
                        if recovery_hooks is not None
                        and c.get("test_injection") == "p10-known-invalid-credential"
                        else c.get("state") == "returned"
                        for c in record["provider_calls"]
                    )
                    and (
                        recovery_hooks is None
                        or sum(
                            c.get("test_injection") == "p10-known-invalid-credential"
                            for c in record["provider_calls"]
                        )
                        == 1
                    ),
                }
            )
            if errors:
                record["state"] = "failed"
            for t, db in databases.items():
                try:
                    final = {
                        "database": db.name,
                        "owner": read_owner(db),
                        "fingerprints": fingerprint(db),
                        "snapshot": snapshot(db),
                    }
                    previous_path = directory / (t + "-before.json")
                    if previous_path.exists():
                        prior_baseline = json.loads(previous_path.read_text())
                        if "model_transition" in prior_baseline:
                            final["model_transition"] = prior_baseline["model_transition"]
                    durable_json(directory / (t + "-final-state.json"), final)
                    before_path = directory / (t + "-before.json")
                    if not before_path.exists():
                        continue
                    before = json.loads(before_path.read_text())
                    originals = {r[0]: r[1:] for r in before["snapshot"]["events"]}
                    retained = {r[0]: r[1:] for r in final["snapshot"]["events"]}
                    expected_ids = {
                        r["event"]["event_id"] for r in plan["events"] if r["tenant"] == t
                    }
                    expected_ids |= {
                        step["request"]["event_id"]
                        for step in spectrum_steps
                        if step["tenant"] == t and step["expected_status"] < 400
                    }
                    complete = record["state"] == "pending-final-verification"
                    record["checks"].append(
                        {
                            "name": t + " final exact ledger append and retained owner",
                            "passed": final["owner"] == before["owner"]
                            and all(retained.get(k) == v for k, v in originals.items())
                            and (
                                (set(retained) - set(originals)) == expected_ids
                                if complete
                                else (set(retained) - set(originals)) <= expected_ids
                            ),
                        }
                    )
                    correction_updates = {}
                    for group in selected_groups:
                        if (
                            group["tenant"] == t
                            and group.get("user_correction")
                            and not group.get("verify_user_inputs")
                        ):
                            from engram_pilot_completion_fixtures import correction_expected_updates

                            expected, _receipt = correction_expected_updates(
                                before["snapshot"], final["snapshot"], group
                            )
                            correction_updates.update(expected)
                    tenant_recovery_triggers = {
                        g["recover_user_inputs"][-1]["event_id"]
                        for g in recovery_groups
                        if g["tenant"] == t
                    }

                    def material(row, allowed_triggers=tenant_recovery_triggers):
                        return material_node(row, allowed_triggers)

                    for group in [*recovery_groups, *verified_groups]:
                        if group["tenant"] != t:
                            continue
                        from engram_pilot_completion_fixtures import verified_recovered_user_receipt

                        verified_recovered_user_receipt(final["snapshot"], group)
                        record["checks"].append(
                            {
                                "name": group["name"] + " final exact recovered receipt",
                                "passed": True,
                            }
                        )

                    after_nodes = {(r[0], r[1]): material(r) for r in final["snapshot"]["nodes"]}

                    def material_edge(row):
                        allowed = (
                            {"created_at"}
                            if row[0] == "Summary" and row[2] == "SUMMARIZES"
                            else set()
                        )
                        return {k: v for k, v in row[5].items() if k not in allowed}

                    after_edges = {
                        tuple(r[:5]): material_edge(r) for r in final["snapshot"]["edges"]
                    }
                    durable_json(
                        directory / (t + "-derived-refresh.json"),
                        {
                            "approved": "Summary content/created_at and Event importance refresh",
                            "before_nodes": before["snapshot"]["nodes"],
                            "after_nodes": final["snapshot"]["nodes"],
                            "before_edges": before["snapshot"]["edges"],
                            "after_edges": final["snapshot"]["edges"],
                        },
                    )
                    record["checks"].append(
                        {
                            "name": t + " prior graph preserved except approved derived refresh",
                            "passed": all(
                                after_nodes.get((r[0], r[1]))
                                == material(
                                    [r[0], r[1], correction_updates.get((r[0], r[1]), r[2])]
                                )
                                for r in before["snapshot"]["nodes"]
                            )
                            and all(
                                after_edges.get(tuple(r[:5])) == material_edge(r)
                                for r in before["snapshot"]["edges"]
                            ),
                        }
                    )
                    old_episodes = {r[1] for r in before["snapshot"]["nodes"] if r[0] == "Episode"}
                    record["checks"].append(
                        {
                            "name": t + " exact prior Episode membership retained",
                            "passed": episode_membership_edges(before["snapshot"], old_episodes)
                            == episode_membership_edges(final["snapshot"], old_episodes),
                        }
                    )
                    record["checks"].append(
                        {
                            "name": t + " final zero pending and exactly declared DLQ",
                            "passed": not final["snapshot"]["pending"]
                            and declared_dead_letters(
                                final["snapshot"], selected_groups, t, require_all=complete
                            ),
                        }
                    )
                except Exception as exc:
                    record["state"] = "failed"
                    record.setdefault("finalization_errors", []).append(
                        {"tenant": t, "type": type(exc).__name__, "message": str(exc)[:300]}
                    )
                finally:
                    try:
                        close_database(db)
                    except Exception as exc:
                        record["state"] = "failed"
                        record.setdefault("finalization_errors", []).append(
                            {"tenant": t, "close_error": type(exc).__name__}
                        )
        finally:
            litellm.acompletion = original_completion
            spanner.Client = original_client
            structlog.configure(**old_config)
            if record.get("observation_errors") or any(not c["passed"] for c in record["checks"]):
                record["state"] = "failed"
            elif record["state"] == "pending-final-verification":
                record["state"] = (
                    "passed-retained-read-checkpoint"
                    if retained_reads_only
                    else "passed-selected-journeys"
                    if getattr(args, "journeys_only", False)
                    else "passed-spectrum-checkpoint"
                    if selected_groups
                    else "passed-first-checkpoint"
                )
            save()
    if record["state"] not in {
        "passed-first-checkpoint",
        "passed-spectrum-checkpoint",
        "passed-selected-journeys",
        "passed-retained-read-checkpoint",
    }:
        raise RuntimeError("Pilot entry checkpoint failed; inspect retained report")
    print(
        json.dumps(
            {
                "state": record["state"],
                "checks": len(record["checks"]),
                "provider_calls": len(record["provider_calls"]),
                "report": str(directory / "results.json"),
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--predecessor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--spectrum", action="store_true", help="Run the additional frozen journey families"
    )
    parser.add_argument(
        "--journey-file", type=Path, help="Explicit frozen spectrum JSON in the same format"
    )
    parser.add_argument(
        "--journeys-only",
        action="store_true",
        help="Execute selected groups only; no entry checkpoint acceptance claim",
    )
    parser.add_argument(
        "--service-account", default="engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com"
    )
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        parser.error("run ID must be alphanumeric/hyphen")
    asyncio.run(execute(args))


if __name__ == "__main__":
    main()
