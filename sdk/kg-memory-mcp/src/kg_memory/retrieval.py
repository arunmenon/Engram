"""Retrieval engine for the knowledge graph.

Provides keyword search, BFS neighborhood expansion, path finding,
type-filtered traversal, and file context aggregation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from kg_memory.graph import EdgeType, KnowledgeGraph, Node, NodeType


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    node_id: str
    node_type: str
    name: str
    score: float
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubgraphResult:
    """A subgraph returned from neighborhood/path queries."""

    nodes: dict[str, Node]
    edges: list[dict[str, Any]]


@dataclass
class FileContextResult:
    """Aggregated context for a single file."""

    file_node: Node | None
    module: str
    classes: list[Node]
    functions: list[Node]
    imports: list[str]
    dependents: list[str]
    governing_adrs: list[Node]
    related_concepts: list[Node]
    decisions: list[Node]
    reconciled_links: list[dict[str, str]]


@dataclass
class GraphStats:
    """Graph statistics for the kg_status tool."""

    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    indexed_paths: int
    reconciliation_clusters: int
    same_as_edges: int
    related_to_edges: int


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class Retriever:
    """Retrieval engine over the in-memory knowledge graph."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    # --- Keyword search ---

    def search(
        self,
        query: str,
        node_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search nodes by keyword matching against names and properties.

        Scores are based on match quality:
        - Exact name match: 1.0
        - Name contains query: 0.8
        - Query word in name: 0.6
        - Property value match: 0.4
        """
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        results: list[SearchResult] = []

        type_filter = set(node_types) if node_types else None

        for node in self.graph.nodes.values():
            if type_filter and node.node_type not in type_filter:
                continue

            score = self._score_node(node, query_lower, query_words)
            if score > 0:
                results.append(
                    SearchResult(
                        node_id=node.id,
                        node_type=node.node_type,
                        name=node.name,
                        score=score,
                        properties=node.properties,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _score_node(self, node: Node, query_lower: str, query_words: set[str]) -> float:
        """Score a node against a search query."""
        name_lower = node.name.lower()
        best_score = 0.0

        # Exact name match
        if name_lower == query_lower:
            return 1.0

        # Name contains query
        if query_lower in name_lower:
            best_score = max(best_score, 0.8)

        # Query words in name
        name_words = set(name_lower.replace("_", " ").replace("-", " ").split())
        overlap = query_words & name_words
        if overlap:
            word_score = 0.6 * (len(overlap) / len(query_words))
            best_score = max(best_score, word_score)

        # Property value matching
        for value in node.properties.values():
            if isinstance(value, str):
                value_lower = value.lower()
                if query_lower in value_lower:
                    best_score = max(best_score, 0.4)
                    break
                value_words = set(value_lower.split())
                prop_overlap = query_words & value_words
                if prop_overlap:
                    prop_score = 0.3 * (len(prop_overlap) / len(query_words))
                    best_score = max(best_score, prop_score)

        return best_score

    # --- Neighborhood expansion (BFS) ---

    def get_neighbors(
        self,
        node_id: str,
        edge_types: list[str] | None = None,
        depth: int = 1,
        limit: int = 30,
    ) -> SubgraphResult:
        """BFS neighborhood expansion from a node.

        Returns all nodes and edges reachable within `depth` hops,
        optionally filtered by edge type.
        """
        if node_id not in self.graph.nodes:
            return SubgraphResult(nodes={}, edges=[])

        visited: set[str] = {node_id}
        collected_nodes: dict[str, Node] = {node_id: self.graph.nodes[node_id]}
        collected_edges: list[dict[str, Any]] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue and len(collected_nodes) < limit:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            # Outgoing edges
            for edge in self.graph.get_outgoing(current_id, edge_types):
                collected_edges.append(edge.to_dict())
                if edge.target not in visited:
                    visited.add(edge.target)
                    target_node = self.graph.get_node(edge.target)
                    if target_node:
                        collected_nodes[edge.target] = target_node
                        queue.append((edge.target, current_depth + 1))

            # Incoming edges
            for edge in self.graph.get_incoming(current_id, edge_types):
                collected_edges.append(edge.to_dict())
                if edge.source not in visited:
                    visited.add(edge.source)
                    source_node = self.graph.get_node(edge.source)
                    if source_node:
                        collected_nodes[edge.source] = source_node
                        queue.append((edge.source, current_depth + 1))

        return SubgraphResult(nodes=collected_nodes, edges=collected_edges)

    # --- Path finding ---

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[str] | None:
        """BFS to find shortest path between two nodes.

        Returns a list of node IDs forming the path, or None if no path exists.
        """
        if source_id not in self.graph.nodes or target_id not in self.graph.nodes:
            return None
        if source_id == target_id:
            return [source_id]

        visited: set[str] = {source_id}
        parent: dict[str, str] = {}
        queue: deque[tuple[str, int]] = deque([(source_id, 0)])

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= max_depth:
                continue

            # Check both directions
            neighbors: set[str] = set()
            for edge in self.graph.get_outgoing(current_id):
                neighbors.add(edge.target)
            for edge in self.graph.get_incoming(current_id):
                neighbors.add(edge.source)

            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                parent[neighbor_id] = current_id

                if neighbor_id == target_id:
                    # Reconstruct path
                    path = [target_id]
                    node = target_id
                    while node != source_id:
                        node = parent[node]
                        path.append(node)
                    path.reverse()
                    return path

                queue.append((neighbor_id, current_depth + 1))

        return None

    # --- File context ---

    def file_context(self, file_path: str) -> FileContextResult:
        """Get full context for a file path.

        Aggregates: contained symbols, imports, dependents,
        governing ADRs, related concepts, decisions, and reconciled links.
        """
        file_node = self.graph.get_node_by_path(file_path)
        if file_node is None:
            # Try with file: prefix
            file_node = self.graph.get_node(f"file:{file_path}")

        classes: list[Node] = []
        functions: list[Node] = []
        imports: list[str] = []
        dependents: list[str] = []
        governing_adrs: list[Node] = []
        related_concepts: list[Node] = []
        decisions: list[Node] = []
        reconciled_links: list[dict[str, str]] = []
        module_name = ""

        if file_node is None:
            return FileContextResult(
                file_node=None,
                module=module_name,
                classes=classes,
                functions=functions,
                imports=imports,
                dependents=dependents,
                governing_adrs=governing_adrs,
                related_concepts=related_concepts,
                decisions=decisions,
                reconciled_links=reconciled_links,
            )

        node_id = file_node.id

        # Contained symbols (outgoing CONTAINS edges)
        for edge in self.graph.get_outgoing(node_id, [EdgeType.CONTAINS]):
            target = self.graph.get_node(edge.target)
            if target:
                if target.node_type == NodeType.CLASS:
                    classes.append(target)
                elif target.node_type == NodeType.FUNCTION:
                    functions.append(target)

        # Imports (outgoing IMPORTS edges)
        for edge in self.graph.get_outgoing(node_id, [EdgeType.IMPORTS]):
            target = self.graph.get_node(edge.target)
            if target:
                imports.append(target.name)

        # Dependents (incoming IMPORTS edges — who imports this file)
        for edge in self.graph.get_incoming(node_id, [EdgeType.IMPORTS]):
            source = self.graph.get_node(edge.source)
            if source:
                dependents.append(source.name)

        # Governing ADRs (incoming GOVERNS edges)
        for edge in self.graph.get_incoming(node_id, [EdgeType.GOVERNS]):
            source = self.graph.get_node(edge.source)
            if source and source.node_type == NodeType.ADR:
                governing_adrs.append(source)
                # Get decisions from this ADR
                for dec_edge in self.graph.get_incoming(source.id, [EdgeType.DECIDED_IN]):
                    dec_node = self.graph.get_node(dec_edge.source)
                    if dec_node and dec_node.node_type == NodeType.DECISION:
                        decisions.append(dec_node)

        # Related concepts (traverse through governs → defines)
        for adr in governing_adrs:
            for edge in self.graph.get_outgoing(adr.id, [EdgeType.DEFINES]):
                concept = self.graph.get_node(edge.target)
                if concept and concept.node_type == NodeType.CONCEPT:
                    related_concepts.append(concept)

        # Reconciled links (SAME_AS edges on any of our nodes)
        all_node_ids = {node_id} | {n.id for n in classes + functions}
        for nid in all_node_ids:
            for edge in self.graph.get_outgoing(nid, [EdgeType.SAME_AS]):
                target = self.graph.get_node(edge.target)
                if target:
                    reconciled_links.append(
                        {"source": nid, "target": target.id, "target_name": target.name}
                    )
            for edge in self.graph.get_incoming(nid, [EdgeType.SAME_AS]):
                source = self.graph.get_node(edge.source)
                if source:
                    reconciled_links.append(
                        {"source": source.id, "target": nid, "source_name": source.name}
                    )

        # Module name from path
        path = file_node.properties.get("path", "")
        if path.endswith(".py"):
            module_name = path.replace("/", ".").removesuffix(".py").removeprefix("src.")

        return FileContextResult(
            file_node=file_node,
            module=module_name,
            classes=classes,
            functions=functions,
            imports=imports,
            dependents=dependents,
            governing_adrs=governing_adrs,
            related_concepts=related_concepts,
            decisions=decisions,
            reconciled_links=reconciled_links,
        )

    # --- Statistics ---

    def get_stats(self) -> GraphStats:
        """Return graph statistics including reconciliation info."""
        raw_stats = self.graph.stats()

        same_as_count = raw_stats["edge_counts"].get(EdgeType.SAME_AS, 0)
        related_to_count = raw_stats["edge_counts"].get(EdgeType.RELATED_TO, 0)

        # Count reconciliation clusters (connected components via SAME_AS)
        visited: set[str] = set()
        clusters = 0
        for node_id in self.graph.nodes:
            if node_id in visited:
                continue
            same_as_edges = self.graph.get_outgoing(
                node_id, [EdgeType.SAME_AS]
            ) + self.graph.get_incoming(node_id, [EdgeType.SAME_AS])
            if same_as_edges:
                clusters += 1
                # BFS through SAME_AS
                queue = deque([node_id])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    for e in self.graph.get_outgoing(current, [EdgeType.SAME_AS]):
                        if e.target not in visited:
                            queue.append(e.target)
                    for e in self.graph.get_incoming(current, [EdgeType.SAME_AS]):
                        if e.source not in visited:
                            queue.append(e.source)

        return GraphStats(
            total_nodes=raw_stats["total_nodes"],
            total_edges=raw_stats["total_edges"],
            node_counts=raw_stats["node_counts"],
            edge_counts=raw_stats["edge_counts"],
            indexed_paths=raw_stats["indexed_paths"],
            reconciliation_clusters=clusters,
            same_as_edges=same_as_count,
            related_to_edges=related_to_count,
        )
