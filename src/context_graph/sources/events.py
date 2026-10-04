"""What a source adapter emits."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Agent ids the webhook routes ingest under; the generic ingest refuses them,
# so source trust cannot be claimed by an API client
WEBHOOK_AGENT_PREFIX = "webhook:"

# Pull request references in release notes: "#123", or GitHub's own
# ".../pull/123" links (auto-generated notes use these)
PR_REFERENCE = re.compile(r"(?<![\w/])#(\d+)\b|/pull/(\d+)\b")

# A breaking-change marker, not "non-breaking"
BREAKING = re.compile(r"(?<![\w-])breaking(?:\s+changes?)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class SourceEvent:
    """One event translated from a webhook delivery.

    ``scope`` groups events into a session (a repository or a project), so
    an artifact's events follow each other in the graph.
    """

    event_type: str
    payload: dict[str, Any]
    scope: str
    occurred_at: str | None = None
    cdevents_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
