"""Bounded live pack assessment, using fresh databases and normal Engram flows.

No production changes, direct artifact inserts, scripted models, or cleanup of
retained goal data. Private bound apps are not the public tenant dispatcher.
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import json
import os
import socket
import subprocess
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import uvicorn
from engram_experiment_support import (
    CONTROL_COLUMNS,
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
from context_graph.adapters.spanner.schema import schema_statements
from context_graph.adapters.spanner.tenant_control import TENANT_CONTROL_DDL, TenantFence
from context_graph.api.app import create_app
from context_graph.settings import Settings
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import VALID_CONSUMERS, _build_consumer

ROOT = Path(__file__).resolve().parents[1]
GCLOUD = "/Users/arunmenon/google-cloud-sdk/bin/gcloud"
PROJECT, INSTANCE = "portiq-mvp", "engram-experiment"
SA = "engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com"
CONFIGURATIONS = {
    "core": ([], []),
    "user": (["user"], []),
    "user-memory": (["user", "memory"], []),
    "pdlc": ([], ["pdlc"]),
    "pdlc-memory": (["memory"], ["pdlc"]),
}
AUTH = "composition-assessment-local-query-key"


def token(*, impersonate=False):
    command = [GCLOUD, "auth", "print-access-token"]
    if impersonate:
        command.append("--impersonate-service-account=" + SA)
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Credential refresh failed; credential output suppressed")
    return result.stdout.strip()


def database_id(run_id, config):
    suffix = {"user-memory": "um", "pdlc-memory": "pm"}.get(config, config)
    return f"engram-assess-{run_id}-{suffix}"


def settings_for(run_id, config, *, target_database=None):
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "spanner")
    settings.spanner.project = PROJECT
    settings.spanner.instance = INSTANCE
    settings.spanner.database = target_database or database_id(run_id, config)
    settings.spanner.emulator_host = None
    settings.spanner.create_if_missing = False
    settings.spanner.allow_create_on_instance = False
    settings.archive.enabled = False
    settings.ontology.builtin_packs, settings.ontology.packs = CONFIGURATIONS[config]
    settings.ontology.trusted_source_ids = ["demo.query"]
    settings.ontology.serve_unevaluated = True
    settings.intent.use_llm = False
    settings.auth.api_key = AUTH
    settings.rate_limit.enabled = False
    settings.consumer.block_timeout_ms = 100
    settings.consumer.projection_batch_size = 1
    settings.consumer.projection_batch_timeout_ms = 100
    settings.query.default_timeout_ms = 30000
    settings.llm.timeout_seconds = 30
    settings.llm.max_retries = 0
    for kind in VALID_CONSUMERS:
        setattr(settings.consumer, "group_" + kind, "assessment-" + kind)
    return settings


def binding_for(run_id, config, *, target_database=None, epoch=1):
    return TenantBinding.from_settings(
        "assessment-" + config,
        "assessment-" + run_id + "-" + config,
        epoch,
        settings_for(run_id, config, target_database=target_database),
        engine_revision="composition-assessment-v1",
    )


def manifest(run_id):
    return {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "Five private bound runtimes; real HTTP, five workers, real model and Spanner",
        "limitations": [
            "Not public tenant dispatcher acceptance",
            "Unevaluated-bundle development gate enabled",
            "No historical migration",
            "No new Memory semantics or producer",
        ],
        "retention": (
            "Preserve assessment databases and evidence; do not modify existing goal targets"
        ),
        "configurations": {
            name: {
                "database": database_id(run_id, name),
                "packs": binding_for(run_id, name).bundle.pack_identities,
            }
            for name in CONFIGURATIONS
        },
        "expected_checks": [
            "Normal event accepted, one ledger row, one Event, retrievable through subgraph API",
            "Exact retry does not add ledger or graph records",
            "Invalid event rejected without writes",
            "Session-end triggers real extraction; core and user results checked separately",
            "User-disabled selections have no user-profile/preference outputs",
            "User-enabled selections produce a profile and preference, retrievable via user API",
            "Diagnostic: composed graph reader retains the enabled profile (not HTTP acceptance)",
            "PDLC admission and Change artifact/evidence retrieval succeed only with PDLC selected",
            "Memory-selected configurations have no useful Memory producer (blocked capability)",
            "Worker delivery completion and dead letters recorded, never treated as output proof",
            "Enrichment keywords persist for every accepted event after workers finish",
            "Same event/session identities across databases do not leak tenant-specific content",
        ],
    }


def prepare(run_id, directory):
    credentials = Credentials(token=token())

    def create(config):
        path = directory / (config + "-preparation.json")
        dbid = database_id(run_id, config)
        record = {"database": dbid, "state": "creation intended"}
        durable_json(path, record)
        client = spanner.Client(project=PROJECT, credentials=credentials)
        db = client.instance(INSTANCE).database(
            dbid, ddl_statements=[*schema_statements(384), TENANT_CONTROL_DDL]
        )
        try:
            if db.exists():
                raise RuntimeError("Refusing to adopt an existing database")
            operation = db.create()
            record.update(state="DDL in progress", operation=operation.operation.name)
            durable_json(path, record)
            operation.result(timeout=240)
            command = [
                GCLOUD,
                "spanner",
                "databases",
                "add-iam-policy-binding",
                dbid,
                "--project=" + PROJECT,
                "--instance=" + INSTANCE,
                "--member=serviceAccount:" + SA,
                "--role=roles/spanner.databaseAdmin",
                "--condition=None",
                "--quiet",
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=45)
            if result.returncode:
                raise RuntimeError("Database-specific IAM grant failed: " + result.stderr[-1000:])
            record.update(state="schema and database-specific IAM prepared")
        except Exception as exc:
            record.update(state="failed", error=type(exc).__name__ + ": " + str(exc))
        finally:
            durable_json(path, record)
            client.close()
        print(json.dumps({"configuration": config, **record}), flush=True)
        return record["state"] == "schema and database-specific IAM prepared"

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        return all(list(executor.map(create, CONFIGURATIONS)))


def event(run_id, key, *, event_type="observation.input", payload=None):
    return dict(
        event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + key)),
        event_type=event_type,
        occurred_at="2026-10-10T02:00:00+00:00",
        session_id="composition:" + run_id,
        agent_id="assessment-agent",
        trace_id=run_id,
        payload_ref="assessment:" + key,
        payload=payload or {},
    )


async def run_configuration(
    run_id, config, directory, *, target_database=None, epoch=1, prebound=False
):
    path = directory / (config + "-observations.json")
    evidence = {"configuration": config, "checks": [], "responses": [], "state": "starting"}
    durable_json(path, evidence)
    consumers, tasks, stores = [], [], []
    server = server_task = None
    database = None
    binding = binding_for(run_id, config, target_database=target_database, epoch=epoch)
    settings = binding.settings()
    credentials = Credentials(token=token(impersonate=True))
    original_client = spanner.Client

    def authenticated_client(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original_client(*args, **kwargs)

    spanner.Client = authenticated_client
    client = authenticated_client(project=PROJECT)
    pool = BurstyPool()
    database = client.instance(INSTANCE).database(settings.spanner.database, pool=pool)
    prepare_cleanup(database, client, pool)

    def check(name, passed, detail=None, *, status=None):
        evidence["checks"].append(
            dict(name=name, status=status or ("PASS" if passed else "FAIL"), detail=detail)
        )
        durable_json(path, evidence)

    try:
        before = await asyncio.to_thread(fingerprint, database)
        assert not any(v["count"] for v in before.values()), (
            "Assessment DB is not empty; refusing adoption"
        )
        owner = [*TenantFence.from_binding(binding)._identity(), "active"]
        existing_owner = await asyncio.to_thread(read_owner, database)
        if prebound:
            assert existing_owner == [owner], "Prebound assessment authority differs"
        else:
            assert not existing_owner, "Assessment target already bound"
        evidence["owner_intent"] = owner
        durable_json(path, evidence)

        # Control metadata only. All application data below enters through HTTP.
        def bind():
            with database.batch() as batch:
                batch.insert(
                    "TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *owner]]
                )

        if not prebound:
            await asyncio.to_thread(bind)
        assert await asyncio.to_thread(read_owner, database) == [owner]
        app = create_app(binding.settings(), bundle=binding.bundle)
        app.state.tenant_binding = binding
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                DemoAuthentication(app, binding, token=AUTH),
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
        assert server.started, "HTTP startup timeout"
        for kind in VALID_CONSUMERS:
            consumer, store = await _build_consumer(
                kind, binding.settings(), tenant_binding=binding
            )
            consumers.append(consumer)
            stores.append(store)
            tasks.append(asyncio.create_task(consumer.run()))

        async def settled():
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                for task in tasks:
                    if task.done():
                        await task
                        raise RuntimeError("Worker stopped unexpectedly")
                lags = await asyncio.gather(*(c._subscription.lag() for c in consumers))
                state = await asyncio.to_thread(snapshot, database)
                if all(lag == 0 for lag in lags) and not state["pending"]:
                    return state
                await asyncio.sleep(0.2)
            raise TimeoutError("Workers did not complete delivery within 60 seconds")

        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + AUTH},
            timeout=40,
        ) as http:

            async def request(method, route, body=None):
                response = await http.request(method, route, json=body)
                try:
                    answer = response.json()
                except ValueError:
                    answer = response.text
                evidence["responses"].append(
                    dict(
                        method=method,
                        route=route,
                        input=body,
                        status=response.status_code,
                        body=answer,
                    )
                )
                durable_json(path, evidence)
                return response.status_code, answer

            text = (
                f"My name is Casey. I am an engineer on tenant {config}. "
                "I prefer concise bullet-point answers. "
                "I use Python to build the Orion service."
            )
            observation = event(run_id, "observation", payload={"content": text, "input": text})
            status, _ = await request("POST", "/v1/events", observation)
            check("core admission", status == 201, status)
            if status != 201:
                raise RuntimeError("Core admission failed")
            state = await settled()
            check(
                "core ledger and Event",
                len(state["events"]) == 1
                and any(n[:2] == ["Event", observation["event_id"]] for n in state["nodes"]),
            )
            query = dict(
                query="event " + observation["event_id"],
                session_id=observation["session_id"],
                agent_id=observation["agent_id"],
                seed_nodes=[observation["event_id"]],
                intent="what",
                max_depth=1,
                timeout_ms=30000,
            )
            status, answer = await request("POST", "/v1/query/subgraph", query)
            check(
                "core API retrieval",
                status == 200 and observation["event_id"] in answer.get("nodes", {}),
            )
            before_retry = await asyncio.to_thread(fingerprint, database)
            status, answer = await request("POST", "/v1/events", observation)
            state = await settled()
            check(
                "exact retry ledger idempotency",
                status in (200, 201) and len(state["events"]) == 1,
                answer,
            )
            invalid = event(run_id, "invalid")
            invalid.pop("session_id")
            status, answer = await request("POST", "/v1/events", invalid)
            check(
                "invalid event no writes",
                status == 422 and await asyncio.to_thread(fingerprint, database) == before_retry,
                status,
            )

            end = event(run_id, "session-end", event_type="system.session_end")
            status, _ = await request("POST", "/v1/events", end)
            check("session-end admission", status == 201)
            state = await settled()
            labels = [node[0] for node in state["nodes"]]
            check("session produces core entities", "Entity" in labels)
            user_enabled = "user" in CONFIGURATIONS[config][0]
            if user_enabled:
                check("user profile produced", "UserProfile" in labels)
                check("user preference produced", "Preference" in labels)
                status, answer = await request("GET", "/v1/users/user:assessment-agent/profile")
                check("user profile API retrieval", status == 200, answer)
                status, answer = await request("GET", "/v1/users/user:assessment-agent/preferences")
                check("user preferences API retrieval", status == 200 and bool(answer), answer)
                status, answer = await request(
                    "POST",
                    "/v1/query/subgraph",
                    {
                        **query,
                        "query": "How does Casey prefer answers?",
                        "intent": "personalize",
                        "max_depth": 3,
                    },
                )
                check("personalization API responds", status == 200, answer)
                key = ("UserProfile", "profile:user:assessment-agent")
                observed = await app.state.stores.pack_reads.read_keyed_nodes([key])
                check(
                    "diagnostic: composed profile identity",
                    key in observed,
                    "Direct composed-reader diagnostic on HTTP-produced data; not API acceptance",
                )
            else:
                check(
                    "disabled user outputs absent",
                    not (
                        {"UserProfile", "Preference", "Skill", "Workflow", "BehavioralPattern"}
                        & set(labels)
                    ),
                )

            pr = event(
                run_id,
                "change",
                event_type="pdlc.change.created",
                payload={
                    "repo": "assessment/" + config,
                    "number": 7,
                    "title": "Tenant " + config + " change",
                },
            )
            status, answer = await request("POST", "/v1/events", pr)
            pdlc_enabled = bool(CONFIGURATIONS[config][1])
            check("PDLC selection admission", status == (201 if pdlc_enabled else 422), answer)
            state = await settled()
            expected_keywords = {
                observation["event_id"]: ["observation", "input"],
                end["event_id"]: ["system", "session_end"],
            }
            if pdlc_enabled and status == 201:
                expected_keywords[pr["event_id"]] = ["pdlc", "change", "created"]
            event_props = {key: props for label, key, props in state["nodes"] if label == "Event"}
            check(
                "enrichment persists after worker completion",
                all(
                    event_props.get(key, {}).get("keywords") == keywords
                    for key, keywords in expected_keywords.items()
                ),
                {
                    key: {
                        "expected": keywords,
                        "actual": event_props.get(key, {}).get("keywords"),
                    }
                    for key, keywords in expected_keywords.items()
                },
            )
            if pdlc_enabled and status == 201:
                change_id = "Change:assessment/" + config + "|7"
                check(
                    "PDLC Change projected",
                    any(n[:2] == ["Change", change_id] for n in state["nodes"]),
                )
                status, answer = await request(
                    "POST",
                    "/v1/query/artifacts",
                    {
                        "query": "trace this change",
                        "seed_node_ids": [change_id],
                        "include_untrusted": False,
                    },
                )
                artifact = answer.get("nodes", {}).get(change_id, {})
                check(
                    "PDLC artifact API with evidence",
                    status == 200
                    and set(answer.get("nodes", {})) == {change_id}
                    and artifact.get("node_type") == "Change"
                    and artifact.get("attributes", {}).get("title")
                    == "Tenant " + config + " change"
                    and artifact.get("provenance", {}).get("event_id") == pr["event_id"],
                    answer,
                )
            else:
                check(
                    "disabled PDLC outputs absent", "Change" not in [n[0] for n in state["nodes"]]
                )
            check("dead letters absent", not state["dead_letters"], state["dead_letters"])
            if "memory" in CONFIGURATIONS[config][0]:
                check(
                    "useful Memory behavior",
                    False,
                    "No registered Belief/Goal/Episode producer; no conversion invented",
                    status="BLOCKED",
                )
            evidence["final_snapshot"] = state
            evidence["state"] = (
                "completed with findings"
                if any(c["status"] != "PASS" for c in evidence["checks"])
                else "completed"
            )
    except Exception as exc:
        evidence.update(
            state="failed",
            error=type(exc).__name__ + ": " + str(exc),
            traceback=traceback.format_exc(),
        )
    finally:
        evidence["shutdown_errors"] = await stop_demo(consumers, tasks, stores, server, server_task)
        if database is not None:
            try:
                evidence["retained_snapshot"] = await asyncio.to_thread(snapshot, database)
            except Exception as exc:
                evidence["snapshot_error"] = type(exc).__name__ + ": " + str(exc)
            await asyncio.to_thread(close_database, database)
        spanner.Client = original_client
        durable_json(path, evidence)
        print(
            json.dumps(
                {
                    "configuration": config,
                    "state": evidence["state"],
                    "checks": evidence["checks"],
                    "error": evidence.get("error"),
                }
            ),
            flush=True,
        )
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=("prepare", "run"), required=True)
    parser.add_argument("--configuration", choices=CONFIGURATIONS)
    args = parser.parse_args()
    import re

    if not re.fullmatch(r"[a-z0-9]{4,8}", args.run_id):
        parser.error("run-id must be 4–8 lowercase letters/digits")
    os.environ.pop("SPANNER_EMULATOR_HOST", None)
    os.environ["HF_HUB_OFFLINE"] = "1"
    directory = ROOT / "docs/review/spanner-compatibility/runs" / ("composition-" + args.run_id)
    directory.mkdir(exist_ok=True)
    if args.phase == "prepare":
        if (directory / "manifest.json").exists():
            parser.error("Existing preparation manifest; reconcile it rather than overwrite")
        durable_json(directory / "manifest.json", manifest(args.run_id))
        raise SystemExit(0 if prepare(args.run_id, directory) else 1)
    if not (directory / "manifest.json").exists():
        parser.error("Preparation manifest required")
    selected = [args.configuration] if args.configuration else list(CONFIGURATIONS)
    results = []
    for config in selected:
        if (directory / (config + "-observations.json")).exists():
            parser.error("Existing run evidence; refusing overwrite")
        results.append(asyncio.run(run_configuration(args.run_id, config, directory)))
    success = all(
        result["state"] == "completed"
        and bool(result["checks"])
        and not result.get("shutdown_errors")
        and not result.get("snapshot_error")
        and all(check["status"] == "PASS" for check in result["checks"])
        for result in results
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
