"""Explicit removals preserve legacy None behavior; no service or cloud calls."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.neo4j.pack_graph import Neo4jPackGraph
from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.log import json_value
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite

REF = NodeRef("Sample", "Sample:west|7")
OTHER = NodeRef("Sample", "Sample:west|8")


def backends():
    return [MemoryGraphStore(), SpannerGraphStore(MagicMock()), Neo4jPackGraph()]


@pytest.mark.asyncio
async def test_clear_and_set_preserve_legacy_null_and_create_defaults():
    graph = MemoryGraphStore()
    await graph.upsert_nodes([NodeWrite(REF, {"description": "old", "reading": 1})])
    await graph.upsert_nodes([NodeWrite(REF, {"description": None, "reading": 2})])
    assert (await graph.get_nodes([REF]))[REF]["description"] == "old"
    await graph.upsert_nodes([NodeWrite(REF, {"reading": 3}, remove_properties=("description",))])
    assert (await graph.get_nodes([REF]))[REF] == {"node_id": REF.key, "reading": 3}
    await graph.upsert_nodes(
        [NodeWrite(OTHER, defaults={"description": "default"}, remove_properties=("description",))]
    )
    assert (await graph.get_nodes([OTHER]))[OTHER] == {"node_id": OTHER.key}
    await graph.upsert_nodes([NodeWrite(OTHER, remove_properties=("absent",))])
    assert (await graph.get_nodes([OTHER]))[OTHER] == {"node_id": OTHER.key}


@pytest.mark.asyncio
async def test_edge_removal_keeps_identity_and_missing_endpoint_semantics():
    graph = MemoryGraphStore()
    await graph.upsert_nodes([NodeWrite(REF), NodeWrite(OTHER)])
    await graph.upsert_edges([EdgeWrite("OBSERVED", REF, OTHER, {"label": "old", "score": 1})])
    await graph.upsert_edges([EdgeWrite("OBSERVED", REF, OTHER, {"label": None})])
    assert next(iter(graph.edges.values()))["label"] == "old"
    await graph.upsert_edges(
        [EdgeWrite("OBSERVED", REF, OTHER, {"score": 2}, remove_properties=("label",))]
    )
    assert next(iter(graph.edges.values())) == {"score": 2}
    assert (
        await graph.upsert_edges(
            [EdgeWrite("OBSERVED", REF, NodeRef("Sample", "missing"), remove_properties=("label",))]
        )
        == 0
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "removed",
    [
        ("node_id",),
        ("updated_at",),
        ("source_trust",),
        ("status",),
        ("label", "label"),
        ("bad-name",),
    ],
)
async def test_invalid_late_node_write_refuses_whole_batch_before_io(removed):
    for graph in backends():
        graph._merge_nodes = AsyncMock()
        if isinstance(graph, Neo4jPackGraph):
            graph._pack_write = AsyncMock()
        with pytest.raises(ValueError):
            await graph.upsert_nodes(
                [NodeWrite(REF, {"reading": 1}), NodeWrite(OTHER, remove_properties=removed)]
            )
        graph._merge_nodes.assert_not_called()
        if isinstance(graph, Neo4jPackGraph):
            graph._pack_write.assert_not_called()


@pytest.mark.asyncio
async def test_set_remove_overlap_and_non_tuple_refuse_before_io():
    for graph in backends():
        graph._merge_nodes = AsyncMock()
        if isinstance(graph, Neo4jPackGraph):
            graph._pack_write = AsyncMock()
        for write in [
            NodeWrite(REF, {"label": None}, remove_properties=("label",)),
            NodeWrite(REF, remove_properties=["label"]),
        ]:
            with pytest.raises(ValueError):
                await graph.upsert_nodes([write])
        graph._merge_nodes.assert_not_called()
        if isinstance(graph, Neo4jPackGraph):
            graph._pack_write.assert_not_called()


@pytest.mark.asyncio
async def test_create_only_removal_refuses_whole_edge_batch_before_any_io():
    for graph in backends():
        graph._get_nodes = AsyncMock(side_effect=AssertionError("unexpected read"))
        graph._pack_write = AsyncMock(side_effect=AssertionError("unexpected write"))
        graph._upsert_edges = AsyncMock(side_effect=AssertionError("unexpected write"))
        with pytest.raises(ValueError, match="create_only"):
            await graph.upsert_edges(
                [
                    EdgeWrite("OBSERVED", REF, OTHER, {"score": 1}),
                    EdgeWrite(
                        "OBSERVED", REF, OTHER, create_only=True, remove_properties=("label",)
                    ),
                ]
            )
        graph._get_nodes.assert_not_called()
        graph._pack_write.assert_not_called()
        graph._upsert_edges.assert_not_called()


@pytest.mark.asyncio
async def test_neo4j_explicit_null_map_survives_legacy_filter_without_query_interpolation():
    graph = Neo4jPackGraph()
    graph._pack_write = AsyncMock(return_value=[1])
    await graph.upsert_nodes(
        [NodeWrite(REF, {"reading": 2, "legacy_null": None}, remove_properties=("description",))]
    )
    statement, params = graph._pack_write.call_args.args[0][0]
    assert "description" not in statement
    assert params["rows"][0]["props"] == {"reading": 2, "description": None}
    await graph.upsert_edges(
        [EdgeWrite("OBSERVED", REF, OTHER, {"score": 2}, remove_properties=("label",))]
    )
    statement, params = graph._pack_write.call_args.args[0][0]
    assert "SET r += row.props" in statement
    assert params["rows"][0]["props"] == {"score": 2, "label": None}


@pytest.mark.asyncio
async def test_spanner_actual_merge_transaction_sets_and_removes_together():
    graph = SpannerGraphStore(MagicMock())
    transaction = MagicMock()
    transaction.read.return_value = [
        ["Sample", REF.key, {"node_id": REF.key, "description": "old", "reading": 1}, None]
    ]

    async def write_in_commits(groups, estimate, write):
        items = [item for group in groups for item in group]
        write(items, True)(transaction)
        return []

    graph._write_in_commits = write_in_commits
    await graph.upsert_nodes([NodeWrite(REF, {"reading": 2}, remove_properties=("description",))])
    transaction.read.assert_called_once()
    transaction.insert_or_update.assert_called_once()
    table, columns, rows = transaction.insert_or_update.call_args.args
    assert table == "GraphNodes"
    assert json_value(rows[0][columns.index("props")]) == {"node_id": REF.key, "reading": 2}


@pytest.mark.asyncio
async def test_spanner_same_edge_set_clear_set_is_one_ordered_transaction():
    graph = SpannerGraphStore(MagicMock())
    graph._get_nodes = AsyncMock(
        return_value={
            ("Sample", REF.key): {"node_id": REF.key},
            ("Sample", OTHER.key): {"node_id": OTHER.key},
        }
    )
    transaction = MagicMock()

    def read(table, columns, keys):
        if table == "GraphNodes":
            return [["Sample", REF.key], ["Sample", OTHER.key]]
        assert table == "GraphEdges"
        return [["Sample", REF.key, "OBSERVED", "Sample", OTHER.key, {"label": "old", "score": 1}]]

    transaction.read.side_effect = read

    async def write_in_commits(groups, estimate, write):
        return [write([item for group in groups for item in group], True)(transaction)]

    graph._write_in_commits = write_in_commits
    await graph.upsert_edges(
        [
            EdgeWrite("OBSERVED", REF, OTHER, {"score": 2}, remove_properties=("label",)),
            EdgeWrite("OBSERVED", REF, OTHER, {"score": 3}),
        ]
    )
    transaction.insert_or_update.assert_called_once()
    table, columns, rows = transaction.insert_or_update.call_args.args
    assert table == "GraphEdges"
    assert json_value(rows[0][columns.index("props")]) == {"score": 3}
