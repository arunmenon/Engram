"""Tests for Neo4j batch Cypher templates and index completeness.

Validates:
- All node types have BATCH_MERGE_* templates in queries.py
- All 20 edge types have batch templates in _BATCH_EDGE_QUERIES
- ALL_INDEXES includes relationship, composite, and property indexes
- Batch templates contain required UNWIND, MERGE, and tenant_id patterns
"""

from __future__ import annotations

from context_graph.adapters.neo4j import queries
from context_graph.adapters.neo4j.store import _BATCH_EDGE_QUERIES
from context_graph.domain.models import EdgeType

# ---------------------------------------------------------------------------
# Batch node templates exist
# ---------------------------------------------------------------------------


class TestBatchNodeTemplates:
    """Verify that all node types have batch MERGE templates."""

    def test_batch_merge_event_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_EVENT_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_EVENT_NODES

    def test_batch_merge_entity_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_ENTITY_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_ENTITY_NODES

    def test_batch_merge_summary_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_SUMMARY_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_SUMMARY_NODES

    def test_batch_merge_belief_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_BELIEF_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_BELIEF_NODES

    def test_batch_merge_goal_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_GOAL_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_GOAL_NODES

    def test_batch_merge_episode_nodes_exists(self) -> None:
        assert hasattr(queries, "BATCH_MERGE_EPISODE_NODES")
        assert "UNWIND" in queries.BATCH_MERGE_EPISODE_NODES

    def test_batch_node_templates_have_merge(self) -> None:
        """All batch node templates must contain a MERGE statement."""
        templates = [
            queries.BATCH_MERGE_EVENT_NODES,
            queries.BATCH_MERGE_ENTITY_NODES,
            queries.BATCH_MERGE_SUMMARY_NODES,
            queries.BATCH_MERGE_BELIEF_NODES,
            queries.BATCH_MERGE_GOAL_NODES,
            queries.BATCH_MERGE_EPISODE_NODES,
        ]
        for template in templates:
            assert "MERGE" in template, f"Missing MERGE in: {template[:60]}"

    def test_batch_node_templates_set_tenant_id(self) -> None:
        """All batch node templates must set tenant_id on the node."""
        templates = [
            queries.BATCH_MERGE_EVENT_NODES,
            queries.BATCH_MERGE_ENTITY_NODES,
            queries.BATCH_MERGE_SUMMARY_NODES,
            queries.BATCH_MERGE_BELIEF_NODES,
            queries.BATCH_MERGE_GOAL_NODES,
            queries.BATCH_MERGE_EPISODE_NODES,
        ]
        for template in templates:
            assert "tenant_id" in template, f"Missing tenant_id in: {template[:60]}"


# ---------------------------------------------------------------------------
# Batch edge templates: all 20 edge types
# ---------------------------------------------------------------------------


