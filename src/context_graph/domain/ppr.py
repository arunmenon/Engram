"""Personalized PageRank approximation (L5).

Computes approximate PPR scores using iterative power method on a local
adjacency graph. Pure Python implementation -- no GDS or external deps required.

Source: ADR-0009 amendment
"""

from __future__ import annotations


def approximate_ppr(
    adjacency: dict[str, list[tuple[str, float]]],
    seeds: list[str],
    damping: float = 0.85,
    iterations: int = 5,
) -> dict[str, float]:
    """Compute approximate Personalized PageRank via iterative power method.

    Parameters
    ----------
    adjacency:
        Graph as adjacency list: node_id -> [(neighbor_id, edge_weight), ...]
    seeds:
        Seed node IDs that receive teleportation probability.
    damping:
        Probability of following an edge (vs teleporting to seed). Default 0.85.
    iterations:
        Number of power iteration rounds. Default 5.

    Returns
    -------
    dict mapping node_id -> PPR score (normalized to sum=1.0)
    """
    if not adjacency or not seeds:
        return {}

    # Collect all nodes
    all_nodes: set[str] = set(adjacency.keys())
    for neighbors in adjacency.values():
        for nid, _ in neighbors:
            all_nodes.add(nid)

    n = len(all_nodes)
    if n == 0:
        return {}

    # Initialize: equal probability across valid seeds
    valid_seeds = [s for s in seeds if s in all_nodes]
    if not valid_seeds:
        return {}

    seed_prob = 1.0 / len(valid_seeds)
    scores: dict[str, float] = {node: 0.0 for node in all_nodes}
    for s in valid_seeds:
        scores[s] = seed_prob

    # Precompute normalized out-weights
    out_weights: dict[str, list[tuple[str, float]]] = {}
    for node_id, neighbors in adjacency.items():
        if neighbors:
            total_weight = sum(w for _, w in neighbors)
            if total_weight > 0:
                out_weights[node_id] = [(nid, w / total_weight) for nid, w in neighbors]

    # Power iteration
    for _ in range(iterations):
        new_scores: dict[str, float] = {node: 0.0 for node in all_nodes}

        # Teleportation component
        for s in valid_seeds:
            new_scores[s] += (1 - damping) * seed_prob

        # Propagation component
        for node_id in all_nodes:
            if node_id in out_weights:
                for neighbor_id, norm_weight in out_weights[node_id]:
                    new_scores[neighbor_id] += damping * scores[node_id] * norm_weight
            else:
                # Dangling node: distribute equally to seeds
                for s in valid_seeds:
                    new_scores[s] += damping * scores[node_id] * seed_prob

        # Normalize
        total = sum(new_scores.values())
        scores = {k: v / total for k, v in new_scores.items()} if total > 0 else new_scores

    return scores
