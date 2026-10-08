"""Run tracked Engram flows against the explicitly disposable real Spanner DB.

No Redis/Neo4j runners. Credentials are read privately from four assignment
lines. Direct SQL is restricted to fixture reset and persisted-state inspection.
Requires disposable-database authorization; preserves the source database/schema.
The ontology phase can provision/drop a separate manifest-owned target.
Each phase starts/finishes its own persistent run record.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import shlex
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility"
TABLES = (
    "GraphEdges",
    "GraphNodes",
    "ConsumerDeadLetters",
    "ConsumerDeliveries",
    "ConsumerCursors",
    "ConsumerGroups",
    "Events",
)


def load_credentials(path: Path) -> dict[str, str]:
    keys = (
        "GOOGLE_CLOUD_PROJECT",
        "SPANNER_INSTANCE_ID",
        "SPANNER_DATABASE_ID",
        "GOOGLE_OAUTH_ACCESS_TOKEN",
    )
    result = {}
    for line in path.read_text().splitlines():
        if any(
            line.startswith(prefix) for key in keys for prefix in (key + "=", "export " + key + "=")
        ):
            key, _, value = shlex.split(line)[-1].partition("=")
            result[key] = value
    if set(result) != set(keys):
        raise ValueError("four expected credential assignments required")
    return result


def configure(values: dict[str, str], packs: str = "pdlc") -> None:
    for key in ("SPANNER_EMULATOR_HOST", "CG_SPANNER_EMULATOR_HOST"):
        os.environ.pop(key, None)
    for key in ("EVENT_LOG", "SUBSCRIPTION", "GRAPH", "KEYWORD_INDEX", "VECTOR_INDEX"):
        os.environ["CG_STORAGE_" + key] = "spanner"
    os.environ.update(
        CG_SPANNER_PROJECT=values["GOOGLE_CLOUD_PROJECT"],
        CG_SPANNER_INSTANCE=values["SPANNER_INSTANCE_ID"],
        CG_SPANNER_DATABASE=values["SPANNER_DATABASE_ID"],
        CG_SPANNER_CREATE_IF_MISSING="false",
        CG_SPANNER_ALLOW_CREATE_ON_INSTANCE="false",
        CG_ONTOLOGY_PACKS=packs,
        CG_ONTOLOGY_PACK_DIRS=str(ROOT / "tests/fixtures/packs/crm"),
        CG_ONTOLOGY_TRUSTED_SOURCES="webhook:github,webhook:jira,importer:crm",
        CG_CONSUMER_BLOCK_TIMEOUT_MS="20",
        CG_CONSUMER_PROJECTION_BATCH_TIMEOUT_MS="20",
        CG_ONTOLOGY_EVAL_STATE_TTL_S="0",
        CG_WEBHOOK_GITHUB_SECRET="compat-test-secret",
        CG_WEBHOOK_JIRA_SECRET="compat-test-secret",
        CG_INTENT_USE_LLM="false",
        LITELLM_LOCAL_MODEL_COST_MAP="true",
    )
    for key in ("CG_AUTH_API_KEY", "CG_AUTH_ADMIN_KEY"):
        os.environ.pop(key, None)  # ASGI fixture process only; external HTTP runs use keys.


class Run:
    def __init__(self, phase: str, values: dict[str, str], credential_file: Path) -> None:
        self.id = f"20261006-cloud-{phase}-{uuid4().hex[:8]}"
        self.directory = RECORDS / "runs" / self.id
        self.checks: list[dict] = []
        self.resets: list[dict] = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        manifest = {
            "run_id": self.id,
            "phase": phase,
            "backend": "real_spanner",
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "companion_sha256": {name:hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
                                 for name in ("engram_spanner_compat_remaining.py","engram_spanner_compat_pack_cases.py","engram_spanner_process_bootstrap.py","engram_spanner_compat_completion.py")
                                 if (ROOT / "scripts" / name).exists()},
            "started_at": datetime.now(UTC).isoformat(),
            "target": {
                k: values[k]
                for k in ("GOOGLE_CLOUD_PROJECT", "SPANNER_INSTANCE_ID", "SPANNER_DATABASE_ID")
            },
            "authorization": "user explicitly confirmed existing engram DB disposable",
            "auth": "explicit token SDK bootstrap; unmodified ADC startup not proved",
            "credential_window_file_updated_at": datetime.fromtimestamp(
                credential_file.stat().st_mtime, UTC
            ).isoformat(),
            "all_storage_ports": "spanner",
            "fixture_reset": list(TABLES),
            "schema_changes": (
                "ontology may initialize empty disposable target; source schema preserved"
                if phase == "ontology"
                else False
            ),
            "database_drop": (
                "only target successfully created by this run; user databases preserved"
                if phase == "ontology"
                else False
            ),
            "provider_mode": ("one bounded configured live LLM call" if phase=="live-pack" else "scripted LLM; local embedding if installed; no paid provider calls"),
            "max_phase_seconds": 600,
            "phase_limits": {"evaluation-completion": {"events":0,"eval_TTL_seconds":0.08,"synthetic_state_read_failure":True}, "consolidation-completion": {"events":4,"max_cycles":6,"provider":"scripted failure/recovery","overlap_gate":True}, "context-completion": {"events":10,"max_pages":6,"page_size":2,"synthetic_SQL_delay_seconds":0.12,"query_budget_seconds":0.03},
                             "ingress-completion": {"max_events":30,"batch_limit":3,"import_limit":6,"import_chunk":2,"synthetic_store_failure":True},
                             "recovery": {"events": 4, "worker_processes_at_once": 1,
                                            "faults": "synthetic write/ACK boundary; real process kills"},
                             "combined": {"events": 19, "worker_processes_at_once": 1},
                             "concurrency": {"events": 18, "worker_processes_at_once": 2,
                                             "read_gates": "controlled replica scheduling"},
                             "startup": {"writes": 0, "API_processes_at_once": 1,
                                         "database_creation": False},
                             "schema": {"writes": 0, "API_processes_at_once": 1},
                             "endpoints": {"events": 9, "Entity_fixture_nodes": 4,
                                           "provider": "fixed384-vector, synthetic feedback fault"},
                             "upgrades": {"events": 1, "targets": ["engram","engram-compat-target"],
                                          "synthetic_replay_write_failure": True,
                                          "public_document_expiry": True},
                             "pack-cases": {"events": 8, "catalog_nodes": 3, "lookup_limit": 2},
                             "maintenance": {"events": 7, "fixture_entities": 2, "fixture_edges": 3,
                                             "max_timer_cycles": 1, "provider": "none"},
                             "commit-cases": {"events": 13, "duplicate_requests": 6, "mutations": 66, "bytes": 2048,
                                              "synthetic_third_chunk_failure": True},
                             "pack-policy": {"events": 3, "authoritative_fixture_nodes": 1, "proposal_node_limit": 1,
                                             "proposal_link_limit": 1, "provider": "scripted"},
                             "knowledge-safe": {"events": 6, "users": 2, "interest_creation": False,
                                                "provider": "scripted", "max_phase_seconds": 600},
                             "keyword-features": {"events":4,"fixture_vectors":2,"dims":384,"query_limit":10,
                                                  "provider":"scripted","HyDE_timeout_seconds":0.05},
                             "subscriptions": {"events":18,"shards":16,"worker_loops_at_once":2,
                                               "block_ms":3000,"pending_page_size":3,"synthetic_lost_commit_response":True},
                             "webhook-handlers": {"deliveries":49,"max_events":43,"provider":"none","worker_loops_at_once":1},
                             "enrichment-cases": {"events":5,"worker_loops_at_once":1,"configured_dims":384,
                                                  "invalid_vectors":"3 dims / zero384", "synthetic_provider_and_storage_failures":True},
                             "archive-restore": {"events":2,"archive":"run-owned FS directory",
                                                 "synthetic_archive_failure":True,"worker_loops_at_once":1},
                             "ordering-races": {"events":3,"worker_loops_at_once":1,"provider":"scripted384",
                                                "schedule":"enrichment first / causal parent later"},
                             "live-pack": {"events":1,"paid_calls_max":1,"max_output_tokens":256,"retries":0,
                                           "provider":"existing configured model, no substitution","timeout_seconds":30},
                             "user-feedback": {"events":5,"users":2,"provider":"none","worker_loops_at_once":1},
                             "feedback-recheck": {"writes":0,"fixture":"prior user-feedback"},
                             "user-delete-recheck": {"writes":0,"fixture":"user-feedback-09524f75","max_graph_nodes_read":9}}
                .get(phase, {}),
        }
        path = Path("/private/tmp") / f"{self.id}-manifest.json"
        path.write_text(json.dumps(manifest))
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/track_spanner_compatibility.py"),
                "start",
                "--run-id",
                self.id,
                "--manifest",
                str(path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        (self.directory / "harness.py").write_text(Path(__file__).read_text())
        companion = ROOT / "scripts/engram_spanner_compat_remaining.py"
        if companion.exists():
            (self.directory / companion.name).write_text(companion.read_text())
        pack_cases = ROOT / "scripts/engram_spanner_compat_pack_cases.py"
        if pack_cases.exists():
            (self.directory / pack_cases.name).write_text(pack_cases.read_text())
        completion=ROOT / "scripts/engram_spanner_compat_completion.py"
        if completion.exists():(self.directory / completion.name).write_bytes(completion.read_bytes())
        self.log = (self.directory / "execution.log").open("w")
        sys.stdout = self.log
        sys.stderr = self.log

    async def check(
        self, name: str, scenarios: list[str], function, *, timeout_seconds=120
    ) -> None:
        started = time.monotonic()
        try:
            observation = await asyncio.wait_for(function(), timeout=timeout_seconds)
            item = {
                "name": name,
                "scenarios": scenarios,
                "verdict": "passed",
                "observation": observation,
            }
        except Exception as exc:
            print(traceback.format_exc(), flush=True)
            # Error strings can contain request data; scrub tokens before persistence.
            item = {
                "name": name,
                "scenarios": scenarios,
                "verdict": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:1200],
            }
        item["seconds"] = round(time.monotonic() - started, 2)
        self.checks.append(item)
        print(json.dumps(item), flush=True)

    async def reset(self, database, values) -> None:
        if (
            database.database_id != "engram"
            or values["GOOGLE_CLOUD_PROJECT"] != "portiq-mvp"
            or values["SPANNER_INSTANCE_ID"] != "engram-experiment"
        ):
            raise RuntimeError("refusing reset outside user-authorized disposable target")
        for table in TABLES:
            rows = await asyncio.to_thread(
                database.execute_partitioned_dml, f"DELETE FROM {table} WHERE TRUE"
            )
            self.resets.append({"table": table, "rows": rows})

    def finish(self, values, summary="") -> None:
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.log.close()
        path = self.directory / "execution.log"
        sanitized = path.read_text(errors="replace")
        for secret in (values["GOOGLE_OAUTH_ACCESS_TOKEN"],os.environ.get("OPENAI_API_KEY")):
            if secret:sanitized=sanitized.replace(secret,"[REDACTED_CREDENTIAL]")
        path.write_text(sanitized)
        data = {
            "checks": self.checks,
            "resets": self.resets,
            "summary": summary,
            "scope": "subchecks; full scenario rows remain pending until all requirements proved",
            "cleanup": "no database/schema deletion; final fixture retained for inspection",
        }
        text = json.dumps(data, indent=2).replace(
            values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[REDACTED_TOKEN]"
        )
        if os.environ.get("OPENAI_API_KEY"):
            text=text.replace(os.environ["OPENAI_API_KEY"],"[REDACTED_CREDENTIAL]")
        (self.directory / "observations.json").write_text(text + "\n")
        results = {
            "scenarios": [],
            "summary": summary,
            "cleanup": data["cleanup"],
            "evidence": str((self.directory / "observations.json").relative_to(ROOT)),
        }
        p = Path("/private/tmp") / f"{self.id}-results.json"
        p.write_text(json.dumps(results))
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/track_spanner_compatibility.py"),
                "finish",
                "--run-id",
                self.id,
                "--results",
                str(p),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print(
            json.dumps(
                {
                    "run_id": self.id,
                    "checks": [
                        {k: c[k] for k in ("name", "verdict", "seconds")} for c in self.checks
                    ],
                    "summary": summary,
                }
            )
        )


async def journeys(run: Run, database, values) -> None:
    import httpx
    import pytest
    from tests.unit import test_pack_toy_end_to_end as crm
    from tests.unit import test_pdlc_end_to_end as pdlc
    from tests.unit.test_backend_end_to_end import _run_flow

    from context_graph.adapters.registry import open_stores
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ontology.versioning import reconcile
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    async def drain(consumer, stores, group):
        # The legacy helper queries lag before group creation; missing cursors
        # produce zero on real Spanner, causing premature stop. Establish group first.
        await consumer.ensure_group()
        probe = stores.subscription(group, "compat-drain-probe")
        task = asyncio.create_task(consumer.run())
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                await asyncio.sleep(0.1)
                if task.done():
                    await task
                    raise RuntimeError("worker exited before drain")
                if await probe.lag() == 0 and not await consumer._subscription.delivery_counts(100):
                    break
            else:
                raise TimeoutError("worker drain deadline")
        finally:
            consumer.stop()
            await asyncio.wait_for(task, timeout=15)

    async def agent():
        await run.reset(database, values)
        configure(values)
        settings = Settings()
        stores = await open_stores(settings, prepare_ingest=True)
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("tests.unit.test_backend_end_to_end._drain", drain)
            await _run_flow(mp, settings, stores, "spanner")
        return {
            "event_count": 3,
            "ledger_projection_enrichment_context_lineage_subgraph_health": "asserted",
            "process_model": (
                "ASGI and worker loops in one process; separate-process acceptance still required"
            ),
        }

    await run.check(
        "agent_memory_API_worker_journey",
        ["APP-01", "ING-01", "PROJ-01", "ENR-01", "MEM-01", "MEM-02", "MEM-03"],
        agent,
    )

    async def domain():
        await run.reset(database, values)
        configure(values)
        os.environ["CG_WEBHOOK_GITHUB_SECRET"] = pdlc.SECRET
        os.environ["CG_WEBHOOK_JIRA_SECRET"] = pdlc.SECRET
        settings = Settings()
        stores = await open_stores(settings, prepare_ingest=True)
        with pytest.MonkeyPatch.context() as mp:
            # Run stock API/worker journey, but do not let the legacy helper create/drop a database.
            async def status_only(client, settings, stores, backend):
                response = await client.get("/v1/ontology")
                assert response.status_code == 200
                body = response.json()
                assert body["graph"]["version"] == body["version"]

            mp.setattr(pdlc, "_check_versioning", status_only)
            mp.setattr(pdlc, "_drain", drain)
            await pdlc._run(mp, settings, stores, "spanner")
        return {
            "signed_deliveries": len(pdlc.DELIVERIES),
            "projection_gate_questions_pack_extraction": "asserted",
            "blue_green": "not exercised; no replacement memory graph",
        }

    await run.check(
        "signed_PDLC_API_projection_artifact_extraction",
        ["APP-02", "HOOK-01", "HOOK-02", "ART-01", "PEXT-01", "PEXT-02", "ONT-01"],
        domain,
    )

    async def sales():
        await run.reset(database, values)
        configure(values, "crm")
        settings = Settings()
        stores = await open_stores(settings, prepare_ingest=True)
        projector = configured_projector(settings.ontology)

        async def existing_stores(*args, **kwargs):
            return stores

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("context_graph.api.app.open_stores", existing_stores)
            app = create_app()
            async with (
                lifespan(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://compat"
                ) as client,
            ):
                response = await client.post("/v1/events/batch", json={"events": crm._events()})
                assert response.status_code == 201 and response.json()["accepted"] == len(
                    crm.HISTORY
                )
                await reconcile(
                    stores.graph,
                    stores.event_log,
                    projector,
                    allow_breaking=False,
                    batch_size=100,
                    lookup_limit=settings.ontology.lookup_limit,
                )
                worker = ProjectionConsumer(
                    stores.subscription(settings.consumer.group_projection, "compat"),
                    stores.event_log,
                    stores.graph,
                    settings,
                    projector,
                )
                await drain(worker, stores, settings.consumer.group_projection)
                await crm._check_graph(stores)
                await crm._check_gate(client, settings, stores, projector)
                await crm._check_questions(client)
        return {
            "ingested": len(crm.HISTORY),
            "lifecycle_graph_eval_and_pipeline_coverage_questions": "asserted",
        }

    await run.check(
        "CRM_API_projection_gate_retrieval",
        ["APP-03", "ING-02", "PROJ-02", "ART-02", "ART-05"],
        sales,
    )


async def boundaries(run: Run, database, values) -> None:
    import gzip
    import hmac
    from datetime import timedelta

    import httpx
    from tests.unit.test_pack_toy_end_to_end import _events

    from context_graph.api.app import create_app, lifespan

    await run.reset(database, values)
    configure(values, "pdlc,crm")
    app = create_app()
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://compat") as client:

            def event(**changes):
                body = {
                    "event_id": str(uuid4()),
                    "event_type": "tool.execute",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "session_id": "compat-boundary",
                    "agent_id": "compat",
                    "trace_id": "compat",
                    "payload_ref": "compat",
                }
                body.update(changes)
                return body

            async def valid_json():
                body = event(
                    payload={
                        "nested": {
                            "float": 0.2002386475503002,
                            "null": None,
                            "bool": True,
                            "unicode": "नमस्ते",
                            "list": [1, "x"],
                        }
                    }
                )
                response = await client.post("/v1/events", json=body)
                assert response.status_code == 201, response.text
                duplicate = await client.post("/v1/events", json=body)
                assert duplicate.json()["status"] == "duplicate"
                (stored,) = await app.state.stores.event_log.get_documents([body["event_id"]])
                assert stored["payload"] == body["payload"]
                return {"created": True, "duplicate": True, "lossless_nested_float": True}

            await run.check(
                "valid_ingest_duplicate_JSON_roundtrip", ["ING-01", "ING-04", "LED-01"], valid_json
            )

            async def missing_payload():
                body = {
                    **_events()[0],
                    "event_type": "crm.deal.created",
                    "payload": {"title": "missing ID"},
                }
                response = await client.post("/v1/events", json=body)
                assert response.status_code == 422, (
                    f"missing pack key accepted HTTP{response.status_code}"
                )

            await run.check("pack_payload_missing_key_rejected", ["ING-01"], missing_payload)

            async def timezone():
                body = event(occurred_at="2026-10-04T12:00:00", ended_at="2026-10-04T12:01:00Z")
                response = await client.post("/v1/events", json=body)
                assert response.status_code == 422, (
                    f"mixed timezone response HTTP{response.status_code}"
                )

            await run.check("mixed_timezone_controlled_error", ["ING-01"], timezone)

            async def gzip_integrity():
                body = gzip.compress(json.dumps(event()).encode())[:-8]
                response = await client.post(
                    "/v1/events", content=body, headers={"Content-Encoding": "gzip"}
                )
                assert response.status_code == 400, f"truncated gzip HTTP{response.status_code}"

            await run.check("truncated_gzip_rejected", ["ING-03"], gzip_integrity)

            async def batch():
                response = await client.post("/v1/events/batch", json={"events": []})
                assert response.status_code == 422
                good = event()
                response = await client.post(
                    "/v1/events/batch", json={"events": [good, "bad", good]}
                )
                body = response.json()
                assert (
                    response.status_code == 201 and body["accepted"] == 2 and body["rejected"] == 1
                )
                assert [r["status"] for r in body["results"]] == ["created", "duplicate"]
                assert body["errors"][0]["index"] == 1
                response = await client.post("/v1/events/batch", json={"events": [good] * 1001})
                assert response.status_code == 422
                return {"mixed_created_duplicate_rejected": True, "empty_and_max_plus_one": True}

            await run.check("batch_mixed_outcomes_and_boundaries", ["ING-02"], batch)

            async def imports():
                old = datetime.now(UTC) - timedelta(days=2)
                events = [
                    event(
                        occurred_at=(old + timedelta(minutes=n)).isoformat(),
                        session_id="compat-import",
                    )
                    for n in [3, 1, 2]
                ]
                body = gzip.compress(
                    b"\n".join([json.dumps(e).encode() for e in events] + [b"invalid-json"])
                )
                response = await client.post(
                    "/v1/events/import", content=body, headers={"Content-Encoding": "gzip"}
                )
                assert response.status_code == 200
                outcomes = [json.loads(line) for line in response.text.splitlines()]
                assert outcomes[-1]["summary"]["created"] == 3
                assert outcomes[-1]["summary"]["rejected"] == 1
                ids = await app.state.stores.event_log.read_session_ids("compat-import")
                assert ids == [events[i]["event_id"] for i in [1, 2, 0]]
                response = await client.post(
                    "/v1/events/import", content=body, headers={"Content-Encoding": "gzip"}
                )
                assert json.loads(response.text.splitlines()[-1])["summary"]["duplicate"] == 3
                return {"gzip_NDJSON_order_invalid_line_retry": True}

            await run.check(
                "historical_import_order_invalid_line_retry", ["ING-05", "LED-02"], imports
            )

            async def undeclared():
                response = await client.post("/v1/events", json=event(event_type="crm.unknown"))
                assert response.status_code == 422
                response = await client.post("/v1/events", json=event(agent_id="webhook:github"))
                assert response.status_code == 422
                return {"namespace_and_reserved_identity": "rejected"}

            await run.check(
                "namespace_and_webhook_identity_guards", ["ING-01", "OPS-02"], undeclared
            )

            async def signed(payload):
                body = json.dumps(payload).encode()
                sig = "sha256=" + hmac.new(b"compat-test-secret", body, hashlib.sha256).hexdigest()
                return await client.post(
                    "/v1/webhooks/github",
                    content=body,
                    headers={"x-github-event": "pull_request", "x-hub-signature-256": sig},
                )

            async def future_hook():
                response = await signed(
                    {
                        "action": "opened",
                        "repository": {"full_name": "compat/app"},
                        "pull_request": {
                            "number": 1,
                            "title": "future",
                            "created_at": "2099-01-01T00:00:00Z",
                        },
                    }
                )
                assert response.status_code in (400, 422), (
                    f"future webhook HTTP{response.status_code}"
                )

            await run.check("webhook_future_envelope_rejected", ["HOOK-03"], future_hook)

            async def bad_hook():
                response = await signed({"repository": ["bad"]})
                assert response.status_code in (400, 422), (
                    f"malformed webhook HTTP{response.status_code}"
                )

            await run.check("webhook_nested_shape_controlled_error", ["HOOK-03"], bad_hook)

            async def signature():
                response = await client.post("/v1/webhooks/github", json={"action": "opened"})
                assert response.status_code == 401
                return {"unsigned": "rejected"}

            await run.check("webhook_signature_guard", ["HOOK-03", "OPS-02"], signature)

            async def observers():
                for url in [
                    "/v1/health",
                    "/v1/admin/health/detailed",
                    "/v1/admin/stats",
                    "/v1/ontology",
                ]:
                    response = await client.get(url)
                    assert response.status_code == 200, f"{url}:HTTP{response.status_code}"
                return {"health_detailed_stats_ontology": "HTTP200"}

            await run.check("observability_routes", ["OPS-01", "ONT-01"], observers)


async def knowledge(run: Run, database, values, *, include_interests=True) -> None:
    """Actual extraction/consolidation loops, with a deterministic provider only."""
    import httpx

    from context_graph.api.app import create_app, lifespan
    from context_graph.settings import Settings
    from context_graph.worker.consolidation import ConsolidationConsumer
    from context_graph.worker.extraction import ExtractionConsumer
    from context_graph.worker.projection import ProjectionConsumer

    await run.reset(database, values)
    configure(values)
    app = create_app()

    class Provider:
        async def extract_from_session(self, **kwargs):
            agent = kwargs["agent_id"]
            return {
                "persona": {"name": agent, "role": "engineer", "tech_level": "advanced"},
                "entities": [{"name": "Spanner", "entity_type": "technology"}],
                "preferences": [
                    {
                        "preference_id": f"pref:{agent}",
                        "key": "database",
                        "polarity": "positive",
                        "about_entity": "Spanner",
                    }
                ],
                "skills": [
                    {"skill_id": "skill:shared-python", "name": "Python", "proficiency": 0.8}
                ],
                "interests": [
                    {"entity_name": "Spanner", "entity_type": "technology", "weight": 0.9}
                ] if include_interests else [],
            }

        async def generate_text(self, prompt):
            return "The session explored Spanner storage and Python."

    async def drain(worker):
        await worker.ensure_group()
        task = asyncio.create_task(worker.run())
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                await asyncio.sleep(0.1)
                if task.done():
                    await task
                    raise RuntimeError("worker exited before drain")
                if (
                    await worker._subscription.lag() == 0
                    and not await worker._subscription.delivery_counts(100)
                ):
                    return
            raise TimeoutError("worker drain deadline")
        finally:
            worker.stop()
            await asyncio.wait_for(task, 15)

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://compat",
        ) as client,
    ):
        stores = app.state.stores
        settings = Settings()
        ids = []

        async def extract():
            for agent in ("compat-a", "compat-b"):
                for kind in ("tool.execute", "system.session_end"):
                    event_id = str(uuid4())
                    ids.append(event_id)
                    response = await client.post(
                        "/v1/events",
                        json={
                            "event_id": event_id,
                            "event_type": kind,
                            "occurred_at": datetime.now(UTC).isoformat(),
                            "session_id": agent,
                            "agent_id": agent,
                            "trace_id": agent,
                            "payload_ref": "payload:compat",
                            "payload": {"content": "I use Spanner and Python"},
                        },
                    )
                    assert response.status_code == 201, response.text
            await drain(
                ProjectionConsumer(
                    stores.subscription(settings.consumer.group_projection, "knowledge-projection"),
                    stores.event_log,
                    stores.graph,
                    settings,
                )
            )
            await drain(
                ExtractionConsumer(
                    stores.subscription(settings.consumer.group_extraction, "knowledge-extraction"),
                    stores.event_log,
                    Provider(),
                    settings,
                    graph_store=stores.graph,
                    user_store=stores.graph,
                )
            )
            responses = {}
            for agent in ("compat-a", "compat-b"):
                for endpoint in (
                    "profile",
                    "preferences",
                    "skills",
                    "patterns",
                    "interests",
                    "data-export",
                ):
                    response = await client.get(f"/v1/users/user:{agent}/{endpoint}")
                    assert response.status_code == 200, response.text
                    responses[f"{agent}/{endpoint}"] = response.json()
                assert responses[f"{agent}/profile"]["display_name"] == f"{agent} (engineer)"
                assert len(responses[f"{agent}/preferences"]) == 1
                assert len(responses[f"{agent}/skills"]) == 1
                assert len(responses[f"{agent}/interests"]) == int(include_interests)
                assert responses[f"{agent}/data-export"]["provenance_chains"]
            entity = await client.get("/v1/entities/entity:Spanner")
            assert entity.status_code == 200, entity.text
            missing = await client.get("/v1/entities/entity:missing")
            assert missing.status_code == 404
            return {
                "user_routes": responses,
                "entity": entity.json(),
                "provider": "scripted; embedding disabled in this extraction case",
                "interest_creation_included": include_interests,
                "scope": "interest write/evidence remains failed under #20 when omitted",
            }

        await run.check(
            "entity_user_extraction_read_export", ["EXT-01", "EXT-02", "USER-01", "APP-01"], extract
        )

        async def feedback():
            before = await stores.event_log.stream_length()
            payload = {
                "query_id": "compat-feedback",
                "session_id": "compat-a",
                "helpful_node_ids": [ids[0], "missing"],
                "irrelevant_node_ids": [ids[1]],
            }
            observations = []
            for _ in range(2):
                response = await client.post("/v1/feedback", json=payload)
                assert response.status_code == 201, response.text
                assert response.json()["bumped"] == 1 and response.json()["decremented"] == 1
                observations.append(response.json())
            assert await stores.event_log.stream_length() == before + 2
            return {
                "responses": observations,
                "resubmission": "two audit events, two adjustments; not idempotent",
            }

        await run.check("feedback_audit_and_missing_node_resubmission", ["FB-01"], feedback)

        async def summarize():
            response = await client.post("/v1/admin/reconsolidate", json={"session_id": "compat-a"})
            assert response.status_code == 200, response.text
            assert response.json()["summaries_created"] >= 1
            settings.decay.reflection_threshold = 1
            settings.decay.reconsolidation_interval_hours = 0.0003
            worker = ConsolidationConsumer(
                stores.subscription(
                    settings.consumer.group_consolidation, "knowledge-consolidation"
                ),
                stores.event_log,
                stores.graph,
                settings,
                llm_client=Provider(),
            )
            await worker.ensure_group()
            task = asyncio.create_task(worker.run())
            try:
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    stats = await stores.graph.get_graph_stats()
                    if stats["nodes"].get("Summary", 0) >= 4:
                        break
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("timer summaries not created")
            finally:
                worker.stop()
                await asyncio.wait_for(task, 20)
            return {
                "admin": response.json(),
                "graph": await stores.graph.get_graph_stats(),
                "timer": "session and agent summaries observed; cycle error log checked separately",
            }

        await run.check("admin_and_timer_consolidation", ["CONS-01", "CONS-02"], summarize)

        async def deletion():
            response = await client.delete("/v1/users/user:compat-a")
            assert response.status_code == 200, response.text
            assert (await client.get("/v1/users/user:compat-a/profile")).status_code == 404
            assert (await client.get("/v1/users/user:compat-a/preferences")).json() == []
            assert (await client.get("/v1/users/user:compat-b/profile")).status_code == 200
            assert len((await client.get("/v1/users/user:compat-b/skills")).json()) == 1
            assert (await client.get("/v1/entities/entity:Spanner")).status_code == 200
            docs = await stores.event_log.get_documents(ids)
            assert all(doc is not None for doc in docs)
            return {
                "deletion": response.json(),
                "other_user_shared_skill_entity_and_ledger": "preserved",
                "user_entity": "redacted tombstone per implementation",
            }

        await run.check("user_delete_shared_resource_preservation", ["USER-02"], deletion)


async def processes(run: Run, database, values, credential_file) -> None:
    """Independent ordinary API/worker processes; provider and token bootstrap only."""
    import socket

    import httpx

    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings

    await run.reset(database, values)
    configure(values)
    stores = await open_stores(Settings())
    settings = Settings()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    api_key, admin_key = uuid4().hex, uuid4().hex
    environment = os.environ.copy()
    environment.update(
        ENGRAM_COMPAT_CREDENTIAL_FILE=str(credential_file),
        ENGRAM_COMPAT_API_PORT=str(port),
        CG_AUTH_API_KEY=api_key,
        CG_AUTH_ADMIN_KEY=admin_key,
        PYTHONPATH=str(ROOT / "src") + ":" + str(ROOT),
        PYTHONUNBUFFERED="1",
    )
    bootstrap = ROOT / "scripts/engram_spanner_process_bootstrap.py"
    (run.directory / "process-bootstrap.py").write_text(bootstrap.read_text())
    workers = {}
    logs = {}

    def start(mode):
        logs[mode] = (run.directory / f"{mode}.log").open("w")
        env = {**environment, "ENGRAM_COMPAT_PROCESS": mode}
        workers[mode] = subprocess.Popen(
            [sys.executable, str(bootstrap)],
            cwd=ROOT,
            env=env,
            stdout=logs[mode],
            stderr=logs[mode],
        )

    try:
        start("api")
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + api_key},
            timeout=10,
        ) as client:

            async def journey():
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    if workers["api"].poll() is not None:
                        raise RuntimeError("API process exited")
                    try:
                        if (await client.get("/v1/health")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("API startup deadline")
                ids = [str(uuid4()), str(uuid4()), str(uuid4())]
                for index, kind in enumerate(
                    ("tool.execute", "tool.execute", "system.session_end")
                ):
                    body = {
                        "event_id": ids[index],
                        "event_type": kind,
                        "occurred_at": datetime.now(UTC).isoformat(),
                        "session_id": "compat-process",
                        "agent_id": "compat-process",
                        "trace_id": "compat-process",
                        "payload_ref": "payload:process",
                        "payload": {"content": "Spanner Python database migration"},
                    }
                    if index:
                        body["parent_event_id"] = ids[index - 1]
                    response = await client.post("/v1/events", json=body)
                    assert response.status_code == 201, response.text
                # Project before extraction so this case isolates cross-process storage.
                start("projection")
                group_fields = ["group_projection"]
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    if (await stores.graph.get_graph_stats())["nodes"].get("Event", 0) == 3:
                        break
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("separate projection did not materialize events")
                for mode in ("enrichment", "extraction", "pack_extraction", "consolidation"):
                    start(mode)
                    group_fields.append("group_" + mode)
                deadline = time.monotonic() + 65
                while time.monotonic() < deadline:
                    ready = all(
                        "pending_drain_completed"
                        in (run.directory / f"{mode}.log").read_text(errors="replace")
                        for mode in workers
                        if mode != "api"
                    )
                    profile = await client.get(
                        "/v1/users/user:compat-process/profile",
                        headers={"Authorization": "Bearer " + admin_key},
                    )
                    drained = True
                    for field in group_fields:
                        sub = stores.subscription(
                            getattr(settings.consumer, field),
                            {
                                "group_projection": "projection-1",
                                "group_enrichment": "enrichment-1",
                                "group_extraction": "extraction-1",
                                "group_pack_extraction": "pack-extraction-1",
                                "group_consolidation": "consolidation-1",
                            }[field],
                        )
                        if await sub.lag() or await sub.delivery_counts(100):
                            drained = False
                    if ready and drained and profile.status_code == 200:
                        break
                    if any(p.poll() is not None for p in workers.values()):
                        raise RuntimeError("process exited during journey")
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("five worker groups did not drain/profile missing")
                context = await client.get("/v1/context/compat-process")
                assert context.status_code == 200 and set(ids).issubset(context.json()["nodes"])
                entity = await client.get("/v1/entities/entity:Spanner")
                assert entity.status_code == 200, entity.text
                query = await client.post(
                    "/v1/query/subgraph",
                    json={
                        "query": "Spanner migration",
                        "session_id": "compat-process",
                        "agent_id": "compat-process",
                    },
                    timeout=60,
                )
                assert query.status_code == 200 and query.json()["nodes"], query.text
                denied = await client.post("/v1/admin/replay", json={"confirm": False})
                assert denied.status_code == 401, denied.text
                reconsolidate = await client.post(
                    "/v1/admin/reconsolidate",
                    json={"session_id": "compat-process"},
                    headers={"Authorization": "Bearer " + admin_key},
                )
                assert (
                    reconsolidate.status_code == 200 and reconsolidate.json()["summaries_created"]
                )
                return {
                    "all_five_worker_processes": "started and drained",
                    "profile": profile.json(),
                    "entity": entity.json(),
                    "context_nodes": len(context.json()["nodes"]),
                    "subgraph_nodes": len(query.json()["nodes"]),
                    "admin_key_separation": "asserted",
                    "summary": reconsolidate.json(),
                    "provider": "scripted; local embedding; interest omitted to isolate issue20",
                }

            await run.check(
                "independent_API_and_five_worker_process_journey",
                ["BOOT-01", "APP-01", "EXT-01", "ENR-01", "OPS-02"],
                journey,
            )
            if run.checks[-1]["verdict"] == "passed":

                async def native_search():
                    def embedded_rows():
                        with database.snapshot() as snapshot:
                            return list(
                                snapshot.execute_sql(
                                    "SELECT node_id, embedding FROM GraphNodes "
                                    "WHERE label = 'Entity' AND embedding IS NOT NULL"
                                )
                            )

                    rows = await asyncio.to_thread(embedded_rows)
                    assert rows, "extraction did not persist an Entity embedding"
                    own, embedding = rows[0]
                    assert len(embedding) == settings.embedding.dimensions
                    hits = await stores.vector_index.nearest(
                        [float(value) for value in embedding], top_k=10, threshold=0.0
                    )
                    assert hits and hits[0].id == own, "native ANN missed its own vector"
                    assert all(0 <= hit.score <= 1 for hit in hits)
                    keyword = await stores.keyword_index.search(
                        "Spanner", session_id="compat-process", limit=10
                    )
                    assert keyword, "native full text returned no matching event"
                    assert not await stores.keyword_index.search(
                        "Spanner", session_id="compat-no-session", limit=10
                    )
                    return {
                        "persisted_vector_dimensions": len(embedding),
                        "self_hit": hits[0].id,
                        "scores": [hit.score for hit in hits],
                        "keyword_hits": [hit.id for hit in keyword],
                        "native_path": "exact dimensions invoke forced ANN index; no fallback",
                        "scope": "self-hit and session-filter smoke; multi-vector recall pending",
                    }

                await run.check(
                    "extraction_embedding_native_ANN_full_text",
                    ["SEARCH-01", "SEARCH-02"],
                    native_search,
                )
    finally:
        exits = {}
        for mode, process in workers.items():
            if process.poll() is None:
                process.terminate()
            try:
                exits[mode] = await asyncio.to_thread(process.wait, timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                exits[mode] = await asyncio.to_thread(process.wait, timeout=5)
            logs[mode].close()
            path = run.directory / f"{mode}.log"
            path.write_text(
                path.read_text(errors="replace")
                .replace(values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[REDACTED_TOKEN]")
                .replace(api_key, "[REDACTED_API_KEY]")
                .replace(admin_key, "[REDACTED_ADMIN_KEY]")
            )
        (run.directory / "process-cleanup.json").write_text(
            json.dumps({"exit_codes": exits, "all_owned_processes_stopped": True}, indent=2)
        )
        await stores.close()


async def replay_boundary(run: Run, database, values, credential_file) -> None:
    """Tie reproduction in a killable real API process."""
    import socket

    import httpx

    from context_graph.adapters.registry import open_stores
    from context_graph.domain.models import EventQuery
    from context_graph.settings import Settings

    await run.reset(database, values)
    configure(values)
    stores = await open_stores(Settings())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    key = uuid4().hex
    environment = os.environ.copy()
    environment.update(
        ENGRAM_COMPAT_CREDENTIAL_FILE=str(credential_file),
        ENGRAM_COMPAT_API_PORT=str(port),
        ENGRAM_COMPAT_PROCESS="api",
        CG_AUTH_API_KEY=key,
        CG_AUTH_ADMIN_KEY=key,
        PYTHONUNBUFFERED="1",
    )
    bootstrap = ROOT / "scripts/engram_spanner_process_bootstrap.py"
    (run.directory / "process-bootstrap.py").write_text(bootstrap.read_text())
    log_path = run.directory / "api.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [sys.executable, str(bootstrap)], cwd=ROOT, env=environment, stdout=log, stderr=log
        )
        try:
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Authorization": "Bearer " + key},
                timeout=10,
            ) as client:
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    try:
                        if (await client.get("/v1/health")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if process.poll() is not None:
                        raise RuntimeError("API process exited")
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("API startup deadline")
                timestamp = datetime.now(UTC).isoformat()
                events = [
                    {
                        "event_id": str(uuid4()),
                        "event_type": "tool.execute",
                        "occurred_at": timestamp,
                        "session_id": "compat-replay-ties",
                        "agent_id": "compat-replay",
                        "trace_id": "compat-replay",
                        "payload_ref": f"payload:{index}",
                    }
                    for index in range(128)
                ]
                response = await client.post("/v1/events/batch", json={"events": events})
                assert response.status_code == 201 and response.json()["accepted"] == 128, (
                    response.text
                )

                async def cursor():
                    first = await stores.event_log.search(EventQuery(limit=100))
                    second = await stores.event_log.search(
                        EventQuery(limit=100, after=first[-1].occurred_at)
                    )
                    observation = {
                        "first_ids": [str(e.event_id) for e in first],
                        "second_ids": [str(e.event_id) for e in second],
                        "same_page": [e.event_id for e in first] == [e.event_id for e in second],
                        "ledger_count": await stores.event_log.stream_length(),
                    }
                    (run.directory / "replay-pages.json").write_text(
                        json.dumps(observation, indent=2)
                    )
                    assert not observation["same_page"], (
                        "replay cursor repeats the same 100-event page at tied times"
                    )
                    return observation

                await run.check(
                    "replay_tied_timestamp_cursor_progress", ["LIFE-04", "LED-02"], cursor
                )

                async def request_replay():
                    assert database.database_id == "engram"
                    assert values["GOOGLE_CLOUD_PROJECT"] == "portiq-mvp"
                    assert values["SPANNER_INSTANCE_ID"] == "engram-experiment"
                    rejected = await client.post("/v1/admin/replay", json={"confirm": False})
                    assert rejected.status_code == 400
                    response = await client.post(
                        "/v1/admin/replay", json={"confirm": True}, timeout=30
                    )
                    assert response.status_code == 200, response.text
                    assert response.json()["events_replayed"] == 128, response.text
                    return response.json()

                await run.check("replay_API_completes_once_per_event", ["LIFE-04"], request_replay)
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                exit_code = await asyncio.to_thread(process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = await asyncio.to_thread(process.wait, timeout=5)
            (run.directory / "process-cleanup.json").write_text(
                json.dumps(
                    {
                        "exit_code": exit_code,
                        "owned_API_stopped": True,
                        "forced_deadline": "30s HTTP deadline then terminate/kill; replay stopped",
                    }
                )
            )
    log_path.write_text(
        log_path.read_text(errors="replace")
        .replace(values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[REDACTED_TOKEN]")
        .replace(key, "[REDACTED_KEY]")
    )
    await stores.close()


async def retention_boundary(run: Run, database, values) -> None:
    """Historical ingest -> pending delivery -> real consolidation timer/archive."""
    from datetime import timedelta

    import httpx

    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.api.app import create_app, lifespan
    from context_graph.settings import Settings
    from context_graph.worker.consolidation import ConsolidationConsumer
    from context_graph.worker.projection import ProjectionConsumer

    await run.reset(database, values)
    configure(values)
    os.environ["CG_CONSUMER_CLAIM_IDLE_MS"] = "0"
    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://compat"
        ) as client,
    ):
        stores = app.state.stores
        settings = Settings()
        event_id = str(uuid4())
        response = await client.post(
            "/v1/events",
            json={
                "event_id": event_id,
                "event_type": "tool.execute",
                "occurred_at": (datetime.now(UTC) - timedelta(days=100)).isoformat(),
                "session_id": "compat-retention",
                "agent_id": "compat-retention",
                "trace_id": "compat-retention",
                "payload_ref": "payload:old",
                "payload": {"content": "historical content awaiting processing"},
            },
        )
        assert response.status_code == 201, response.text
        projection = ProjectionConsumer(
            stores.subscription(settings.consumer.group_projection, "retention-projection"),
            stores.event_log,
            stores.graph,
            settings,
        )
        await projection.ensure_group()
        pending = await projection._subscription.read_new(count=10, block_ms=20)
        assert len(pending) == 1
        for field in (
            "group_extraction",
            "group_enrichment",
            "group_consolidation",
            "group_pack_extraction",
        ):
            await stores.subscription(
                getattr(settings.consumer, field), "retention-probe"
            ).ensure_group()
        settings.decay.reconsolidation_interval_hours = 0.0003
        archive = FilesystemArchiveStore(run.directory / "archives")
        consolidation = ConsolidationConsumer(
            stores.subscription(settings.consumer.group_consolidation, "retention-consolidation"),
            stores.event_log,
            stores.graph,
            settings,
            archive_store=archive,
        )

        async def protect_pending():
            assert (
                database.database_id == "engram"
                and values["SPANNER_INSTANCE_ID"] == "engram-experiment"
                and values["GOOGLE_CLOUD_PROJECT"] == "portiq-mvp"
            )
            await consolidation.ensure_group()
            task = asyncio.create_task(consolidation.run())
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if await archive.list_archives():
                        break
                    await asyncio.sleep(0.2)
                else:
                    raise TimeoutError("consolidation timer did not archive historical record")
                await asyncio.sleep(0.5)
            finally:
                consolidation.stop()
                await asyncio.wait_for(task, 15)
            doc = (await stores.event_log.get_documents([event_id]))[0]
            archives = await archive.list_archives()
            observation = {
                "event_id": event_id,
                "pending": await projection._subscription.delivery_counts(100),
                "document_present": doc is not None,
                "archives": archives,
            }
            (run.directory / "retention-observation.json").write_text(
                json.dumps(observation, indent=2)
            )
            assert doc is not None, (
                "retention deleted document while projection delivery is pending"
            )
            return observation

        await run.check(
            "retention_protects_pending_historical_content", ["LIFE-01", "LIFE-02"], protect_pending
        )

        async def missing_doc_not_acked():
            task = asyncio.create_task(projection.run())
            try:
                await asyncio.sleep(3)
            finally:
                projection.stop()
                await asyncio.wait_for(task, 15)
            stats = await stores.graph.get_graph_stats()
            counts = await projection._subscription.delivery_counts(100)
            observation = {
                "graph": stats,
                "pending": counts,
                "document_present": (await stores.event_log.get_documents([event_id]))[0]
                is not None,
            }
            (run.directory / "retention-worker-observation.json").write_text(
                json.dumps(observation, indent=2)
            )
            assert stats["nodes"].get("Event", 0) == 1 or counts, (
                "projection ACKed missing content without producing a graph event"
            )
            return observation

        await run.check(
            "projection_does_not_silently_ACK_expired_content",
            ["LIFE-01", "SUB-03"],
            missing_doc_not_acked,
        )
    os.environ.pop("CG_CONSUMER_CLAIM_IDLE_MS", None)


async def native_entity_boundary(run: Run, database, values) -> None:
    """Read-only follow-up using embeddings written by the process journey."""
    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings

    stores = await open_stores(Settings())

    async def label_isolation():
        def embedded_rows():
            with database.snapshot() as snapshot:
                return list(
                    snapshot.execute_sql(
                        "SELECT label, node_id, embedding FROM GraphNodes "
                        "WHERE embedding IS NOT NULL"
                    )
                )

        rows = await asyncio.to_thread(embedded_rows)
        labels = {node_id: label for label, node_id, embedding in rows}
        entity = next((row for row in rows if row[0] == "Entity"), None)
        assert entity is not None, "populated extraction fixture required"
        hits = await stores.vector_index.nearest(
            [float(value) for value in entity[2]], top_k=10, threshold=0
        )
        observation = {
            "embedded_labels": labels,
            "hits": [{"id": h.id, "label": labels.get(h.id), "score": h.score} for h in hits],
        }
        (run.directory / "native-entity-results.json").write_text(json.dumps(observation, indent=2))
        assert hits and all(labels.get(hit.id) == "Entity" for hit in hits), (
            "entity vector search returned non-Entity graph rows"
        )
        return observation

    await run.check(
        "native_entity_vector_label_isolation", ["SEARCH-02", "MEM-03"], label_isolation
    )
    await stores.close()


async def ontology_target(run: Run, database, values) -> None:
    """Owned second database prerequisite; exercise rebuild/cutover if permitted."""
    import httpx
    from google.api_core.exceptions import PermissionDenied
    from google.cloud import spanner
    from tests.unit.test_pack_toy_end_to_end import _events

    from context_graph.adapters.registry import open_stores
    from context_graph.adapters.spanner.schema import schema_differences, schema_statements
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.__main__ import run_rebuild
    from context_graph.settings import Settings

    await run.reset(database, values)
    configure(values, "crm")
    provided = os.environ.get("ENGRAM_COMPAT_TARGET_DATABASE")
    if provided and provided != "engram-compat-target":
        raise ValueError("only explicitly requested disposable target is allowed")
    target_id = provided or ("engramcompat" + uuid4().hex[:12])
    receipt = {
        "project": values["GOOGLE_CLOUD_PROJECT"],
        "instance": values["SPANNER_INSTANCE_ID"],
        "source_database": "engram",
        "owned_target": target_id,
        "created": False,
        "user_provided_disposable": bool(provided),
    }
    path = run.directory / "owned-target.json"
    path.write_text(json.dumps(receipt, indent=2))
    target = (
        spanner.Client(project=values["GOOGLE_CLOUD_PROJECT"])
        .instance(values["SPANNER_INSTANCE_ID"])
        .database(target_id, ddl_statements=schema_statements(384))
    )
    try:
        try:
            if provided:
                assert target.database_id == "engram-compat-target"
                assert values["GOOGLE_CLOUD_PROJECT"] == "portiq-mvp"
                assert values["SPANNER_INSTANCE_ID"] == "engram-experiment"

                def target_tables():
                    with target.snapshot() as snapshot:
                        return list(
                            snapshot.execute_sql(
                                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                                "WHERE TABLE_SCHEMA = '' AND TABLE_TYPE = 'BASE TABLE'"
                            )
                        )

                tables = await asyncio.to_thread(target_tables)
                receipt["existing_tables"] = [row[0] for row in tables]
                if not tables:
                    await asyncio.to_thread(
                        lambda: target.update_ddl(schema_statements(384)).result(timeout=240)
                    )
                    receipt["schema_applied_to_empty_user_target"] = True
                differences = await asyncio.to_thread(schema_differences, target, 384)
                assert not differences, str(differences)
                for table in TABLES:
                    rows = await asyncio.to_thread(
                        target.execute_partitioned_dml, f"DELETE FROM {table} WHERE TRUE"
                    )
                    receipt.setdefault("target_resets", []).append({"table": table, "rows": rows})
            else:
                await asyncio.to_thread(lambda: target.create().result(timeout=90))
                receipt["created"] = True
            path.write_text(json.dumps(receipt, indent=2))
        except PermissionDenied as exc:
            run.checks.append(
                {
                    "name": "owned_rebuild_database_access_or_provisioning",
                    "scenarios": ["ONT-03", "ONT-04"],
                    "verdict": "blocked",
                    "error_type": "PermissionDenied",
                    "error": str(exc)[:1200],
                    "seconds": 0,
                }
            )
            receipt["provisioning_denied"] = True
            return
        settings = Settings()
        candidate = settings.model_copy(
            update={"spanner": settings.spanner.model_copy(update={"database": target_id})}
        )
        app = create_app()
        async with (
            lifespan(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://compat"
            ) as client,
        ):
            response = await client.post("/v1/events/batch", json={"events": _events()})
            assert response.status_code == 201 and response.json()["accepted"] == 11

            async def build():
                code = await run_rebuild(settings, candidate, [], skip_gate=False, force=False)
                assert code == 0, f"ontology rebuild CLI returned{code}"
                stores = await open_stores(candidate)
                try:
                    return {
                        "exit_code": code,
                        "target_graph": await stores.graph.get_graph_stats(),
                        "target_ledger_count": await stores.event_log.stream_length(),
                        "source_ledger_count": await app.state.stores.event_log.stream_length(),
                    }
                finally:
                    await stores.close()

            await run.check("owned_same_backend_ontology_rebuild", ["ONT-03"], build)

            async def cutover():
                stores = await open_stores(candidate)
                try:
                    count = await stores.event_log.stream_length()
                    source_count = await app.state.stores.event_log.stream_length()
                    (run.directory / "cutover-ledger.json").write_text(
                        json.dumps(
                            {
                                "source_count": source_count,
                                "cutover_count": count,
                                "target_database": target_id,
                            },
                            indent=2,
                        )
                    )
                    assert count == source_count, (
                        "Spanner graph target settings select a new empty ledger during cutover"
                    )
                    return {"source_count": source_count, "cutover_count": count}
                finally:
                    await stores.close()

            await run.check("Spanner_graph_cutover_preserves_source_ledger", ["ONT-04"], cutover)
    finally:
        if receipt["created"]:
            assert target_id != "engram" and target.database_id == receipt["owned_target"]
            await asyncio.to_thread(target.drop)
            receipt["dropped_owned_target"] = True
        elif provided:
            receipt["preserved_user_target_database_schema"] = True
        path.write_text(json.dumps(receipt, indent=2))


async def admin_boundary(run: Run, database, values) -> None:
    """Authorization, missing-user APIs and actual graph prune with ledger kept."""
    from datetime import timedelta

    import httpx

    from context_graph.api.app import create_app, lifespan
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    await run.reset(database, values)
    configure(values)
    api_key, admin_key = uuid4().hex, uuid4().hex
    os.environ.update(CG_AUTH_API_KEY=api_key, CG_AUTH_ADMIN_KEY=admin_key)
    admin_header = {"Authorization": "Bearer " + admin_key}
    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://compat",
            headers={"Authorization": "Bearer " + api_key},
        ) as client,
    ):
        stores = app.state.stores
        settings = Settings()

        async def authorization():
            assert (
                await client.post("/v1/events", json={}, headers={"Authorization": "Bearer wrong"})
            ).status_code == 401
            assert (await client.get("/v1/admin/stats")).status_code == 401
            assert (await client.get("/v1/users/user:missing/profile")).status_code == 401
            assert (
                await client.get("/v1/users/user:missing/profile", headers=admin_header)
            ).status_code == 404
            for endpoint in ("preferences", "skills", "patterns", "interests", "data-export"):
                response = await client.get(
                    f"/v1/users/user:missing/{endpoint}", headers=admin_header
                )
                assert response.status_code == 200, response.text
            assert (await client.delete("/v1/users/user:missing", headers=admin_header)).json()[
                "deleted_count"
            ] == 0
            response = await client.post("/v1/events/import", content="{}\n")
            assert response.status_code == 401
            metrics = await client.get("/metrics/")
            assert metrics.status_code == 200 and "http" in metrics.text.lower()
            return {
                "API_admin_import_user_separation": "asserted",
                "missing_user": "404 profile; empty lists/export; zero-delete",
                "metrics": "Prometheus HTTP200",
            }

        await run.check(
            "auth_missing_user_and_metrics",
            ["OPS-01", "OPS-02", "USER-01", "USER-02"],
            authorization,
        )

        async def pruning():
            ids = [str(uuid4()) for _ in range(3)]
            events = [
                {
                    "event_id": ids[i],
                    "event_type": "tool.execute",
                    "occurred_at": (datetime.now(UTC) - timedelta(days=days)).isoformat(),
                    "session_id": "compat-prune",
                    "agent_id": "compat-prune",
                    "trace_id": "compat-prune",
                    "payload_ref": f"payload:{i}",
                    "importance_hint": 1,
                    **({"parent_event_id": ids[i - 1]} if i else {}),
                }
                for i, days in enumerate((40, 10, 0))
            ]
            response = await client.post("/v1/events/batch", json={"events": events})
            assert response.status_code == 201 and response.json()["accepted"] == 3
            worker = ProjectionConsumer(
                stores.subscription(settings.consumer.group_projection, "prune-projection"),
                stores.event_log,
                stores.graph,
                settings,
            )
            await worker.ensure_group()
            task = asyncio.create_task(worker.run())
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    await asyncio.sleep(0.1)
                    if (
                        await worker._subscription.lag() == 0
                        and not await worker._subscription.delivery_counts(100)
                    ):
                        break
                else:
                    raise TimeoutError("prune projection drain")
            finally:
                worker.stop()
                await asyncio.wait_for(task, 15)
            before = await stores.graph.get_graph_stats()
            dry = await client.post(
                "/v1/admin/prune", json={"tier": "cold", "dry_run": True}, headers=admin_header
            )
            assert dry.status_code == 200 and dry.json()["pruned_nodes"] == 2, dry.text
            assert (await stores.graph.get_graph_stats())["nodes"]["Event"] == 3
            assert (
                database.database_id == "engram"
                and values["SPANNER_INSTANCE_ID"] == "engram-experiment"
                and values["GOOGLE_CLOUD_PROJECT"] == "portiq-mvp"
            )
            live = await client.post(
                "/v1/admin/prune", json={"tier": "cold", "dry_run": False}, headers=admin_header
            )
            assert live.status_code == 200 and live.json()["pruned_nodes"] == 2, live.text
            after = await stores.graph.get_graph_stats()
            assert after["nodes"]["Event"] == 1 and after["total_edges"] == 0
            assert await stores.event_log.stream_length() == 3
            assert all(doc is not None for doc in await stores.event_log.get_documents(ids))
            return {
                "dry": dry.json(),
                "live": live.json(),
                "before": before,
                "after": after,
                "ledger_documents_preserved": 3,
            }

        await run.check("cold_archive_prune_dry_live_counts_edges_ledger", ["LIFE-03"], pruning)
    os.environ.pop("CG_AUTH_API_KEY", None)
    os.environ.pop("CG_AUTH_ADMIN_KEY", None)


async def artifact_boundaries(run: Run, database, values) -> None:
    """Cloud recheck6/7 through API ingestion, projection and artifact routes."""
    import httpx
    from tests.unit import test_pack_toy_end_to_end as crm

    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ontology.versioning import reconcile
    from context_graph.ports.pack_graph import EdgeWrite, NodeRef
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    await run.reset(database, values)
    configure(values, "crm")
    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://compat",
        ) as client,
    ):
        stores = app.state.stores
        settings = Settings()
        projector = configured_projector(settings.ontology)
        response = await client.post("/v1/events/batch", json={"events": crm._events()})
        assert response.status_code == 201 and response.json()["accepted"] == 11
        await reconcile(
            stores.graph,
            stores.event_log,
            projector,
            allow_breaking=False,
            batch_size=100,
            lookup_limit=settings.ontology.lookup_limit,
        )
        worker = ProjectionConsumer(
            stores.subscription(settings.consumer.group_projection, "artifact-projection"),
            stores.event_log,
            stores.graph,
            settings,
            projector,
        )
        await worker.ensure_group()
        task = asyncio.create_task(worker.run())
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                await asyncio.sleep(0.1)
                if (
                    await worker._subscription.lag() == 0
                    and not await worker._subscription.delivery_counts(100)
                ):
                    break
            else:
                raise TimeoutError("artifact projection drain")
        finally:
            worker.stop()
            await asyncio.wait_for(task, 15)
        await crm._check_graph(stores)
        await crm._check_gate(client, settings, stores, projector)

        async def baseline():
            await crm._check_questions(client)
            return {"CRM_competencies": "passed before rejection/budget injection"}

        await run.check(
            "artifact_baseline_real_ingest_projection_gate",
            ["APP-03", "ART-02", "ART-05"],
            baseline,
        )

        async def completeness():
            retriever = app.state.artifacts
            previous = retriever._max_calls
            retriever._max_calls = 1
            try:
                response = await client.post(
                    "/v1/query/artifacts",
                    json={
                        "query": "Which accounts have no deals?",
                        "seed_node_ids": ["Account:acme"],
                        "intent": "coverage",
                    },
                )
            finally:
                retriever._max_calls = previous
            assert response.status_code == 200, response.text
            body = response.json()
            (run.directory / "incomplete-coverage.json").write_text(json.dumps(body, indent=2))
            assert body["meta"]["truncated"]
            reasons = {key: node["retrieval_reason"] for key, node in body["nodes"].items()}
            assert reasons.get("Account:acme") != "no_link", (
                "truncated coverage returns Acme as no_link although confirmed deals exist"
            )
            return body

        await run.check("incomplete_reads_do_not_claim_absence", ["ART-04"], completeness)

        async def rejection():
            # Seed a rejection through the public graph write port after actual projection.
            await stores.graph.upsert_edges(
                [
                    EdgeWrite(
                        "BELONGS_TO",
                        NodeRef("Deal", "Deal:D-7"),
                        NodeRef("Account", "Account:acme"),
                        {"link_status": "rejected"},
                    )
                ]
            )
            response = await client.post(
                "/v1/query/artifacts",
                json={
                    "query": "Which account does deal D-7 belong to?",
                    "seed_node_ids": ["Deal:D-7"],
                    "intent": "pipeline",
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            (run.directory / "rejected-link-answer.json").write_text(json.dumps(body, indent=2))
            assert not any(
                edge.get("properties", {}).get("link_status") == "rejected"
                for edge in body["edges"]
            ), "artifact answer includes rejected relationship as evidence"
            assert "Account:acme" not in body["nodes"], (
                "rejected-only route still admits the account"
            )
            return body

        await run.check("rejected_link_not_traversed_or_cited", ["ART-03"], rejection)


async def pack_stats_boundary(run: Run, database, values) -> None:
    """Check real admin stats against the successfully rebuilt PDLC target."""
    import httpx

    from context_graph.api.app import create_app, lifespan

    target_id = os.environ.get("ENGRAM_COMPAT_TARGET_DATABASE")
    assert target_id == "engram-compat-target", "explicit rebuilt target required"
    configure(values, "pdlc")
    os.environ["CG_SPANNER_DATABASE"] = target_id
    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://compat"
        ) as client,
    ):
        stores = app.state.stores
        target = stores.event_log.database
        assert target.database_id == target_id

        async def stats():
            response = await client.get("/v1/admin/stats")
            assert response.status_code == 200
            body = response.json()

            def actual_counts():
                with target.snapshot(multi_use=True) as snapshot:
                    nodes = dict(
                        snapshot.execute_sql(
                            "SELECT label, COUNT(*) FROM GraphNodes GROUP BY label"
                        )
                    )
                    edges = dict(
                        snapshot.execute_sql(
                            "SELECT edge_type, COUNT(*) FROM GraphEdges GROUP BY edge_type"
                        )
                    )
                    return {"nodes": nodes, "edges": edges}

            actual = await asyncio.to_thread(actual_counts)
            observation = {"database": target_id, "admin": body, "actual": actual}
            (run.directory / "pack-stats.json").write_text(json.dumps(observation, indent=2))
            pack_labels = [
                name for name, node in app.state.ontology.node_types.items()
                if node.pack == "pdlc" and actual["nodes"].get(name, 0) > 0
            ]
            assert pack_labels, "rebuilt target must contain PDLC nodes"
            for label in pack_labels:
                assert body["nodes"].get(label) == actual["nodes"].get(label), (
                    f"admin stats omit or miscount ontology label{label}"
                )
            for edge_type in actual["edges"]:
                assert body["edges"].get(edge_type) == actual["edges"].get(edge_type), (
                    f"admin stats omit ontology relationship{edge_type}"
                )
            return observation

        await run.check("admin_stats_count_pack_types", ["OPS-01"], stats)
    os.environ["CG_SPANNER_DATABASE"] = values["SPANNER_DATABASE_ID"]


async def pdlc_evaluations(run: Run, database, values) -> None:
    """Webhook PDLC competencies, real target rebuild, then larger OpenDAL corpus."""
    import httpx
    import pytest
    from tests.unit import test_pdlc_end_to_end as fixture

    from context_graph.adapters.registry import open_stores
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.__main__ import evaluate_graph, run_rebuild
    from context_graph.ontology.runtime import configured_projector
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    async def drain(worker, stores=None, group=None):
        await worker.ensure_group()
        task = asyncio.create_task(worker.run())
        try:
            deadline = time.monotonic() + 400
            while time.monotonic() < deadline:
                await asyncio.sleep(0.1)
                if task.done():
                    await task
                    raise RuntimeError("PDLC projection worker exited early")
                if (
                    await worker._subscription.lag() == 0
                    and not await worker._subscription.delivery_counts(100)
                ):
                    return
            raise TimeoutError("PDLC drain deadline400s")
        finally:
            worker.stop()
            await asyncio.wait_for(task, 20)

    await run.reset(database, values)
    configure(values)
    os.environ.update(
        CG_WEBHOOK_GITHUB_SECRET=fixture.SECRET, CG_WEBHOOK_JIRA_SECRET=fixture.SECRET
    )
    settings = Settings()
    stores = await open_stores(settings, prepare_ingest=True)

    async def payments():
        with pytest.MonkeyPatch.context() as mp:

            async def version_only(client, settings, stores, backend):
                assert (await client.get("/v1/ontology")).status_code == 200

            mp.setattr(fixture, "_check_versioning", version_only)
            mp.setattr(fixture, "_drain", drain)
            await fixture._run(mp, settings, stores, "spanner")
        reports = await evaluate_graph(
            settings,
            stores.graph,
            configured_projector(settings.ontology).registry,
            [fixture.EVAL_SETS],
            record=False,
        )
        report = [r.as_dict() for r in reports]
        (run.directory / "pdlc-webhook-evaluation.json").write_text(json.dumps(report, indent=2))
        assert all(r.passed for r in reports)
        return {
            "signed_deliveries": 8,
            "evaluation": report,
            "artifact_questions_and_pack_extraction": "passed",
        }

    await run.check(
        "PDLC_signed_webhook_full_fixture_evaluation",
        ["APP-02", "ART-01", "ONT-01", "PEXT-01", "PEXT-02"],
        payments,
    )

    if os.environ.get("ENGRAM_COMPAT_TARGET_DATABASE") == "engram-compat-target":

        async def target_rebuild():
            candidate = settings.model_copy(
                update={
                    "spanner": settings.spanner.model_copy(
                        update={"database": "engram-compat-target"}
                    )
                }
            )
            target_stores = await open_stores(candidate)
            try:
                target = target_stores.event_log.database
                assert (
                    target.database_id == "engram-compat-target"
                    and values["SPANNER_INSTANCE_ID"] == "engram-experiment"
                    and values["GOOGLE_CLOUD_PROJECT"] == "portiq-mvp"
                )
                for table in TABLES:
                    rows = await asyncio.to_thread(
                        target.execute_partitioned_dml, f"DELETE FROM {table} WHERE TRUE"
                    )
                    run.resets.append(
                        {"database": "engram-compat-target", "table": table, "rows": rows}
                    )
            finally:
                await target_stores.close()
            code = await run_rebuild(
                settings, candidate, [str(fixture.EVAL_SETS)], skip_gate=False, force=False
            )
            assert code == 0, f"PDLC rebuild returned{code}"
            target_stores = await open_stores(candidate)
            try:
                reports = await evaluate_graph(
                    candidate,
                    target_stores.graph,
                    configured_projector(candidate.ontology).registry,
                    [fixture.EVAL_SETS],
                    record=False,
                )
                report = [r.as_dict() for r in reports]
                (run.directory / "pdlc-target-evaluation.json").write_text(
                    json.dumps(report, indent=2)
                )
                assert all(r.passed for r in reports)
                return {"target": "engram-compat-target", "exit_code": code, "evaluation": report}
            finally:
                await target_stores.close()

        await run.check(
            "PDLC_real_target_rebuild_evaluation", ["ONT-03", "APP-02", "ART-01"], target_rebuild
        )

    await stores.close()
    await run.reset(database, values)
    configure(values)
    os.environ["CG_WEBHOOK_GITHUB_SECRET"] = fixture.SECRET
    opendal = ROOT / "tests/fixtures/opendal"
    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://compat",
        ) as client,
    ):

        async def large_corpus():
            deliveries = json.loads((opendal / "deliveries.json").read_text())["deliveries"]
            event_count = 0
            for delivery in deliveries:
                body = json.dumps(delivery["body"]).encode()
                for attempt in range(10):
                    response = await client.post(
                        "/v1/webhooks/github",
                        content=body,
                        headers=fixture._headers(
                            "github", delivery["event"], body, delivery["delivery"]
                        ),
                    )
                    if response.status_code != 429:
                        break
                    delay = float(response.json().get("retry_after", 1))
                    await asyncio.sleep(min(5, max(0.1, delay)) + 0.05)
                assert response.status_code == 202, response.text
                event_count += len(response.json()["event_ids"])
            stores = app.state.stores
            settings = Settings()
            projector = configured_projector(settings.ontology)
            worker = ProjectionConsumer(
                stores.subscription(settings.consumer.group_projection, "opendal-projection"),
                stores.event_log,
                stores.graph,
                settings,
                projector,
            )
            await drain(worker)
            reports = await evaluate_graph(
                settings, stores.graph, projector.registry, [opendal], record=True
            )
            report = [r.as_dict() for r in reports]
            (run.directory / "pdlc-opendal-evaluation.json").write_text(
                json.dumps(report, indent=2)
            )
            assert all(r.passed for r in reports), "OpenDAL PDLC evaluation gate failed"
            return {
                "signed_deliveries": len(deliveries),
                "normalized_events": event_count,
                "evaluation": report,
                "scope": "OpenDAL: releases/reverts/change content; no Jira/review/CI/deploy data",
            }

        await run.check(
            "PDLC_OpenDAL_signed_ingestion_projection_evaluation",
            ["APP-02", "ART-01", "HOOK-01"],
            large_corpus,
            timeout_seconds=480,
        )


async def pdlc_api_evaluation(run: Run, database, values) -> None:
    """Read the populated OpenDAL corpus through the artifact HTTP route."""
    import httpx
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.evaluation import load_eval_set, f1_score
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.worker.projection import ProjectionConsumer

    configure(values, "pdlc")
    app = create_app()
    async with lifespan(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://compat"
    ) as client:
        async def finish_projection():
            from context_graph.ontology.versioning import reconcile
            settings = Settings()
            stores = app.state.stores
            assert stores.event_log.database.database_id == values["SPANNER_DATABASE_ID"] == "engram"
            projector = configured_projector(settings.ontology)
            await stores.graph.ensure_pack_schema(projector.registry, settings.embedding.dimensions)
            await reconcile(stores.graph, stores.event_log, projector,
                            allow_breaking=settings.ontology.allow_breaking,
                            allow_version_problems=settings.ontology.allow_version_problems,
                            batch_size=settings.ontology.replay_batch_size,
                            lookup_limit=settings.ontology.lookup_limit)
            worker = ProjectionConsumer(
                stores.subscription(settings.consumer.group_projection, "opendal-projection"),
                stores.event_log, stores.graph, settings,
                projector)
            await worker.ensure_group()
            task = asyncio.create_task(worker.run())
            try:
                deadline = time.monotonic() + 160
                while time.monotonic() < deadline:
                    await asyncio.sleep(0.2)
                    if task.done():
                        await task
                        raise RuntimeError("OpenDAL continuation worker exited early")
                    if (await worker._subscription.lag() == 0 and
                            not await worker._subscription.delivery_counts(100)):
                        return {"unread": 0, "pending": 0, "ledger": await stores.event_log.stream_length()}
                raise TimeoutError("OpenDAL continuation drain deadline160s")
            finally:
                worker.stop()
                await asyncio.wait_for(task, 20)
        await run.check("PDLC_OpenDAL_projection_continuation_drain", ["APP-02", "PROJ-02"],
                        finish_projection, timeout_seconds=190)
        async def gate():
            assert await app.state.stores.event_log.stream_length() == 292
            reports = await evaluate_graph(
                Settings(), app.state.stores.graph, app.state.ontology,
                [ROOT / "tests/fixtures/opendal"], record=True)
            result = [report.as_dict() for report in reports]
            (run.directory / "pdlc-opendal-evaluation.json").write_text(
                json.dumps(result, indent=2))
            assert all(report.passed for report in reports)
            return result
        await run.check("PDLC_OpenDAL_recorded_evaluation_gate", ["APP-02", "ART-01"],
                        gate, timeout_seconds=240)
        async def questions():
            evaluation = load_eval_set(ROOT / "tests/fixtures/opendal/pdlc.eval.yaml")
            answers = []
            for question in evaluation.questions:
                payload = {"query": question.query, "seed_node_ids": question.seed_node_ids,
                           "max_nodes": 500}
                if question.intent is not None:
                    payload["intent"] = question.intent
                response = await client.post("/v1/query/artifacts", json=payload)
                assert response.status_code == 200, response.text
                body = response.json()
                assert not body["meta"]["eval_pending"], body["meta"]
                found = {key for key, node in body["nodes"].items()
                         if (question.answer.node_type is None or
                             node["node_type"] == question.answer.node_type)
                         and (not question.answer.reasons or
                              node["retrieval_reason"] in question.answer.reasons)}
                answers.append({"id": question.id, "f1": f1_score(found, set(question.expected)),
                                "found": sorted(found), "expected": question.expected,
                                "response": body})
            mean = sum(answer["f1"] for answer in answers) / len(answers)
            result = {"mean_f1": mean, "min_f1": evaluation.min_f1, "questions": answers}
            (run.directory / "pdlc-opendal-http-evaluation.json").write_text(
                json.dumps(result, indent=2))
            assert mean >= evaluation.min_f1, "OpenDAL artifact API gate failed"
            return result
        await run.check("PDLC_OpenDAL_artifact_HTTP_competencies", ["APP-02", "ART-01"],
                        questions, timeout_seconds=240)


async def execute(args, values) -> None:
    from google.cloud import spanner
    from google.oauth2.credentials import Credentials

    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings

    configure(values)
    original = spanner.Client
    credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

    def authenticated_client(*a, **kw):
        kw["credentials"] = credentials
        return original(*a, **kw)

    spanner.Client = authenticated_client
    run = Run(args.phase, values, args.credential_file)
    stores = None
    try:
        stores = await open_stores(Settings())
        database = stores.event_log.database
        if args.phase in ("ingress-completion","context-completion","consolidation-completion","evaluation-completion"):
            from engram_spanner_compat_completion import ingress,context_cases,consolidation_cases,evaluation_cases
            function={"ingress-completion":ingress,"context-completion":context_cases,"consolidation-completion":consolidation_cases,"evaluation-completion":evaluation_cases}[args.phase]
            await asyncio.wait_for(function(run,database,values,args.credential_file),timeout=600)
        elif args.phase == "journeys":
            await asyncio.wait_for(journeys(run, database, values), timeout=600)
        elif args.phase == "boundaries":
            await asyncio.wait_for(boundaries(run, database, values), timeout=600)
        elif args.phase in ("knowledge","knowledge-safe"):
            await asyncio.wait_for(knowledge(run, database, values,include_interests=args.phase=="knowledge"), timeout=600)
        elif args.phase == "processes":
            await asyncio.wait_for(
                processes(run, database, values, args.credential_file), timeout=600
            )
        elif args.phase == "replay":
            await asyncio.wait_for(
                replay_boundary(run, database, values, args.credential_file), timeout=600
            )
        elif args.phase == "retention":
            await asyncio.wait_for(retention_boundary(run, database, values), timeout=600)
        elif args.phase == "search":
            await asyncio.wait_for(native_entity_boundary(run, database, values), timeout=600)
        elif args.phase == "ontology":
            await asyncio.wait_for(ontology_target(run, database, values), timeout=600)
        elif args.phase == "admin":
            await asyncio.wait_for(admin_boundary(run, database, values), timeout=600)
        elif args.phase == "artifacts":
            await asyncio.wait_for(artifact_boundaries(run, database, values), timeout=600)
        elif args.phase == "stats":
            await asyncio.wait_for(pack_stats_boundary(run, database, values), timeout=600)
        elif args.phase == "pdlc":
            await asyncio.wait_for(pdlc_evaluations(run, database, values), timeout=600)
        elif args.phase == "pdlc-api":
            await asyncio.wait_for(pdlc_api_evaluation(run, database, values), timeout=600)
        elif args.phase in ("pack-cases", "maintenance", "commit-cases", "pack-policy", "keyword-features", "subscriptions", "webhook-handlers", "enrichment-cases", "archive-restore", "ordering-races", "live-pack", "user-feedback", "feedback-recheck", "user-delete-recheck"):
            from engram_spanner_compat_pack_cases import pack_cases, maintenance, commit_cases, pack_policy, keyword_features, subscriptions, webhook_handlers, enrichment_cases, archive_restore, ordering_races, live_pack, user_feedback, feedback_recheck, user_delete_recheck
            function = {"pack-cases":pack_cases,"maintenance":maintenance,"commit-cases":commit_cases,"pack-policy":pack_policy,"keyword-features":keyword_features,"subscriptions":subscriptions,"webhook-handlers":webhook_handlers,"enrichment-cases":enrichment_cases,"archive-restore":archive_restore,"ordering-races":ordering_races,"live-pack":live_pack,"user-feedback":user_feedback,"feedback-recheck":feedback_recheck,"user-delete-recheck":user_delete_recheck}[args.phase]
            await asyncio.wait_for(function(run, database, values, args.credential_file),timeout=600)
        elif args.phase in ("recovery", "combined", "concurrency", "startup", "schema", "endpoints", "vector", "upgrades", "shutdown", "json"):
            from engram_spanner_compat_remaining import recovery, combined, concurrency, startup, endpoints, vector_isolation, upgrade_failures, shutdown, JSON_boundaries
            if args.phase == "schema":
                await asyncio.wait_for(startup(run, database, values, args.credential_file,
                                              modes=("dimension_mismatch",)), timeout=600)
            else:
                function = {"recovery": recovery, "combined": combined, "concurrency": concurrency,
                            "startup": startup, "endpoints": endpoints, "vector": vector_isolation,
                            "upgrades": upgrade_failures, "shutdown": shutdown, "json": JSON_boundaries}[args.phase]
                await asyncio.wait_for(function(run, database, values, args.credential_file), timeout=600)
    except Exception as exc:
        run.checks.append(
            {
                "name": "phase_setup",
                "scenarios": ["BOOT-02", "BOOT-03"],
                "verdict": "blocked",
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "seconds": 0,
            }
        )
    finally:
        if stores is not None:
            await stores.close()
        spanner.Client = original
        run.finish(
            values, "Engram journeys against disposable real database; subcheck evidence recorded"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=[
            "ingress-completion",
            "context-completion",
            "consolidation-completion",
            "evaluation-completion",
            "journeys",
            "boundaries",
            "knowledge",
            "knowledge-safe",
            "processes",
            "replay",
            "retention",
            "search",
            "ontology",
            "admin",
            "artifacts",
            "stats",
            "pdlc",
            "pdlc-api",
            "recovery",
            "combined",
            "concurrency",
            "startup",
            "schema",
            "endpoints",
            "vector",
            "upgrades",
            "shutdown",
            "json",
            "pack-cases",
            "maintenance",
            "commit-cases",
            "pack-policy",
            "keyword-features",
            "subscriptions",
            "webhook-handlers",
            "enrichment-cases",
            "archive-restore",
            "ordering-races",
            "live-pack",
            "user-feedback",
            "feedback-recheck",
            "user-delete-recheck",
        ],
        default="journeys",
    )
    parser.add_argument(
        "--credential-file", type=Path, default=Path("/private/tmp/engram-spanner-token-env")
    )
    parser.add_argument("--disposable-engram-confirmed", action="store_true", required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    values = load_credentials(args.credential_file)
    import fcntl

    # Serial database fixture ownership across independent runner invocations.
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another compatibility run owns the disposable database") from exc
        asyncio.run(execute(args, values))


if __name__ == "__main__":
    main()
