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


class TestSearch:
    async def test_terms_in_text_and_list_fields(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes(
            [
                _change(title="Fix refund retry", files=["refund/retry.py", "README.md"]),
                NodeWrite(
                    NodeRef("Change", "Change:acme/app|8"),
                    {"title": "Refund logs", "files": ["logs.py"], "number": 8},
                ),
                NodeWrite(NodeRef("Change", "Change:acme/app|9"), {"title": "Other", "number": 9}),
            ]
        )
        found = await graph.search_nodes("Change", ["title", "files"], ["refund", "retry.py"], 10)
        assert [(props["node_id"], hits) for props, hits in found] == [
            (CHANGE.key, 2),
            ("Change:acme/app|8", 1),
        ]
        assert len(await graph.search_nodes("Change", ["title"], ["refund"], 1)) == 1
        assert await graph.search_nodes("Change", ["title"], ["absent"], 10) == []
        assert await graph.search_nodes("Change", [], ["refund"], 10) == []


class TestReviewFindings:
    """Backend differences found in the phase 1 review (ADR-0018 notes)."""

    async def test_neighbors_reports_the_target_when_both_ends_are_asked(
        self, graph: GraphBackend
    ) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {})])
        await graph.upsert_edges([EdgeWrite("IMPLEMENTS", CHANGE, ITEM)])
        for refs in ([ITEM, CHANGE], [CHANGE, ITEM]):
            (row,) = await graph.neighbors(refs, None, "both", 10)
            assert row["node_label"] == "WorkItem"

    async def test_nested_values_are_json_text_everywhere(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(meta={"a": 1}, files=["x"])])
        node = (await graph.get_nodes([CHANGE]))[CHANGE]
        assert node["meta"] == '{"a":1}'
        assert node["files"] == ["x"]

    async def test_repeated_edge_writes_each_count(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {})])
        edge = EdgeWrite("IMPLEMENTS", CHANGE, ITEM)
        assert await graph.upsert_edges([edge, edge]) == 2
        assert len(await graph.neighbors([CHANGE], None, "out", 10)) == 1

    async def test_find_nodes_is_ordered_by_key(self, graph: GraphBackend) -> None:
        refs = [NodeRef("Deployment", f"Deployment:{name}") for name in ("c", "a", "b")]
        await graph.upsert_nodes([NodeWrite(ref, {"environment": "prod"}) for ref in refs])
        found = await graph.find_nodes("Deployment", {"environment": "prod"}, 2)
        assert [n["node_id"] for n in found] == ["Deployment:a", "Deployment:b"]


class TestFindLatest:
    """to_latest is ordered in the backend, before any limit (review 3.2 and N2)."""

    async def _deployments(self, graph: GraphBackend) -> None:
        # Key order (z, a, m, b) differs from start order
        starts = {
            "z": "2026-10-01T10:00:00+00:00",
            "a": "2026-10-03T10:00:00+00:00",
            "m": "2026-10-02T10:00:00+00:00",
            "b": "2026-10-04T10:00:00+00:00",
        }
        writes = [
            NodeWrite(
                NodeRef("Deployment", f"Deployment:{name}"),
                {"environment": "prod", "artifact_id": "app:1", "started_at": started},
            )
            for name, started in starts.items()
        ]
        writes.append(
            NodeWrite(
                NodeRef("Deployment", "Deployment:staging"),
                {
                    "environment": "staging",
                    "artifact_id": "app:1",
                    "started_at": "2026-10-05T10:00:00+00:00",
                },
            )
        )
        writes.append(
            NodeWrite(
                NodeRef("Deployment", "Deployment:undated"),
                {"environment": "prod", "artifact_id": "app:1"},
            )
        )
        await graph.upsert_nodes(writes)

    async def test_the_latest_match(self, graph: GraphBackend) -> None:
        await self._deployments(graph)
        prod = {"environment": "prod", "artifact_id": "app:1"}
        latest = await graph.find_latest("Deployment", prod, "started_at", None)
        assert latest is not None
        assert latest["node_id"] == "Deployment:b"
        assert (
            await graph.find_latest("Deployment", {"environment": "dev"}, "started_at", None)
            is None
        )

    async def test_not_after_a_moment(self, graph: GraphBackend) -> None:
        await self._deployments(graph)
        prod = {"environment": "prod", "artifact_id": "app:1"}
        before = await graph.find_latest(
            "Deployment", prod, "started_at", "2026-10-03T12:00:00+00:00"
        )
        assert before is not None
        assert before["node_id"] == "Deployment:a"
        exactly = await graph.find_latest(
            "Deployment", prod, "started_at", "2026-10-02T10:00:00+00:00"
        )
        assert exactly is not None
        assert exactly["node_id"] == "Deployment:m"  # the bound is inclusive
        assert (
            await graph.find_latest("Deployment", prod, "started_at", "2026-09-30T00:00:00+00:00")
            is None
        )


