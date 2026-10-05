"""Ingest bodies and outcomes (review of 2026-10-05: findings 3.7, 3.8, 3.9, N4)."""

from __future__ import annotations

import gzip
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import orjson

from context_graph.api.rate_limit import EventQuota
from context_graph.ports.event_store import AppendOutcome

if TYPE_CHECKING:
    import pytest
    from fastapi.testclient import TestClient

    from context_graph.domain.models import Event


def _event(**overrides: object) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": "s",
        "agent_id": "a",
        "trace_id": "t",
        "payload_ref": "p",
        **overrides,
    }


class TestBodies:
    def test_a_body_that_is_not_an_object_is_a_client_error(self, test_client: TestClient) -> None:
        response = test_client.post("/v1/events", json=[])
        assert response.status_code == 422
        assert test_client.post("/v1/events", content=b"{not json").status_code == 400

    def test_gzip_bodies_are_read(self, test_client: TestClient) -> None:
        body = gzip.compress(orjson.dumps({"events": [_event(), _event()]}))
        response = test_client.post(
            "/v1/events/batch", content=body, headers={"Content-Encoding": "gzip"}
        )
        assert response.status_code == 201, response.text
        assert response.json()["accepted"] == 2

    def test_size_is_bounded_before_and_after_decompression(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        test_client.app.state.settings.ingest.max_body_bytes = 2_000  # type: ignore[attr-defined]
        big = orjson.dumps({"events": [_event(payload={"x": "y" * 5_000})]})
        assert test_client.post("/v1/events/batch", content=big).status_code == 413
        bomb = gzip.compress(big)  # small on the wire, too large decoded
        assert len(bomb) < 2_000
        response = test_client.post(
            "/v1/events/batch", content=bomb, headers={"Content-Encoding": "gzip"}
        )
        assert response.status_code == 413
        assert "decompressed" in response.text

    def test_unknown_encodings_are_refused(self, test_client: TestClient) -> None:
        response = test_client.post("/v1/events", content=b"x", headers={"Content-Encoding": "br"})
        assert response.status_code == 415


class TestOutcomes:
    def test_created_then_duplicate(self, test_client: TestClient) -> None:
        event = _event()
        first = test_client.post("/v1/events", json=event).json()
        again = test_client.post("/v1/events", json=event).json()
        assert (first["status"], again["status"]) == ("created", "duplicate")
        batch = test_client.post("/v1/events/batch", json={"events": [event, _event()]}).json()
        assert [r["status"] for r in batch["results"]] == ["duplicate", "created"]

    def test_a_batch_with_nothing_accepted_is_not_201(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/v1/events/batch", json={"events": [_event(event_type="BAD"), "not an event"]}
        )
        assert response.status_code == 422
        body = response.json()
        assert (body["accepted"], body["rejected"]) == (0, 2)
        assert body["errors"][1]["errors"][0]["message"] == "an event must be a JSON object"

    def test_store_failures_are_reported_per_event(self, test_client: TestClient) -> None:
        store = test_client.app.state.event_store  # type: ignore[attr-defined]
        ok, broken = _event(), _event()

        async def outcomes(
            events: list[Event], payloads: list[dict[str, Any] | None] | None = None
        ) -> list[AppendOutcome]:
            return [
                AppendOutcome("failed", error="OOM")
                if str(e.event_id) == broken["event_id"]
                else AppendOutcome("created", "9-0")
                for e in events
            ]

        store.append_batch_outcomes = outcomes
        response = test_client.post("/v1/events/batch", json={"events": [ok, broken]})
        assert response.status_code == 201
        body = response.json()
        assert body["accepted"] == 1
        assert body["errors"] == [
            {
                "index": 1,
                "event_id": broken["event_id"],
                "errors": [{"field": "store", "message": "OOM"}],
            }
        ]
        only_broken = test_client.post("/v1/events/batch", json={"events": [broken]})
        assert only_broken.status_code == 503
        assert test_client.post("/v1/events", json=broken).status_code == 503


class TestEventQuota:
    def test_batches_are_charged_per_event(self, test_client: TestClient) -> None:
        test_client.app.state.event_quota = EventQuota(events_per_minute=5)  # type: ignore[attr-defined]
        first = test_client.post("/v1/events/batch", json={"events": [_event() for _ in range(4)]})
        assert first.status_code == 201
        second = test_client.post("/v1/events/batch", json={"events": [_event(), _event()]})
        assert second.status_code == 429
        assert int(second.headers["Retry-After"]) >= 1

    def test_the_bucket_refills(self) -> None:
        quota = EventQuota(events_per_minute=60)
        assert quota.charge("c", 60) is None
        wait_s = quota.charge("c", 30)
        assert wait_s is not None
        assert 29 < wait_s <= 30.1
        # A request larger than the whole quota waits for a full bucket, then passes
        assert EventQuota(events_per_minute=10).charge("d", 1_000) is None
