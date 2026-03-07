"""Tests for LLM extraction models and graph wiring."""

from __future__ import annotations

from kg_memory.extraction import (
    ADRExtraction,
    Concept,
    ConfigExtraction,
    Decision,
    TradeOff,
    apply_config_extraction_to_graph,
    apply_extraction_to_graph,
)
from kg_memory.graph import EdgeType, KnowledgeGraph, Node, NodeType


class TestExtractionModels:
    def test_decision_model(self) -> None:
        d = Decision(statement="Use Redis", rationale="Fast", confidence=0.9)
        assert d.statement == "Use Redis"
        assert d.confidence == 0.9

    def test_concept_model(self) -> None:
        c = Concept(name="Ebbinghaus decay", definition="Time-based decay", category="algorithm")
        assert c.category == "algorithm"

    def test_trade_off_model(self) -> None:
        t = TradeOff(option_chosen="Redis", option_rejected="Kafka", reason="Simpler")
        assert t.option_chosen == "Redis"

    def test_adr_extraction_defaults(self) -> None:
        e = ADRExtraction()
        assert e.decisions == []
        assert e.concepts == []
        assert e.trade_offs == []

    def test_config_extraction_defaults(self) -> None:
        e = ConfigExtraction()
        assert e.conventions == []
        assert e.concepts == []


class TestApplyExtractionToGraph:
    def test_creates_decision_nodes(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="adr:0001",
                node_type=NodeType.ADR,
                name="ADR-0001",
                properties={"path": "docs/adr/0001.md"},
            )
        )

        extraction = ADRExtraction(
            decisions=[Decision(statement="Use Redis", rationale="Fast", confidence=0.9)]
        )
        apply_extraction_to_graph(g, "adr:0001", extraction)

        decision_nodes = g.get_nodes_by_type(NodeType.DECISION)
        assert len(decision_nodes) == 1
        assert decision_nodes[0].name == "Use Redis"

        # Check DECIDED_IN edge
        edges = g.get_incoming("adr:0001", [EdgeType.DECIDED_IN])
        assert len(edges) == 1

    def test_creates_concept_nodes(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="adr:0008",
                node_type=NodeType.ADR,
                name="ADR-0008",
                properties={"path": "docs/adr/0008.md"},
            )
        )

        extraction = ADRExtraction(
            concepts=[
                Concept(
                    name="Ebbinghaus decay", definition="Time-based scoring", category="algorithm"
                )
            ]
        )
        apply_extraction_to_graph(g, "adr:0008", extraction)

        concepts = g.get_nodes_by_type(NodeType.CONCEPT)
        assert len(concepts) == 1
        assert concepts[0].properties["category"] == "algorithm"

        # Check DEFINES edge
        edges = g.get_outgoing("adr:0008", [EdgeType.DEFINES])
        assert len(edges) == 1

    def test_creates_trade_off_nodes(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="adr:0003",
                node_type=NodeType.ADR,
                name="ADR-0003",
                properties={"path": "docs/adr/0003.md"},
            )
        )

        extraction = ADRExtraction(
            trade_offs=[TradeOff(option_chosen="Redis", option_rejected="Kafka", reason="Simpler")]
        )
        apply_extraction_to_graph(g, "adr:0003", extraction)

        trade_offs = g.get_nodes_by_type(NodeType.TRADE_OFF)
        assert len(trade_offs) == 1
        assert "Redis" in trade_offs[0].name

    def test_governs_existing_module(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="adr:0008",
                node_type=NodeType.ADR,
                name="ADR-0008",
                properties={"path": "docs/adr/0008.md"},
            )
        )
        g.add_node(
            Node(
                id="file:src/scoring.py",
                node_type=NodeType.FILE,
                name="scoring",
                properties={"path": "src/scoring.py"},
            )
        )

        extraction = ADRExtraction(modules_governed=["src/scoring.py"])
        apply_extraction_to_graph(g, "adr:0008", extraction)

        edges = g.get_outgoing("adr:0008", [EdgeType.GOVERNS])
        assert len(edges) == 1
        assert edges[0].target == "file:src/scoring.py"

    def test_principles_stored(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="adr:0001",
                node_type=NodeType.ADR,
                name="ADR-0001",
                properties={"path": "docs/adr/0001.md"},
            )
        )

        extraction = ADRExtraction(principles=["Immutable events", "Derived projection"])
        apply_extraction_to_graph(g, "adr:0001", extraction)

        node = g.get_node("adr:0001")
        assert node.properties["principles"] == ["Immutable events", "Derived projection"]

    def test_nonexistent_adr_ignored(self) -> None:
        g = KnowledgeGraph()
        extraction = ADRExtraction(decisions=[Decision(statement="X", rationale="Y")])
        apply_extraction_to_graph(g, "adr:nonexistent", extraction)
        assert len(g.get_nodes_by_type(NodeType.DECISION)) == 0


class TestApplyConfigExtraction:
    def test_creates_concepts(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="config:overview",
                node_type=NodeType.CONFIG,
                name="Overview",
                properties={"path": "CLAUDE.md"},
            )
        )

        extraction = ConfigExtraction(
            concepts=[
                Concept(
                    name="Atlas pattern", definition="Response envelope format", category="pattern"
                )
            ]
        )
        apply_config_extraction_to_graph(g, "config:overview", extraction)

        concepts = g.get_nodes_by_type(NodeType.CONCEPT)
        assert len(concepts) == 1

    def test_conventions_stored(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="config:coding",
                node_type=NodeType.CONFIG,
                name="Coding",
                properties={"path": "CLAUDE.md"},
            )
        )

        extraction = ConfigExtraction(conventions=["Use descriptive names", "No mocks"])
        apply_config_extraction_to_graph(g, "config:coding", extraction)

        node = g.get_node("config:coding")
        assert "Use descriptive names" in node.properties["conventions"]
