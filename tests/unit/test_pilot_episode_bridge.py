"""P06 source-grounded partition, preservation and public-history preflight."""

import copy
import json
from pathlib import Path

import pytest
from engram_pilot_episode_bridge import membership, verify_public_membership, verify_snapshot

ROOT = Path(__file__).parents[2]


def fixture():
    return json.loads((ROOT / "docs/pilot/pilot-p06-1016-01-journeys.json").read_text())


def snapshot(graph):
    return dict(
        nodes=[[label, key, p] for (label, key), p in graph.nodes.items()],
        edges=[[a[0], a[1], kind, b[0], b[1], p] for (a, kind, b), p in graph.edges.items()],
    )


def check(name, passed, actual=None):
    assert passed, (name, actual)


@pytest.mark.parametrize("tenant", ["a", "b"])
async def test_bridge_preserves_published_membership_and_public_history(tenant):
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.consolidation import (
        create_summary_from_events,
        group_events_into_episodes,
    )
    from context_graph.domain.episodes import materialize_episode_snapshot
    from context_graph.domain.models import Event, SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    group = next(g for g in fixture()["groups"] if g["tenant"] == tenant)
    graph = MemoryGraphStore()
    records = []
    positions = {}

    async def admit(step):
        event = Event.model_validate_json(json.dumps(step["request"])).model_copy(
            update={"global_position": f"{len(records) + 1}-0"}
        )
        await graph.merge_event_node(event_to_node(event))
        record = event.model_dump(mode="json")
        records.append(record)
        positions[str(event.event_id)] = event.global_position

    async def materialize(expected):
        selected = [r for r in records if r["event_id"] in expected["members"]]
        summary = create_summary_from_events(selected, "episode", expected["id"])
        assert summary.summary_id == expected["summary"]
        await graph.write_summary_with_edges(
            summary.summary_id,
            summary.scope,
            summary.scope_id,
            summary.content,
            summary.created_at.isoformat(),
            summary.event_count,
            [dt.isoformat() for dt in summary.time_range],
            expected["members"],
        )
        assert (
            await materialize_episode_snapshot(graph, expected["session"], summary, selected)
            == expected["id"]
        )

    for step in group["steps"][:3]:
        await admit(step)
    primary = [r for r in records if r["session_id"] == group["session"]]
    assert [len(part) for part in group_events_into_episodes(primary)] == [1, 1]
    for expected in [*group["initial"], group["control"]]:
        await materialize(expected)
    before = copy.deepcopy(snapshot(graph))
    old = {
        e["id"]: verify_snapshot(before, e, positions, check, "initial")
        for e in [*group["initial"], group["control"]]
    }
    # Both initial snapshots exist before the late Event is admitted.
    assert not any(key == group["merged"]["id"] for (_, key) in graph.nodes)
    await admit(group["steps"][3])
    primary = [r for r in records if r["session_id"] == group["session"]]
    assert [len(part) for part in group_events_into_episodes(primary)] == [3]
    await materialize(group["merged"])
    after = snapshot(graph)
    for e in [*group["initial"], group["control"]]:
        assert verify_snapshot(after, e, positions, check, "preserved") == old[e["id"]]
        assert membership(before, e["id"]) == membership(after, e["id"])
    verify_snapshot(after, group["merged"], positions, check, "merged")
    for control in (False, True):
        answer = (
            await selected_engine(graph).get_subgraph(
                SubgraphQuery(
                    query="Show recorded history",
                    intent="when",
                    session_id=group["control_session"] if control else group["session"],
                    agent_id=group["owner"],
                    max_nodes=100,
                )
            )
        ).model_dump(mode="json")
        chosen = [group["control"]] if control else [*group["initial"], group["merged"]]
        forbidden = [*group["initial"], group["merged"]] if control else [group["control"]]
        assert {e[k] for e in chosen for k in ("id", "summary")} <= answer["nodes"].keys()
        assert not {e[k] for e in forbidden for k in ("id", "summary")} & answer["nodes"].keys()
        assert not answer["meta"]["truncated"]
        verify_public_membership(answer, chosen, check, "public graph")
        for e in chosen:
            for nid in (e["id"], e["summary"]):
                assert answer["nodes"][nid]["provenance"]["event_id"] == e["anchor"]
                assert (
                    answer["nodes"][nid]["provenance"]["global_position"] == positions[e["anchor"]]
                )


def test_bridge_oracle_rejects_extra_member_before_acceptance():
    group = fixture()["groups"][0]
    e = group["merged"]
    state = dict(
        nodes=[
            [
                "Episode",
                e["id"],
                dict(
                    complete=True,
                    snapshot_kind="membership",
                    session_id=e["session"],
                    summary_id=e["summary"],
                    source_event_ids=[*e["members"], "foreign"],
                    event_count=4,
                    start_time=e["start"],
                    end_time=e["end"],
                ),
            ]
        ],
        edges=[],
    )
    with pytest.raises(AssertionError, match="Episode identity"):
        verify_snapshot(state, e, {}, check, "tampered")


@pytest.mark.parametrize(
    "tamper",
    [
        "extra_episode",
        "extra_summary",
        "extra_summary_target",
        "extra_member",
        "missing_summary_link",
    ],
)
def test_public_oracle_rejects_extra_context_and_membership(tamper):
    e = fixture()["groups"][0]["initial"][0]
    answer = dict(
        nodes={
            e["id"]: dict(node_type="Episode", attributes={}),
            e["summary"]: dict(node_type="Summary", attributes=dict(scope="episode")),
        },
        edges=[],
    )
    for kind in ("CONTAINS", "DERIVED_FROM"):
        answer["edges"].extend(
            dict(edge_type=kind, source=e["id"], target=eid) for eid in e["members"]
        )
    answer["edges"].extend(
        dict(edge_type="SUMMARIZES", source=e["summary"], target=target)
        for target in [e["id"], *e["members"]]
    )
    verify_public_membership(answer, [e], check, "valid")
    if tamper == "extra_episode":
        answer["nodes"]["foreign"] = dict(node_type="Episode", attributes={})
    elif tamper == "extra_summary":
        answer["nodes"]["foreign"] = dict(node_type="Summary", attributes=dict(scope="episode"))
    elif tamper == "extra_summary_target":
        answer["edges"].append(dict(edge_type="SUMMARIZES", source=e["summary"], target="foreign"))
    elif tamper == "extra_member":
        answer["edges"].append(dict(edge_type="CONTAINS", source=e["id"], target="foreign"))
    else:
        answer["edges"] = [
            r
            for r in answer["edges"]
            if not (r["source"] == e["summary"] and r["target"] == e["id"])
        ]
    with pytest.raises(AssertionError):
        verify_public_membership(answer, [e], check, "tampered")
