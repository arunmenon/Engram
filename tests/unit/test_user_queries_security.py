"""Tests for H7 fix: Cypher injection prevention in DERIVED_FROM queries."""

from __future__ import annotations

import pytest

from context_graph.adapters.neo4j.user_queries import (
    _DERIVED_FROM_SOURCE_TYPES,
    _build_derived_from_query,
)


class TestBuildDerivedFromQuery:
    """Test the allowlist-based query builder."""

    def test_preference_id_returns_valid_cypher(self) -> None:
        query = _build_derived_from_query("preference_id")
        assert "source:Preference" in query
        assert "preference_id: $source_id" in query
        assert "DERIVED_FROM" in query

    def test_skill_id_returns_valid_cypher(self) -> None:
        query = _build_derived_from_query("skill_id")
        assert "source:Skill" in query
        assert "skill_id: $source_id" in query

    def test_pattern_id_returns_valid_cypher(self) -> None:
        query = _build_derived_from_query("pattern_id")
        assert "source:BehavioralPattern" in query

    def test_workflow_id_returns_valid_cypher(self) -> None:
        query = _build_derived_from_query("workflow_id")
        assert "source:Workflow" in query

    def test_unknown_field_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown source_id_field"):
            _build_derived_from_query("malicious_field")

    def test_injection_attempt_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown source_id_field"):
            _build_derived_from_query("x}) DETACH DELETE (n) //")

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown source_id_field"):
            _build_derived_from_query("")

    def test_all_allowlist_entries_produce_valid_queries(self) -> None:
        for field_name in _DERIVED_FROM_SOURCE_TYPES:
            query = _build_derived_from_query(field_name)
            assert "$source_id" in query
            assert "DERIVED_FROM" in query
