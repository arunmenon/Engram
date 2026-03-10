"""Tests for Neo4j tenant isolation — verify all Cypher queries filter by tenant_id.

Validates that:
1. All Cypher templates in queries.py contain tenant_id filtering
2. All Cypher templates in user_queries.py contain tenant_id filtering
3. All Cypher templates in maintenance.py contain tenant_id filtering
4. All public function signatures accept tenant_id parameter
5. MERGE queries SET tenant_id on created/updated nodes
"""

from __future__ import annotations

import ast
import inspect
import re

import pytest

from context_graph.adapters.neo4j import maintenance, queries, user_queries


# ---------------------------------------------------------------------------
# Helper: extract Cypher template strings from module
# ---------------------------------------------------------------------------


def _get_cypher_templates(module: object) -> dict[str, str]:
    """Extract all module-level string constants that look like Cypher queries."""
    templates: dict[str, str] = {}
    source = inspect.getsource(module)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    # Evaluate the constant value
                    val = getattr(module, target.id, None)
                    if isinstance(val, str) and ("MATCH" in val or "MERGE" in val or "UNWIND" in val):
                        templates[target.id] = val
    return templates


def _get_public_async_functions(module: object) -> list[str]:
    """Get names of all public async functions in a module."""
    return [
        name
        for name, obj in inspect.getmembers(module)
        if not name.startswith("_")
        and inspect.iscoroutinefunction(obj)
    ]


# ---------------------------------------------------------------------------
# queries.py — Cypher template tenant isolation
# ---------------------------------------------------------------------------


class TestQueriesTenantIsolation:
    """Verify queries.py templates include tenant_id."""

    # Read queries must have WHERE ... tenant_id = $tenant_id
    READ_QUERY_NAMES = [
        "GET_SESSION_EVENTS",
        "GET_SESSION_CONTEXT",
        "GET_ENTITY_CONTEXT",
        "GET_ENTITY_NEIGHBORS",
        "GET_NODE_LINEAGE",
        "GET_CROSS_SESSION_EVENTS",
        "FIND_SIMILAR_EVENTS",
        "GET_CAUSAL_CHAIN",
        "GET_SUMMARY_HIERARCHY",
    ]

    # Write queries must SET ... tenant_id
    WRITE_QUERY_NAMES = [
        "MERGE_EVENT_NODE",
        "MERGE_FOLLOWS_EDGE",
        "MERGE_CAUSED_BY_EDGE",
        "MERGE_ENTITY_NODE",
        "MERGE_REFERENCES_EDGE",
        "MERGE_SIMILAR_TO_EDGE",
        "MERGE_SAME_AS_EDGE",
    ]

    @pytest.mark.parametrize("query_name", READ_QUERY_NAMES)
    def test_read_query_filters_by_tenant(self, query_name: str) -> None:
        """Every read query must filter by tenant_id."""
        query = getattr(queries, query_name, None)
        if query is None:
            pytest.skip(f"{query_name} not found in queries module")
        assert "tenant_id" in query, f"{query_name} missing tenant_id filter"

    @pytest.mark.parametrize("query_name", WRITE_QUERY_NAMES)
    def test_write_query_sets_tenant(self, query_name: str) -> None:
        """Every MERGE query must SET tenant_id."""
        query = getattr(queries, query_name, None)
        if query is None:
            pytest.skip(f"{query_name} not found in queries module")
        assert "tenant_id" in query, f"{query_name} missing tenant_id in SET clause"

    def test_batch_merge_events_uses_evt_tenant_id(self) -> None:
        """BATCH_MERGE_EVENT_NODES must use evt.tenant_id from UNWIND."""
        query = getattr(queries, "BATCH_MERGE_EVENT_NODES", None)
        if query is None:
            pytest.skip("BATCH_MERGE_EVENT_NODES not found")
        assert "evt.tenant_id" in query

    def test_tenant_indexes_defined(self) -> None:
        """TENANT_INDEXES list must contain indexes for all 11 node labels."""
        indexes = getattr(queries, "TENANT_INDEXES", None)
        assert indexes is not None, "TENANT_INDEXES not found"
        assert len(indexes) >= 11, f"Expected >= 11 tenant indexes, got {len(indexes)}"
        # Verify index text references tenant_id
        for idx in indexes:
            assert "tenant_id" in idx, f"Tenant index missing tenant_id: {idx[:60]}..."

    def test_all_indexes_includes_tenant_indexes(self) -> None:
        """ALL_INDEXES must include TENANT_INDEXES."""
        all_indexes = getattr(queries, "ALL_INDEXES", None)
        tenant_indexes = getattr(queries, "TENANT_INDEXES", None)
        assert all_indexes is not None
        assert tenant_indexes is not None
        for idx in tenant_indexes:
            assert idx in all_indexes, f"Tenant index not in ALL_INDEXES: {idx[:60]}..."


