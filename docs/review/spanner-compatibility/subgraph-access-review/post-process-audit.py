"""Read-only fresh-process audit of #61 evidence and retained assessment data."""
import hashlib
import json

from engram_composition_assessment import INSTANCE, PROJECT, ROOT, token
from engram_composition_reuse import TARGET
from engram_experiment_support import durable_json, fingerprint, read_owner, snapshot
from google.cloud import spanner
from google.oauth2.credentials import Credentials

run = ROOT / "docs/review/spanner-compatibility/runs/subgraph-access-1014-01"
manifest = json.loads((run / "manifest.json").read_text())
hashes = json.loads((run / "source-hashes.json").read_text())
changed = [name for name, digest in hashes.items()
           if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
assert not changed


def normalized(state):
    return {key: sorted(json.dumps(row, sort_keys=True) for row in rows)
            for key, rows in state.items()}


counts = {}
for config in manifest["configurations"]:
    record = json.loads((run / (config + ".json")).read_text())
    assert record["state"] == "passed" and not record["shutdown_errors"]
    assert all(check["passed"] for check in record["checks"])
    assert normalized(record["final_snapshot"]) == normalized(record["retained_snapshot"])
    plan = manifest["fixtures"][config]
    ids = {event["event_id"] for event in plan["events"][:3]}
    incoming = [request for request in record["requests"] if request["route"] == "/v1/events"]
    assert [request["input"] for request in incoming] == plan["events"]
    assert all(request["status"] in {200, 201} for request in incoming)
    reads = [request for request in record["requests"] if request["route"] == "/v1/query/subgraph"]
    assert len(reads) == len(record["read_snapshots"])
    event_page = False
    for request, pair in zip(reads, record["read_snapshots"], strict=True):
        assert request["status"] == 200
        returned = request["output"]["nodes"]
        event_ids = {key for key, node in returned.items() if node["node_type"] == "Event"}
        assert event_ids <= ids
        for eid in event_ids:
            provenance = returned[eid]["provenance"]
            assert provenance["event_id"] == eid
            assert provenance["agent_id"] == plan["owner"]
            assert provenance["session_id"] == plan["session"]
        if pair["case"].startswith("AC01"):
            assert event_ids == ids and plan["entity"] in returned
            assert not request["output"]["meta"]["truncated"]
            if config == "pdlc-memory":
                assert plan["episode"] in returned
        if pair["case"].startswith("AC03") and event_ids:
            assert len(returned) == len(event_ids) == 1
            event_page = True
        if pair["case"] == "AC04-empty":
            assert not returned
        from context_graph.adapters.spanner.log import json_value
        before = {(label, key): json_value(props) for label, key, props in pair["before"]["nodes"]}
        after = {(label, key): json_value(props) for label, key, props in pair["after"]["nodes"]}
        assert before.keys() == after.keys()
        for key, props in before.items():
            actual = after[key]
            if key[0] == "Event" and key[1] in event_ids:
                assert actual["access_count"] == props.get("access_count", 0) + 1
                assert actual["last_accessed_at"] >= (props.get("last_accessed_at") or "")
                excluded = {"access_count", "last_accessed_at"}
                assert {k: v for k, v in actual.items() if k not in excluded} == {k: v for k, v in props.items() if k not in excluded}
            else:
                assert actual == props
        assert {k: v for k, v in normalized(pair["before"]).items() if k != "nodes"} == {k: v for k, v in normalized(pair["after"]).items() if k != "nodes"}
    assert event_page
    export = run / (config + "-previous-export.json")
    proof = json.loads(export.with_suffix(".verified.json").read_text())
    assert proof["verified"] and hashlib.sha256(export.read_bytes()).hexdigest() == proof["sha256"]
    counts[config] = len(record["checks"])

retained = json.loads((run / "pdlc-memory-retained.json").read_text())
client = spanner.Client(project=PROJECT, credentials=Credentials(token=token(impersonate=True)))
db = client.instance(INSTANCE).database(TARGET.rsplit("/", 1)[1])
owner, fp, actual = read_owner(db), fingerprint(db), snapshot(db)
assert owner == retained["owner"] and fp == retained["fingerprints"]
assert normalized(actual) == normalized(record["retained_snapshot"])
result = dict(database=TARGET, owner=owner, fingerprints=fp, owner_matches=True,
              fingerprints_match=True, retained_snapshot_matches=True,
              source_hashes_checked=len(hashes), changed_sources=changed,
              assertions=counts, both_exports_verified=True,
              independent_per_read_access_deltas_verified=True)
durable_json(run / "post-process-recheck.json", result)
print(json.dumps({k: v for k, v in result.items() if k not in {"owner", "fingerprints"}}))
