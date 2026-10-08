"""GitHub and Jira webhooks: translation and the route (ADR-0018 phase 1)."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any

import httpx
import orjson
import pytest
from fastapi import FastAPI

from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.api.routes.webhooks import router
from context_graph.ontology import load_registry
from context_graph.settings import Settings
from context_graph.sources import github, jira

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "webhooks"
SECRET = "test-secret"  # noqa: S105 - test value, not a credential


def _fixture(name: str) -> dict[str, Any]:
    return orjson.loads((FIXTURES / f"{name}.json").read_bytes())


class TestGitHub:
    @pytest.mark.parametrize(
        ("event_name", "fixture", "event_type"),
        [
            ("pull_request", "github_pull_request_opened", "pdlc.change.created"),
            ("pull_request", "github_pull_request_merged", "pdlc.change.merged"),
            ("pull_request_review", "github_pull_request_review_submitted", "pdlc.change.reviewed"),
            ("check_run", "github_check_run_completed", "pdlc.testcaserun.finished"),
            ("release", "github_release_published", "pdlc.release.published"),
            ("deployment_status", "github_deployment_status_success", "pdlc.service.deployed"),
            ("issues", "github_issues_closed", "pdlc.ticket.closed"),
        ],
    )
    def test_translated_events_are_declared(
        self, event_name: str, fixture: str, event_type: str
    ) -> None:
        (event,) = github.translate(event_name, _fixture(fixture))
        assert event.event_type == event_type
        assert event_type in load_registry(["pdlc"]).event_types
        assert event.scope == "acme/payments"
        assert event.cdevents_type and event.cdevents_type.startswith("dev.cdevents.")

    def test_payload_fields(self) -> None:
        (merged,) = github.translate("pull_request", _fixture("github_pull_request_merged"))
        assert merged.payload["merge_sha"] == "def456"
        assert merged.payload["number"] == 7
        assert merged.occurred_at == "2026-10-01T12:00:00Z"
        (run,) = github.translate("check_run", _fixture("github_check_run_completed"))
        assert run.payload["outcome"] == "failure"
        assert run.payload["change_number"] == 7
        (release,) = github.translate("release", _fixture("github_release_published"))
        assert [e["pr_number"] for e in release.payload["entries"]] == [7, 8]
        (issue,) = github.translate("issues", _fixture("github_issues_closed"))
        assert issue.payload == {
            "tracker": "github",
            "key": "acme/payments#12",
            "title": "Refunds duplicated",
            "work_type": "bug",
            "status": "Done",
            "resolution": "completed",
        }

    def test_ignored_deliveries(self) -> None:
        assert github.translate("ping", _fixture("github_ping")) == []
        assert github.translate("pull_request", {"action": "opened"}) == []  # no repository
        labeled = _fixture("github_pull_request_opened") | {"action": "labeled"}
        assert github.translate("pull_request", labeled) == []


class TestJira:
    def test_created_and_closed(self) -> None:
        (created,) = jira.translate(_fixture("jira_issue_created"))
        assert created.event_type == "pdlc.ticket.created"
        assert created.payload["parent_key"] == "PAY-300"
        assert created.payload["work_type"] == "story"
        assert created.scope == "jira:PAY"
        assert created.occurred_at == "2025-10-02T09:00:00+00:00"
        (closed,) = jira.translate(_fixture("jira_issue_updated_done"))
        assert closed.event_type == "pdlc.ticket.closed"
        assert closed.payload["resolution"] == "Fixed"

    def test_ignored(self) -> None:
        assert jira.translate({"webhookEvent": "comment_created", "issue": {"key": "A-1"}}) == []
        assert jira.translate({"webhookEvent": "jira:issue_deleted", "issue": {"key": "A-1"}}) == []


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _app(
    monkeypatch: pytest.MonkeyPatch, *, configured: bool = True
) -> tuple[FastAPI, MemoryEventLog]:
    if configured:
        monkeypatch.setenv("CG_WEBHOOK_GITHUB_SECRET", SECRET)
        monkeypatch.setenv("CG_WEBHOOK_JIRA_SECRET", SECRET)
    else:
        monkeypatch.delenv("CG_WEBHOOK_GITHUB_SECRET", raising=False)
    monkeypatch.setenv("CG_WEBHOOK_MAX_BODY_BYTES", "4000")
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    log = MemoryEventLog()
    app.state.settings = Settings()
    app.state.event_store = log
    app.state.ontology = load_registry(["pdlc"])
    return app, log


async def _post(app: FastAPI, path: str, body: bytes, headers: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, content=body, headers=headers)


class TestRoute:
    @pytest.mark.parametrize(
        "mutation", ["missing_repo", "list_action", "object_action", "missing_time", "naive_time"]
    )
    async def test_invalid_pr_has_no_ledger_effects(self, monkeypatch, mutation):
        app, log = _app(monkeypatch)
        payload = _fixture("github_pull_request_opened")
        if mutation == "missing_repo":
            payload.pop("repository")
        elif mutation == "list_action":
            payload["action"] = []
        elif mutation == "object_action":
            payload["action"] = {}
        else:
            payload["pull_request"]["created_at"] = (
                None if mutation == "missing_time" else "2026-10-01T12:00:00"
            )
        body = orjson.dumps(payload)
        response = await _post(
            app,
            "/v1/webhooks/github",
            body,
            {"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": _sign(body)},
        )
        assert response.status_code == 422
        assert await log.stream_length() == 0

    async def test_signed_body_identity_ignores_transport_delivery(self, monkeypatch):
        from datetime import UTC, datetime

        from context_graph.api.routes.webhooks import build_events
        from context_graph.domain.event_acceptance import request_fingerprint

        body = (FIXTURES / "github_pull_request_opened.json").read_bytes()
        translated = github.translate("pull_request", orjson.loads(body))
        (first,) = build_events(
            "github", "first", hashlib.sha256(body).hexdigest(), translated, datetime.now(UTC)
        )
        (replay,) = build_events(
            "github",
            "another-delivery",
            hashlib.sha256(body).hexdigest(),
            translated,
            datetime.now(UTC),
        )
        assert request_fingerprint(*first) == request_fingerprint(*replay)

    async def test_signed_delivery_is_ingested_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app, log = _app(monkeypatch)
        body = (FIXTURES / "github_pull_request_merged.json").read_bytes()
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-1",
            "X-Hub-Signature-256": _sign(body),
        }
        first = await _post(app, "/v1/webhooks/github", body, headers)
        again = await _post(app, "/v1/webhooks/github", body, headers)

        assert first.status_code == 202
        assert first.json() == again.json()
        (event_id,) = first.json()["event_ids"]
        assert await log.stream_length() == 1  # the redelivery was deduplicated
        (document,) = await log.get_documents([event_id])
        assert document is not None
        assert document["event_type"] == "pdlc.change.merged"
        assert document["agent_id"] == "webhook:github"
        assert document["session_id"] == "pdlc:acme/payments"
        assert document["trace_id"] == hashlib.sha256(body).hexdigest()
        assert document["payload"]["cdevents_type"] == "dev.cdevents.change.merged"
        assert document["occurred_at"].startswith("2026-10-01T12:00:00")

    async def test_jira(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app, log = _app(monkeypatch)
        body = (FIXTURES / "jira_issue_created.json").read_bytes()
        response = await _post(app, "/v1/webhooks/jira", body, {"X-Hub-Signature": _sign(body)})
        assert response.status_code == 202
        assert len(response.json()["event_ids"]) == 1
        assert await log.stream_length() == 1

    @pytest.mark.parametrize("signature", [None, "sha256=00", "sha1=abc", _sign(b"other body")])
    async def test_bad_signatures(
        self, monkeypatch: pytest.MonkeyPatch, signature: str | None
    ) -> None:
        app, log = _app(monkeypatch)
        body = (FIXTURES / "github_ping.json").read_bytes()
        headers = {"X-GitHub-Event": "ping"}
        if signature:
            headers["X-Hub-Signature-256"] = signature
        assert (await _post(app, "/v1/webhooks/github", body, headers)).status_code == 401
        assert await log.stream_length() == 0

    async def test_unconfigured_unknown_and_large(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app, _log = _app(monkeypatch, configured=False)
        body = b"{}"
        assert (await _post(app, "/v1/webhooks/github", body, {})).status_code == 503
        assert (await _post(app, "/v1/webhooks/gitlab", body, {})).status_code == 404
        app, _log = _app(monkeypatch)
        large = b'{"x": "' + b"a" * 5000 + b'"}'
        headers = {"X-Hub-Signature-256": _sign(large)}
        assert (await _post(app, "/v1/webhooks/github", large, headers)).status_code == 413

    async def test_untranslated_delivery_is_accepted_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app, log = _app(monkeypatch)
        body = (FIXTURES / "github_ping.json").read_bytes()
        headers = {"X-GitHub-Event": "ping", "X-Hub-Signature-256": _sign(body)}
        response = await _post(app, "/v1/webhooks/github", body, headers)
        assert response.status_code == 202
        assert response.json() == {"event_ids": []}
        assert await log.stream_length() == 0

    async def test_non_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app, _log = _app(monkeypatch)
        body = b"not json"
        response = await _post(
            app, "/v1/webhooks/github", body, {"X-Hub-Signature-256": _sign(body)}
        )
        assert response.status_code == 400


class TestReviewFindings:
    """Regression cases from the phase 1 review (ADR-0018 implementation notes)."""

    async def test_odd_signature_headers_are_401_not_500(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app, _log = _app(monkeypatch)
        body = b"{}"
        transport = httpx.ASGITransport(app=app)
        headers: list[bytes] = [
            "sha256=\xff\xfe".encode("latin-1"),
            ("sha256=" + "g" * 64).encode(),
            ("sha256=" + "a" * 63).encode(),
        ]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for header in headers:
                response = await client.post(
                    "/v1/webhooks/github",
                    content=body,
                    headers=[(b"X-Hub-Signature-256", header)],
                )
                assert response.status_code == 401

    async def test_declared_length_over_the_limit_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app, _log = _app(monkeypatch)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/webhooks/github", content=b"{}", headers={"Content-Length": "999999"}
            )
        assert response.status_code == 413

    async def test_a_replayed_body_under_a_new_delivery_id_is_deduplicated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app, log = _app(monkeypatch)
        body = (FIXTURES / "github_pull_request_merged.json").read_bytes()
        for delivery in ("one", "two"):
            headers = {
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery,
                "X-Hub-Signature-256": _sign(body),
            }
            assert (await _post(app, "/v1/webhooks/github", body, headers)).status_code == 202
        assert await log.stream_length() == 1

    def test_release_notes_and_ids(self) -> None:
        release = _fixture("github_release_published")
        release["release"]["body"] = (
            "* Fix retry by @ann in https://github.com/acme/payments/pull/12\n"
            "Non-breaking changes only"
        )
        (event,) = github.translate("release", release)
        assert [e["pr_number"] for e in event.payload["entries"]] == [12]
        assert event.payload["has_breaking"] is False
        release["release"]["body"] = "## Breaking changes\n- drop v1 API #3"
        (event,) = github.translate("release", release)
        assert event.payload["has_breaking"] is True
        review = _fixture("github_pull_request_review_submitted")
        del review["review"]["id"]
        assert github.translate("pull_request_review", review) == []
        (deployed,) = github.translate(
            "deployment_status", _fixture("github_deployment_status_success")
        )
        assert deployed.payload["service"] == "acme/payments"