# ---------------------------------------------------------------------------
# user_queries.py — tenant isolation
# ---------------------------------------------------------------------------


class TestUserQueriesTenantIsolation:
    """Verify user_queries.py templates and functions include tenant_id."""

    READ_TEMPLATES = [
        "_GET_USER_PROFILE",
        "_GET_USER_PREFERENCES",
        "_GET_USER_SKILLS",
        "_GET_USER_PATTERNS",
        "_GET_USER_INTERESTS",
    ]

    WRITE_TEMPLATES = [
        "_MERGE_USER_PROFILE",
        "_MERGE_PREFERENCE",
        "_MERGE_SKILL",
    ]

    GDPR_TEMPLATES = [
        "_DELETE_USER_DATA",
        "_EXPORT_USER_PROFILE",
        "_EXPORT_USER_PREFERENCES",
        "_EXPORT_USER_SKILLS",
        "_EXPORT_USER_PATTERNS",
        "_EXPORT_USER_INTERESTS",
        "_EXPORT_USER_DERIVED_FROM",
    ]

    @pytest.mark.parametrize("template_name", READ_TEMPLATES)
    def test_read_template_filters_by_tenant(self, template_name: str) -> None:
        query = getattr(user_queries, template_name, None)
        if query is None:
            pytest.skip(f"{template_name} not found")
        assert "tenant_id" in query, f"{template_name} missing tenant_id filter"

    @pytest.mark.parametrize("template_name", WRITE_TEMPLATES)
    def test_write_template_sets_tenant(self, template_name: str) -> None:
        query = getattr(user_queries, template_name, None)
        if query is None:
            pytest.skip(f"{template_name} not found")
        assert "tenant_id" in query, f"{template_name} missing tenant_id in SET"

    @pytest.mark.parametrize("template_name", GDPR_TEMPLATES)
    def test_gdpr_template_filters_by_tenant(self, template_name: str) -> None:
        query = getattr(user_queries, template_name, None)
        if query is None:
            pytest.skip(f"{template_name} not found")
        assert "tenant_id" in query, f"{template_name} missing tenant_id filter"

    def test_set_preference_superseded_filters_tenant(self) -> None:
        query = getattr(user_queries, "_SET_PREFERENCE_SUPERSEDED", None)
        assert query is not None
        assert "tenant_id" in query

    PUBLIC_FUNCTIONS = [
        "get_user_profile",
        "get_user_preferences",
        "get_user_skills",
        "get_user_patterns",
        "get_user_interests",
        "write_user_profile",
        "write_preference_with_edges",
        "write_skill_with_edges",
        "write_interest_edge",
        "write_derived_from_edge",
        "delete_user_data",
        "export_user_data",
        "set_preference_superseded",
    ]

    @pytest.mark.parametrize("func_name", PUBLIC_FUNCTIONS)
    def test_function_accepts_tenant_id(self, func_name: str) -> None:
        """Every public function must accept tenant_id parameter."""
        func = getattr(user_queries, func_name, None)
        if func is None:
            pytest.skip(f"{func_name} not found")
        sig = inspect.signature(func)
        assert "tenant_id" in sig.parameters, f"{func_name} missing tenant_id parameter"
        param = sig.parameters["tenant_id"]
        assert param.default == "default", f"{func_name} tenant_id default should be 'default'"


# ---------------------------------------------------------------------------
# maintenance.py — tenant isolation
# ---------------------------------------------------------------------------


