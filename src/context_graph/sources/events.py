"""What a source adapter emits."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# "#123" references in free text (release notes, commit messages)
PR_REFERENCE = re.compile(r"(?<![\w/])#(\d+)\b")


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
