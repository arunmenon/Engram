"""Three-tier entity reconciliation for the knowledge graph.

Adapts patterns from context_graph.domain.entity_resolution for the
KG Memory MCP server. Provides:

Tier 1: Exact match (normalization + alias dictionary)
Tier 2: Fuzzy match (SequenceMatcher)
Tier 3: Semantic match (LLM-powered, optional)

Works without LLM (tiers 1-2 only) when extractor is None.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, NodeType

if TYPE_CHECKING:
    from kg_memory.extraction import LLMExtractor

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Lowercase, strip, collapse spaces, remove underscores/hyphens for comparison."""
    result = name.lower().strip()
    result = result.replace("_", " ").replace("-", " ")
    return " ".join(result.split())


# ---------------------------------------------------------------------------
# Alias dictionary — maps canonical names to known aliases
# ---------------------------------------------------------------------------

CODE_ALIAS_DICT: dict[str, list[str]] = {
    "neo4j graph store": ["neo4jgraphstore", "neo4j adapter", "neo4j store"],
    "graph store": ["graphstore", "graph store interface", "graph store protocol"],
    "redis event store": ["rediseventstore", "redis store", "event store"],
    "ebbinghaus decay": ["decay scoring", "4 factor scoring", "memory decay", "ebbinghaus scoring"],
    "event ledger": ["event log", "append only ledger", "immutable event log"],
    "atlas pattern": ["atlas response", "atlas format"],
    "knowledge graph": ["kg", "context graph"],
    "entity resolution": ["entity reconciliation", "entity matching", "dedup"],
    "pydantic": ["pydantic v2", "pydantic model"],
    "fastapi": ["fast api"],
    "litellm": ["lite llm"],
    "redis streams": ["redis stream", "xadd", "xreadgroup"],
    "union find": ["unionfind", "disjoint set", "uf"],
    "sequence matcher": ["sequencematcher", "difflib matcher"],
    "tree sitter": ["treesitter", "tree sitter parser"],
    "mcp": ["model context protocol"],
}

# Build reverse lookup: normalized alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in CODE_ALIAS_DICT.items():
    _ALIAS_TO_CANONICAL[normalize_name(_canonical)] = _canonical
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[normalize_name(_alias)] = _canonical


def resolve_alias(name: str) -> str:
    """Return canonical name if *name* is a known alias, otherwise return normalized name."""
    normalized = normalize_name(name)
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


# ---------------------------------------------------------------------------
# Reconciliation action and result
# ---------------------------------------------------------------------------


class ReconciliationAction(enum.StrEnum):
    MERGE = "MERGE"
    SAME_AS = "SAME_AS"
    RELATED_TO = "RELATED_TO"
    SKIP = "SKIP"


@dataclass
class ReconciliationResult:
    action: ReconciliationAction
    source_id: str
    target_id: str
    confidence: float
    justification: str


# ---------------------------------------------------------------------------
# Tier 1: Exact match after normalization + alias resolution
# ---------------------------------------------------------------------------


def resolve_exact(name_a: str, name_b: str) -> ReconciliationAction | None:
    """Tier 1: Exact match after normalization + alias resolution.

    Returns MERGE if both names resolve to the same canonical form,
    None otherwise.
    """
    canonical_a = resolve_alias(name_a)
    canonical_b = resolve_alias(name_b)
    if canonical_a == canonical_b:
        return ReconciliationAction.MERGE
    return None


# ---------------------------------------------------------------------------
# Tier 2: Fuzzy match using SequenceMatcher
# ---------------------------------------------------------------------------


def resolve_fuzzy(
    name_a: str,
    name_b: str,
    threshold_same: float = 0.85,
    threshold_related: float = 0.70,
) -> tuple[ReconciliationAction | None, float]:
    """Tier 2: Fuzzy match using SequenceMatcher.

    Returns (action, similarity_score). Action is:
    - SAME_AS if similarity >= threshold_same
    - RELATED_TO if similarity >= threshold_related
    - None if below threshold_related
    """
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    if not norm_a or not norm_b:
        return None, 0.0

    # Compare both raw normalized and alias-resolved forms, take best
    canonical_a = resolve_alias(name_a)
    canonical_b = resolve_alias(name_b)
    score = max(
        SequenceMatcher(None, norm_a, norm_b).ratio(),
        SequenceMatcher(None, canonical_a, canonical_b).ratio(),
        SequenceMatcher(None, norm_a, canonical_b).ratio(),
        SequenceMatcher(None, canonical_a, norm_b).ratio(),
    )

    if score >= threshold_same:
        return ReconciliationAction.SAME_AS, round(score, 4)
    if score >= threshold_related:
        return ReconciliationAction.RELATED_TO, round(score, 4)
    return None, round(score, 4)


