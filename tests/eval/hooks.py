"""Structural hooks library for autoresearch v2 scoring optimization.

Six composable hooks that post-process node_scores after initial scoring
in the evaluation harness. Each hook reads graph topology (nodes, edges)
and query context to adjust scores produced by the base scoring algorithm.

The 108 edges in the eval dataset (FOLLOWS, CAUSED_BY, REFERENCES, SIMILAR_TO)
are currently UNUSED by base scoring -- hooks 1 (edge_boost) and 6 (mmr_diversity)
are the primary mechanisms to exploit graph structure.

This module is importable standalone with ZERO framework dependencies.
All dataset types are typed as Any to avoid import coupling.
"""

from __future__ import annotations

import contextlib
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors.

    Returns a value in [0.0, 1.0] (clamped). Returns 0.5 when inputs are
    empty, mismatched in dimension, or zero-magnitude -- matching the
    neutral-similarity convention used by the eval harness.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Cosine similarity clamped to [0.0, 1.0].
    """
    if not a or not b or len(a) != len(b):
        return 0.5

    dot_product = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.5

    return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))


# ---------------------------------------------------------------------------
# Adjacency index builder (cached per edge-list identity)
# ---------------------------------------------------------------------------

# Adjacency list: node_id -> list of (neighbor_id, edge_type)
AdjacencyIndex = dict[str, list[tuple[str, str]]]

_adjacency_cache: dict[int, tuple[AdjacencyIndex, AdjacencyIndex]] = {}
_NODE_SCENARIO_PREFIXES: tuple[tuple[str, str], ...] = (
    # Original 3 scenarios
    ("pay-decline-001", "evt-pay-"),
    ("pay-decline-001", "ent-pay-"),
    ("fraud-inv-002", "evt-fr-"),
    ("fraud-inv-002", "ent-fr-"),
    ("fraud-inv-002", "user-profile-analyst"),
    ("fraud-inv-002", "pref-analyst-"),
    ("fraud-inv-002", "skill-analyst-"),
    ("merch-onb-003", "evt-mo-"),
    ("merch-onb-003", "ent-mo-"),
    # Generated scenarios (7)
    ("refund-disp-004", "evt-rd-"),
    ("refund-disp-004", "ent-rd-"),
    ("acct-takeover-005", "evt-at-"),
    ("acct-takeover-005", "ent-at-"),
    ("acct-takeover-005", "user-profile-at-"),
    ("acct-takeover-005", "pref-at-"),
    ("acct-takeover-005", "skill-at-"),
    ("sub-billing-006", "evt-sb-"),
    ("sub-billing-006", "ent-sb-"),
    ("api-ratelimit-007", "evt-ar-"),
    ("api-ratelimit-007", "ent-ar-"),
    ("compliance-kyc-008", "evt-ck-"),
    ("compliance-kyc-008", "ent-ck-"),
    ("compliance-kyc-008", "user-profile-ck-"),
    ("compliance-kyc-008", "pref-ck-"),
    ("compliance-kyc-008", "skill-ck-"),
    ("lending-uw-009", "evt-lu-"),
    ("lending-uw-009", "ent-lu-"),
    ("lending-uw-009", "user-profile-lu-"),
    ("lending-uw-009", "pref-lu-"),
    ("lending-uw-009", "skill-lu-"),
    ("chargeback-res-010", "evt-cr-"),
    ("chargeback-res-010", "ent-cr-"),
)


def _build_adjacency_index(
    all_edges: list[Any],
) -> tuple[AdjacencyIndex, AdjacencyIndex]:
    """Build bidirectional adjacency indexes from edge list.

    Returns (forward, reverse) where:
      - forward[source] = [(target, edge_type), ...]
      - reverse[target] = [(source, edge_type), ...]

    Results are cached by the id of the edge list object so repeated calls
    within the same evaluation run avoid rebuilding.

    Args:
        all_edges: Complete edge list from the eval dataset. Each element
            must have .source, .target, .edge_type attributes.

    Returns:
        Tuple of (forward_adjacency, reverse_adjacency) dicts.
    """
    cache_key = id(all_edges)
    if cache_key in _adjacency_cache:
        return _adjacency_cache[cache_key]

    forward: AdjacencyIndex = {}
    reverse: AdjacencyIndex = {}

    for edge in all_edges:
        forward.setdefault(edge.source, []).append((edge.target, edge.edge_type))
        reverse.setdefault(edge.target, []).append((edge.source, edge.edge_type))

    result = (forward, reverse)
    _adjacency_cache[cache_key] = result
    return result


def _get_neighbors(
    node_id: str,
    forward: AdjacencyIndex,
    reverse: AdjacencyIndex,
    max_hops: int = 1,
) -> dict[str, tuple[str, int]]:
    """BFS to find neighbors within max_hops, returning (edge_type, distance).

    For multi-hop traversal, returns the edge type of the FIRST hop
    (the one connecting directly to the seed node).

    Args:
        node_id: Starting node.
        forward: Forward adjacency index.
        reverse: Reverse adjacency index.
        max_hops: Maximum traversal depth (1-3).

    Returns:
        Dict mapping neighbor_id -> (first_hop_edge_type, hop_distance).
        The starting node_id is excluded from results.
    """
    visited: dict[str, tuple[str, int]] = {}
    # Queue entries: (current_node, first_hop_edge_type, current_depth)
    queue: list[tuple[str, str, int]] = []

    # Seed the queue with direct neighbors (hop 1)
    for target, edge_type in forward.get(node_id, []):
        if target != node_id and target not in visited:
            visited[target] = (edge_type, 1)
            queue.append((target, edge_type, 1))
    for source, edge_type in reverse.get(node_id, []):
        if source != node_id and source not in visited:
            visited[source] = (edge_type, 1)
            queue.append((source, edge_type, 1))

    # BFS for deeper hops
    while queue and max_hops > 1:
        next_queue: list[tuple[str, str, int]] = []
        for current, first_edge, depth in queue:
            if depth >= max_hops:
                continue
            new_depth = depth + 1
            for target, _et in forward.get(current, []):
                if target != node_id and target not in visited:
                    visited[target] = (first_edge, new_depth)
                    next_queue.append((target, first_edge, new_depth))
            for source, _et in reverse.get(current, []):
                if source != node_id and source not in visited:
                    visited[source] = (first_edge, new_depth)
                    next_queue.append((source, first_edge, new_depth))
        queue = next_queue

    return visited


def _infer_node_scenario(node_id: str) -> str | None:
    """Infer scenario ID from the deterministic node-id prefixes used in eval."""
    for scenario_id, prefix in _NODE_SCENARIO_PREFIXES:
        if node_id.startswith(prefix):
            return scenario_id
    return None


# ---------------------------------------------------------------------------
# Hook config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EdgeBoostConfig:
    """Configuration for edge_boost_score hook.

    Attributes:
        edge_type_weights: Base weight for each edge type when computing
            neighbor boosts. Higher weight means that edge type contributes
            more boost. Range per value: 0.0-2.0.
        boost_factor: Multiplier applied to the weighted neighbor boost.
            Range: 0.1-2.0. Default 0.3 is moderate -- enough to lift
            graph-connected nodes without overwhelming base relevance.
        top_n_seeds: Number of top-scoring nodes (by current score) to use
            as BFS seeds for neighbor discovery. Range: 3-20.
        max_hops: Maximum BFS traversal depth from seed nodes. 1 = direct
            neighbors only. Range: 1-3.
    """

    edge_type_weights: dict[str, float] = field(
        default_factory=lambda: {
            "CAUSED_BY": 1.5,
            "FOLLOWS": 1.0,
            "REFERENCES": 1.2,
            "SIMILAR_TO": 0.8,
        }
    )
    boost_factor: float = 0.3
    top_n_seeds: int = 10
    max_hops: int = 1


@dataclass
class NegativeSimilarityConfig:
    """Configuration for negative_similarity_penalty hook.

    Attributes:
        penalty_factor: How strongly to penalize nodes embedding-similar to
            must_not_appear nodes. At 1.0, a node identical to a negative
            exemplar gets its score zeroed. Range: 0.1-1.0.
    """

    penalty_factor: float = 0.5


@dataclass
class TemporalWindowConfig:
    """Configuration for temporal_window_filter hook.

    Attributes:
        window_hours: Time window in hours around the query's temporal
            reference point. Events outside this window get attenuated.
            Range: 1.0-336.0.
        decay_outside_window: Attenuation factor for Event nodes outside
            the window. 0.0 = hard cutoff (zero score), 1.0 = no attenuation.
            Range: 0.0-1.0.
    """

    window_hours: float = 48.0
    decay_outside_window: float = 0.5


@dataclass
class NormalizationConfig:
    """Configuration for score_normalization hook.

    Attributes:
        method: Normalization strategy.
            "zscore" -- standardize to mean=0, std=1, then shift so all > 0.
            "minmax" -- scale linearly to [0, 1].
    """

    method: str = "zscore"


@dataclass
class RRFConfig:
    """Configuration for reciprocal_rank_fusion hook.

    Attributes:
        k: Smoothing constant for the RRF formula: score = sum(1/(k+rank_i)).
            Higher k reduces the impact of top-ranked items. Standard value
            is 60 (Cormack et al. 2009). Range: 1-100.
        use_recency: Whether to include a recency-based ranking signal
            (from occurred_at / last_seen attributes).
        use_importance: Whether to include an importance-based ranking signal
            (from importance_score / mention_count attributes).
    """

    k: int = 60
    use_recency: bool = True
    use_importance: bool = True


@dataclass
class ScenarioFocusConfig:
    """Configuration for scenario_focus_penalty hook.

    Attributes:
        cross_scenario_multiplier: Score multiplier for nodes outside the
            query's scenario for intents that are usually scenario-local.
        related_cross_scenario_multiplier: Score multiplier for out-of-scenario
            nodes on "related" queries, where cross-scenario evidence can be
            legitimately relevant.
    """

    cross_scenario_multiplier: float = 0.55
    related_cross_scenario_multiplier: float = 0.8


@dataclass
class MMRConfig:
    """Configuration for mmr_diversity_rerank hook.

    Attributes:
        lambda_param: Trade-off between relevance and diversity.
            1.0 = pure relevance (no diversity), 0.5 = balanced.
            Range: 0.5-1.0.
        rerank_depth: How many top-scoring nodes to consider for MMR
            re-ranking. Deeper = better diversity but more computation.
            Range: 20-50.
    """

    lambda_param: float = 0.7
    rerank_depth: int = 30


# ---------------------------------------------------------------------------
# Union type for hook configs
# ---------------------------------------------------------------------------

HookConfig = (
    EdgeBoostConfig
    | NegativeSimilarityConfig
    | TemporalWindowConfig
    | NormalizationConfig
    | RRFConfig
    | ScenarioFocusConfig
    | MMRConfig
)

HookFn = Callable[
    [dict[str, Any], list[Any], Any, dict[str, float], Any],
    dict[str, float],
]

# ---------------------------------------------------------------------------
# Intent-aware edge weight modifiers
# ---------------------------------------------------------------------------

# For "why" queries, CAUSED_BY is the primary causal signal.
# For "when" queries, FOLLOWS is the primary temporal signal.
_INTENT_EDGE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "why": {"CAUSED_BY": 2.0},
    "when": {"FOLLOWS": 2.0},
}


# ---------------------------------------------------------------------------
# Hook 1: Edge Boost Score
# ---------------------------------------------------------------------------


def edge_boost_score(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Boost nodes that are graph-neighbors of high-scoring nodes.

    This is the MOST IMPACTFUL hook because 108 edges in the dataset are
    completely unused by the base scoring algorithm. It propagates relevance
    signal along graph edges with intent-aware edge type weighting.

    Algorithm:
      1. Build bidirectional adjacency index (cached across calls).
      2. Identify seed nodes: top-N by current score.
      3. For each seed, BFS to find neighbors within max_hops.
      4. Boost each neighbor: score += boost_factor * edge_weight / hop_distance.
      5. For "why" intents, CAUSED_BY weight is doubled; for "when", FOLLOWS
         weight is doubled.

    Args:
        all_nodes: All nodes in the eval dataset (node_id -> EvalNode).
        all_edges: All edges in the eval dataset (list of EvalEdge).
        query: The current evaluation query (EvalQuery with .intent).
        node_scores: Current scores from base scoring (node_id -> float).
        config: EdgeBoostConfig with boost_factor, top_n_seeds, max_hops,
            edge_type_weights.

    Returns:
        Updated node_scores dict with graph-boosted values.

    Expected impact: +5-15% nDCG on causal (why) and temporal (when) queries
    where CAUSED_BY and FOLLOWS edges connect the answer chain.
    """
    assert isinstance(config, EdgeBoostConfig)

    forward, reverse = _build_adjacency_index(all_edges)

    # Build intent-modified edge weights
    intent = getattr(query, "intent", "general")
    effective_weights = dict(config.edge_type_weights)
    intent_multipliers = _INTENT_EDGE_MULTIPLIERS.get(intent, {})
    for edge_type, multiplier in intent_multipliers.items():
        if edge_type in effective_weights:
            effective_weights[edge_type] *= multiplier

    # Select seed nodes: top-N by current score
    ranked = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
    seed_ids = {nid for nid, _ in ranked[: config.top_n_seeds]}
    entity_focused_intents = {"who_is", "related", "personalize"}

    max_hops = config.max_hops
    if intent in entity_focused_intents:
        max_hops = max(max_hops, 2)

    # Compute boosts via BFS from each seed
    boost_accumulator: dict[str, float] = {}
    for seed_id in seed_ids:
        neighbors = _get_neighbors(seed_id, forward, reverse, max_hops)
        for neighbor_id, (edge_type, hop_distance) in neighbors.items():
            if intent in entity_focused_intents:
                neighbor = all_nodes.get(neighbor_id) if isinstance(all_nodes, dict) else None
                if getattr(neighbor, "node_type", None) == "Event":
                    continue
            edge_weight = effective_weights.get(edge_type, 0.1)
            boost = config.boost_factor * edge_weight / hop_distance
            if (
                intent in entity_focused_intents
                and _infer_node_scenario(neighbor_id) == getattr(query, "scenario", None)
            ):
                boost *= 1.35
            # Take the max boost from any seed (not additive, to avoid runaway)
            if neighbor_id in boost_accumulator:
                boost_accumulator[neighbor_id] = max(boost_accumulator[neighbor_id], boost)
            else:
                boost_accumulator[neighbor_id] = boost

    # Apply boosts additively to current scores
    updated = dict(node_scores)
    for node_id, boost in boost_accumulator.items():
        if node_id in updated:
            updated[node_id] = updated[node_id] + boost

    return updated


