"""Run tracked Engram flows against the explicitly disposable real Spanner DB.

No Redis/Neo4j runners. Credentials are read privately from four assignment
lines. Direct SQL is restricted to fixture reset and persisted-state inspection.
Requires the user's disposable-database authorization; never drops the database
or changes schema. Each phase starts/finishes its own persistent run record.
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
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility"
TABLES = ("GraphEdges", "GraphNodes", "ConsumerDeadLetters", "ConsumerDeliveries",
          "ConsumerCursors", "ConsumerGroups", "Events")


def load_credentials(path: Path) -> dict[str, str]:
    keys = ("GOOGLE_CLOUD_PROJECT", "SPANNER_INSTANCE_ID", "SPANNER_DATABASE_ID",
            "GOOGLE_OAUTH_ACCESS_TOKEN")
    result = {}
    for line in path.read_text().splitlines():
        if any(line.startswith(prefix) for key in keys for prefix in (key + "=", "export " + key + "=")):
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
        CG_SPANNER_CREATE_IF_MISSING="false", CG_SPANNER_ALLOW_CREATE_ON_INSTANCE="false",
        CG_ONTOLOGY_PACKS=packs, CG_ONTOLOGY_PACK_DIRS=str(ROOT / "tests/fixtures/packs/crm"),
        CG_ONTOLOGY_TRUSTED_SOURCES="webhook:github,webhook:jira,importer:crm",
        CG_CONSUMER_BLOCK_TIMEOUT_MS="20", CG_ONTOLOGY_EVAL_STATE_TTL_S="0",
        CG_WEBHOOK_GITHUB_SECRET="compat-test-secret", CG_WEBHOOK_JIRA_SECRET="compat-test-secret",
        CG_INTENT_USE_LLM="false", LITELLM_LOCAL_MODEL_COST_MAP="true",
    )
    for key in ("CG_AUTH_API_KEY", "CG_AUTH_ADMIN_KEY"):
        os.environ.pop(key, None)  # ASGI fixture process only; external HTTP runs use keys.


class Run:
    def __init__(self, phase: str, values: dict[str, str]) -> None:
        self.id = f"20261006-cloud-{phase}-{uuid4().hex[:8]}"
        self.directory = RECORDS / "runs" / self.id
        self.checks: list[dict] = []
        self.resets: list[dict] = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        manifest = {
            "run_id": self.id, "phase": phase, "backend": "real_spanner",
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "started_at": datetime.now(UTC).isoformat(),
            "target": {k: values[k] for k in ("GOOGLE_CLOUD_PROJECT", "SPANNER_INSTANCE_ID", "SPANNER_DATABASE_ID")},
            "authorization": "user explicitly confirmed existing engram DB disposable",
            "auth": "explicit token SDK bootstrap; unmodified ADC startup not proved",
            "all_storage_ports": "spanner", "fixture_reset": list(TABLES),
            "schema_changes": False, "database_drop": False,
            "provider_mode": "scripted/disabled; no live provider cost",
            "max_phase_seconds": 600,
        }
        path = Path("/private/tmp") / f"{self.id}-manifest.json"
        path.write_text(json.dumps(manifest))
        subprocess.run([sys.executable, str(ROOT / "scripts/track_spanner_compatibility.py"),
                        "start", "--run-id", self.id, "--manifest", str(path)], check=True,
                       stdout=subprocess.DEVNULL)
        self.log = (self.directory / "execution.log").open("w")
        sys.stdout = self.log
        sys.stderr = self.log

    async def check(self, name: str, scenarios: list[str], function) -> None:
        started = time.monotonic()
        try:
            observation = await asyncio.wait_for(function(), timeout=120)
            item = {"name": name, "scenarios": scenarios, "verdict": "passed",
                    "observation": observation}
        except Exception as exc:
            # Error strings can contain request data; scrub tokens before persistence.
            item = {"name": name, "scenarios": scenarios, "verdict": "failed",
                    "error_type": type(exc).__name__, "error": str(exc)[:1200]}
        item["seconds"] = round(time.monotonic() - started, 2)
        self.checks.append(item)
        print(json.dumps(item), flush=True)

    async def reset(self, database, values) -> None:
        if (database.database_id != "engram" or values["GOOGLE_CLOUD_PROJECT"] != "portiq-mvp"
                or values["SPANNER_INSTANCE_ID"] != "engram-experiment"):
            raise RuntimeError("refusing reset outside user-authorized disposable target")
        for table in TABLES:
            rows = await asyncio.to_thread(database.execute_partitioned_dml,
                                           f"DELETE FROM {table} WHERE TRUE")
            self.resets.append({"table": table, "rows": rows})

    def finish(self, values, summary="") -> None:
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.log.close()
        path = self.directory / "execution.log"
        path.write_text(path.read_text(errors="replace").replace(values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[REDACTED_TOKEN]"))
        data = {"checks": self.checks, "resets": self.resets,
                "summary": summary, "scope": "subchecks; full scenario rows remain pending until all requirements proved",
                "cleanup": "no database/schema deletion; final fixture retained for inspection"}
        text = json.dumps(data, indent=2).replace(values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[REDACTED_TOKEN]")
        (self.directory / "observations.json").write_text(text + "\n")
        results = {"scenarios": [], "summary": summary, "cleanup": data["cleanup"],
                   "evidence": str((self.directory / "observations.json").relative_to(ROOT))}
        p = Path("/private/tmp") / f"{self.id}-results.json"
        p.write_text(json.dumps(results))
        subprocess.run([sys.executable, str(ROOT / "scripts/track_spanner_compatibility.py"),
                        "finish", "--run-id", self.id, "--results", str(p)], check=True,
                       stdout=subprocess.DEVNULL)
        print(json.dumps({"run_id": self.id, "checks": [{k: c[k] for k in
              ("name", "verdict", "seconds")} for c in self.checks], "summary": summary}))


async def journeys(run: Run, database, values) -> None:
    import httpx
    import pytest
    from context_graph.adapters.registry import open_stores
    from context_graph.api.app import create_app, lifespan
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ontology.versioning import reconcile
    from context_graph.worker.projection import ProjectionConsumer
    from tests.unit.test_backend_end_to_end import _run_flow
    from tests.unit import test_pdlc_end_to_end as pdlc
    from tests.unit import test_pack_toy_end_to_end as crm

    async def agent():
        await run.reset(database, values)
        configure(values)
        settings = Settings()
        stores = await open_stores(settings, prepare_ingest=True)
        with pytest.MonkeyPatch.context() as mp:
            await _run_flow(mp, settings, stores, "spanner")
        return {"event_count": 3, "ledger_projection_enrichment_context_lineage_subgraph_health": "asserted",
                "process_model": "ASGI and worker loops in one process; separate-process acceptance still required"}
    await run.check("agent_memory_API_worker_journey", ["APP-01", "ING-01", "PROJ-01", "ENR-01", "MEM-01", "MEM-02", "MEM-03"], agent)

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
            await pdlc._run(mp, settings, stores, "spanner")
        return {"signed_deliveries": len(pdlc.DELIVERIES), "projection_gate_questions_pack_extraction": "asserted",
                "blue_green": "not exercised; no replacement memory graph"}
    await run.check("signed_PDLC_API_projection_artifact_extraction", ["APP-02", "HOOK-01", "HOOK-02", "ART-01", "PEXT-01", "PEXT-02", "ONT-01"], domain)

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
            async with lifespan(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://compat") as client:
                    response = await client.post("/v1/events/batch", json={"events": crm._events()})
                    assert response.status_code == 201 and response.json()["accepted"] == len(crm.HISTORY)
                    await reconcile(stores.graph, stores.event_log, projector, allow_breaking=False,
                                    batch_size=100, lookup_limit=settings.ontology.lookup_limit)
                    worker = ProjectionConsumer(stores.subscription(settings.consumer.group_projection, "compat"),
                                                stores.event_log, stores.graph, settings, projector)
                    await crm._drain(worker, stores, settings.consumer.group_projection)
                    await crm._check_graph(stores)
                    await crm._check_gate(client, settings, stores, projector)
                    await crm._check_questions(client)
        return {"ingested": len(crm.HISTORY), "lifecycle_graph_eval_and_pipeline_coverage_questions": "asserted"}
    await run.check("CRM_API_projection_gate_retrieval", ["APP-03", "ING-02", "PROJ-02", "ART-02", "ART-05"], sales)


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
    run = Run(args.phase, values)
    try:
        stores = await open_stores(Settings())
        database = stores.event_log.database
        if args.phase == "journeys":
            await asyncio.wait_for(journeys(run, database, values), timeout=600)
    except Exception as exc:
        run.checks.append({"name": "phase_setup", "scenarios": ["BOOT-02", "BOOT-03"], "verdict": "blocked",
                           "error_type": type(exc).__name__, "error": str(exc)[:1000], "seconds": 0})
    finally:
        spanner.Client = original
        run.finish(values, "Engram journeys against disposable real database; subcheck evidence recorded")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["journeys"], default="journeys")
    parser.add_argument("--credential-file", type=Path, default=Path("/private/tmp/engram-spanner-token-env"))
    parser.add_argument("--disposable-engram-confirmed", action="store_true", required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    values = load_credentials(args.credential_file)
    asyncio.run(execute(args, values))


if __name__ == "__main__":
    main()