# ---------------------------------------------------------------------------
# Tier 3: LLM semantic match
# ---------------------------------------------------------------------------


async def resolve_semantic(
    extractor: LLMExtractor,
    name_a: str,
    name_b: str,
    context_a: str,
    context_b: str,
) -> tuple[ReconciliationAction | None, float]:
    """Tier 3: LLM semantic match for ambiguous pairs.

    Returns (action, similarity_score). Uses LLM to determine if two
    concepts are the same, related, or unrelated.
    """
    score = await extractor.reconcile_entities(name_a, name_b, context_a, context_b)

    if score >= 0.85:
        return ReconciliationAction.SAME_AS, round(score, 4)
    if score >= 0.60:
        return ReconciliationAction.RELATED_TO, round(score, 4)
    return None, round(score, 4)


# ---------------------------------------------------------------------------
# Union-Find for transitive closure
# ---------------------------------------------------------------------------


class UnionFind:
    """Disjoint-set data structure for entity clustering."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """Find root with path compression."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        """Union by rank."""
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return
        if self._rank[root_a] < self._rank[root_b]:
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        if self._rank[root_a] == self._rank[root_b]:
            self._rank[root_a] += 1


def compute_clusters(same_as_pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Group SAME_AS pairs into clusters via Union-Find.

    Returns a dict mapping canonical_id to the full list of cluster member IDs.
    The canonical is chosen alphabetically (earliest ID).
    """
    if not same_as_pairs:
        return {}

    uf = UnionFind()
    for a, b in same_as_pairs:
        uf.union(a, b)

    clusters: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for a, b in same_as_pairs:
        for node_id in (a, b):
            if node_id not in seen:
                seen.add(node_id)
                root = uf.find(node_id)
                clusters[root].append(node_id)

    # Re-key by canonical (alphabetically first)
    result: dict[str, list[str]] = {}
    for members in clusters.values():
        canonical = min(members)
        result[canonical] = sorted(members)
    return result


# ---------------------------------------------------------------------------
# Compatible type pairs for pairwise comparison
# ---------------------------------------------------------------------------

_COMPATIBLE_TYPES: set[tuple[str, str]] = {
    (NodeType.CONCEPT, NodeType.CONCEPT),
    (NodeType.CONCEPT, NodeType.CLASS),
    (NodeType.CONCEPT, NodeType.FUNCTION),
    (NodeType.CLASS, NodeType.CLASS),
    (NodeType.FUNCTION, NodeType.FUNCTION),
    (NodeType.DECISION, NodeType.DECISION),
}


def _are_compatible(type_a: str, type_b: str) -> bool:
    """Check if two node types should be compared for reconciliation."""
    return (type_a, type_b) in _COMPATIBLE_TYPES or (type_b, type_a) in _COMPATIBLE_TYPES


