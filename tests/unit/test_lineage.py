"""Unit tests for context_graph.domain.lineage."""

from __future__ import annotations

from context_graph.domain.lineage import (
    build_context_cypher,
    build_lineage_cypher,
    validate_traversal_bounds,
)


class TestValidateTraversalBounds:
    """Tests for parameter clamping."""

    def test_clamps_high_depth(self) -> None:
        """Depth above max should be clamped."""
        depth, nodes, timeout = validate_traversal_bounds(100, 100, 5000)
        assert depth == 10

    def test_clamps_low_depth(self) -> None:
        """Depth below minimum should be clamped to 1."""
        depth, nodes, timeout = validate_traversal_bounds(0, 100, 5000)
        assert depth == 1

    def test_clamps_negative_depth(self) -> None:
        """Negative depth should be clamped to 1."""
        depth, nodes, timeout = validate_traversal_bounds(-5, 100, 5000)
        assert depth == 1

    def test_clamps_high_nodes(self) -> None:
        """Nodes above max should be clamped to 500."""
        depth, nodes, timeout = validate_traversal_bounds(3, 1000, 5000)
        assert nodes == 500

    def test_clamps_low_nodes(self) -> None:
        """Nodes below minimum should be clamped to 1."""
        depth, nodes, timeout = validate_traversal_bounds(3, 0, 5000)
        assert nodes == 1

    def test_clamps_high_timeout(self) -> None:
        """Timeout above max should be clamped to 30000."""
        depth, nodes, timeout = validate_traversal_bounds(3, 100, 999999)
        assert timeout == 30000

    def test_clamps_low_timeout(self) -> None:
        """Timeout below minimum should be clamped to 100."""
        depth, nodes, timeout = validate_traversal_bounds(3, 100, 10)
        assert timeout == 100

    def test_valid_params_unchanged(self) -> None:
        """Valid parameters should pass through unchanged."""
        depth, nodes, timeout = validate_traversal_bounds(5, 200, 10000)
        assert depth == 5
        assert nodes == 200
        assert timeout == 10000

    def test_custom_maximums(self) -> None:
        """Custom max limits should be respected."""
        depth, nodes, timeout = validate_traversal_bounds(
            20,
            1000,
            60000,
            max_max_depth=20,
            max_max_nodes=1000,
            max_timeout_ms=60000,
        )
        assert depth == 20
        assert nodes == 1000
        assert timeout == 60000

    def test_boundary_values(self) -> None:
        """Values at exact boundaries should pass through."""
        depth, nodes, timeout = validate_traversal_bounds(10, 500, 30000)
        assert depth == 10
        assert nodes == 500
        assert timeout == 30000


class TestBuildLineageCypher:
    """Tests for Cypher query generation."""

    def test_default_contains_caused_by(self) -> None:
        """Default lineage query should use CAUSED_BY edge type."""
        cypher = build_lineage_cypher()
        assert "CAUSED_BY" in cypher

    def test_default_contains_params(self) -> None:
        """Default query should contain the default parameter placeholders."""
        cypher = build_lineage_cypher()
        assert "$node_id" in cypher
        assert "$max_depth" in cypher
        assert "$max_nodes" in cypher

    def test_custom_edge_types(self) -> None:
        """Custom edge types should appear in the generated Cypher."""
        cypher = build_lineage_cypher(edge_types=["CAUSED_BY", "FOLLOWS"])
        assert "CAUSED_BY|FOLLOWS" in cypher

    def test_single_custom_edge_type(self) -> None:
        """A single custom edge type should appear without pipes."""
        cypher = build_lineage_cypher(edge_types=["FOLLOWS"])
        assert "FOLLOWS" in cypher
        assert "|" not in cypher

    def test_custom_param_names(self) -> None:
        """Custom parameter names should be used in the query."""
        cypher = build_lineage_cypher(
            node_id_param="$nid",
            max_depth_param="$md",
            max_nodes_param="$mn",
        )
        assert "$nid" in cypher
        assert "$md" in cypher
        assert "$mn" in cypher

    def test_returns_match_query(self) -> None:
        """Generated query should start with MATCH."""
        cypher = build_lineage_cypher()
        assert cypher.startswith("MATCH")

    def test_returns_chain_nodes_and_rels(self) -> None:
        """Generated query should return chain_nodes and chain_rels."""
        cypher = build_lineage_cypher()
        assert "chain_nodes" in cypher
        assert "chain_rels" in cypher


class TestBuildContextCypher:
    """Tests for context assembly Cypher query."""

    def test_contains_session_id_param(self) -> None:
        """Context query should reference $session_id."""
        cypher = build_context_cypher()
        assert "$session_id" in cypher

    def test_contains_limit_param(self) -> None:
        """Context query should reference $limit."""
        cypher = build_context_cypher()
        assert "$limit" in cypher

    def test_orders_by_occurred_at(self) -> None:
        """Context query should order by occurred_at DESC."""
        cypher = build_context_cypher()
        assert "ORDER BY e.occurred_at DESC" in cypher

    def test_returns_event_node(self) -> None:
        """Context query should return the event node."""
        cypher = build_context_cypher()
        assert "RETURN e" in cypher
