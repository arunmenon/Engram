"""Rule-based intent classification (ADR-0009).

Classifies natural-language queries into IntentType enum values with confidence
scores.  Computes per-edge-type traversal weights by combining intent confidences
with the intent weight matrix from settings.

Pure Python — ZERO framework imports.
"""

from __future__ import annotations

from context_graph.domain.models import IntentType

# Keyword patterns for each intent type.
# Matching is case-insensitive substring search; count drives confidence.
_INTENT_KEYWORDS: dict[str, list[str]] = {
    IntentType.WHY: ["why", "because", "caused", "reason", "root cause", "due to"],
    IntentType.WHEN: [
        "when",
        "timeline",
        "before",
        "after",
        "sequence",
        "order",
        "time",
    ],
    IntentType.WHAT: ["what", "describe", "explain", "definition", "meaning"],
    IntentType.RELATED: ["similar", "related", "like", "compare", "associated"],
    IntentType.WHO_IS: ["who", "person", "user", "team", "member", "author"],
    IntentType.HOW_DOES: [
        "how",
        "process",
        "method",
        "approach",
        "workflow",
        "steps",
    ],
    IntentType.PERSONALIZE: [
        "prefer",
        "favorite",
        "style",
        "personalize",
        "customize",
    ],
}

# Maps dominant intent to seed-node selection strategy.
_SEED_STRATEGIES: dict[str, str] = {
    IntentType.WHY: "causal_roots",
    IntentType.WHEN: "temporal_anchors",
    IntentType.WHAT: "entity_hubs",
    IntentType.WHO_IS: "entity_hubs",
    IntentType.RELATED: "similar_cluster",
    IntentType.HOW_DOES: "workflow_pattern",
    IntentType.PERSONALIZE: "user_profile",
}


def classify_intent(query: str) -> dict[str, float]:
    """Classify a query string into intent types with confidence scores.

    Each intent is scored by counting keyword matches (0.4 per match, capped at 1.0).
    Scores are then normalized so the dominant intent has confidence 1.0.
    If no keywords match, returns GENERAL with confidence 0.5.
    """
    query_lower = query.lower()
    scores: dict[str, float] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        if matches > 0:
            scores[intent] = min(1.0, matches * 0.4)

    if not scores:
        return {IntentType.GENERAL: 0.5}

    # Normalize so the maximum score becomes 1.0
    max_score = max(scores.values())
    if max_score > 0:
        scores = {k: v / max_score for k, v in scores.items()}
    return scores


def get_edge_weights(
    intents: dict[str, float],
    intent_weight_matrix: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Combine intent confidences with the weight matrix to produce per-edge-type weights.

    For each intent present in the query, its row in the matrix is scaled by
    the intent confidence and accumulated into a single edge-weight dict.
    """
    edge_weights: dict[str, float] = {}
    for intent, confidence in intents.items():
        if intent in intent_weight_matrix:
            for edge_type, weight in intent_weight_matrix[intent].items():
                edge_weights[edge_type] = edge_weights.get(edge_type, 0.0) + confidence * weight
    return edge_weights


def select_seed_strategy(intents: dict[str, float]) -> str:
    """Select a seed-node strategy based on the dominant intent.

    Returns "general" when no specific strategy is mapped.
    """
    if not intents:
        return "general"
    dominant = max(intents, key=lambda k: intents[k])
    return _SEED_STRATEGIES.get(dominant, "general")
