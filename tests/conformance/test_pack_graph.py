"""PackGraph conformance (ADR-0018 decision 7): same writes in, same answers out.

Runs on every graph backend (memory always; Neo4j and the Spanner
emulator as ``integration``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite, StateChange
from tests.fixtures.events import make_event

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend

CHANGE = NodeRef("Change", "Change:acme/app|7")
ITEM = NodeRef("WorkItem", "WorkItem:jira|PAY-1")
OTHER_ITEM = NodeRef("WorkItem", "WorkItem:jira|PAY-2")


def _change(**props: object) -> NodeWrite:
    return NodeWrite(
        CHANGE,
        {"node_type": "Change", "repo": "acme/app", "number": 7, **props},
        defaults={"status": "open"},
    )


class TestNodes:
    async def test_upsert_sets_key_defaults_on_create_and_keeps_values(
        self, graph: GraphBackend
    ) -> None:
        await graph.upsert_nodes([_change(title="first", files=["a.py", "b.py"])])
        await graph.upsert_nodes([_change(title=None, merge_sha="abc")])
        await graph.upsert_nodes([NodeWrite(CHANGE, {}, defaults={"status": "ignored"})])

        node = (await graph.get_nodes([CHANGE]))[CHANGE]
        assert node["node_id"] == CHANGE.key
        assert node["status"] == "open"
        assert node["title"] == "first"  # None does not erase
        assert node["merge_sha"] == "abc"
        assert node["files"] == ["a.py", "b.py"]

    async def test_get_and_find(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes(
            [
                NodeWrite(ITEM, {"tracker": "jira", "work_type": "story"}),
                NodeWrite(OTHER_ITEM, {"tracker": "jira", "work_type": "bug"}),
            ]
        )
        assert set(await graph.get_nodes([ITEM, CHANGE])) == {ITEM}
        bugs = await graph.find_nodes("WorkItem", {"tracker": "jira", "work_type": "bug"}, 10)
        assert [node["node_id"] for node in bugs] == [OTHER_ITEM.key]
        assert len(await graph.find_nodes("WorkItem", {}, 10)) == 2
        assert len(await graph.find_nodes("WorkItem", {}, 1)) == 1
        assert await graph.find_nodes("Incident", {}, 10) == []


class TestEdges:
    async def test_merge_once_and_skip_missing_endpoints(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {})])
        implements = EdgeWrite(
            "IMPLEMENTS", CHANGE, ITEM, {"confidence": 1.0, "method": "declared"}
        )

        assert await graph.upsert_edges([implements]) == 1
        assert await graph.upsert_edges([implements]) == 1
        assert await graph.upsert_edges([EdgeWrite("IMPLEMENTS", CHANGE, OTHER_ITEM)]) == 0

        rows = await graph.neighbors([CHANGE], None, "out", 10)
        assert len(rows) == 1
        assert rows[0]["edge_type"] == "IMPLEMENTS"
        assert rows[0]["properties"] == {"confidence": 1.0, "method": "declared"}
        assert (rows[0]["target_label"], rows[0]["target_key"]) == ("WorkItem", ITEM.key)
        assert rows[0]["node"]["node_id"] == ITEM.key

    async def test_edges_reach_todays_types_by_their_own_key(self, graph: GraphBackend) -> None:
        event = make_event(global_position="1-0")
        await graph.merge_event_node(_event_node(event))
        event_ref = NodeRef("Event", str(event.event_id), "event_id")
        await graph.upsert_nodes([_change()])

        assert await graph.upsert_edges([EdgeWrite("DERIVED_FROM", CHANGE, event_ref)]) == 1
        (row,) = await graph.neighbors([event_ref], ["DERIVED_FROM"], "in", 10)
        assert (row["source_label"], row["source_key"]) == ("Change", CHANGE.key)
        assert (row["target_label"], row["target_key"]) == ("Event", str(event.event_id))
        assert row["node_label"] == "Change"

    async def test_neighbors_direction_types_order_and_limit(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {}), NodeWrite(OTHER_ITEM, {})])
        await graph.upsert_edges(
            [
                EdgeWrite("IMPLEMENTS", CHANGE, OTHER_ITEM),
                EdgeWrite("IMPLEMENTS", CHANGE, ITEM),
                EdgeWrite("DEPENDS_ON", ITEM, OTHER_ITEM),
            ]
        )
        out = await graph.neighbors([CHANGE], None, "out", 10)
        assert [r["target_key"] for r in out] == [ITEM.key, OTHER_ITEM.key]
        both = await graph.neighbors([ITEM], None, "both", 10)
        assert [(r["edge_type"], r["node_label"]) for r in both] == [
            ("DEPENDS_ON", "WorkItem"),
            ("IMPLEMENTS", "Change"),
        ]
        assert await graph.neighbors([ITEM], ["REVIEWS"], "both", 10) == []
        assert len(await graph.neighbors([CHANGE], None, "out", 1)) == 1


class TestStates:
    async def test_transitions_respect_only_from_and_current_state(
        self, graph: GraphBackend
    ) -> None:
        await graph.upsert_nodes([_change()])
        reviewed = StateChange(CHANGE, "reviewed", "2026-10-04T10:00:00Z", only_from=("open",))
        merged = StateChange(CHANGE, "merged", "2026-10-04T11:00:00Z")

        assert await graph.change_states([reviewed, merged, reviewed]) == 2
        node = (await graph.get_nodes([CHANGE]))[CHANGE]
        assert node["status"] == "merged"
        assert node["status_changed_at"] == "2026-10-04T11:00:00Z"
        assert await graph.change_states([merged]) == 0  # already there
        assert await graph.change_states([StateChange(ITEM, "done", "x")]) == 0  # missing


def _event_node(event: object) -> object:
    from context_graph.domain.projection import event_to_node

    return event_to_node(event)  # type: ignore[arg-type]
