"""``POST /v1/query/artifacts`` request checks and timeout (ADR-0018 phase 2 review)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from context_graph.api.routes.artifacts import router
from context_graph.domain.models import AtlasResponse
from context_graph.ontology import load_registry
from context_graph.settings import Settings


class SlowRetriever:
    intents = ["trace", "completeness"]

    def __init__(self, delay_s: float) -> None:
        self.delay_s = delay_s
        self.queries: list[Any] = []

    async def retrieve(self, query: Any) -> AtlasResponse:
        self.queries.append(query)
        await asyncio.sleep(self.delay_s)
        return AtlasResponse()


def _app(monkeypatch: pytest.MonkeyPatch, delay_s: float) -> tuple[FastAPI, SlowRetriever]:
    monkeypatch.setenv("CG_QUERY_DEFAULT_TIMEOUT_MS", "50")
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    retriever = SlowRetriever(delay_s)
    app.state.artifacts = retriever
    app.state.settings = Settings()
    app.state.ontology = load_registry(["pdlc"])
    app.state.eval_pending = _Pending(frozenset())
    return app, retriever


class _Pending:
    def __init__(self, packs: frozenset[str]) -> None:
        self._packs = packs

    async def packs(self) -> frozenset[str]:
        return self._packs


async def _post(app: FastAPI, body: dict[str, Any]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/v1/query/artifacts", json=body)


async def test_timeout_is_504(monkeypatch: pytest.MonkeyPatch) -> None:
    app, _retriever = _app(monkeypatch, delay_s=1.0)
    response = await _post(app, {"query": "trace PAY-1"})
    assert response.status_code == 504


@pytest.mark.parametrize(
    "body",
    [
        {"query": "   "},
        {"query": "trace", "seed_nodes": ["Change:a|1"]},  # unknown field
        {"query": "x" * 3000},
        {"query": "trace", "seed_node_ids": [f"Change:a|{n}" for n in range(51)]},
        {"query": "trace", "intent": "nonsense"},
    ],
)
async def test_invalid_requests_are_422(
    monkeypatch: pytest.MonkeyPatch, body: dict[str, Any]
) -> None:
    app, retriever = _app(monkeypatch, delay_s=0.0)
    assert (await _post(app, body)).status_code == 422
    assert retriever.queries == []


async def test_query_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    app, retriever = _app(monkeypatch, delay_s=0.0)
    assert (await _post(app, {"query": "  trace PAY-1 "})).status_code == 200
    assert retriever.queries[0].query == "trace PAY-1"


async def test_a_pending_packs_weights_are_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision 10: until its evaluation set passes, a pack's intents are refused or skipped."""
    app, retriever = _app(monkeypatch, delay_s=0)
    app.state.eval_pending = _Pending(frozenset({"pdlc"}))
    asked = await _post(app, {"query": "trace PAY-1", "intent": "trace"})
    assert asked.status_code == 409
    assert "evaluate --record" in asked.json()["detail"]
    assert (await _post(app, {"query": "trace PAY-1"})).status_code == 200
    assert retriever.queries[-1].exclude_packs == frozenset({"pdlc"})

    monkeypatch.setenv("CG_ONTOLOGY_SERVE_UNEVALUATED", "true")
    app.state.settings = Settings()
    assert (await _post(app, {"query": "trace PAY-1", "intent": "trace"})).status_code == 200
    assert retriever.queries[-1].exclude_packs == frozenset()
