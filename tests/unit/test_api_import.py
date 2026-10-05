"""``POST /v1/events/import``: bulk NDJSON import (review of 2026-10-05: 3.3, 3.6, 3.9)."""

from __future__ import annotations

import gzip
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import orjson
from fastapi import Depends, FastAPI

from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.api.dependencies import require_admin_key
from context_graph.api.middleware import register_middleware
from context_graph.api.routes.events import import_router
from context_graph.ontology import load_registry
from context_graph.ports.errors import UnavailableError
from context_graph.settings import Settings

if TYPE_CHECKING:
    import pytest

ADMIN = "admin-key"  # test value, not a credential
START = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)


def _event(minute: int, **overrides: Any) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": "tool.execute",
        "occurred_at": (START + timedelta(minutes=minute)).isoformat(),
        "session_id": "history",
        "agent_id": "importer",
        "trace_id": "t",
        "payload_ref": "p",
        **overrides,
    }


def _app(monkeypatch: pytest.MonkeyPatch, *, admin_key: str | None = ADMIN) -> FastAPI:
    if admin_key is None:
        monkeypatch.delenv("CG_AUTH_ADMIN_KEY", raising=False)
    else:
        monkeypatch.setenv("CG_AUTH_ADMIN_KEY", admin_key)
    monkeypatch.setenv("CG_INGEST_IMPORT_BATCH_SIZE", "2")
    settings = Settings()
    app = FastAPI()
    register_middleware(app, settings)
    app.include_router(import_router, prefix="/v1", dependencies=[Depends(require_admin_key)])
    app.state.settings = settings
    app.state.event_store = MemoryEventLog()
    app.state.ontology = load_registry(["pdlc"])
    return app


async def _import(
    app: FastAPI,
    lines: list[Any],
    *,
    order: str | None = None,
    key: str | None = ADMIN,
    gzipped: bool = False,
) -> tuple[int, list[dict[str, Any]]]:
    body = b"".join(
        (line if isinstance(line, bytes) else orjson.dumps(line)) + b"\n" for line in lines
    )
    headers = {"Content-Type": "application/x-ndjson"}
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"
    if gzipped:
        body = gzip.compress(body)
        headers["Content-Encoding"] = "gzip"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/events/import",
            content=body,
            headers=headers,
            params={"order": order} if order else None,
        )
    if response.headers.get("content-type", "").startswith("application/x-ndjson"):
        return response.status_code, [orjson.loads(line) for line in response.text.splitlines()]
    return response.status_code, [response.json()]


async def test_history_is_appended_in_occurrence_order(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    late, early, middle = _event(30), _event(10), _event(20)
    status, lines = await _import(app, [late, early, middle], gzipped=True)
    assert status == 200
    *outcomes, summary = lines
    assert summary == {
        "summary": {
            "received": 3,
            "order": "occurred_at",
            "created": 3,
            "duplicate": 0,
            "rejected": 0,
            "failed": 0,
        }
    }
    # Streamed in append order, each with its input index
    assert [o["index"] for o in outcomes] == [1, 2, 0]
    log: MemoryEventLog = app.state.event_store
    ids = await log.read_session_ids("history")
    assert ids == [early["event_id"], middle["event_id"], late["event_id"]]

    # Imports are idempotent: the same file again is all duplicates
    _status, again = await _import(app, [late, early, middle])
    assert again[-1]["summary"]["duplicate"] == 3
    assert {o["status"] for o in again[:-1]} == {"duplicate"}


async def test_input_order_on_request(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    late, early = _event(30), _event(10)
    _status, lines = await _import(app, [late, early], order="input")
    assert [o["index"] for o in lines[:-1]] == [0, 1]
    ids = await app.state.event_store.read_session_ids("history")
    assert ids == [late["event_id"], early["event_id"]]


async def test_bad_lines_are_reported_and_the_rest_imported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(monkeypatch)
    _status, lines = await _import(
        app, [_event(1), b"{oops", _event(2, event_type="NOT.VALID!"), _event(3)]
    )
    rejected = [line for line in lines if line.get("status") == "rejected"]
    assert [r["index"] for r in rejected] == [1, 2]
    assert rejected[0]["errors"][0]["message"].startswith("line is not valid JSON")
    assert lines[-1]["summary"]["created"] == 2


async def test_the_admin_key_vouches_for_webhook_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = _event(
        1,
        event_type="pdlc.change.merged",
        agent_id="webhook:github",
        payload={"repo": "acme/app", "number": 7, "merge_sha": "abc"},
    )
    app = _app(monkeypatch)
    _status, lines = await _import(app, [change])
    assert lines[0]["status"] == "created"  # trusted history, imported in bulk

    unkeyed = _app(monkeypatch, admin_key=None)
    _status, lines = await _import(unkeyed, [change], key=None)
    assert lines[0]["status"] == "rejected"
    assert "reserved for the webhook routes" in lines[0]["errors"][0]["message"]


async def test_the_admin_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    status, _lines = await _import(app, [_event(1)], key="wrong")
    assert status == 401


async def test_an_outage_fails_the_rest_and_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    log: MemoryEventLog = app.state.event_store
    original = log.append_batch_outcomes
    calls = 0

    async def flaky(events: Any, payloads: Any = None) -> Any:
        nonlocal calls
        calls += 1
        if calls > 1:
            msg = "store down"
            raise UnavailableError(msg)
        return await original(events, payloads)

    log.append_batch_outcomes = flaky  # type: ignore[method-assign]
    _status, lines = await _import(app, [_event(m) for m in range(5)])
    assert [line.get("status") for line in lines[:-1]] == [
        "created",
        "created",
        "failed",
        "failed",
        "failed",
    ]
    assert lines[2]["error"] == "the store failed: store down"
    assert calls == 2  # stopped after the first failure
    assert lines[-1]["summary"]["failed"] == 3


async def test_imports_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CG_INGEST_IMPORT_MAX_EVENTS", "3")
    app = _app(monkeypatch)
    status, lines = await _import(app, [_event(m) for m in range(4)])
    assert status == 413
    assert "at most 3 events" in lines[0]["detail"][0]["message"]
    status, _lines = await _import(app, [b"", b"  "])
    assert status == 422
