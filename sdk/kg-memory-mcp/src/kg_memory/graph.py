"""In-memory knowledge graph with adjacency list and multi-index lookups.

Pure Python — no external graph library. Designed for fast traversal,
type-filtered queries, and incremental updates from file watchers.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class NodeType(enum.StrEnum):
    """Node types in the knowledge graph."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    FILE = "file"
    ADR = "adr"
    DECISION = "decision"
    CONCEPT = "concept"
    TRADE_OFF = "trade_off"
    CONFIG = "config"


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


class EdgeType(enum.StrEnum):
    """Edge types in the knowledge graph."""

    # Structural (tree-sitter)
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    METHOD_OF = "method_of"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"

    # Semantic (tree-sitter + LLM)
    GOVERNS = "governs"

    # LLM extraction
    DECIDED_IN = "decided_in"
    DEFINES = "defines"
    IMPLEMENTS = "implements"
    CONSIDERED = "considered"

    # Entity reconciliation
    SAME_AS = "same_as"
    RELATED_TO = "related_to"


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """A node in the knowledge graph."""

    id: str
    node_type: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON persistence."""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """Deserialize from a plain dict."""
        return cls(
            id=data["id"],
            node_type=data["node_type"],
            name=data["name"],
            properties=data.get("properties", {}),
        )


@dataclass
class Edge:
    """A directed edge in the knowledge graph."""

    source: str
    target: str
    edge_type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON persistence."""
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Deserialize from a plain dict."""
        return cls(
            source=data["source"],
            target=data["target"],
            edge_type=data["edge_type"],
            properties=data.get("properties", {}),
        )


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """In-memory knowledge graph with adjacency list and multi-index lookups.

    Supports:
    - O(1) node lookup by id
    - O(1) outgoing/incoming edge traversal
    - O(1) type-filtered node listing
    - O(1) name-based lookup (lowercase)
    - O(1) file path to node id mapping
    - Incremental add/remove for file watcher updates
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.adjacency: dict[str, list[Edge]] = defaultdict(list)
        self.reverse_adjacency: dict[str, list[Edge]] = defaultdict(list)
        self.type_index: dict[str, set[str]] = defaultdict(set)
        self.name_index: dict[str, list[str]] = defaultdict(list)
        self.path_index: dict[str, str] = {}

    # --- Node operations ---

    def add_node(self, node: Node) -> None:
        """Add a node to the graph. Updates indexes."""
        if node.id in self.nodes:
            self.remove_node(node.id)
        self.nodes[node.id] = node
        self.type_index[node.node_type].add(node.id)
        self.name_index[node.name.lower()].append(node.id)
        path = node.properties.get("path")
        if path:
            self.path_index[path] = node.id

    def remove_node(self, node_id: str) -> Node | None:
        """Remove a node and all its edges. Returns the removed node."""
        node = self.nodes.pop(node_id, None)
        if node is None:
            return None

        # Clean type index
        type_set = self.type_index.get(node.node_type)
        if type_set:
            type_set.discard(node_id)

        # Clean name index
        name_key = node.name.lower()
        name_list = self.name_index.get(name_key)
        if name_list:
            try:
                name_list.remove(node_id)
            except ValueError:
                pass
            if not name_list:
                del self.name_index[name_key]

        # Clean path index
        path = node.properties.get("path")
        if path and self.path_index.get(path) == node_id:
            del self.path_index[path]

        # Remove all edges involving this node
        for edge in list(self.adjacency.get(node_id, [])):
            rev_list = self.reverse_adjacency.get(edge.target, [])
            self.reverse_adjacency[edge.target] = [e for e in rev_list if e.source != node_id]
        self.adjacency.pop(node_id, None)

        for edge in list(self.reverse_adjacency.get(node_id, [])):
            fwd_list = self.adjacency.get(edge.source, [])
            self.adjacency[edge.source] = [e for e in fwd_list if e.target != node_id]
        self.reverse_adjacency.pop(node_id, None)

        return node

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by id."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[Node]:
        """Get all nodes of a given type."""
        return [
            self.nodes[nid] for nid in self.type_index.get(node_type, set()) if nid in self.nodes
        ]

    def get_nodes_by_name(self, name: str) -> list[Node]:
        """Get all nodes matching a name (case-insensitive)."""
        return [
            self.nodes[nid] for nid in self.name_index.get(name.lower(), []) if nid in self.nodes
        ]

    def get_node_by_path(self, path: str) -> Node | None:
        """Get a node by file path."""
        node_id = self.path_index.get(path)
        if node_id:
            return self.nodes.get(node_id)
        return None

    # --- Edge operations ---

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge. Both source and target must exist."""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            return
        # Avoid duplicate edges
        for existing in self.adjacency[edge.source]:
            if existing.target == edge.target and existing.edge_type == edge.edge_type:
                return
        self.adjacency[edge.source].append(edge)
        self.reverse_adjacency[edge.target].append(edge)

    def remove_edges_for_source(self, source_id: str) -> None:
        """Remove all outgoing edges from a source node."""
        edges = self.adjacency.pop(source_id, [])
        for edge in edges:
            rev_list = self.reverse_adjacency.get(edge.target, [])
            self.reverse_adjacency[edge.target] = [e for e in rev_list if e.source != source_id]

    def get_outgoing(self, node_id: str, edge_types: list[str] | None = None) -> list[Edge]:
        """Get outgoing edges, optionally filtered by type."""
        edges = self.adjacency.get(node_id, [])
        if edge_types:
            type_set = set(edge_types)
            return [e for e in edges if e.edge_type in type_set]
        return list(edges)

    def get_incoming(self, node_id: str, edge_types: list[str] | None = None) -> list[Edge]:
        """Get incoming edges, optionally filtered by type."""
        edges = self.reverse_adjacency.get(node_id, [])
        if edge_types:
            type_set = set(edge_types)
            return [e for e in edges if e.edge_type in type_set]
        return list(edges)

    # --- Bulk operations ---

    def remove_file_nodes(self, file_path: str) -> list[str]:
        """Remove all nodes originating from a file path.

        Used by the file watcher to clear stale nodes before re-indexing.
        Returns the list of removed node ids.
        """
        removed: list[str] = []
        path_str = str(file_path)
        to_remove = []
        for node_id, node in self.nodes.items():
            node_path = node.properties.get("path", "")
            if node_path == path_str or node_path.startswith(path_str):
                to_remove.append(node_id)
            elif node.properties.get("source_file") == path_str:
                to_remove.append(node_id)
        for node_id in to_remove:
            self.remove_node(node_id)
            removed.append(node_id)
        return removed

    def all_edges(self) -> Iterator[Edge]:
        """Iterate over all edges in the graph."""
        for edges in self.adjacency.values():
            yield from edges

    # --- Statistics ---

    def stats(self) -> dict[str, Any]:
        """Return graph statistics."""
        node_counts: dict[str, int] = defaultdict(int)
        for node in self.nodes.values():
            node_counts[node.node_type] += 1

        edge_counts: dict[str, int] = defaultdict(int)
        total_edges = 0
        for edges in self.adjacency.values():
            for edge in edges:
                edge_counts[edge.edge_type] += 1
                total_edges += 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": total_edges,
            "node_counts": dict(node_counts),
            "edge_counts": dict(edge_counts),
            "indexed_paths": len(self.path_index),
        }

    # --- Serialization ---

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire graph to a plain dict."""
        edges = [edge.to_dict() for edge in self.all_edges()]
        nodes = [node.to_dict() for node in self.nodes.values()]
        return {"nodes": nodes, "edges": edges}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        """Deserialize a graph from a plain dict."""
        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_node(Node.from_dict(node_data))
        for edge_data in data.get("edges", []):
            graph.add_edge(Edge.from_dict(edge_data))
        return graph
