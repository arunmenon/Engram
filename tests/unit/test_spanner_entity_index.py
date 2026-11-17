"""Independent legacy upgrade, native ANN and coexistence budget checks (#44)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.spanner.commits import CommitBudget, CommitTooLarge, node_row_cost
from context_graph.adapters.spanner.entity_index import (
    ENTITY_INDEX_DDL,
    MEMBERSHIP_DDL,
    EntityIndexUpgradeError,
    plan_entity_index_upgrade,
)
from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.schema import SchemaMismatchError, open_database
from context_graph.settings import SpannerSettings

# Frozen independently of the target schema constructor.
LEGACY_NODES = """CREATE TABLE GraphNodes (
    label STRING(64) NOT NULL,
    node_id STRING(MAX) NOT NULL,
    props JSON NOT NULL,
    session_id STRING(MAX) AS (JSON_VALUE(props, '$.session_id')) STORED,
    embedding ARRAY<FLOAT64>(vector_length=>3)
) PRIMARY KEY (label, node_id)"""
LEGACY_INDEX = (
    "CREATE VECTOR INDEX GraphNodesByEmbedding ON GraphNodes (embedding) "
    "WHERE embedding IS NOT NULL OPTIONS (distance_type = 'COSINE')"
)


def legacy_database():
    database = MagicMock()
    database.ddl_statements = [LEGACY_NODES, LEGACY_INDEX]
    database.list_database_operations.return_value = []
    return database


def add_membership(database):
    database.ddl_statements[0] = LEGACY_NODES.replace(
        "embedding ARRAY<FLOAT64>(vector_length=>3)",
        f"embedding ARRAY<FLOAT64>(vector_length=>3), {MEMBERSHIP_DDL}",
    )


def test_independent_legacy_plan_preserves_data_and_old_index():
    database = legacy_database()
    before = list(database.ddl_statements)
    assert plan_entity_index_upgrade(database, 3) == [
        f"ALTER TABLE GraphNodes ADD COLUMN {MEMBERSHIP_DDL}",
        ENTITY_INDEX_DDL,
    ]
    assert database.ddl_statements == before
    database.update_ddl.assert_not_called()


def test_partial_and_complete_upgrade_plans():
    database = legacy_database()
    add_membership(database)
    assert plan_entity_index_upgrade(database, 3) == [ENTITY_INDEX_DDL]
    database.ddl_statements.append(ENTITY_INDEX_DDL)
    assert plan_entity_index_upgrade(database, 3) == []


def test_incompatible_state_never_dropped_or_rewritten():
    database = legacy_database()
    with pytest.raises(EntityIndexUpgradeError, match="dimensions"):
        plan_entity_index_upgrade(database, 4)
    add_membership(database)
    database.ddl_statements[0] = database.ddl_statements[0].replace("TRUE, NULL", "TRUE, FALSE")
    with pytest.raises(EntityIndexUpgradeError, match="membership"):
        plan_entity_index_upgrade(database, 3)
    database = legacy_database()
    database.ddl_statements.append(
        "CREATE INDEX GraphEntitiesByEmbeddingV1 ON GraphNodes (embedding)"
    )
    with pytest.raises(EntityIndexUpgradeError, match="index"):
        plan_entity_index_upgrade(database, 3)


def test_legacy_startup_rejects_without_any_repair_ddl():
    database = legacy_database()
    database.exists.return_value = True
    client = MagicMock()
    client.instance.return_value.database.return_value = database
    with (
        patch("google.cloud.spanner.Client", return_value=client),
        patch(
            "context_graph.adapters.spanner.schema.schema_differences",
            return_value=["Entity-only index missing"],
        ),
        pytest.raises(SchemaMismatchError, match="Entity-only index missing"),
    ):
        open_database(SpannerSettings(project="p", instance="i", database="d", check_schema=True))
    database.update_ddl.assert_not_called()
    database.create.assert_not_called()


async def test_native_ann_filters_before_top_k_and_checks_canonical_identity():
    graph = SpannerGraphStore(MagicMock(), embedding_dimensions=3)
    graph._query = AsyncMock(
        return_value=[
            ("good", {"entity_id": "good", "name": "Good"}, 0.2),
            ("other", {"entity_id": "wrong"}, 0),
            ("missing", {}, 0),
            ("number", {"entity_id": 1}, 0),
            ("", {"entity_id": ""}, 0),
            ("low", {"entity_id": "low"}, 1.5),
        ]
    )
    assert await graph.search_similar_entities([1, 0, 0], 2) == [
        {"entity_id": "good", "name": "Good", "entity_type": None, "score": 0.9}
    ]
    sql, params, _types = graph._query.await_args.args
    assert "FORCE_INDEX=GraphEntitiesByEmbeddingV1" in sql
    assert "embedding IS NOT NULL AND entity_embedding_member IS NOT NULL" in sql
    assert sql.index("entity_embedding_member IS NOT NULL") < sql.index("LIMIT @top_k")
    assert params["top_k"] == 2


def test_coexistence_budgets_and_old_vector_removal_are_not_free():
    props = {"entity_id": "e", "embedding": [1.0] * 1000}
    mutations, size = node_row_cost(("Entity", "e"), props, props["embedding"])
    assert mutations >= 17 * 2
    assert size > 3 * 8 * 1000  # three physical vectors plus independent JSON/keys
    assert len(CommitBudget(max_mutations=40).chunks([1, 2], lambda _: (mutations, size))) == 2
    graph = SpannerGraphStore(
        MagicMock(), embedding_dimensions=1000, commit_budget=CommitBudget(max_bytes=20_000)
    )
    key = ("Entity", "e")
    with pytest.raises(CommitTooLarge):
        graph._node_rows({key: {"entity_id": "e"}}, [key], True, {key: props})


async def test_actual_physical_old_vectors_split_property_update_and_removal_commits():
    # Imported physical vectors can differ from or be absent in JSON props.
    transaction = MagicMock()
    stored = [["Entity", key, {"entity_id": key}, [1.0] * 1000] for key in ("a", "b")]

    def read(table, columns, keyset):
        assert columns == ["label", "node_id", "props", "embedding"]
        return [row for row in stored if row[:2] in keyset.keys]

    transaction.read.side_effect = read
    graph = SpannerGraphStore(
        MagicMock(), embedding_dimensions=1000, commit_budget=CommitBudget(max_bytes=30_000)
    )
    graph._transact = AsyncMock(side_effect=lambda work: work(transaction))
    await graph._upsert_nodes(
        [
            (("Entity", "a"), {"name": "updated"}),
            (("Entity", "b"), {"embedding": None}),
        ]
    )
    # Combined old physical-index cost exceeds budget; each key is retried
    # in its own transaction and the failed large transaction writes nothing.
    assert graph._transact.await_count == 3
    assert transaction.insert_or_update.call_count == 2
    assert all(len(call.args[2]) == 1 for call in transaction.insert_or_update.call_args_list)