class TestBatchEdgeQueries:
    """Verify that all 20 edge types have UNWIND batch templates."""

    def test_batch_edge_queries_has_20_entries(self) -> None:
        """_BATCH_EDGE_QUERIES must map all 20 EdgeType values."""
        assert len(_BATCH_EDGE_QUERIES) == 20

    def test_all_edge_types_covered(self) -> None:
        """Every EdgeType enum member must be in _BATCH_EDGE_QUERIES."""
        for edge_type in EdgeType:
            assert edge_type.value in _BATCH_EDGE_QUERIES, (
                f"Missing batch template for edge type: {edge_type.value}"
            )

    def test_batch_edge_templates_have_unwind(self) -> None:
        """Every batch edge template must start with UNWIND."""
        for edge_type, template in _BATCH_EDGE_QUERIES.items():
            assert "UNWIND" in template, f"Missing UNWIND in batch template for {edge_type}"

    def test_batch_edge_templates_have_merge(self) -> None:
        """Every batch edge template must contain MERGE."""
        for edge_type, template in _BATCH_EDGE_QUERIES.items():
            assert "MERGE" in template, f"Missing MERGE in batch template for {edge_type}"

    def test_batch_edge_templates_have_tenant_guard(self) -> None:
        """Every batch edge template must filter by tenant_id."""
        for edge_type, template in _BATCH_EDGE_QUERIES.items():
            assert "$tenant_id" in template, (
                f"Missing $tenant_id guard in batch template for {edge_type}"
            )

    def test_batch_edge_templates_reference_edge_props(self) -> None:
        """Every batch edge template must SET properties from edge.props."""
        for edge_type, template in _BATCH_EDGE_QUERIES.items():
            assert "edge.props" in template, f"Missing edge.props in batch template for {edge_type}"

    def test_specific_edge_templates_exist(self) -> None:
        """Check that specific batch templates are defined as module attributes."""
        expected_attrs = [
            "BATCH_MERGE_FOLLOWS",
            "BATCH_MERGE_CAUSED_BY",
            "BATCH_MERGE_SIMILAR_TO",
            "BATCH_MERGE_REFERENCES",
            "BATCH_MERGE_SUMMARIZES",
            "BATCH_MERGE_SAME_AS",
            "BATCH_MERGE_RELATED_TO",
            "BATCH_MERGE_HAS_PROFILE",
            "BATCH_MERGE_HAS_PREFERENCE",
            "BATCH_MERGE_HAS_SKILL",
            "BATCH_MERGE_DERIVED_FROM",
            "BATCH_MERGE_EXHIBITS_PATTERN",
            "BATCH_MERGE_INTERESTED_IN",
            "BATCH_MERGE_ABOUT",
            "BATCH_MERGE_ABSTRACTED_FROM",
            "BATCH_MERGE_PARENT_SKILL",
            "BATCH_MERGE_CONTRADICTS",
            "BATCH_MERGE_SUPERSEDES",
            "BATCH_MERGE_PURSUES",
            "BATCH_MERGE_CONTAINS",
        ]
        for attr_name in expected_attrs:
            assert hasattr(queries, attr_name), f"Missing attribute: queries.{attr_name}"


# ---------------------------------------------------------------------------
# Index completeness
# ---------------------------------------------------------------------------


class TestIndexCompleteness:
    """Verify that ALL_INDEXES includes new relationship, composite, and property indexes."""

    def test_all_indexes_count(self) -> None:
        """ALL_INDEXES: 1 session + 11 tenant + 3 rel + 3 composite + 3 property = 21."""
        assert len(queries.ALL_INDEXES) == 21

    def test_relationship_indexes_present(self) -> None:
        """Relationship indexes for FOLLOWS, SIMILAR_TO, REFERENCES must be in ALL_INDEXES."""
        assert queries.INDEX_FOLLOWS_REL in queries.ALL_INDEXES
        assert queries.INDEX_SIMILAR_REL in queries.ALL_INDEXES
        assert queries.INDEX_REFERENCES_REL in queries.ALL_INDEXES

    def test_composite_indexes_present(self) -> None:
        """Composite indexes for session+time, event_type+tenant, entity_type+tenant."""
        assert queries.INDEX_EVENT_SESSION_TIME in queries.ALL_INDEXES
        assert queries.INDEX_EVENT_TYPE_TENANT in queries.ALL_INDEXES
        assert queries.INDEX_ENTITY_TYPE_TENANT in queries.ALL_INDEXES

    def test_property_indexes_present(self) -> None:
        """Property indexes for importance, access_count, entity name."""
        assert queries.INDEX_EVENT_IMPORTANCE in queries.ALL_INDEXES
        assert queries.INDEX_EVENT_ACCESS_COUNT in queries.ALL_INDEXES
        assert queries.INDEX_ENTITY_NAME in queries.ALL_INDEXES

    def test_relationship_indexes_syntax(self) -> None:
        """Relationship index DDL must use the FOR ()-[r:TYPE]-() syntax."""
        for idx in queries.RELATIONSHIP_INDEXES:
            assert "IF NOT EXISTS" in idx
            assert "FOR ()-[r:" in idx

    def test_composite_indexes_syntax(self) -> None:
        """Composite index DDL must specify two properties."""
        for idx in queries.COMPOSITE_INDEXES:
            assert "IF NOT EXISTS" in idx
            # Each composite index ON clause has a comma separating two properties
            on_clause = idx.split("ON")[1] if "ON" in idx else ""
            assert "," in on_clause, f"Composite index missing second property: {idx[:60]}"

    def test_property_indexes_syntax(self) -> None:
        """Property index DDL must use CREATE INDEX ... IF NOT EXISTS."""
        for idx in queries.PROPERTY_INDEXES:
            assert "CREATE INDEX" in idx
            assert "IF NOT EXISTS" in idx
