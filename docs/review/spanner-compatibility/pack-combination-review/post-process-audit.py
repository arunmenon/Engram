"""Independent fresh-process read-only audit of frozen combination evidence."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from engram_composition_assessment import INSTANCE, PROJECT, ROOT, token
from engram_composition_reuse import TARGET
from engram_experiment_support import durable_json, fingerprint, read_owner, snapshot
from google.cloud import spanner
from google.oauth2.credentials import Credentials
from context_graph.adapters.spanner.log import json_value

run = ROOT / "docs/review/spanner-compatibility/runs/pack-combination-1014-02"
manifest = json.loads((run / "manifest.json").read_text())
hashes = json.loads((run / "source-hashes.json").read_text())
changed = [name for name, digest in hashes.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
assert not changed
assert manifest["configurations"] == ["core", "user", "user-memory", "pdlc", "pdlc-memory"]


def normalized(value):
    return {key: sorted(json.dumps(row, sort_keys=True) for row in rows) for key, rows in value.items()}


results = {}
for config in manifest["configurations"]:
    plan = manifest["fixtures"][config]
    record = json.loads((run / (config + ".json")).read_text())
    assert record["state"] == "passed" and not record["shutdown_errors"]
    assert all(check["passed"] for check in record["checks"])
    assert record["fixtures"] == plan
    assert normalized(record["final_snapshot"]) == normalized(record["retained_snapshot"])
    state = record["retained_snapshot"]
    nodes = {(label, key): json_value(props) for label, key, props in state["nodes"]}
    edges = {tuple(row[:5]) for row in state["edges"]}
    events = {plan["events"][key]["event_id"]: plan["events"][key] for key in plan["accepted"]}
    assert {row[0] for row in state["events"]} == set(events)
    assert {key for label, key in nodes if label == "Event"} == set(events)
    assert not state["pending"] and not state["dead_letters"]
    for eid, source in events.items():
        props = nodes[("Event", eid)]
        assert all(props[field] == source[field] for field in ["event_id", "event_type", "occurred_at", "agent_id", "session_id", "trace_id"])
        assert props["keywords"] == source["event_type"].split(".")
    def sources(label, key, kind="DERIVED_FROM"):
        return {edge[4] for edge in edges if edge[:4] == (label, key, kind, "Event")}
    ids = plan["ids"]
    expected_references = {plan["events"][key]["event_id"] for key in plan["accepted"][:5]}
    actual_references = {edge[1] for edge in edges if edge[0] == "Event" and edge[2:] == ("REFERENCES", "Entity", ids["entity"])}
    assert actual_references == expected_references
    if plan["user"]:
        assert {key for label, key in nodes if label == "UserProfile"} == {ids["profile"]}
        assert {key for label, key in nodes if label == "Preference"} == {ids["positive"], ids["negative"]}
        for polarity, source_key in [("positive", "preference"), ("negative", "correction")]:
            props = nodes[("Preference", ids[polarity])]
            assert props["observation_count"] == 1
            assert props["support_event_ids"] == [plan["events"][source_key]["event_id"]]
        assert sources("Preference", ids["negative"]) == {plan["events"]["correction"]["event_id"]}
        assert ("Preference", ids["negative"], "SUPERSEDES", "Preference", ids["positive"]) in edges
    else:
        assert not any(label in {"UserProfile", "Preference", "Skill"} for label, key in nodes)
        assert not any("user_extraction_receipt" in props for props in nodes.values())
    if plan["memory"]:
        for label, key, names in [("Belief", "belief", ["belief", "confirmation"]), ("Goal", "goal", ["goal", "completion"])]:
            assert {nid for family, nid in nodes if family == label} == {ids[key]}
            props = nodes[(label, ids[key])]
            assert props["state_revision"] == 1 and props["complete"]
            assert sources(label, ids[key]) == {plan["events"][name]["event_id"] for name in names}
        assert nodes[("Belief", ids["belief"])]["confirmation_count"] == 2
        assert nodes[("Goal", ids["goal"])]["status"] == "completed"
        for kind, keys in [("user", plan["accepted"][:5])] + ([("pdlc", ["pr", "merge"])] if plan["pdlc"] else []):
            identity = ids[kind + "_episode"]
            members = {plan["events"][key]["event_id"] for key in keys}
            props = nodes[("Episode", identity)]
            assert props["complete"] and set(props["source_event_ids"]) == members
            assert sources("Episode", identity) == sources("Episode", identity, "CONTAINS") == members
            summary = nodes[("Summary", props["summary_id"])]
            assert summary["scope"] == "episode" and summary["scope_id"] == identity
            assert summary["event_count"] == len(members)
            assert sources("Summary", props["summary_id"], "SUMMARIZES") == members
    else:
        assert not any(label in {"Belief", "Goal", "Episode"} for label, key in nodes)
    if plan["pdlc"]:
        assert {key for label, key in nodes if label == "Change"} == {ids["change"], ids["unrelated"]}
        assert {key for label, key in nodes if label == "Decision"} == {ids["decision"]}
        assert nodes[("Change", ids["change"])]["status"] == "merged"
        assert sources("Change", ids["change"]) == {plan["events"][key]["event_id"] for key in ["pr", "merge"]}
        assert sources("Decision", ids["decision"]) == {plan["events"]["preference"]["event_id"]}
    else:
        assert not any(label in {"Change", "Decision"} for label, key in nodes)
    for request in record["requests"]:
        if request["status"] == 200 and request["route"].startswith("/v1/query/"):
            answer = request["output"]
            assert "user_extraction_receipt" not in json.dumps(answer)
            for node_id, node in answer.get("nodes", {}).items():
                if node["node_type"] == "Event":
                    provenance = node["provenance"]
                    assert node_id in events
                    assert all(provenance[field] == events[node_id][field] for field in ["event_id", "agent_id", "session_id", "trace_id"])
    export = run / (config + "-previous-export.json")
    proof = json.loads(export.with_suffix(".verified.json").read_text())
    assert proof["verified"] and hashlib.sha256(export.read_bytes()).hexdigest() == proof["sha256"]
    retained = json.loads((run / (config + "-retained.json")).read_text())
    results[config] = dict(assertions=len(record["checks"]), accepted=len(events), epoch=retained["owner"][0][3], nodes=len(nodes), edges=len(edges))

client = spanner.Client(project=PROJECT, credentials=Credentials(token=token(impersonate=True)))
db = client.instance(INSTANCE).database(TARGET.rsplit("/", 1)[1])
owner, fp, actual = read_owner(db), fingerprint(db), snapshot(db)
assert owner == retained["owner"] and fp == retained["fingerprints"]
assert normalized(actual) == normalized(state)
result = dict(database=TARGET, owner=owner, fingerprints=fp, results=results,
              source_hashes_checked=len(hashes), changed_sources=changed,
              all_exports_verified=True, independent_graph_and_sources_verified=True,
              owner_matches=True, fingerprints_match=True, retained_snapshot_matches=True)
durable_json(run / "post-process-recheck.json", result)
print(json.dumps({key:value for key,value in result.items() if key not in {"owner", "fingerprints"}}))