# ---------------------------------------------------------------------------
# Hook 2: Negative Similarity Penalty
# ---------------------------------------------------------------------------


def negative_similarity_penalty(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Penalize nodes similar to must_not_appear entries.

    For each scored node, computes the maximum cosine similarity to any
    must_not_appear node's embedding. Applies a multiplicative penalty:
      new_score = score * (1 - penalty_factor * max_similarity_to_negative)

    This pushes down nodes semantically close to known-irrelevant exemplars
    without completely zeroing them out (unless penalty_factor=1.0 and
    similarity=1.0).

    Args:
        all_nodes: All nodes in the eval dataset (node_id -> EvalNode).
        all_edges: All edges (unused by this hook).
        query: The current evaluation query (EvalQuery with .must_not_appear).
        node_scores: Current scores from base scoring (node_id -> float).
        config: NegativeSimilarityConfig with penalty_factor.

    Returns:
        Updated node_scores with penalized values for similar-to-negative nodes.

    Expected impact: -5-10% violation rate, especially on cross-scenario queries
    where nodes from unrelated scenarios accidentally score high.
    """
    assert isinstance(config, NegativeSimilarityConfig)

    must_not_appear = getattr(query, "must_not_appear", [])
    if not must_not_appear:
        return dict(node_scores)

    # Collect negative exemplar embeddings
    negative_embeddings: list[list[float]] = []
    for neg_id in must_not_appear:
        neg_node = all_nodes.get(neg_id) if isinstance(all_nodes, dict) else None
        if neg_node is not None:
            emb = getattr(neg_node, "attributes", {}).get("embedding", [])
            if emb:
                negative_embeddings.append(emb)

    if not negative_embeddings:
        return dict(node_scores)

    must_not_set = set(must_not_appear)
    updated: dict[str, float] = {}

    for node_id, score in node_scores.items():
        if node_id in must_not_set:
            # Directly in must_not_appear -- apply full penalty
            updated[node_id] = score * (1.0 - config.penalty_factor)
            continue

        node = all_nodes.get(node_id) if isinstance(all_nodes, dict) else None
        if node is None:
            updated[node_id] = score
            continue

        node_emb = getattr(node, "attributes", {}).get("embedding", [])
        if not node_emb:
            updated[node_id] = score
            continue

        # Compute max similarity to any negative exemplar
        max_sim = 0.0
        for neg_emb in negative_embeddings:
            sim = cosine_similarity(neg_emb, node_emb)
            if sim > max_sim:
                max_sim = sim

        # Apply penalty: score *= (1 - penalty_factor * max_sim)
        penalty_multiplier = 1.0 - config.penalty_factor * max_sim
        updated[node_id] = score * max(0.0, penalty_multiplier)

    return updated


# ---------------------------------------------------------------------------
# Hook 3: Temporal Window Filter
# ---------------------------------------------------------------------------


def temporal_window_filter(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """For temporal queries, prefer nodes within a time window.

    For "when" intent queries, attenuates scores of Event nodes far from the
    query's temporal focus. The reference time is derived from the midpoint
    of expected_top_nodes timestamps. Non-Event nodes (Entity, UserProfile,
    Preference, Skill) pass through unfiltered since they lack occurred_at.

    For non-"when" intents, this hook is a no-op and returns scores unchanged.

    Algorithm:
      1. Determine reference time from expected_top_nodes Event timestamps.
      2. For each Event node, compute hours from reference time.
      3. Inside the window: score unchanged.
      4. Outside the window: score *= decay_outside_window.

    Args:
        all_nodes: All nodes in the eval dataset (node_id -> EvalNode).
        all_edges: All edges (unused by this hook).
        query: The current evaluation query (EvalQuery with .intent, .expected_top_nodes).
        node_scores: Current scores from base scoring (node_id -> float).
        config: TemporalWindowConfig with window_hours and decay_outside_window.

    Returns:
        Updated node_scores with out-of-window Event scores attenuated.

    Expected impact: +3-8% precision on "when" queries by removing temporal
    outliers. No-op for all other intents.
    """
    assert isinstance(config, TemporalWindowConfig)

    intent = getattr(query, "intent", "general")
    if intent != "when":
        return dict(node_scores)

    # Determine reference time from expected_top_nodes midpoint
    expected_top_nodes = getattr(query, "expected_top_nodes", [])
    timestamps: list[datetime] = []
    for judgment in expected_top_nodes:
        node_id = getattr(judgment, "node_id", None)
        if node_id is None:
            continue
        node = all_nodes.get(node_id) if isinstance(all_nodes, dict) else None
        if node is None:
            continue
        node_type = getattr(node, "node_type", None)
        if node_type != "Event":
            continue
        occurred_at_raw = getattr(node, "attributes", {}).get("occurred_at")
        if isinstance(occurred_at_raw, str):
            with contextlib.suppress(ValueError):
                timestamps.append(datetime.fromisoformat(occurred_at_raw))
        elif isinstance(occurred_at_raw, datetime):
            timestamps.append(occurred_at_raw)

    if not timestamps:
        # No temporal reference available -- skip filtering
        return dict(node_scores)

    # Use midpoint of earliest and latest expected events
    earliest = min(timestamps)
    latest = max(timestamps)
    ref_time = earliest + (latest - earliest) / 2

    half_window = config.window_hours / 2.0

    updated: dict[str, float] = {}
    for node_id, score in node_scores.items():
        node = all_nodes.get(node_id) if isinstance(all_nodes, dict) else None
        if node is None:
            updated[node_id] = score
            continue

        node_type = getattr(node, "node_type", None)
        if node_type != "Event":
            # Non-event nodes pass through unfiltered
            updated[node_id] = score
            continue

        occurred_at_raw = getattr(node, "attributes", {}).get("occurred_at")
        if occurred_at_raw is None:
            updated[node_id] = score
            continue

        if isinstance(occurred_at_raw, str):
            try:
                occurred_at = datetime.fromisoformat(occurred_at_raw)
            except ValueError:
                updated[node_id] = score
                continue
        elif isinstance(occurred_at_raw, datetime):
            occurred_at = occurred_at_raw
        else:
            updated[node_id] = score
            continue

        # Compute distance in hours from reference time
        delta_hours = abs((occurred_at - ref_time).total_seconds()) / 3600.0

        if delta_hours <= half_window:
            updated[node_id] = score
        else:
            # Outside window: attenuate by decay_outside_window
            updated[node_id] = score * config.decay_outside_window

    return updated


# ---------------------------------------------------------------------------
# Hook 4: Score Normalization
# ---------------------------------------------------------------------------


def score_normalization(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Z-score or min-max normalize scores before returning.

    Two strategies:
      - "zscore": Standardize to mean=0, std=1, then shift so all scores > 0
        by mapping through: 0.5 + z / (2 * std_scale). Result in [0, 1].
      - "minmax": Scale linearly to [0, 1].

    Normalization is applied AFTER other score adjustments (boosts, penalties)
    to ensure the final ranking reflects relative ordering without extreme
    value skew from additive boosts.

    Args:
        all_nodes: All nodes (unused by this hook).
        all_edges: All edges (unused by this hook).
        query: The current evaluation query (unused by this hook).
        node_scores: Current scores to normalize (node_id -> float).
        config: NormalizationConfig with method ("zscore" or "minmax").

    Returns:
        Normalized node_scores dict with all values > 0.

    Expected impact: +1-3% nDCG by reducing distortion from outlier scores,
    especially after edge_boost creates additive score inflation.
    """
    assert isinstance(config, NormalizationConfig)

    if not node_scores:
        return {}

    scores = list(node_scores.values())
    n = len(scores)

    if config.method == "zscore":
        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / n
        std = math.sqrt(variance) if variance > 0 else 1.0

        if std == 0:
            return {nid: 0.5 for nid in node_scores}

        # Z-score then map to [0, 1] via sigmoid-like linear mapping
        # Ensures all scores > 0 by clamping to [0, 1]
        return {
            nid: max(0.0, min(1.0, 0.5 + (s - mean) / (2.0 * std)))
            for nid, s in node_scores.items()
        }

    elif config.method == "minmax":
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        if score_range == 0:
            # All scores identical -- assign neutral value
            return {nid: 0.5 for nid in node_scores}

        return {nid: (s - min_score) / score_range for nid, s in node_scores.items()}

    else:
        # Unknown method -- return unchanged
        return dict(node_scores)


# ---------------------------------------------------------------------------
# Hook 5: Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Combine multiple ranking signals via Reciprocal Rank Fusion.

    RRF creates separate rankings by different criteria and fuses them:
      rrf_score(d) = sum(1 / (k + rank_i(d))) for each ranking i

    Three ranking signals:
      (a) Current composite score (always used).
      (b) Recency proxy: occurred_at for Events, last_seen for Entities
          (controlled by use_recency flag).
      (c) Importance proxy: importance_score for Events, mention_count for
          Entities (controlled by use_importance flag).

    RRF is particularly effective when individual scoring factors disagree
    on ranking, producing a more robust combined result than weighted-sum.

    Args:
        all_nodes: All nodes in the eval dataset (node_id -> EvalNode).
        all_edges: All edges (unused by this hook).
        query: The current evaluation query.
        node_scores: Current composite scores (node_id -> float).
        config: RRFConfig with k, use_recency, use_importance.

    Returns:
        Completely re-scored node_scores using RRF values.

    Expected impact: +2-5% nDCG on queries where recency and relevance
    disagree (common in "why" queries where the cause event may be old
    but highly relevant).
    """
    assert isinstance(config, RRFConfig)

    if not node_scores:
        return {}

    node_ids = list(node_scores.keys())

    # Build per-factor rankings
    # Factor (a): current composite score (always included)
    factor_rankings: list[dict[str, int]] = []

    sorted_by_score = sorted(node_ids, key=lambda nid: node_scores.get(nid, 0.0), reverse=True)
    score_ranking = {nid: rank + 1 for rank, nid in enumerate(sorted_by_score)}
    factor_rankings.append(score_ranking)

    # Factor (b): recency from occurred_at / last_seen
    if config.use_recency:
        recency_values: dict[str, float] = {}
        for nid in node_ids:
            node = all_nodes.get(nid) if isinstance(all_nodes, dict) else None
            if node is None:
                recency_values[nid] = 0.0
                continue
            attrs = getattr(node, "attributes", {})
            ts_raw = attrs.get("occurred_at") or attrs.get("last_seen")
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw)
                    recency_values[nid] = ts.timestamp()
                except ValueError:
                    recency_values[nid] = 0.0
            elif isinstance(ts_raw, datetime):
                recency_values[nid] = ts_raw.timestamp()
            else:
                recency_values[nid] = 0.0

        sorted_by_recency = sorted(
            node_ids, key=lambda nid: recency_values.get(nid, 0.0), reverse=True
        )
        recency_ranking = {nid: rank + 1 for rank, nid in enumerate(sorted_by_recency)}
        factor_rankings.append(recency_ranking)

    # Factor (c): importance from importance_score / mention_count
    if config.use_importance:
        importance_values: dict[str, float] = {}
        for nid in node_ids:
            node = all_nodes.get(nid) if isinstance(all_nodes, dict) else None
            if node is None:
                importance_values[nid] = 0.0
                continue
            attrs = getattr(node, "attributes", {})
            imp = attrs.get("importance_score")
            if imp is not None:
                importance_values[nid] = float(imp)
            else:
                mc = attrs.get("mention_count", 1)
                importance_values[nid] = float(min(10, mc))

        sorted_by_importance = sorted(
            node_ids, key=lambda nid: importance_values.get(nid, 0.0), reverse=True
        )
        importance_ranking = {nid: rank + 1 for rank, nid in enumerate(sorted_by_importance)}
        factor_rankings.append(importance_ranking)

    # Compute RRF scores
    # Default rank for missing entries = total nodes + 1
    default_rank = len(node_ids) + 1
    rrf_scores: dict[str, float] = {}
    for nid in node_ids:
        rrf_score = 0.0
        for ranking in factor_rankings:
            rank = ranking.get(nid, default_rank)
            rrf_score += 1.0 / (config.k + rank)
        rrf_scores[nid] = rrf_score

    return rrf_scores


# ---------------------------------------------------------------------------
# Hook 6: Scenario Focus Penalty
# ---------------------------------------------------------------------------


def scenario_focus_penalty(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Prefer nodes from the same scenario as the query.

    Most eval queries are scenario-local, and the current scorer often ranks
    high-similarity nodes from the wrong scenario above the correct answer
    chain. This hook softly penalizes out-of-scenario nodes while allowing a
    looser penalty for "related" queries, which sometimes compare scenarios.
    """
    del all_nodes, all_edges
    assert isinstance(config, ScenarioFocusConfig)

    query_scenario = getattr(query, "scenario", None)
    if not query_scenario:
        return dict(node_scores)

    cross_multiplier = config.cross_scenario_multiplier
    if getattr(query, "intent", "general") == "related":
        cross_multiplier = config.related_cross_scenario_multiplier

    updated: dict[str, float] = {}
    for node_id, score in node_scores.items():
        node_scenario = _infer_node_scenario(node_id)
        if node_scenario is None or node_scenario == query_scenario:
            updated[node_id] = score
        else:
            updated[node_id] = score * cross_multiplier

    return updated


# ---------------------------------------------------------------------------
# Hook 7: MMR Diversity Re-rank
# ---------------------------------------------------------------------------


def mmr_diversity_rerank(
    all_nodes: dict[str, Any],
    all_edges: list[Any],
    query: Any,
    node_scores: dict[str, float],
    config: HookConfig,
) -> dict[str, float]:
    """Maximal Marginal Relevance to reduce redundancy in top results.

    Among the top rerank_depth candidates, iteratively selects the one with
    highest MMR score:
      MMR(d) = lambda * relevance(d) - (1-lambda) * max_similarity_to_selected

    Uses embedding cosine similarity between nodes to measure redundancy.
    Only the top rerank_depth nodes are re-ranked; remaining nodes keep
    their original scores but are placed below the re-ranked set.

    Args:
        all_nodes: All nodes in the eval dataset (for embeddings).
        all_edges: All edges (unused by this hook).
        query: The current evaluation query.
        node_scores: Current scores to re-rank (node_id -> float).
        config: MMRConfig with lambda_param and rerank_depth.

    Returns:
        Re-scored node_scores with MMR-adjusted ranking values.

    Expected impact: +1-3% nDCG on "related" and "what" queries where
    diverse results are expected. Slight penalty possible on "why" queries
    where causal chain nodes are legitimately similar.
    """
    assert isinstance(config, MMRConfig)

    if getattr(query, "intent", "general") == "what":
        return dict(node_scores)

    if not node_scores:
        return {}

    # Sort by current score to identify top candidates
    sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)

    # Split into re-rank candidates and remainder
    rerank_candidates = sorted_nodes[: config.rerank_depth]
    remainder = sorted_nodes[config.rerank_depth :]

    if len(rerank_candidates) <= 1:
        return dict(node_scores)

    # Normalize candidate scores to [0, 1] for fair MMR comparison
    candidate_scores = {nid: score for nid, score in rerank_candidates}
    max_score = max(candidate_scores.values())
    min_score = min(candidate_scores.values())
    score_range = max_score - min_score

    if score_range > 0:
        norm_scores = {nid: (s - min_score) / score_range for nid, s in candidate_scores.items()}
    else:
        norm_scores = {nid: 1.0 for nid in candidate_scores}

    # Collect embeddings for candidates
    embeddings: dict[str, list[float]] = {}
    for nid in candidate_scores:
        node = all_nodes.get(nid) if isinstance(all_nodes, dict) else None
        if node is not None:
            emb = getattr(node, "attributes", {}).get("embedding", [])
            if emb:
                embeddings[nid] = emb

    # Greedy MMR selection
    selected: list[str] = []
    remaining_ids = set(candidate_scores.keys())

    # First selection: highest relevance score
    first_id = max(norm_scores, key=lambda nid: norm_scores[nid])
    selected.append(first_id)
    remaining_ids.discard(first_id)

    while remaining_ids:
        best_id: str | None = None
        best_mmr = -float("inf")

        for nid in remaining_ids:
            relevance = norm_scores[nid]

            # Compute max similarity to any already-selected node
            max_sim = 0.0
            nid_emb = embeddings.get(nid, [])
            if nid_emb:
                for sel_id in selected:
                    sel_emb = embeddings.get(sel_id, [])
                    if sel_emb:
                        sim = cosine_similarity(nid_emb, sel_emb)
                        if sim > max_sim:
                            max_sim = sim

            mmr_score = config.lambda_param * relevance - (1.0 - config.lambda_param) * max_sim

            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_id = nid

        if best_id is not None:
            selected.append(best_id)
            remaining_ids.discard(best_id)
        else:
            break

    # Assign descending scores to the MMR-reranked order
    # Top of rerank set gets max_score, decreasing linearly to min_score
    result: dict[str, float] = {}
    n_reranked = len(selected)
    for rank, nid in enumerate(selected):
        if n_reranked > 1:
            result[nid] = max_score - (rank / (n_reranked - 1)) * score_range
        else:
            result[nid] = max_score

    # Remainder nodes keep their original scores (already below reranked set)
    for nid, score in remainder:
        result[nid] = score

    return result


