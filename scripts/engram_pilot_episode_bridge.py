"""P06 staged Episode membership proof through normal API/workers, no graph writes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from engram_pilot_completion_fixtures import decoded_snapshot_cell as decode
from engram_pilot_completion_fixtures import p04_negative_proof


def episode(session, records):
    members = sorted(r["event_id"] for r in records)
    identity = (
        "episode-"
        + hashlib.sha256(json.dumps([session, members], separators=(",", ":")).encode()).hexdigest()
    )
    summary = (
        "summary-" + identity + "-" + hashlib.sha256("|".join(members).encode()).hexdigest()[:12]
    )
    stamps = sorted(r["occurred_at"] for r in records)
    return dict(
        id=identity,
        summary=summary,
        session=session,
        members=members,
        start=stamps[0],
        end=stamps[-1],
        anchor=min(records, key=lambda r: (r["occurred_at"], r["event_id"]))["event_id"],
    )


def freeze(run_id):
    start = datetime.now(UTC) - timedelta(minutes=90)
    groups = []
    for tenant in ("a", "b"):
        owner = run_id + ":" + tenant + ":episode-owner"
        primary = run_id + ":" + tenant + ":episode-session"
        control = primary + ":unrelated"
        records = []
        for key, minutes, session in (
            ("first", 0, primary),
            ("later", 40, primary),
            ("control", 0, control),
            ("bridge", 20, primary),
        ):
            records.append(
                dict(
                    event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + tenant + ":" + key)),
                    event_type="observation.input",
                    occurred_at=(start + timedelta(minutes=minutes)).isoformat(),
                    session_id=session,
                    agent_id=owner,
                    trace_id=run_id,
                    payload_ref="pilot-p06:" + key,
                    payload=dict(
                        content=(
                            "The operator recorded rollout progress. "
                            "This is activity history, not a goal completion."
                        )
                    ),
                )
            )
        initial = [episode(primary, [r]) for r in records[:2]]
        groups.append(
            dict(
                name=tenant + "-episode-bridge",
                tenant=tenant,
                episode_bridge=True,
                owner=owner,
                session=primary,
                control_session=control,
                steps=[
                    dict(scenario=key, request=r, expected_status=201)
                    for key, r in zip(("first", "later", "control", "bridge"), records, strict=True)
                ],
                queries=[],
                initial=initial,
                control=episode(control, [records[2]]),
                merged=episode(primary, [records[0], records[1], records[3]]),
                reflection_threshold=5,
                phase_wait_seconds=1200,
                source_kind="Activity at 0/40 minutes; late event at 20 minutes after publication",
            )
        )
    groups[0]["retained_negative_proofs"] = [p04_negative_proof()]
    return dict(
        coverage="P06 Episode bridging and preserved membership history on both tenants",
        groups=groups,
    )


def membership(state, identity):
    return sorted(
        json.dumps(r, sort_keys=True, default=str)
        for r in state["edges"]
        if r[0] == "Episode" and r[1] == identity and r[2] in {"CONTAINS", "DERIVED_FROM"}
    )


def same_bounds(actual, expected):
    try:
        return [datetime.fromisoformat(v) for v in actual] == [
            datetime.fromisoformat(v) for v in expected
        ]
    except (ValueError, TypeError):
        return False


def verify_snapshot(state, expected, positions, check, label):
    nodes = {(r[0], r[1]): decode(r[2]) for r in state["nodes"]}
    props = nodes.get(("Episode", expected["id"]), {})
    summary = nodes.get(("Summary", expected["summary"]), {})
    check(
        label + " Episode identity, complete membership and bounds",
        props.get("complete") is True
        and props.get("snapshot_kind") == "membership"
        and props.get("session_id") == expected["session"]
        and props.get("summary_id") == expected["summary"]
        and props.get("source_event_ids") == expected["members"]
        and props.get("event_count") == len(expected["members"])
        and same_bounds(
            [props.get("start_time"), props.get("end_time")], [expected["start"], expected["end"]]
        ),
    )
    check(
        label + " exact linked Summary structure",
        summary.get("scope") == "episode"
        and summary.get("scope_id") == expected["id"]
        and summary.get("event_count") == len(expected["members"])
        and same_bounds(summary.get("time_range", []), [expected["start"], expected["end"]]),
    )
    for kind in ("CONTAINS", "DERIVED_FROM"):
        actual = {
            (r[3], r[4])
            for r in state["edges"]
            if r[0] == "Episode" and r[1] == expected["id"] and r[2] == kind
        }
        check(label + " exact " + kind, actual == {("Event", eid) for eid in expected["members"]})
        check(
            label + " membership method " + kind,
            all(
                decode(r[5])
                == dict(method="temporal_consolidation", session_id=expected["session"])
                for r in state["edges"]
                if r[0] == "Episode" and r[1] == expected["id"] and r[2] == kind
            ),
        )
    summary_targets = {
        (r[3], r[4])
        for r in state["edges"]
        if r[0] == "Summary" and r[1] == expected["summary"] and r[2] == "SUMMARIZES"
    }
    check(
        label + " Summary exact source and Episode links",
        summary_targets
        == {("Episode", expected["id"]), *(("Event", eid) for eid in expected["members"])},
    )
    check(
        label + " exact admitted source positions",
        all(
            nodes.get(("Event", eid), {}).get("global_position") == positions[eid]
            for eid in expected["members"]
        ),
    )
    return dict(
        properties=props,
        membership=membership(state, expected["id"]),
        summary_structure={
            k: summary[k] for k in ("scope", "scope_id", "event_count", "time_range")
        },
    )


def public_context_ids(answer):
    nodes = answer.get("nodes", {})
    episodes = {nid for nid, n in nodes.items() if n.get("node_type") == "Episode"}
    summaries = {
        nid
        for nid, n in nodes.items()
        if n.get("node_type") == "Summary" and n.get("attributes", {}).get("scope") == "episode"
    }
    return episodes, summaries


def verify_public_membership(answer, chosen, check, label):
    episodes, summaries = public_context_ids(answer)
    check(
        label + " exact Episode context",
        episodes == {e["id"] for e in chosen} and summaries == {e["summary"] for e in chosen},
    )
    edges = {(e["edge_type"], e["source"], e["target"]) for e in answer.get("edges", [])}
    for e in chosen:
        wanted = {
            (kind, e["id"], eid) for kind in ("CONTAINS", "DERIVED_FROM") for eid in e["members"]
        }
        actual = {
            (kind, source, target)
            for kind, source, target in edges
            if source == e["id"] and kind in {"CONTAINS", "DERIVED_FROM"}
        }
        check(label + " exact public directed membership", actual == wanted)
        actual_targets = {
            target
            for kind, source, target in edges
            if source == e["summary"] and kind == "SUMMARIZES"
        }
        check(label + " exact public Summary targets", actual_targets == {e["id"], *e["members"]})


def probe(database, expected):
    from google.cloud.spanner_v1 import KeySet

    keys = [
        [kind, e[k]] for e in expected for kind, k in (("Episode", "id"), ("Summary", "summary"))
    ]
    with database.snapshot() as snap:
        rows = list(snap.read("GraphNodes", ["label", "node_id", "props"], KeySet(keys=keys)))
    nodes = {(r[0], r[1]): decode(r[2]) for r in rows}
    return all(
        nodes.get(("Episode", e["id"]), {}).get("complete") is True
        and ("Summary", e["summary"]) in nodes
        for e in expected
    )


async def execute(plan, *, request, check, databases, record, save, settle):
    groups = plan["groups"]
    if not groups or not all(g.get("episode_bridge") for g in groups):
        raise ValueError("Episode bridge execution cannot mix other group types")
    positions = {}
    report = record.setdefault(
        "episode_bridge",
        dict(
            phases=[],
            scope="Episode membership/context isolation; general Event recall separately observed",
        ),
    )
    initial = await settle()
    for g in groups:
        t = g["tenant"]
        check(
            t + " frozen session importance qualifies for consolidation",
            record["settings"][t]["reflection_threshold"] == g["reflection_threshold"]
            and g["reflection_threshold"] <= 5,
        )
        sessions = {g["session"], g["control_session"]}
        check(
            t + " fresh primary/control sessions",
            not any(decode(r[1]).get("session_id") in sessions for r in initial[t]["events"]),
        )
        ids = {e[k] for e in [*g["initial"], g["control"], g["merged"]] for k in ("id", "summary")}
        check(
            t + " fresh Episode/Summary identities", not ids & {r[1] for r in initial[t]["nodes"]}
        )
    previous = {}
    for phase in ("published", "bridged"):
        entry = dict(phase=phase, inputs=[], tenants={})
        report["phases"].append(entry)
        save()
        for g in groups:
            steps = g["steps"][:3] if phase == "published" else g["steps"][3:]
            for step in steps:
                code, answer = await request(g["tenant"], "/v1/events", step["request"])
                check(g["name"] + ":" + step["scenario"] + " admission", code == 201)
                positions[step["request"]["event_id"]] = answer["global_position"]
                entry["inputs"].append(
                    dict(
                        tenant=g["tenant"],
                        event_id=step["request"]["event_id"],
                        position=answer["global_position"],
                    )
                )
                save()
        await settle()
        deadline = time.monotonic() + min(g["phase_wait_seconds"] for g in groups)
        while True:
            ready = await asyncio.gather(
                *(
                    asyncio.to_thread(
                        probe,
                        databases[g["tenant"]],
                        [
                            *g["initial"],
                            g["control"],
                            *([g["merged"]] if phase == "bridged" else []),
                        ],
                    )
                    for g in groups
                )
            )
            entry["materialization_polls"] = entry.get("materialization_polls", 0) + 1
            if entry["materialization_polls"] % 10 == 0:
                save()
            if all(ready):
                states = await settle()
                coherent = True
                for g in groups:
                    nodes = {(r[0], r[1]): decode(r[2]) for r in states[g["tenant"]]["nodes"]}
                    expected = [
                        *g["initial"],
                        g["control"],
                        *([g["merged"]] if phase == "bridged" else []),
                    ]
                    coherent = coherent and all(
                        nodes.get(("Episode", e["id"]), {}).get("complete") is True
                        and ("Summary", e["summary"]) in nodes
                        for e in expected
                    )
                if coherent:
                    break
            if time.monotonic() >= deadline:
                check(phase + " scheduled Episode snapshots available", False, ready)
            await asyncio.sleep(1)
        check(phase + " scheduled Episode snapshots available", True)
        for g in groups:
            t = g["tenant"]
            expected = [*g["initial"], g["control"], *([g["merged"]] if phase == "bridged" else [])]
            proofs = {
                e["id"]: verify_snapshot(
                    states[t], e, positions, check, t + ":" + phase + ":" + e["id"]
                )
                for e in expected
            }
            if phase == "bridged":
                check(
                    t + " both earlier Episode properties and membership exactly preserved",
                    all(
                        proofs[e["id"]] == previous[t][e["id"]]
                        for e in [*g["initial"], g["control"]]
                    ),
                )
            previous[t] = proofs
            entry["tenants"][t] = dict(storage=proofs, reads=[])
            save()
            for control in (False, True):
                chosen = (
                    [g["control"]]
                    if control
                    else [*g["initial"], *([g["merged"]] if phase == "bridged" else [])]
                )
                forbidden = [*g["initial"], g["merged"]] if control else [g["control"]]
                body = dict(
                    query="Show the recorded activity and its membership history",
                    intent="when",
                    session_id=g["control_session"] if control else g["session"],
                    agent_id=g["owner"],
                    max_nodes=100,
                    timeout_ms=30000,
                )
                required = {e[k] for e in chosen for k in ("id", "summary")} | {
                    eid for e in chosen for eid in e["members"]
                }
                excluded = {e[k] for e in forbidden for k in ("id", "summary")}
                read_deadline = deadline
                while True:
                    code, answer = await request(t, "/v1/query/subgraph", body)
                    entry["tenants"][t]["reads"].append(
                        dict(control=control, status=code, response=answer)
                    )
                    save()
                    actual_episodes, actual_summaries = public_context_ids(answer)
                    check(
                        t + ":" + phase + " public read and Episode context isolation",
                        code == 200
                        and not excluded & answer.get("nodes", {}).keys()
                        and actual_episodes <= {e["id"] for e in chosen}
                        and actual_summaries <= {e["summary"] for e in chosen},
                    )
                    if required <= answer["nodes"].keys() and not answer.get("meta", {}).get(
                        "truncated"
                    ):
                        break
                    if time.monotonic() >= read_deadline:
                        check(t + ":" + phase + " public Episode convergence", False)
                    await asyncio.sleep(1)
                check(t + ":" + phase + " complete public Episode membership history", True)
                verify_public_membership(answer, chosen, check, t + ":" + phase)
                for e in chosen:
                    for nid in (e["id"], e["summary"]):
                        provenance = answer["nodes"][nid].get("provenance") or {}
                        check(
                            t + ":" + phase + " exact snapshot source anchor",
                            provenance.get("source") == "spanner"
                            and provenance.get("event_id") == e["anchor"]
                            and provenance.get("global_position") == positions[e["anchor"]],
                        )
                    for eid in e["members"]:
                        provenance = answer["nodes"][eid].get("provenance") or {}
                        check(
                            t + ":" + phase + " exact member source position",
                            answer["nodes"][eid].get("node_type") == "Event"
                            and provenance.get("event_id") == eid
                            and provenance.get("source") == "spanner"
                            and provenance.get("global_position") == positions[eid],
                        )
                entry["tenants"][t].setdefault("general_event_recall_diagnostics", []).append(
                    dict(
                        control=control,
                        unrelated_source_present=any(
                            eid in answer["nodes"] for e in forbidden for eid in e["members"]
                        ),
                    )
                )
                save()
    report["state"] = "passed staged membership and published-history checks"
    save()
