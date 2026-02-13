"""4-factor Ebbinghaus decay scoring (ADR-0008).

Computes recency, importance, relevance, and composite scores for graph nodes.
Pure Python + stdlib — ZERO framework imports.

Scoring formula:
  - Recency: R = e^(-t / S) where S = s_base + (access_count * s_boost)
  - Importance: normalized hint + access + centrality boosts
  - Relevance: cosine similarity between query and node embeddings
  - Composite: weighted sum of all factors, normalized
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from context_graph.domain.models import NodeScores


def compute_recency_score(
    occurred_at: datetime,
    access_count: int = 0,
    s_base: float = 168.0,
    s_boost: float = 24.0,
    now: datetime | None = None,
    last_accessed_at: datetime | None = None,
) -> float:
    """Ebbinghaus forgetting curve: R = e^(-t / S).

    S = s_base + (access_count * s_boost) — stability grows with repeated access.
    t = hours since the most recent of occurred_at and last_accessed_at.

    Returns a value in [0.0, 1.0].
    """
    if now is None:
        now = datetime.now(UTC)
    effective_time = occurred_at
    if last_accessed_at is not None:
        effective_time = max(occurred_at, last_accessed_at)
    t_hours = max(0.0, (now - effective_time).total_seconds() / 3600.0)
    stability = s_base + (access_count * s_boost)
    if stability <= 0:
        return 0.0
    return math.exp(-t_hours / stability)


def compute_importance_score(
    importance_hint: int | None = None,
    access_count: int = 0,
    in_degree: int = 0,
) -> float:
    """Normalize importance to [0.0, 1.0] with access and centrality boosts.

    Base score comes from importance_hint (1-10 scale, normalized to 0.0-1.0).
    Defaults to 0.5 when no hint is provided.
    """
    base = (importance_hint / 10.0) if importance_hint is not None else 0.5
    access_boost = min(0.2, math.log1p(access_count) * 0.05)
    degree_boost = min(0.2, math.log1p(in_degree) * 0.05)
    return min(1.0, base + access_boost + degree_boost)


def compute_relevance_score(
    query_embedding: list[float],
    node_embedding: list[float],
) -> float:
    """Cosine similarity between query and node embeddings.

    Returns 0.5 when either embedding is empty, dimensions mismatch,
    or vectors are zero. Result is clamped to [0.0, 1.0].
    """
    if not query_embedding or not node_embedding or len(query_embedding) != len(node_embedding):
        return 0.5
    dot_product = sum(a * b for a, b in zip(query_embedding, node_embedding, strict=True))
    norm_query = math.sqrt(sum(a * a for a in query_embedding))
    norm_node = math.sqrt(sum(b * b for b in node_embedding))
    if norm_query == 0.0 or norm_node == 0.0:
        return 0.5
    return max(0.0, min(1.0, dot_product / (norm_query * norm_node)))


def compute_composite_score(
    recency: float,
    importance: float,
    relevance: float,
    user_affinity: float = 0.0,
    w_recency: float = 1.0,
    w_importance: float = 1.0,
    w_relevance: float = 1.0,
    w_user_affinity: float = 0.5,
) -> float:
    """Weighted composite score, normalized by total weight."""
    total_weight = w_recency + w_importance + w_relevance + w_user_affinity
    if total_weight == 0:
        return 0.0
    raw = (
        w_recency * recency
        + w_importance * importance
        + w_relevance * relevance
        + w_user_affinity * user_affinity
    )
    return raw / total_weight


def score_node(
    node_data: dict[str, Any],
    query_embedding: list[float] | None = None,
    s_base: float = 168.0,
    s_boost: float = 24.0,
    w_recency: float = 1.0,
    w_importance: float = 1.0,
    w_relevance: float = 1.0,
    w_user_affinity: float = 0.5,
    now: datetime | None = None,
) -> NodeScores:
    """Score a node from its data dict and return a NodeScores model.

    Expected keys in node_data:
      - occurred_at: ISO datetime string or datetime object
      - access_count: int (default 0)
      - importance_score: int 1-10 or None
      - embedding: list[float] (default [])
      - in_degree: int (default 0)
      - user_affinity: float (default 0.0)
    """
    # Parse occurred_at
    occurred_at_raw = node_data.get("occurred_at")
    if isinstance(occurred_at_raw, str):
        occurred_at = datetime.fromisoformat(occurred_at_raw)
    elif isinstance(occurred_at_raw, datetime):
        occurred_at = occurred_at_raw
    else:
        # Fallback to now (node will get recency=1.0)
        occurred_at = datetime.now(UTC) if now is None else now

    access_count = node_data.get("access_count", 0)
    importance_hint = node_data.get("importance_score")
    node_embedding = node_data.get("embedding", [])
    in_degree = node_data.get("in_degree", 0)
    user_affinity = node_data.get("user_affinity", 0.0)

    # Parse last_accessed_at for recency boost
    last_accessed_raw = node_data.get("last_accessed_at")
    last_accessed_at: datetime | None = None
    if isinstance(last_accessed_raw, str):
        last_accessed_at = datetime.fromisoformat(last_accessed_raw)
    elif isinstance(last_accessed_raw, datetime):
        last_accessed_at = last_accessed_raw

    recency = compute_recency_score(
        occurred_at,
        access_count=access_count,
        s_base=s_base,
        s_boost=s_boost,
        now=now,
        last_accessed_at=last_accessed_at,
    )
    importance = compute_importance_score(
        importance_hint=importance_hint, access_count=access_count, in_degree=in_degree
    )
    relevance = compute_relevance_score(query_embedding or [], node_embedding)
    composite = compute_composite_score(
        recency,
        importance,
        relevance,
        user_affinity=user_affinity,
        w_recency=w_recency,
        w_importance=w_importance,
        w_relevance=w_relevance,
        w_user_affinity=w_user_affinity,
    )

    # importance_score in NodeScores is int (1-10 scale); map from float
    importance_int = importance_hint if importance_hint is not None else round(importance * 10)

    return NodeScores(
        decay_score=round(composite, 6),
        relevance_score=round(relevance, 6),
        importance_score=importance_int,
    )


def compute_user_affinity(
    session_proximity: float = 0.0,
    retrieval_recurrence: float = 0.0,
    entity_overlap: float = 0.0,
) -> float:
    """Compute user affinity from sub-components (ADR-0008).

    Weighted average: 0.4*proximity + 0.3*recurrence + 0.3*overlap.
    All inputs should be in [0.0, 1.0]. Result is clamped to [0.0, 1.0].
    """
    raw = 0.4 * session_proximity + 0.3 * retrieval_recurrence + 0.3 * entity_overlap
    return max(0.0, min(1.0, raw))
