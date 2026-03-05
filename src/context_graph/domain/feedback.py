"""Retrieval feedback domain model.

Captures user feedback on retrieval quality — which nodes were helpful
and which were irrelevant — to enable feedback-driven importance scoring.

Pure Python + Pydantic v2 — ZERO framework imports.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RetrievalFeedback(BaseModel):
    """User feedback on a retrieval result."""

    query_id: str
    session_id: str
    helpful_node_ids: list[str] = Field(default_factory=list, max_length=100)
    irrelevant_node_ids: list[str] = Field(default_factory=list, max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
