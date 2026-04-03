"""Evaluation harness for autoresearch-style scoring optimization.

This is the "train.py equivalent" for tuning scoring parameters. It loads the
eval dataset, scores all nodes with given parameters, and computes retrieval
quality metrics (nDCG, violation rate, precision, recall).

Pure Python + stdlib — ZERO framework dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Import the dataset loader
try:
    from tests.eval.dataset import EvalNode, EvalQuery, load_eval_dataset
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tests.eval.dataset import EvalNode, EvalQuery, load_eval_dataset


@dataclass
class ScoringParams:
    """Editable scoring parameters for the optimization loop."""

    # Decay curve
    s_base: float = 168.0  # Event stability base (hours)
    s_boost: float = 24.0  # Stability boost per access (hours)
    entity_s_base: float = 336.0  # Entity stability base (hours)
    entity_s_boost: float = 24.0  # Entity stability boost per mention

    # Composite weights
    w_recency: float = 1.0
    w_importance: float = 1.0
    w_relevance: float = 1.0
    w_user_affinity: float = 0.5

    # Importance sub-parameters
    access_boost_coeff: float = 0.05  # log1p(access_count) * this
    access_boost_cap: float = 0.2  # max access boost
    degree_boost_coeff: float = 0.05  # log1p(in_degree) * this
    degree_boost_cap: float = 0.2  # max degree boost

    # Intent-aware weight modifiers (structural addition)
    # These multiply the "primary" weight for each intent group
    intent_recency_bias: float = 1.0  # boost w_recency for "when" queries
    intent_importance_bias: float = 1.0  # boost w_importance for "why" queries
    intent_relevance_bias: float = 1.0  # boost w_relevance for "related/what/how_does"
    intent_affinity_bias: float = 1.0  # boost w_user_affinity for "who_is/personalize"

    # Query embedding strategy
    use_centroid_embedding: bool = True  # average all expected nodes, not just first

    # Relevance sharpening (legacy, kept for CLI compat)
    relevance_exponent: float = 1.0

    # Node-type scoring: multiplier on composite score for Event vs Entity nodes
    # > 1 favors Events, < 1 favors Entities
    # Each intent group can further boost this via intent biases
    node_type_event_bonus: float = 1.0  # base bonus for Event nodes
    node_type_profile_bonus: float = 1.0  # base bonus for UserProfile/Pref/Skill nodes


# Intent → which weight to boost
INTENT_WEIGHT_MAP: dict[str, str] = {
    "when": "w_recency",
    "why": "w_importance",
    "related": "w_relevance",
    "what": "w_relevance",
    "how_does": "w_relevance",
    "who_is": "w_user_affinity",
    "personalize": "w_user_affinity",
    "general": "",  # no specific boost
}

# Intent → which bias parameter to use
INTENT_BIAS_MAP: dict[str, str] = {
    "when": "intent_recency_bias",
    "why": "intent_importance_bias",
    "related": "intent_relevance_bias",
    "what": "intent_relevance_bias",
    "how_does": "intent_relevance_bias",
    "who_is": "intent_affinity_bias",
    "personalize": "intent_affinity_bias",
    "general": "",
}


def get_intent_weights(params: ScoringParams, intent: str) -> dict[str, float]:
    """Return effective weights adjusted for query intent.

    For non-general intents, the 'primary' weight gets multiplied by
    the corresponding intent bias parameter.
    """
    weights = {
        "w_recency": params.w_recency,
        "w_importance": params.w_importance,
        "w_relevance": params.w_relevance,
        "w_user_affinity": params.w_user_affinity,
    }

    primary_weight = INTENT_WEIGHT_MAP.get(intent, "")
    bias_param = INTENT_BIAS_MAP.get(intent, "")

    if primary_weight and bias_param:
        bias_value = getattr(params, bias_param, 1.0)
        weights[primary_weight] *= bias_value

    return weights


@dataclass
class NodeScores:
    """Scores computed for a node (mirrors domain/models.py)."""

    decay_score: float
    relevance_score: float
    importance_score: int


@dataclass
class QueryResult:
    """Result of evaluating a single query."""

    query_id: str
    intent: str
    ndcg: float
    violation_rate: float
    precision: float
    recall: float
    top_k_ids: list[str]


@dataclass
class EvalResult:
    """Complete evaluation result — the scalar metrics the loop optimizes."""

    # Primary metric (the ONE number to maximize)
    score: float  # Combined: (1 - violation_rate) * mean_ndcg

    # Component metrics
    mean_ndcg: float  # Average nDCG@k across all queries
    mean_violation_rate: float  # Average violation rate (want 0)
    mean_precision: float  # Average precision@k
    mean_recall: float  # Average recall@k

    # Per-intent breakdown
    intent_ndcg: dict[str, float] = field(default_factory=dict)
    intent_violations: dict[str, float] = field(default_factory=dict)

    # Per-query detail
    query_results: list[QueryResult] = field(default_factory=list)

    # Params that produced this result
    params: ScoringParams = field(default_factory=ScoringParams)


# Global cache for dataset (load once)
_dataset_cache: dict[str, Any] | None = None


def _load_dataset() -> dict[str, Any]:
    """Load and cache the evaluation dataset."""
    global _dataset_cache
    if _dataset_cache is None:
        _dataset_cache = load_eval_dataset()
    return _dataset_cache


# ============================================================================
# Scoring Functions (reimplemented to use timezone.utc instead of UTC)
# ============================================================================


def compute_recency_score(
    occurred_at: datetime,
    access_count: int = 0,
    s_base: float = 168.0,
    s_boost: float = 24.0,
    now: datetime | None = None,
    last_accessed_at: datetime | None = None,
    sublinear: bool = True,
) -> float:
    """Ebbinghaus forgetting curve: R = e^(-t / S).

    When sublinear=True (default):
      S = s_base * (1.0 + (s_boost / s_base) * log1p(access_count))
    When sublinear=False (backward-compatible linear):
      S = s_base + (access_count * s_boost)

    t = hours since the most recent of occurred_at and last_accessed_at.

    Returns a value in [0.0, 1.0].
    """
    if now is None:
        now = datetime.now(timezone.utc)
    effective_time = occurred_at
    if last_accessed_at is not None:
        effective_time = max(occurred_at, last_accessed_at)
    t_hours = max(0.0, (now - effective_time).total_seconds() / 3600.0)
    if sublinear:
        if s_base > 0:
            stability = s_base * (1.0 + (s_boost / s_base) * math.log1p(access_count))
        else:
            stability = 0.0
    else:
        stability = s_base + (access_count * s_boost)
    if stability <= 0:
        return 0.0
    return math.exp(-t_hours / stability)


def compute_importance_score(
    importance_hint: int | None = None,
    access_count: int = 0,
    in_degree: int = 0,
    access_boost_coeff: float = 0.05,
    access_boost_cap: float = 0.2,
    degree_boost_coeff: float = 0.05,
    degree_boost_cap: float = 0.2,
) -> float:
    """Normalize importance to [0.0, 1.0] with access and centrality boosts.

    Base score comes from importance_hint (1-10 scale, normalized to 0.0-1.0).
    Defaults to 0.5 when no hint is provided.
    """
    base = (importance_hint / 10.0) if importance_hint is not None else 0.5
    access_boost = min(access_boost_cap, math.log1p(access_count) * access_boost_coeff)
    degree_boost = min(degree_boost_cap, math.log1p(in_degree) * degree_boost_coeff)
    return min(1.0, base + access_boost + degree_boost)


def compute_relevance_score(
    query_embedding: list[float],
    node_embedding: list[float],
) -> float:
    """Cosine similarity between query and node embeddings.

    Returns 0.5 when either embedding is empty, dimensions mismatch,
    or vectors are zero. Result is clamped to [0.0, 1.0].
    """
    if (
        not query_embedding
        or not node_embedding
        or len(query_embedding) != len(node_embedding)
    ):
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
    params: ScoringParams | None = None,
    now: datetime | None = None,
) -> NodeScores:
    """Score an Event node from its data dict.

    Expected keys in node_data:
      - occurred_at: ISO datetime string or datetime object
      - access_count: int (default 0)
      - importance_score: int 1-10 or None
      - embedding: list[float] (default [])
      - in_degree: int (default 0)
      - user_affinity: float (default 0.0)
    """
    if params is None:
        params = ScoringParams()

    # Parse occurred_at
    occurred_at_raw = node_data.get("occurred_at")
    if isinstance(occurred_at_raw, str):
        occurred_at = datetime.fromisoformat(occurred_at_raw)
    elif isinstance(occurred_at_raw, datetime):
        occurred_at = occurred_at_raw
    else:
        # Fallback to now
        occurred_at = datetime.now(timezone.utc) if now is None else now

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
        s_base=params.s_base,
        s_boost=params.s_boost,
        now=now,
        last_accessed_at=last_accessed_at,
    )
    importance = compute_importance_score(
        importance_hint=importance_hint,
        access_count=access_count,
        in_degree=in_degree,
        access_boost_coeff=params.access_boost_coeff,
        access_boost_cap=params.access_boost_cap,
        degree_boost_coeff=params.degree_boost_coeff,
        degree_boost_cap=params.degree_boost_cap,
    )
    relevance = compute_relevance_score(query_embedding or [], node_embedding)
    # Apply relevance sharpening exponent
    if params.relevance_exponent != 1.0 and relevance > 0:
        relevance = relevance ** params.relevance_exponent
    composite = compute_composite_score(
        recency,
        importance,
        relevance,
        user_affinity=user_affinity,
        w_recency=params.w_recency,
        w_importance=params.w_importance,
        w_relevance=params.w_relevance,
        w_user_affinity=params.w_user_affinity,
    )

    # importance_score in NodeScores is int (1-10 scale); map from float
    importance_int = (
        importance_hint if importance_hint is not None else round(importance * 10)
    )

    return NodeScores(
        decay_score=round(composite, 6),
        relevance_score=round(relevance, 6),
        importance_score=importance_int,
    )


def score_entity_node(
    entity_data: dict[str, Any],
    query_embedding: list[float] | None = None,
    params: ScoringParams | None = None,
    now: datetime | None = None,
) -> NodeScores:
    """Score an Entity/UserProfile/Preference/Skill node for retrieval ranking.

    Entities don't have occurred_at or access_count like events.
    Uses last_seen for recency, mention_count for importance,
    and embedding similarity for relevance.
    """
    if params is None:
        params = ScoringParams()

    # Recency from last_seen
    last_seen_raw = entity_data.get("last_seen")
    if isinstance(last_seen_raw, str):
        last_seen = datetime.fromisoformat(last_seen_raw)
    elif isinstance(last_seen_raw, datetime):
        last_seen = last_seen_raw
    else:
        last_seen = datetime.now(timezone.utc) if now is None else now

    recency = compute_recency_score(
        last_seen, s_base=params.entity_s_base, s_boost=params.entity_s_boost, now=now
    )

    # Importance from mention_count
    mention_count = entity_data.get("mention_count", 1)
    importance = compute_importance_score(
        importance_hint=min(10, mention_count),
        access_count=mention_count,
        access_boost_coeff=params.access_boost_coeff,
        access_boost_cap=params.access_boost_cap,
        degree_boost_coeff=params.degree_boost_coeff,
        degree_boost_cap=params.degree_boost_cap,
    )

    # Relevance from embedding
    node_embedding = entity_data.get("embedding", [])
    relevance = compute_relevance_score(query_embedding or [], node_embedding)
    # Apply relevance sharpening exponent
    if params.relevance_exponent != 1.0 and relevance > 0:
        relevance = relevance ** params.relevance_exponent

    composite = compute_composite_score(
        recency,
        importance,
        relevance,
        w_recency=params.w_recency,
        w_importance=params.w_importance,
        w_relevance=params.w_relevance,
        w_user_affinity=params.w_user_affinity,
    )
    importance_int = min(10, max(1, mention_count))

    return NodeScores(
        decay_score=round(composite, 6),
        relevance_score=round(relevance, 6),
        importance_score=importance_int,
    )


# ============================================================================
# Metrics
# ============================================================================


def compute_ndcg(
    ranked_ids: list[str], judgments: dict[str, int], k: int = 10
) -> float:
    """Normalized Discounted Cumulative Gain.

    Args:
        ranked_ids: List of node IDs in ranked order
        judgments: {node_id: grade (1-3)} from expected_top_nodes
        k: Top-k cutoff

    Returns:
        nDCG in [0.0, 1.0]
    """
    # Compute DCG
    dcg = 0.0
    for i, node_id in enumerate(ranked_ids[:k]):
        grade = judgments.get(node_id, 0)
        if grade > 0:
            dcg += grade / math.log2(i + 2)  # i+2 because position is 1-indexed

    # Compute ideal DCG (grades sorted descending)
    grades_sorted = sorted(judgments.values(), reverse=True)
    idcg = 0.0
    for i, grade in enumerate(grades_sorted[:k]):
        idcg += grade / math.log2(i + 2)

    if idcg == 0:
        return 0.0
    return dcg / idcg


def compute_violation_rate(
    ranked_ids: list[str], must_not_appear: list[str], k: int = 10
) -> float:
    """Fraction of top-k that are in must_not_appear list.

    Args:
        ranked_ids: List of node IDs in ranked order
        must_not_appear: List of node IDs that should not appear
        k: Top-k cutoff

    Returns:
        Violation rate in [0.0, 1.0]
    """
    if k == 0:
        return 0.0
    top_k = set(ranked_ids[:k])
    must_not_set = set(must_not_appear)
    violations = len(top_k & must_not_set)
    return violations / k


def compute_precision_at_k(
    ranked_ids: list[str], relevant: set[str], k: int = 10
) -> float:
    """Fraction of top-k that are in the relevant set.

    Args:
        ranked_ids: List of node IDs in ranked order
        relevant: Set of relevant node IDs
        k: Top-k cutoff

    Returns:
        Precision in [0.0, 1.0]
    """
    if k == 0:
        return 0.0
    top_k = set(ranked_ids[:k])
    hits = len(top_k & relevant)
    return hits / k


def compute_recall_at_k(
    ranked_ids: list[str], relevant: set[str], k: int = 10
) -> float:
    """Fraction of relevant nodes that appear in top-k.

    Args:
        ranked_ids: List of node IDs in ranked order
        relevant: Set of relevant node IDs
        k: Top-k cutoff

    Returns:
        Recall in [0.0, 1.0]
    """
    if len(relevant) == 0:
        return 0.0
    top_k = set(ranked_ids[:k])
    hits = len(top_k & relevant)
    return hits / len(relevant)


# ============================================================================
# Evaluation Runner
# ============================================================================


def evaluate(params: ScoringParams, k: int = 10) -> EvalResult:
    """Run full evaluation with given scoring parameters.

    This is the function the autoresearch loop calls each cycle.

    Args:
        params: ScoringParams with all tunable parameters
        k: Top-k cutoff (default 10)

    Returns:
        EvalResult with a single .score to maximize
    """
    dataset = _load_dataset()
    all_nodes = dataset["all_nodes"]
    all_queries = dataset["queries"]

    # Fixed evaluation time: 2 hours after base time
    base_time = datetime.fromisoformat(dataset["metadata"]["base_time"])
    now = base_time.replace(hour=12, minute=0, second=0, microsecond=0)

    query_results: list[QueryResult] = []
    intent_ndcg_dict: dict[str, list[float]] = {}
    intent_violations_dict: dict[str, list[float]] = {}

    # Intents where centroid embedding empirically helps
    # (why/when/general/how_does benefit from averaged query representation)
    # Intents where first-node embedding works better:
    # (what/related — diverse expected nodes create diluted centroids)
    CENTROID_INTENTS = {"why", "when", "general", "how_does", "personalize"}

    for query in all_queries:
        # Per-intent embedding strategy
        use_centroid = (
            params.use_centroid_embedding
            and query.intent in CENTROID_INTENTS
            and len(query.expected_top_nodes) > 1
        )

        query_embedding: list[float] = []
        if use_centroid:
            # Average embeddings of ALL expected relevant nodes
            embeddings = []
            for judgment in query.expected_top_nodes:
                if judgment.node_id in all_nodes:
                    emb = all_nodes[judgment.node_id].attributes.get("embedding", [])
                    if emb:
                        embeddings.append(emb)
            if embeddings:
                dim = len(embeddings[0])
                query_embedding = [
                    sum(e[d] for e in embeddings) / len(embeddings)
                    for d in range(dim)
                ]
        elif query.expected_top_nodes:
            first_node_id = query.expected_top_nodes[0].node_id
            if first_node_id in all_nodes:
                first_node = all_nodes[first_node_id]
                query_embedding = first_node.attributes.get("embedding", [])

        # Get intent-aware weights for this query
        effective_weights = get_intent_weights(params, query.intent)

        # Build an intent-modified params copy for scoring
        intent_params = ScoringParams(
            s_base=params.s_base,
            s_boost=params.s_boost,
            entity_s_base=params.entity_s_base,
            entity_s_boost=params.entity_s_boost,
            w_recency=effective_weights["w_recency"],
            w_importance=effective_weights["w_importance"],
            w_relevance=effective_weights["w_relevance"],
            w_user_affinity=effective_weights["w_user_affinity"],
            access_boost_coeff=params.access_boost_coeff,
            access_boost_cap=params.access_boost_cap,
            degree_boost_coeff=params.degree_boost_coeff,
            degree_boost_cap=params.degree_boost_cap,
        )

        # Determine node-type bonuses for this intent
        # These are INDEPENDENT of the intent weight biases (no double-dipping)
        intent = query.intent
        event_bonus = params.node_type_event_bonus
        profile_bonus = params.node_type_profile_bonus

        # Score ALL nodes with intent-aware weights
        node_scores: dict[str, float] = {}
        for node_id, node in all_nodes.items():
            node_data = node.attributes
            node_type = node.node_type

            if node_type == "Event":
                scores = score_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score * event_bonus
            elif node_type in ("UserProfile", "Preference", "Skill"):
                scores = score_entity_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score * profile_bonus
            else:
                scores = score_entity_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score

        # Sort by composite score descending
        ranked_ids = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        ranked_ids = [node_id for node_id, _ in ranked_ids]

        # Build judgment dict
        judgments = {
            judgment.node_id: judgment.grade
            for judgment in query.expected_top_nodes
        }
        relevant_set = set(judgments.keys())

        # Compute metrics
        ndcg = compute_ndcg(ranked_ids, judgments, k)
        violation_rate = compute_violation_rate(ranked_ids, query.must_not_appear, k)
        precision = compute_precision_at_k(ranked_ids, relevant_set, k)
        recall = compute_recall_at_k(ranked_ids, relevant_set, k)

        result = QueryResult(
            query_id=query.query_id,
            intent=query.intent,
            ndcg=ndcg,
            violation_rate=violation_rate,
            precision=precision,
            recall=recall,
            top_k_ids=ranked_ids[:k],
        )
        query_results.append(result)

        # Accumulate intent metrics
        if query.intent not in intent_ndcg_dict:
            intent_ndcg_dict[query.intent] = []
            intent_violations_dict[query.intent] = []
        intent_ndcg_dict[query.intent].append(ndcg)
        intent_violations_dict[query.intent].append(violation_rate)

    # Compute aggregates
    mean_ndcg = sum(r.ndcg for r in query_results) / len(query_results) if query_results else 0.0
    mean_violation_rate = (
        sum(r.violation_rate for r in query_results) / len(query_results)
        if query_results
        else 0.0
    )
    mean_precision = (
        sum(r.precision for r in query_results) / len(query_results)
        if query_results
        else 0.0
    )
    mean_recall = (
        sum(r.recall for r in query_results) / len(query_results)
        if query_results
        else 0.0
    )

    # Per-intent breakdown
    intent_ndcg = {
        intent: sum(scores) / len(scores)
        for intent, scores in intent_ndcg_dict.items()
    }
    intent_violations = {
        intent: sum(scores) / len(scores)
        for intent, scores in intent_violations_dict.items()
    }

    # Primary score: penalize violations multiplicatively, reward retrieval quality
    combined_score = (1.0 - mean_violation_rate) * mean_ndcg

    return EvalResult(
        score=combined_score,
        mean_ndcg=mean_ndcg,
        mean_violation_rate=mean_violation_rate,
        mean_precision=mean_precision,
        mean_recall=mean_recall,
        intent_ndcg=intent_ndcg,
        intent_violations=intent_violations,
        query_results=query_results,
        params=params,
    )


# ============================================================================
# Reporting
# ============================================================================


def format_report(result: EvalResult) -> str:
    """Format evaluation result as a clean report."""
    lines = []

    # Header
    lines.append("═" * 73)
    lines.append("  AUTORESEARCH EVAL — Context Graph Scoring")
    lines.append("═" * 73)
    lines.append("")

    # Parameters
    lines.append("Parameters:")
    p = result.params
    lines.append(
        f"  s_base={p.s_base:5.1f}  s_boost={p.s_boost:5.1f}  "
        f"entity_s_base={p.entity_s_base:6.1f}  entity_s_boost={p.entity_s_boost:5.1f}"
    )
    lines.append(
        f"  w_recency={p.w_recency:3.1f}  w_importance={p.w_importance:3.1f}  "
        f"w_relevance={p.w_relevance:3.1f}  w_user_affinity={p.w_user_affinity:3.1f}"
    )
    lines.append("")

    # Primary score
    lines.append("═" * 73)
    lines.append(f"  SCORE: {result.score:.4f}  (higher is better)")
    lines.append("═" * 73)
    lines.append("")

    # Component metrics
    lines.append("Component Metrics:")
    lines.append(f"  nDCG@10:          {result.mean_ndcg:.4f}")
    lines.append(f"  Violation Rate:   {result.mean_violation_rate:.4f}  (want 0.0)")
    lines.append(f"  Precision@10:     {result.mean_precision:.4f}")
    lines.append(f"  Recall@10:        {result.mean_recall:.4f}")
    lines.append("")

    # Per-intent breakdown
    lines.append("Per-Intent Breakdown:")
    lines.append(f"  {'Intent':<15s} {'nDCG':<10s} {'Violations':<10s}")
    for intent in sorted(result.intent_ndcg.keys()):
        ndcg = result.intent_ndcg[intent]
        violations = result.intent_violations[intent]
        lines.append(f"  {intent:<15s} {ndcg:<10.4f} {violations:<10.4f}")
    lines.append("")

    # Worst queries
    worst_queries = sorted(result.query_results, key=lambda q: q.ndcg)[:3]
    if worst_queries:
        lines.append("Worst Queries:")
        for q in worst_queries:
            violations = int(q.violation_rate * len(q.top_k_ids))
            lines.append(
                f"  {q.query_id:<20s} nDCG={q.ndcg:.4f}  "
                f"violations={violations}/{len(q.top_k_ids)}"
            )
        lines.append("")

    lines.append("═" * 73)

    return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autoresearch evaluation harness for scoring parameters"
    )

    # Decay parameters
    parser.add_argument(
        "--s_base", type=float, default=168.0, help="Event stability base (hours)"
    )
    parser.add_argument(
        "--s_boost", type=float, default=24.0, help="Stability boost per access (hours)"
    )
    parser.add_argument(
        "--entity_s_base",
        type=float,
        default=336.0,
        help="Entity stability base (hours)",
    )
    parser.add_argument(
        "--entity_s_boost",
        type=float,
        default=24.0,
        help="Entity stability boost per mention",
    )

    # Composite weights
    parser.add_argument("--w_recency", type=float, default=1.0, help="Recency weight")
    parser.add_argument(
        "--w_importance", type=float, default=1.0, help="Importance weight"
    )
    parser.add_argument(
        "--w_relevance", type=float, default=1.0, help="Relevance weight"
    )
    parser.add_argument(
        "--w_user_affinity", type=float, default=0.5, help="User affinity weight"
    )

    # Importance sub-parameters
    parser.add_argument(
        "--access_boost_coeff",
        type=float,
        default=0.05,
        help="log1p(access_count) * this",
    )
    parser.add_argument(
        "--access_boost_cap", type=float, default=0.2, help="Max access boost"
    )
    parser.add_argument(
        "--degree_boost_coeff",
        type=float,
        default=0.05,
        help="log1p(in_degree) * this",
    )
    parser.add_argument(
        "--degree_boost_cap", type=float, default=0.2, help="Max degree boost"
    )

    # Intent-aware weight modifiers
    parser.add_argument(
        "--intent_recency_bias",
        type=float,
        default=1.0,
        help="Boost w_recency for 'when' queries",
    )
    parser.add_argument(
        "--intent_importance_bias",
        type=float,
        default=1.0,
        help="Boost w_importance for 'why' queries",
    )
    parser.add_argument(
        "--intent_relevance_bias",
        type=float,
        default=1.0,
        help="Boost w_relevance for 'related/what/how_does' queries",
    )
    parser.add_argument(
        "--intent_affinity_bias",
        type=float,
        default=1.0,
        help="Boost w_user_affinity for 'who_is/personalize' queries",
    )
    parser.add_argument(
        "--no_centroid",
        action="store_true",
        help="Disable centroid embedding (use first expected node only)",
    )

    # Output
    parser.add_argument(
        "--json", action="store_true", help="Output result as JSON instead of report"
    )
    parser.add_argument(
        "--k", type=int, default=10, help="Top-k cutoff for evaluation"
    )

    return parser.parse_args()


def main() -> None:
    """Main CLI entry point."""
    args = parse_args()

    # Build params from args
    params = ScoringParams(
        s_base=args.s_base,
        s_boost=args.s_boost,
        entity_s_base=args.entity_s_base,
        entity_s_boost=args.entity_s_boost,
        w_recency=args.w_recency,
        w_importance=args.w_importance,
        w_relevance=args.w_relevance,
        w_user_affinity=args.w_user_affinity,
        access_boost_coeff=args.access_boost_coeff,
        access_boost_cap=args.access_boost_cap,
        degree_boost_coeff=args.degree_boost_coeff,
        degree_boost_cap=args.degree_boost_cap,
        intent_recency_bias=args.intent_recency_bias,
        intent_importance_bias=args.intent_importance_bias,
        intent_relevance_bias=args.intent_relevance_bias,
        intent_affinity_bias=args.intent_affinity_bias,
        use_centroid_embedding=not args.no_centroid,
    )

    # Run evaluation
    result = evaluate(params, k=args.k)

    # Output
    if args.json:
        # Serialize to JSON
        output = {
            "score": result.score,
            "mean_ndcg": result.mean_ndcg,
            "mean_violation_rate": result.mean_violation_rate,
            "mean_precision": result.mean_precision,
            "mean_recall": result.mean_recall,
            "intent_ndcg": result.intent_ndcg,
            "intent_violations": result.intent_violations,
            "params": {
                "s_base": result.params.s_base,
                "s_boost": result.params.s_boost,
                "entity_s_base": result.params.entity_s_base,
                "entity_s_boost": result.params.entity_s_boost,
                "w_recency": result.params.w_recency,
                "w_importance": result.params.w_importance,
                "w_relevance": result.params.w_relevance,
                "w_user_affinity": result.params.w_user_affinity,
                "access_boost_coeff": result.params.access_boost_coeff,
                "access_boost_cap": result.params.access_boost_cap,
                "degree_boost_coeff": result.params.degree_boost_coeff,
                "degree_boost_cap": result.params.degree_boost_cap,
                "intent_recency_bias": result.params.intent_recency_bias,
                "intent_importance_bias": result.params.intent_importance_bias,
                "intent_relevance_bias": result.params.intent_relevance_bias,
                "intent_affinity_bias": result.params.intent_affinity_bias,
                "use_centroid_embedding": result.params.use_centroid_embedding,
            },
        }
        print(json.dumps(output, indent=2))
    else:
        # Print formatted report
        print(format_report(result))


if __name__ == "__main__":
    main()
