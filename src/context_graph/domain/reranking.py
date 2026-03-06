"""Reciprocal rank fusion and diversity re-ranking (L4).

Pure domain module — no framework or adapter imports.

References:
- Cormack, Clarke, Buettcher (2009): RRF with k=60
- Carbonell, Goldstein (1998): MMR for diversity
"""

from __future__ import annotations

import math


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists using Reciprocal Rank Fusion.

    Each ranked_list is ``[(id, score), ...]`` sorted by score descending.
    RRF score for item *i* = sum over lists of ``1 / (k + rank_in_list)``.

    Args:
        ranked_lists: One list per retrieval channel, each containing
            ``(item_id, channel_score)`` pairs ordered by descending score.
        k: Smoothing constant. Higher values reduce the impact of rank
            position differences. The canonical value is 60.

    Returns:
        Fused list of ``(item_id, rrf_score)`` sorted by RRF score descending.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, (item_id, _score) in enumerate(ranked_list):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def maximal_marginal_relevance(
    candidates: list[tuple[str, float, list[float]]],
    selected: list[str],
    lambda_param: float = 0.5,
) -> list[tuple[str, float]]:
    """MMR for diversity — re-ranks candidates to balance relevance and diversity.

    Args:
        candidates: ``[(id, relevance_score, embedding), ...]``
        selected: IDs of already-selected items (used to penalize similarity).
        lambda_param: Trade-off between relevance (1.0) and diversity (0.0).

    Returns:
        Re-ranked list of ``(id, mmr_score)`` sorted by MMR score descending.
    """
    if not candidates:
        return []

    # Build lookup for selected embeddings
    candidate_map: dict[str, tuple[float, list[float]]] = {}
    for item_id, relevance, embedding in candidates:
        candidate_map[item_id] = (relevance, embedding)

    # Collect embeddings of already-selected items from candidate pool
    selected_embeddings: list[list[float]] = []
    for sid in selected:
        if sid in candidate_map:
            selected_embeddings.append(candidate_map[sid][1])

    results: list[tuple[str, float]] = []
    for item_id, relevance, embedding in candidates:
        if item_id in selected:
            # Already selected — penalize heavily but still score
            max_sim = 1.0
        elif not selected_embeddings:
            max_sim = 0.0
        else:
            max_sim = max(_cosine_similarity(embedding, sel_emb) for sel_emb in selected_embeddings)

        mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim
        results.append((item_id, mmr_score))

    return sorted(results, key=lambda x: x[1], reverse=True)
