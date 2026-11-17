"""Rehearse the real evaluation gate on an exclusively leased Spanner sandbox.

Runs the frozen release story, the CLI's evaluate_graph routine, and the real
artifact route in-process. It does not exercise network auth, deployment,
blue/green cutover, or shell CLI construction. Only registered sandbox slots
can be used; normal fencing and verified cleanup apply.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from fastapi import FastAPI

from context_graph.api.routes.artifacts import router
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ontology.__main__ import _retriever, evaluate_graph
from context_graph.ontology.versioning import EvalPending, plan_for_state, read_state, record_state
from context_graph.workbench.journey_runner import _execute, frozen_registry
from context_graph.workbench.journeys import release_journey
from context_graph.workbench.pool_config import configured_execution


def existing_gcloud_credentials(binary: str) -> None:
    from google.cloud import spanner
    from google.oauth2.credentials import Credentials

    def refresh(request, scopes):
        result = subprocess.run(
            [binary, "auth", "print-access-token"], check=True, capture_output=True, text=True
        )
        return result.stdout.strip(), datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

    original = spanner.Client

    def client(*args, **kwargs):
        token, expiry = refresh(None, None)
        kwargs["credentials"] = Credentials(token, expiry=expiry, refresh_handler=refresh)
        return original(*args, **kwargs)

    spanner.Client = client


async def rehearse(pool: Path, output: Path) -> None:
    execution = configured_execution(pool)
    journey = release_journey()
    bundle = resolve_bundle(frozen_registry(journey.pack_digest))
    evidence = {"scope": __doc__, "stages": []}

    def stage(name, **data):
        evidence["stages"].append({"stage": name, **data})
        print(json.dumps({"stage": name, **data}, default=str), flush=True)

    try:
        async with execution.open(bundle, journey.trusted_producers) as runtime:
            graph, registry = runtime.stores.graph, bundle.registry
            await graph.ensure_pack_schema(registry, runtime.settings.embedding.dimensions)
            state = await read_state(graph)
            stage("initial", change=plan_for_state(state, registry).as_dict())
            await record_state(
                graph, registry, applied="rehearsal", extra={"eval_pending": ["pdlc"]}
            )
            app = FastAPI()
            app.include_router(router, prefix="/v1")
            app.state.settings = runtime.settings
            app.state.ontology = registry
            app.state.artifacts = _retriever(runtime.settings, graph, registry)
            # Zero TTL makes this rehearsal's refresh explicit, not a claim that
            # deployment caches update immediately.
            app.state.eval_pending = EvalPending(graph, registry, ttl_s=0)
            request = {"query": "Where is PAY-341 deployed?", "intent": "trace"}
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://rehearsal"
            ) as api:
                before = await api.post("/v1/query/artifacts", json=request)
                assert before.status_code == 409, before.text
                stage("intent_pending", status=before.status_code, response=before.json())
                run = await _execute(journey, bundle, runtime)
                counts = {
                    status: sum(check["status"] == status for check in run["checks"])
                    for status in ("passed", "failed", "unsupported", "error")
                }
                stage("events_projected", counts=counts, passed=run["passed"])
                assert not counts["failed"] and not counts["error"] and not run["dead_letters"]
                with TemporaryDirectory(prefix="engram-evaluation-") as directory:
                    target = Path(directory)
                    shutil.copyfile(
                        Path(__file__).resolve().parents[1]
                        / "src/context_graph/workbench/fixtures/pdlc/release.eval.yaml",
                        target / "pdlc.eval.yaml",
                    )
                    reports = await evaluate_graph(
                        runtime.settings, graph, registry, [target], record=True
                    )
                stage("evaluation_recorded", reports=[report.as_dict() for report in reports])
                assert reports and all(report.passed for report in reports)
                recorded = await read_state(graph)
                assert recorded is not None
                assert recorded.properties["eval_pending"] == []
                after = await api.post("/v1/query/artifacts", json=request)
                assert after.status_code == 200, after.text
                stage(
                    "intent_ready",
                    status=after.status_code,
                    response=after.json(),
                    refresh_ttl_seconds=0,
                )
        stage("cleanup", storage=runtime.evidence)
        assert runtime.evidence.get("cleanup") == "verified"
    finally:
        await execution.close()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gcloud", help="Use an existing local gcloud login; no tokens are saved")
    args = parser.parse_args()
    if args.gcloud:
        existing_gcloud_credentials(args.gcloud)
    asyncio.run(rehearse(args.pool, args.output))
