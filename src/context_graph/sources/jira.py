"""Jira webhooks to ``pdlc.*`` events (ADR-0018 phase 1).

| Jira ``webhookEvent`` | Emits |
|---|---|
| jira:issue_created | pdlc.ticket.created |
| jira:issue_updated | pdlc.ticket.updated (pdlc.ticket.closed when Done or Won't Do) |

Other events (deletions, comments, sprints) are ignored. Issue types map
to the pack's work types; the status name is passed as is, and the pack
maps ``To Do``, ``In Progress``, ``Done`` and ``Won't Do``.

Pure functions; no I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from context_graph.sources.events import SourceEvent

WORK_TYPES = {
    "epic": "epic",
    "story": "story",
    "task": "task",
    "sub-task": "task",
    "subtask": "task",
    "bug": "bug",
    "change": "production_change",
}

CLOSED_STATUSES = frozenset({"Done", "Won't Do"})


def translate(payload: dict[str, Any]) -> list[SourceEvent]:
    """The pack events one Jira delivery stands for (empty when not translated)."""
    webhook_event = payload.get("webhookEvent")
    issue = payload.get("issue") or {}
    fields = issue.get("fields") or {}
    key = issue.get("key")
    if webhook_event not in ("jira:issue_created", "jira:issue_updated") or not key:
        return []
    project = (fields.get("project") or {}).get("key") or str(key).split("-")[0]
    status = (fields.get("status") or {}).get("name")
    issue_type = str((fields.get("issuetype") or {}).get("name", "")).lower()
    body = {
        "tracker": "jira",
        "key": key,
        "title": fields.get("summary"),
        "work_type": WORK_TYPES.get(issue_type, "task"),
        "status": status,
        "parent_key": (fields.get("parent") or {}).get("key"),
        "resolution": (fields.get("resolution") or {}).get("name"),
    }
    occurred_at = None
    if isinstance(payload.get("timestamp"), int | float):
        occurred_at = datetime.fromtimestamp(payload["timestamp"] / 1000, tz=UTC).isoformat()
    if webhook_event == "jira:issue_created":
        event_type, cdevents = "pdlc.ticket.created", "dev.cdevents.ticket.created"
    elif status in CLOSED_STATUSES:
        event_type, cdevents = "pdlc.ticket.closed", "dev.cdevents.ticket.closed"
    else:
        event_type, cdevents = "pdlc.ticket.updated", "dev.cdevents.ticket.updated"
    return [SourceEvent(event_type, body, f"jira:{project}", occurred_at, cdevents)]