def _get_node_context(graph: KnowledgeGraph, node_id: str) -> str:
    """Build a brief context string for a node from its properties and edges."""
    node = graph.get_node(node_id)
    if node is None:
        return ""
    parts = [f"Name: {node.name}", f"Type: {node.node_type}"]
    definition = node.properties.get("definition", "")
    if definition:
        parts.append(f"Definition: {definition}")
    category = node.properties.get("category", "")
    if category:
        parts.append(f"Category: {category}")
    source_file = node.properties.get("source_file", "")
    if source_file:
        parts.append(f"Source: {source_file}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Full reconciliation pipeline
# ---------------------------------------------------------------------------


async def reconcile_graph(
    graph: KnowledgeGraph,
    extractor: LLMExtractor | None = None,
) -> list[ReconciliationResult]:
    """Run full 3-tier reconciliation across concept nodes in the graph.

    1. Collect all concept/class/function/decision nodes
    2. Pairwise comparison within compatible types
    3. Tier 1 -> Tier 2 -> Tier 3 (only if extractor provided)
    4. Apply Union-Find for transitive closure on SAME_AS/MERGE
    5. Add SAME_AS and RELATED_TO edges to graph
    """
    # Collect reconcilable nodes
    reconcilable_types = {
        NodeType.CONCEPT,
        NodeType.CLASS,
        NodeType.FUNCTION,
        NodeType.DECISION,
    }
    candidates: list[str] = []
    for node_type in reconcilable_types:
        for node in graph.get_nodes_by_type(node_type):
            candidates.append(node.id)

    if len(candidates) < 2:
        return []

    results: list[ReconciliationResult] = []
    same_as_pairs: list[tuple[str, str]] = []

    # Pairwise comparison
    for i in range(len(candidates)):
        node_a = graph.get_node(candidates[i])
        if node_a is None:
            continue
        for j in range(i + 1, len(candidates)):
            node_b = graph.get_node(candidates[j])
            if node_b is None:
                continue

            # Skip incompatible types
            if not _are_compatible(node_a.node_type, node_b.node_type):
                continue

            # Skip self
            if node_a.id == node_b.id:
                continue

            # Tier 1: Exact match
            action = resolve_exact(node_a.name, node_b.name)
            if action is not None:
                result = ReconciliationResult(
                    action=action,
                    source_id=node_a.id,
                    target_id=node_b.id,
                    confidence=1.0,
                    justification=f"Exact match: '{resolve_alias(node_a.name)}'",
                )
                results.append(result)
                if action in (ReconciliationAction.MERGE, ReconciliationAction.SAME_AS):
                    same_as_pairs.append((node_a.id, node_b.id))
                continue

            # Tier 2: Fuzzy match
            fuzzy_action, fuzzy_score = resolve_fuzzy(node_a.name, node_b.name)
            if fuzzy_action is not None:
                result = ReconciliationResult(
                    action=fuzzy_action,
                    source_id=node_a.id,
                    target_id=node_b.id,
                    confidence=fuzzy_score,
                    justification=(
                        f"Fuzzy match: '{normalize_name(node_a.name)}' ~ "
                        f"'{normalize_name(node_b.name)}' (similarity={fuzzy_score})"
                    ),
                )
                results.append(result)
                if fuzzy_action == ReconciliationAction.SAME_AS:
                    same_as_pairs.append((node_a.id, node_b.id))
                continue

            # Tier 3: Semantic match (only if extractor provided)
            if extractor is not None:
                context_a = _get_node_context(graph, node_a.id)
                context_b = _get_node_context(graph, node_b.id)
                semantic_action, semantic_score = await resolve_semantic(
                    extractor,
                    node_a.name,
                    node_b.name,
                    context_a,
                    context_b,
                )
                if semantic_action is not None:
                    result = ReconciliationResult(
                        action=semantic_action,
                        source_id=node_a.id,
                        target_id=node_b.id,
                        confidence=semantic_score,
                        justification=(
                            f"Semantic match: '{node_a.name}' ~ "
                            f"'{node_b.name}' (LLM score={semantic_score})"
                        ),
                    )
                    results.append(result)
                    if semantic_action == ReconciliationAction.SAME_AS:
                        same_as_pairs.append((node_a.id, node_b.id))

    # Apply Union-Find for transitive closure
    clusters = compute_clusters(same_as_pairs)

    # Add SAME_AS edges for clustered nodes
    for canonical_id, members in clusters.items():
        for member_id in members:
            if member_id != canonical_id:
                graph.add_edge(
                    Edge(
                        source=canonical_id,
                        target=member_id,
                        edge_type=EdgeType.SAME_AS,
                        properties={"source": "reconciliation"},
                    )
                )

    # Add RELATED_TO edges
    for result in results:
        if result.action == ReconciliationAction.RELATED_TO:
            graph.add_edge(
                Edge(
                    source=result.source_id,
                    target=result.target_id,
                    edge_type=EdgeType.RELATED_TO,
                    properties={
                        "confidence": result.confidence,
                        "source": "reconciliation",
                    },
                )
            )

    print(
        f"[reconciliation] Processed {len(candidates)} nodes: "
        f"{len(results)} matches, {len(clusters)} clusters"
    )
    return results