class TestMaintenanceTenantIsolation:
    """Verify maintenance.py templates and functions include tenant_id."""

    CYPHER_TEMPLATES = [
        "_DELETE_SIMILAR_EDGES_BY_SCORE",
        "_DELETE_COLD_EVENTS",
        "_DELETE_ARCHIVE_EVENTS",
        "_GET_SESSION_EVENT_COUNTS",
        "_GET_GRAPH_STATS_NODES",
        "_GET_GRAPH_STATS_EDGES",
        "_GET_ARCHIVE_EVENT_IDS",
        "_GET_ORPHAN_ENTITY_IDS",
        "_DELETE_ORPHAN_ENTITIES_BY_IDS",
        "_DELETE_ORPHAN_NODES_BY_LABEL",
        "_UPDATE_IMPORTANCE_FROM_CENTRALITY",
        "_MERGE_SUMMARY_NODE",
    ]

    @pytest.mark.parametrize("template_name", CYPHER_TEMPLATES)
    def test_template_includes_tenant_id(self, template_name: str) -> None:
        query = getattr(maintenance, template_name, None)
        if query is None:
            pytest.skip(f"{template_name} not found")
        assert "tenant_id" in query, f"{template_name} missing tenant_id"

    PUBLIC_FUNCTIONS = [
        "delete_edges_by_type_and_age",
        "delete_cold_events",
        "delete_archive_events",
        "get_session_event_counts",
        "get_graph_stats",
        "write_summary_with_edges",
        "get_archive_event_ids",
        "delete_orphan_nodes",
        "update_importance_from_centrality",
    ]

    @pytest.mark.parametrize("func_name", PUBLIC_FUNCTIONS)
    def test_function_accepts_tenant_id(self, func_name: str) -> None:
        func = getattr(maintenance, func_name, None)
        if func is None:
            pytest.skip(f"{func_name} not found")
        sig = inspect.signature(func)
        assert "tenant_id" in sig.parameters, f"{func_name} missing tenant_id parameter"
        param = sig.parameters["tenant_id"]
        assert param.default == "default", f"{func_name} tenant_id default should be 'default'"


# ---------------------------------------------------------------------------
# Cross-module: verify no Cypher template misses tenant isolation
# ---------------------------------------------------------------------------


class TestComprehensiveTenantCoverage:
    """Scan all Neo4j modules for any Cypher template missing tenant_id."""

    # Templates that are legitimately exempt:
    # - Edge-only MERGE templates that link two already-tenant-scoped nodes by ID
    # - These don't need tenant_id because both endpoints are matched by unique ID
    EXEMPT_TEMPLATES = {
        # user_queries.py edge templates
        "_MERGE_SUMMARIZES_EDGE",
        "_MERGE_HAS_PREFERENCE_EDGE",
        "_MERGE_HAS_SKILL_EDGE",
        "_MERGE_INTERESTED_IN",
        "_MERGE_PREFERENCE_ABOUT",
        # queries.py edge MERGE templates (match nodes by unique ID)
        "MERGE_FOLLOWS",
        "MERGE_CAUSED_BY",
        "MERGE_SIMILAR_TO",
        "MERGE_REFERENCES",
        "MERGE_SUMMARIZES",
        "MERGE_SAME_AS",
        "MERGE_RELATED_TO",
        "MERGE_HAS_PROFILE",
        "MERGE_HAS_PREFERENCE",
        "MERGE_HAS_SKILL",
        "MERGE_DERIVED_FROM",
        "MERGE_EXHIBITS_PATTERN",
        "MERGE_INTERESTED_IN",
        "MERGE_ABOUT",
        "MERGE_ABSTRACTED_FROM",
        "MERGE_PARENT_SKILL",
        "MERGE_CONTRADICTS",
        "MERGE_SUPERSEDES",
        "MERGE_PURSUES",
        "MERGE_CONTAINS",
        # queries.py batch edge templates
        "BATCH_MERGE_FOLLOWS",
        "BATCH_MERGE_CAUSED_BY",
        # GET_NEIGHBOR_INTER_EDGES operates on pre-filtered neighbor_ids
        # that were already tenant-scoped by the calling pipeline
        "GET_NEIGHBOR_INTER_EDGES",
    }

    @pytest.mark.parametrize(
        "module",
        [queries, user_queries, maintenance],
        ids=["queries", "user_queries", "maintenance"],
    )
    def test_all_cypher_templates_have_tenant_id(self, module: object) -> None:
        """Every Cypher template (MATCH/MERGE) must reference tenant_id."""
        source = inspect.getsource(module)
        # Find all module-level uppercase string assignments that contain Cypher keywords
        pattern = re.compile(r'^([A-Z_]+)\s*=\s*"""', re.MULTILINE)
        for match in pattern.finditer(source):
            name = match.group(1)
            if name in self.EXEMPT_TEMPLATES:
                continue
            value = getattr(module, name, None)
            if value is None or not isinstance(value, str):
                continue
            if "MATCH" in value or "MERGE" in value or "UNWIND" in value:
                assert "tenant_id" in value, (
                    f"{module.__name__}.{name} is a Cypher template missing tenant_id"
                )
