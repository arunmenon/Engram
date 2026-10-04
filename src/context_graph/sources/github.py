"""GitHub webhooks to ``pdlc.*`` events (ADR-0018 phase 1).

Translated deliveries (``X-GitHub-Event``), others are ignored:

| GitHub event | Action | Emits |
|---|---|---|
| pull_request | opened, reopened | pdlc.change.created |
| pull_request | edited, synchronize | pdlc.change.updated |
| pull_request | closed, merged | pdlc.change.merged |
| pull_request | closed, not merged | pdlc.change.abandoned |
| pull_request_review | submitted | pdlc.change.reviewed |
| check_run | completed | pdlc.testcaserun.finished (skipped: .skipped) |
| release | published | pdlc.release.published |
| deployment_status | success | pdlc.service.deployed |
| issues | opened | pdlc.ticket.created |
| issues | edited, reopened, labeled, assigned | pdlc.ticket.updated |
| issues | closed | pdlc.ticket.closed |

Issue states are expressed in the tracker vocabulary the pack maps
(``To Do``, ``Done``, ``Won't Do``). Changed files are not part of pull
request webhooks, so ``files`` is empty; TOUCHES links need them.

Pure functions; no I/O.
"""

from __future__ import annotations

from typing import Any

from context_graph.sources.events import PR_REFERENCE, SourceEvent

CHECK_OUTCOMES = {
    "success": "success",
    "failure": "failure",
    "cancelled": "cancel",
    "timed_out": "error",
    "action_required": "error",
    "startup_failure": "error",
    "stale": "error",
    "skipped": "skipped",
    "neutral": "skipped",
}

REVIEW_VERDICTS = {
    "approved": "approved",
    "changes_requested": "changes_requested",
    "commented": "commented",
}

ISSUE_UPDATES = frozenset({"edited", "reopened", "labeled", "unlabeled", "assigned", "unassigned"})


def _repo(payload: dict[str, Any]) -> str | None:
    repository = payload.get("repository") or {}
    name = repository.get("full_name")
    return name if isinstance(name, str) else None


def translate(event_name: str, payload: dict[str, Any]) -> list[SourceEvent]:
    """The pack events one GitHub delivery stands for (empty when not translated)."""
    repo = _repo(payload)
    if repo is None:
        return []
    action = payload.get("action")
    handler = _HANDLERS.get(event_name)
    return handler(repo, action, payload) if handler else []


def _pull_request(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    pr = payload.get("pull_request") or {}
    base = {
        "repo": repo,
        "number": pr.get("number", payload.get("number")),
        "title": pr.get("title"),
        "body": pr.get("body") or "",
    }
    head_sha = (pr.get("head") or {}).get("sha")
    if action in ("opened", "reopened"):
        return [
            SourceEvent(
                "pdlc.change.created",
                {**base, "head_sha": head_sha, "files": []},
                repo,
                pr.get("created_at") if action == "opened" else pr.get("updated_at"),
                "dev.cdevents.change.created",
            )
        ]
    if action in ("edited", "synchronize"):
        return [
            SourceEvent(
                "pdlc.change.updated",
                {**base, "head_sha": head_sha},
                repo,
                pr.get("updated_at"),
                "dev.cdevents.change.updated",
            )
        ]
    if action == "closed" and pr.get("merged"):
        return [
            SourceEvent(
                "pdlc.change.merged",
                {**base, "merge_sha": pr.get("merge_commit_sha"), "files": []},
                repo,
                pr.get("merged_at"),
                "dev.cdevents.change.merged",
            )
        ]
    if action == "closed":
        return [
            SourceEvent(
                "pdlc.change.abandoned",
                base,
                repo,
                pr.get("closed_at"),
                "dev.cdevents.change.abandoned",
            )
        ]
    return []


def _review(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    review = payload.get("review") or {}
    verdict = REVIEW_VERDICTS.get(str(review.get("state", "")).lower())
    if action != "submitted" or verdict is None:
        return []
    pr = payload.get("pull_request") or {}
    return [
        SourceEvent(
            "pdlc.change.reviewed",
            {
                "repo": repo,
                "number": pr.get("number"),
                "review_id": str(review.get("id")),
                "verdict": verdict,
            },
            repo,
            review.get("submitted_at"),
            "dev.cdevents.change.reviewed",
        )
    ]


def _check_run(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    run = payload.get("check_run") or {}
    if action != "completed":
        return []
    outcome = CHECK_OUTCOMES.get(str(run.get("conclusion", "")), "error")
    pulls = run.get("pull_requests") or []
    event_type = "pdlc.testcaserun.skipped" if outcome == "skipped" else "pdlc.testcaserun.finished"
    return [
        SourceEvent(
            event_type,
            {
                "repo": repo,
                "test_id": run.get("name"),
                "name": run.get("name"),
                "path": None,
                "run_id": str(run.get("id")),
                "outcome": outcome,
                "commit_sha": run.get("head_sha"),
                "change_number": pulls[0].get("number") if pulls else None,
            },
            repo,
            run.get("completed_at"),
            "dev.cdevents." + event_type.removeprefix("pdlc."),
        )
    ]


def _release(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    release = payload.get("release") or {}
    if action != "published":
        return []
    notes = release.get("body") or ""
    numbers = sorted({int(n) for n in PR_REFERENCE.findall(notes)})
    return [
        SourceEvent(
            "pdlc.release.published",
            {
                "repo": repo,
                "version": release.get("tag_name"),
                "has_breaking": "breaking" in notes.lower(),
                "entries": [{"pr_number": n, "section": "other"} for n in numbers],
            },
            repo,
            release.get("published_at"),
            "dev.cdevents.artifact.published",
        )
    ]


def _deployment_status(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    status = payload.get("deployment_status") or {}
    deployment = payload.get("deployment") or {}
    if status.get("state") != "success":
        return []
    repository = payload.get("repository") or {}
    return [
        SourceEvent(
            "pdlc.service.deployed",
            {
                "service": repository.get("name"),
                "environment": deployment.get("environment") or status.get("environment"),
                "artifact_id": deployment.get("sha"),
                "repo": repo,
                "change_numbers": [],
            },
            repo,
            status.get("created_at"),
            "dev.cdevents.service.deployed",
        )
    ]


def _issue(repo: str, action: Any, payload: dict[str, Any]) -> list[SourceEvent]:
    issue = payload.get("issue") or {}
    if issue.get("pull_request"):
        return []  # pull requests also arrive as issues
    labels = {str(label.get("name", "")).lower() for label in issue.get("labels") or []}
    closed = issue.get("state") == "closed"
    status = "To Do"
    if closed:
        status = "Won't Do" if issue.get("state_reason") == "not_planned" else "Done"
    body = {
        "tracker": "github",
        "key": f"{repo}#{issue.get('number')}",
        "title": issue.get("title"),
        "work_type": "bug" if "bug" in labels else "task",
        "status": status,
        "resolution": issue.get("state_reason"),
    }
    if action == "opened":
        event_type, cdevents = "pdlc.ticket.created", "dev.cdevents.ticket.created"
    elif action == "closed":
        event_type, cdevents = "pdlc.ticket.closed", "dev.cdevents.ticket.closed"
    elif action in ISSUE_UPDATES:
        event_type, cdevents = "pdlc.ticket.updated", "dev.cdevents.ticket.updated"
    else:
        return []
    return [SourceEvent(event_type, body, repo, issue.get("updated_at"), cdevents)]


_HANDLERS = {
    "pull_request": _pull_request,
    "pull_request_review": _review,
    "check_run": _check_run,
    "release": _release,
    "deployment_status": _deployment_status,
    "issues": _issue,
}
