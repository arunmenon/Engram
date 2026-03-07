"""Tests for the retrieval engine."""

from __future__ import annotations

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType
from kg_memory.retrieval import Retriever


def _build_test_graph() -> KnowledgeGraph:
    """Build a graph with files, classes, functions, ADRs, and concepts."""
    g = KnowledgeGraph()

    # Files
    g.add_node(
        Node(
            id="file:src/scoring.py",
            node_type=NodeType.FILE,
            name="scoring.py",
            properties={"path": "src/scoring.py", "language": "python", "size_lines": 145},
        )
    )
    g.add_node(
        Node(
            id="file:src/models.py",
            node_type=NodeType.FILE,
            name="models.py",
            properties={"path": "src/models.py", "language": "python", "size_lines": 200},
        )
    )

    # Classes and functions
    g.add_node(
        Node(
            id="func:compute_score",
            node_type=NodeType.FUNCTION,
            name="compute_score",
            properties={"source_file": "src/scoring.py", "line": 10},
        )
    )
    g.add_node(
        Node(
            id="class:Event",
            node_type=NodeType.CLASS,
            name="Event",
            properties={"source_file": "src/models.py", "line": 5},
        )
    )

    # ADR
    g.add_node(
        Node(
            id="adr:0008",
            node_type=NodeType.ADR,
            name="ADR-0008",
            properties={"path": "docs/adr/0008-scoring.md", "title": "Memory Scoring"},
        )
    )

    # Concept
    g.add_node(
        Node(
            id="concept:decay",
            node_type=NodeType.CONCEPT,
            name="Ebbinghaus decay",
            properties={"definition": "Memory scoring based on time decay"},
        )
    )

    # Edges
    g.add_edge(
        Edge(source="file:src/scoring.py", target="func:compute_score", edge_type=EdgeType.CONTAINS)
    )
    g.add_edge(Edge(source="file:src/models.py", target="class:Event", edge_type=EdgeType.CONTAINS))
    g.add_edge(
        Edge(source="file:src/scoring.py", target="file:src/models.py", edge_type=EdgeType.IMPORTS)
    )
    g.add_edge(Edge(source="adr:0008", target="file:src/scoring.py", edge_type=EdgeType.GOVERNS))
    g.add_edge(Edge(source="adr:0008", target="concept:decay", edge_type=EdgeType.DEFINES))

    return g


class TestSearch:
    def test_exact_name_match(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("scoring.py")
        assert len(results) > 0
        assert results[0].name == "scoring.py"
        assert results[0].score == 1.0

    def test_partial_name_match(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("score")
        names = [res.name for res in results]
        assert "compute_score" in names

    def test_concept_search(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("decay")
        names = [res.name for res in results]
        assert "Ebbinghaus decay" in names

    def test_type_filter(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("scoring", node_types=["adr"])
        assert all(res.node_type == "adr" for res in results)

    def test_limit(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("s", limit=2)
        assert len(results) <= 2

    def test_no_results(self) -> None:
        r = Retriever(_build_test_graph())
        results = r.search("zzzznonexistent")
        assert len(results) == 0


class TestNeighbors:
    def test_basic_expansion(self) -> None:
        r = Retriever(_build_test_graph())
        result = r.get_neighbors("file:src/scoring.py", depth=1)
        assert len(result.nodes) >= 2  # file itself + at least one neighbor
        assert "func:compute_score" in result.nodes

    def test_edge_type_filter(self) -> None:
        r = Retriever(_build_test_graph())
        result = r.get_neighbors("file:src/scoring.py", edge_types=[EdgeType.CONTAINS])
        node_ids = set(result.nodes.keys())
        assert "func:compute_score" in node_ids

    def test_nonexistent_node(self) -> None:
        r = Retriever(_build_test_graph())
        result = r.get_neighbors("nonexistent")
        assert len(result.nodes) == 0

    def test_depth_2(self) -> None:
        r = Retriever(_build_test_graph())
        result = r.get_neighbors("adr:0008", depth=2)
        # Should reach: adr -> scoring.py -> compute_score, models.py
        assert "file:src/scoring.py" in result.nodes
        assert "concept:decay" in result.nodes


class TestPathFinding:
    def test_direct_path(self) -> None:
        r = Retriever(_build_test_graph())
        path = r.find_path("file:src/scoring.py", "func:compute_score")
        assert path is not None
        assert len(path) == 2

    def test_indirect_path(self) -> None:
        r = Retriever(_build_test_graph())
        path = r.find_path("adr:0008", "func:compute_score")
        assert path is not None
        assert len(path) == 3  # adr -> scoring.py -> compute_score

    def test_no_path(self) -> None:
        g = KnowledgeGraph()
        g.add_node(Node(id="a", node_type=NodeType.FILE, name="a"))
        g.add_node(Node(id="b", node_type=NodeType.FILE, name="b"))
        r = Retriever(g)
        path = r.find_path("a", "b")
        assert path is None

    def test_same_node(self) -> None:
        r = Retriever(_build_test_graph())
        path = r.find_path("adr:0008", "adr:0008")
        assert path == ["adr:0008"]


class TestFileContext:
    def test_file_context(self) -> None:
        r = Retriever(_build_test_graph())
        ctx = r.file_context("src/scoring.py")
        assert ctx.file_node is not None
        assert len(ctx.functions) == 1
        assert ctx.functions[0].name == "compute_score"
        assert len(ctx.governing_adrs) == 1
        assert ctx.governing_adrs[0].name == "ADR-0008"

    def test_imports(self) -> None:
        r = Retriever(_build_test_graph())
        ctx = r.file_context("src/scoring.py")
        assert "models.py" in ctx.imports

    def test_nonexistent_file(self) -> None:
        r = Retriever(_build_test_graph())
        ctx = r.file_context("nonexistent.py")
        assert ctx.file_node is None


class TestStats:
    def test_stats(self) -> None:
        r = Retriever(_build_test_graph())
        stats = r.get_stats()
        assert stats.total_nodes == 6
        assert stats.total_edges == 5
