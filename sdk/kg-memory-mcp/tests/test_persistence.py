"""Tests for JSON persistence (save/load)."""

from __future__ import annotations

from pathlib import Path

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType
from kg_memory.persistence import load_graph, save_graph


def _make_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_node(
        Node(id="file:a.py", node_type=NodeType.FILE, name="a.py", properties={"path": "a.py"})
    )
    g.add_node(Node(id="class:Foo", node_type=NodeType.CLASS, name="Foo", properties={"line": 1}))
    g.add_edge(Edge(source="file:a.py", target="class:Foo", edge_type=EdgeType.CONTAINS))
    return g


class TestPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        graph = _make_graph()
        path = tmp_path / "test.json"
        save_graph(graph, path)
        assert path.exists()

        loaded = load_graph(path)
        assert loaded is not None
        assert len(loaded.nodes) == 2
        assert loaded.get_node("class:Foo") is not None
        assert len(list(loaded.all_edges())) == 1

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        result = load_graph(tmp_path / "nope.json")
        assert result is None

    def test_load_corrupted(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json")
        result = load_graph(path)
        assert result is None

    def test_atomic_write(self, tmp_path: Path) -> None:
        graph = _make_graph()
        path = tmp_path / "atomic.json"
        save_graph(graph, path)
        # No .tmp file should remain
        assert not (tmp_path / "atomic.tmp").exists()
        assert path.exists()
