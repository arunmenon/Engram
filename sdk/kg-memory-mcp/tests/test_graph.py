"""Tests for the in-memory KnowledgeGraph data structures."""

from __future__ import annotations

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType


def _make_graph() -> KnowledgeGraph:
    """Build a small graph for testing."""
    g = KnowledgeGraph()
    g.add_node(
        Node(
            id="file:src/a.py",
            node_type=NodeType.FILE,
            name="a.py",
            properties={"path": "src/a.py"},
        )
    )
    g.add_node(
        Node(
            id="file:src/b.py",
            node_type=NodeType.FILE,
            name="b.py",
            properties={"path": "src/b.py"},
        )
    )
    g.add_node(
        Node(
            id="class:Foo",
            node_type=NodeType.CLASS,
            name="Foo",
            properties={"line": 10, "source_file": "src/a.py"},
        )
    )
    g.add_node(
        Node(
            id="func:bar",
            node_type=NodeType.FUNCTION,
            name="bar",
            properties={"line": 5, "source_file": "src/b.py"},
        )
    )
    g.add_edge(Edge(source="file:src/a.py", target="class:Foo", edge_type=EdgeType.CONTAINS))
    g.add_edge(Edge(source="file:src/b.py", target="func:bar", edge_type=EdgeType.CONTAINS))
    g.add_edge(Edge(source="file:src/a.py", target="file:src/b.py", edge_type=EdgeType.IMPORTS))
    return g


class TestNodeOperations:
    def test_add_and_get_node(self) -> None:
        g = KnowledgeGraph()
        node = Node(
            id="test:1", node_type=NodeType.FILE, name="test", properties={"path": "test.py"}
        )
        g.add_node(node)
        assert g.get_node("test:1") is not None
        assert g.get_node("test:1").name == "test"

    def test_get_nodes_by_type(self) -> None:
        g = _make_graph()
        files = g.get_nodes_by_type(NodeType.FILE)
        assert len(files) == 2
        classes = g.get_nodes_by_type(NodeType.CLASS)
        assert len(classes) == 1

    def test_get_nodes_by_name(self) -> None:
        g = _make_graph()
        results = g.get_nodes_by_name("Foo")
        assert len(results) == 1
        assert results[0].id == "class:Foo"

    def test_get_nodes_by_name_case_insensitive(self) -> None:
        g = _make_graph()
        results = g.get_nodes_by_name("foo")
        assert len(results) == 1

    def test_get_node_by_path(self) -> None:
        g = _make_graph()
        node = g.get_node_by_path("src/a.py")
        assert node is not None
        assert node.id == "file:src/a.py"

    def test_remove_node(self) -> None:
        g = _make_graph()
        removed = g.remove_node("class:Foo")
        assert removed is not None
        assert removed.name == "Foo"
        assert g.get_node("class:Foo") is None
        # CONTAINS edge should be gone too
        edges = g.get_outgoing("file:src/a.py", [EdgeType.CONTAINS])
        assert len(edges) == 0

    def test_add_node_replaces_existing(self) -> None:
        g = KnowledgeGraph()
        g.add_node(Node(id="n:1", node_type=NodeType.FILE, name="old"))
        g.add_node(Node(id="n:1", node_type=NodeType.FILE, name="new"))
        assert g.get_node("n:1").name == "new"


class TestEdgeOperations:
    def test_add_and_get_outgoing(self) -> None:
        g = _make_graph()
        edges = g.get_outgoing("file:src/a.py")
        assert len(edges) == 2  # CONTAINS + IMPORTS

    def test_get_incoming(self) -> None:
        g = _make_graph()
        edges = g.get_incoming("class:Foo")
        assert len(edges) == 1
        assert edges[0].source == "file:src/a.py"

    def test_edge_type_filter(self) -> None:
        g = _make_graph()
        contains = g.get_outgoing("file:src/a.py", [EdgeType.CONTAINS])
        assert len(contains) == 1
        imports = g.get_outgoing("file:src/a.py", [EdgeType.IMPORTS])
        assert len(imports) == 1

    def test_duplicate_edge_ignored(self) -> None:
        g = _make_graph()
        g.add_edge(Edge(source="file:src/a.py", target="class:Foo", edge_type=EdgeType.CONTAINS))
        edges = g.get_outgoing("file:src/a.py", [EdgeType.CONTAINS])
        assert len(edges) == 1

    def test_edge_requires_valid_nodes(self) -> None:
        g = KnowledgeGraph()
        g.add_node(Node(id="a", node_type=NodeType.FILE, name="a"))
        g.add_edge(Edge(source="a", target="nonexistent", edge_type=EdgeType.IMPORTS))
        assert len(g.get_outgoing("a")) == 0

    def test_remove_edges_for_source(self) -> None:
        g = _make_graph()
        g.remove_edges_for_source("file:src/a.py")
        assert len(g.get_outgoing("file:src/a.py")) == 0
        # Reverse adjacency should be cleaned too
        assert len(g.get_incoming("class:Foo")) == 0


class TestBulkOperations:
    def test_remove_file_nodes(self) -> None:
        g = _make_graph()
        removed = g.remove_file_nodes("src/a.py")
        assert "file:src/a.py" in removed
        assert "class:Foo" in removed
        assert g.get_node("file:src/a.py") is None
        assert g.get_node("class:Foo") is None
        # b.py should still exist
        assert g.get_node("file:src/b.py") is not None


class TestSerialization:
    def test_round_trip(self) -> None:
        g = _make_graph()
        data = g.to_dict()
        g2 = KnowledgeGraph.from_dict(data)
        assert len(g2.nodes) == len(g.nodes)
        assert g2.get_node("class:Foo") is not None
        assert len(list(g2.all_edges())) == len(list(g.all_edges()))

    def test_stats(self) -> None:
        g = _make_graph()
        stats = g.stats()
        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 3
        assert stats["node_counts"][NodeType.FILE] == 2
        assert stats["edge_counts"][EdgeType.CONTAINS] == 2
        assert stats["indexed_paths"] == 2
