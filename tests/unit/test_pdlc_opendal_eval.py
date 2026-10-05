"""PDLC evaluation on real data: Apache OpenDAL's history (ADR-0018 decision 10).

``tests/fixtures/opendal/deliveries.json`` holds GitHub webhook deliveries
rebuilt from OpenDAL's git history (288 merged PRs, 4 releases). They are
signed and sent through ``POST /v1/webhooks/github``, so the real GitHub
adapter translates them into the ledger; a blue/green rebuild then projects
the ledger and runs ``tests/fixtures/opendal/pdlc.eval.yaml`` as its gate.
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any

import httpx
import orjson
import pytest
from fastapi import FastAPI

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.api.routes.webhooks import router
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry
from context_graph.ontology.rebuild import RebuildReport, rebuild
from context_graph.settings import Settings

OPENDAL = Path(__file__).resolve().parents[1] / "fixtures" / "opendal"
SECRET = "opendal-eval"  # noqa: S105 - test value, not a credential


async def _ingest(monkeypatch: pytest.MonkeyPatch) -> tuple[MemoryEventLog, Settings]:
    monkeypatch.setenv("CG_WEBHOOK_GITHUB_SECRET", SECRET)
    monkeypatch.delenv("CG_ONTOLOGY_PACKS", raising=False)
    settings = Settings()
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    log = MemoryEventLog()
    app.state.settings = settings
    app.state.event_store = log
    app.state.ontology = load_registry(["pdlc"])
    deliveries: list[dict[str, Any]] = orjson.loads((OPENDAL / "deliveries.json").read_bytes())[
        "deliveries"
    ]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for delivery in deliveries:
            body = orjson.dumps(delivery["body"])
            signature = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
            response = await client.post(
                "/v1/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": delivery["event"],
                    "X-GitHub-Delivery": delivery["delivery"],
                    "X-Hub-Signature-256": signature,
                },
            )
            assert response.status_code == 202, response.text
            assert len(response.json()["event_ids"]) == 1
    return log, settings


@pytest.fixture(scope="module")
async def report() -> RebuildReport:
    monkeypatch = pytest.MonkeyPatch()
    try:
        log, settings = await _ingest(monkeypatch)
        projector = PackProjector(load_registry(["pdlc"]), frozenset({"webhook:github"}))
        return await rebuild(log, MemoryGraphStore(), projector, settings, eval_dirs=[OPENDAL])
    finally:
        monkeypatch.undo()


async def test_opendal_history_is_ingested_and_projected(report: RebuildReport) -> None:
    assert report.events == 292
    assert report.dead_lettered == []


# Measured at PDLC 1.4.0; the misses are the gaps the set's header documents.
# A change in any score fails here: update the pins and the header together.
SCORES = {
    "release-of-8216": 1.0,
    "release-of-8191": 1.0,
    "release-of-7949": 1.0,
    "release-of-8035": 1.0,
    "release-of-7386": 1.0,
    "release-of-7869": 1.0,
    "release-contents-v0.59.1": 0.92,
    "reverted-7983": 0.22,
    "reverted-7927": 0.22,
    "change-for-s3-express": 0.5,
    "change-for-s3-restoration": 0.18,
    "change-for-gcs-grpc": 0.18,
    "change-for-aws-profiles": 0.5,
    "change-for-http-429": 0.33,
    "change-for-gcs-compose": 0.18,
    "release-for-gcs-grpc": 0.5,
    "release-for-s3-express": 1.0,
}


async def test_opendal_eval_set(report: RebuildReport) -> None:
    (gate,) = report.gate
    assert gate.passed, gate.as_dict()
    assert {r.id: round(r.f1, 2) for r in gate.results} == SCORES, gate.as_dict()
    assert round(gate.mean_f1, 2) == 0.63