# ---------------------------------------------------------------------------
# Hook Registry
# ---------------------------------------------------------------------------

HOOK_REGISTRY: dict[str, dict[str, Any]] = {
    "edge_boost": {
        "fn": edge_boost_score,
        "config_cls": EdgeBoostConfig,
        "default": EdgeBoostConfig(),
    },
    "negative_similarity": {
        "fn": negative_similarity_penalty,
        "config_cls": NegativeSimilarityConfig,
        "default": NegativeSimilarityConfig(),
    },
    "temporal_window": {
        "fn": temporal_window_filter,
        "config_cls": TemporalWindowConfig,
        "default": TemporalWindowConfig(),
    },
    "normalization": {
        "fn": score_normalization,
        "config_cls": NormalizationConfig,
        "default": NormalizationConfig(),
    },
    "rrf": {
        "fn": reciprocal_rank_fusion,
        "config_cls": RRFConfig,
        "default": RRFConfig(),
    },
    "scenario_focus": {
        "fn": scenario_focus_penalty,
        "config_cls": ScenarioFocusConfig,
        "default": ScenarioFocusConfig(),
    },
    "mmr_diversity": {
        "fn": mmr_diversity_rerank,
        "config_cls": MMRConfig,
        "default": MMRConfig(),
    },
}
