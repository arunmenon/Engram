"""Tests for the 3-tier entity reconciliation module."""

from __future__ import annotations

import pytest

from kg_memory.graph import EdgeType, KnowledgeGraph, Node, NodeType
from kg_memory.reconciliation import (
    ReconciliationAction,
    UnionFind,
    compute_clusters,
    normalize_name,
    reconcile_graph,
    resolve_alias,
    resolve_exact,
    resolve_fuzzy,
)


class TestNormalization:
    def test_basic(self) -> None:
        assert normalize_name("Neo4j Graph Store") == "neo4j graph store"

    def test_underscores(self) -> None:
        assert normalize_name("graph_store") == "graph store"

    def test_hyphens(self) -> None:
        assert normalize_name("tree-sitter") == "tree sitter"

    def test_collapse_spaces(self) -> None:
        assert normalize_name("  graph   store  ") == "graph store"


class TestAliasResolution:
    def test_known_alias(self) -> None:
        assert resolve_alias("Neo4jGraphStore") == "neo4j graph store"

    def test_known_canonical(self) -> None:
        assert resolve_alias("ebbinghaus decay") == "ebbinghaus decay"

    def test_alias_variant(self) -> None:
        assert resolve_alias("4 factor scoring") == "ebbinghaus decay"

    def test_unknown_name(self) -> None:
        assert resolve_alias("unknown_thing") == "unknown thing"


class TestTier1Exact:
    def test_same_canonical(self) -> None:
        action = resolve_exact("Neo4jGraphStore", "neo4j adapter")
        assert action == ReconciliationAction.MERGE

    def test_different_names(self) -> None:
        action = resolve_exact("Foo", "Bar")
        assert action is None

    def test_alias_match(self) -> None:
        action = resolve_exact("decay scoring", "4 factor scoring")
        assert action == ReconciliationAction.MERGE


class TestTier2Fuzzy:
    def test_high_similarity(self) -> None:
        action, score = resolve_fuzzy("graph store interface", "graph store protocol")
        assert action == ReconciliationAction.SAME_AS
        assert score >= 0.85

    def test_moderate_similarity(self) -> None:
        action, score = resolve_fuzzy("graph store interface", "graph store integration")
        assert action in (ReconciliationAction.SAME_AS, ReconciliationAction.RELATED_TO)
        assert score >= 0.7

    def test_low_similarity(self) -> None:
        action, score = resolve_fuzzy("apple", "zebra")
        assert action is None
        assert score < 0.7

    def test_empty_strings(self) -> None:
        action, score = resolve_fuzzy("", "")
        assert action is None


class TestUnionFind:
    def test_basic_union(self) -> None:
        uf = UnionFind()
        uf.union("a", "b")
        assert uf.find("a") == uf.find("b")

    def test_transitive(self) -> None:
        uf = UnionFind()
        uf.union("a", "b")
        uf.union("b", "c")
        assert uf.find("a") == uf.find("c")

    def test_separate_sets(self) -> None:
        uf = UnionFind()
        uf.union("a", "b")
        uf.union("c", "d")
        assert uf.find("a") != uf.find("c")


class TestComputeClusters:
    def test_single_cluster(self) -> None:
        pairs = [("a", "b"), ("b", "c")]
        clusters = compute_clusters(pairs)
        assert len(clusters) == 1
        members = list(clusters.values())[0]
        assert set(members) == {"a", "b", "c"}

    def test_multiple_clusters(self) -> None:
        pairs = [("a", "b"), ("c", "d")]
        clusters = compute_clusters(pairs)
        assert len(clusters) == 2

    def test_empty(self) -> None:
        assert compute_clusters([]) == {}


class TestReconcileGraph:
    @pytest.mark.asyncio
    async def test_reconcile_same_concepts(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="concept:a",
                node_type=NodeType.CONCEPT,
                name="Neo4jGraphStore",
                properties={"definition": "Neo4j adapter"},
            )
        )
        g.add_node(
            Node(
                id="concept:b",
                node_type=NodeType.CONCEPT,
                name="neo4j adapter",
                properties={"definition": "Neo4j graph store adapter"},
            )
        )

        results = await reconcile_graph(g, extractor=None)
        assert len(results) >= 1
        # Should have created a SAME_AS or MERGE match
        actions = {r.action for r in results}
        assert ReconciliationAction.MERGE in actions or ReconciliationAction.SAME_AS in actions

    @pytest.mark.asyncio
    async def test_reconcile_adds_edges(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="concept:a",
                node_type=NodeType.CONCEPT,
                name="decay scoring",
                properties={"definition": "scoring via decay"},
            )
        )
        g.add_node(
            Node(
                id="concept:b",
                node_type=NodeType.CONCEPT,
                name="4 factor scoring",
                properties={"definition": "4-factor scoring model"},
            )
        )

        await reconcile_graph(g, extractor=None)
        # Should have SAME_AS edges since both map to "ebbinghaus decay"
        same_as = g.get_outgoing("concept:a", [EdgeType.SAME_AS]) + g.get_outgoing(
            "concept:b", [EdgeType.SAME_AS]
        )
        assert len(same_as) >= 1

    @pytest.mark.asyncio
    async def test_incompatible_types_skipped(self) -> None:
        g = KnowledgeGraph()
        g.add_node(
            Node(
                id="concept:a",
                node_type=NodeType.CONCEPT,
                name="scoring",
                properties={"definition": "scoring"},
            )
        )
        g.add_node(
            Node(
                id="adr:1", node_type=NodeType.ADR, name="scoring", properties={"title": "scoring"}
            )
        )

        results = await reconcile_graph(g, extractor=None)
        # ADR and CONCEPT are not in compatible types
        assert len(results) == 0