class TestFindNodesMatching:
    """Many lookups of one type in one call, as a projection flush makes them (review 3.1)."""

    async def test_each_condition_answers_like_find_nodes(self, graph: GraphBackend) -> None:
        refs = {
            name: NodeRef("Deployment", f"Deployment:{name}") for name in ("c", "a", "b", "other")
        }
        await graph.upsert_nodes(
            [
                NodeWrite(refs["c"], {"repo": "acme/app", "artifact_id": "s1"}),
                NodeWrite(refs["a"], {"repo": "acme/app", "artifact_id": "s1"}),
                NodeWrite(refs["b"], {"repo": "acme/app", "artifact_id": "s2"}),
                NodeWrite(refs["other"], {"repo": "acme/other", "artifact_id": "s1"}),
            ]
        )
        conditions = [
            {"repo": "acme/app", "artifact_id": "s1"},
            {"repo": "acme/app", "artifact_id": "none"},
            {"repo": "acme/app", "artifact_id": "s2"},
        ]
        answers = await graph.find_nodes_matching("Deployment", conditions, 10)
        assert [[n["node_id"] for n in answer] for answer in answers] == [
            ["Deployment:a", "Deployment:c"],
            [],
            ["Deployment:b"],
        ]
        for condition, answer in zip(conditions, answers, strict=True):
            assert answer == await graph.find_nodes("Deployment", condition, 10)
        limited = await graph.find_nodes_matching("Deployment", conditions[:1], 1)
        assert [n["node_id"] for n in limited[0]] == ["Deployment:a"]
        assert await graph.find_nodes_matching("Deployment", [], 10) == []


class TestCreateOnlyEdges:
    """Phase 3 review: a proposal never changes an existing link (ADR-0018 notes)."""

    async def test_existing_edge_is_left_as_it_is(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {})])
        declared = {"link_status": "confirmed", "confidence": 1.0}
        await graph.upsert_edges([EdgeWrite("IMPLEMENTS", CHANGE, ITEM, declared)])
        proposed = {"link_status": "proposed", "confidence": 0.5}
        await graph.upsert_edges(
            [EdgeWrite("IMPLEMENTS", CHANGE, ITEM, proposed, create_only=True)]
        )
        (row,) = await graph.neighbors([CHANGE], ["IMPLEMENTS"], "out", 10)
        assert row["properties"]["link_status"] == "confirmed"
        assert row["properties"]["confidence"] == 1.0

    async def test_new_edge_is_created(self, graph: GraphBackend) -> None:
        await graph.upsert_nodes([_change(), NodeWrite(ITEM, {})])
        proposed = {"link_status": "proposed", "confidence": 0.5}
        written = await graph.upsert_edges(
            [EdgeWrite("IMPLEMENTS", CHANGE, ITEM, proposed, create_only=True)]
        )
        assert written == 1
        (row,) = await graph.neighbors([CHANGE], ["IMPLEMENTS"], "out", 10)
        assert row["properties"]["link_status"] == "proposed"
