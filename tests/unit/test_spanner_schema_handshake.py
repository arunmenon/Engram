"""Physical schema compatibility must be checked before serving ANN (#23)."""

from unittest.mock import MagicMock

import pytest

from context_graph.adapters.spanner.entity_index import (
    ENTITY_VECTOR_INDEX,
    MEMBERSHIP_DDL,
)
from context_graph.adapters.spanner.schema import (
    expected_schema,
    schema_differences,
    schema_statements,
)


def database_fixture(dimensions=384, vector_index=True, index_state="READ_WRITE"):
    database = MagicMock()
    physical = schema_statements(dimensions)
    if not vector_index:
        physical = [
            f"CREATE INDEX {ENTITY_VECTOR_INDEX} ON GraphNodes (embedding)"
            if s.startswith("CREATE VECTOR INDEX")
            else s
            for s in physical
        ]
    database.ddl_statements = physical
    expected = expected_schema(384)
    snapshot = database.snapshot.return_value.__enter__.return_value

    def query(sql):
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return [
                (key[6:], column)
                for key, cols in expected.items()
                if key.startswith("table:")
                for column in cols
            ]
        if "INFORMATION_SCHEMA.INDEXES" in sql:
            if "INDEX_STATE" in sql:
                return [(name, index_state) for name in expected["indexes"]]
            return [(name,) for name in expected["indexes"]]
        if "PROPERTY_GRAPHS" in sql:
            return [("EngramGraph",)]
        raise AssertionError(sql)

    snapshot.execute_sql.side_effect = query
    return database


def test_matching_physical_schema_is_accepted():
    assert schema_differences(database_fixture(), 384) == []


def test_existing_vector_dimension_mismatch_is_refused():
    differences = schema_differences(database_fixture(), 3)
    assert any(
        "vector length" in error and "384" in error and "3" in error for error in differences
    )


def test_same_named_nonvector_index_is_refused():
    assert any(
        "vector index" in error
        for error in schema_differences(database_fixture(vector_index=False), 384)
    )


def test_not_ready_index_is_refused():
    assert any(
        "READ_WRITE" in error
        for error in schema_differences(database_fixture(index_state="WRITE_ONLY"), 384)
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (MEMBERSHIP_DDL, "entity_embedding_member BOOL"),
        ("IF(label = 'Entity', TRUE, NULL)", "TRUE"),
        ("'Entity'", "'entity'"),
        ("TRUE, NULL", "TRUE, FALSE"),
        ("BOOL AS", "BOOL NOT NULL AS"),
        (" AND ", " OR "),
        ("STORING (entity_embedding_member)", ""),
        ("AND entity_embedding_member IS NOT NULL", ""),
        ("ON GraphNodes (embedding)", "ON GraphNodes (session_id)"),
        ("distance_type = 'COSINE'", "distance_type = 'EUCLIDEAN'"),
    ],
)
def test_schema_refuses_broadened_or_incompatible_entity_index(old, new):
    database = database_fixture()
    database.ddl_statements = [s.replace(old, new) for s in database.ddl_statements]
    assert schema_differences(database, 384)


def test_quoted_parenthesized_equivalent_definitions_and_legacy_extra_accepted():
    database = database_fixture()
    database.ddl_statements = [
        s.replace(
            "IF(label = 'Entity', TRUE, NULL)", "(IF((`label` = 'Entity'), TRUE, NULL))"
        ).replace(
            "embedding IS NOT NULL AND entity_embedding_member IS NOT NULL",
            "(entity_embedding_member IS NOT NULL) AND (embedding IS NOT NULL)",
        )
        for s in database.ddl_statements
    ] + [
        "CREATE VECTOR INDEX GraphNodesByEmbedding ON GraphNodes (embedding) "
        "WHERE embedding IS NOT NULL OPTIONS (distance_type = 'COSINE')"
    ]
    assert schema_differences(database, 384) == []
