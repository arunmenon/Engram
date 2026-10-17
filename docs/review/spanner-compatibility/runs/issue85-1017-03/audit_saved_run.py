import hashlib, json, subprocess
from pathlib import Path

root = Path.cwd()
p = root / "docs/review/spanner-compatibility/runs/issue85-1017-03"
plan = json.loads((root / "docs/pilot/issue85-1017-03-journeys.json").read_text())
r = json.loads((p / "results.json").read_text())
assert r["state"] == "passed-selected-journeys", r.get("error")
assert all(c["passed"] for c in r["checks"])
assert r["shutdown_errors"] == [] and r["final_worker_lags"] == [0] * 5
assert all(c["state"] == "returned" for c in r["provider_calls"])
g = plan["groups"][0]
old = g["steps"][1]["expected_node"]
new = g["steps"][3]["expected_node"]
approval = g["steps"][2]["expected_node"]
queries = []
for q in g["queries"]:
    matches = [
        x
        for x in r["requests"]
        if x["path"] == "/v1/query/artifacts"
        and x["input"].get("query") == q["text"]
        and x["input"].get("intent") == q["intent"]
        and x["input"].get("seed_node_ids", []) == q["seeds"]
    ]
    assert len(matches) == 1, (q["scenario"], len(matches))
    x = matches[0]
    assert x["status"] == 200
    a = x["output"]
    nodes = a["nodes"]
    meta = a["meta"]
    edges = {(e["source"], e["edge_type"], e["target"]) for e in a["edges"]}
    omitted = {(e["source"], e["edge_type"], e["target"]) for e in meta["excluded_edges"]}
    assert not meta["truncated"]
    if q["scenario"] in ["given-old-trace", "status-old", "why-old", "keyword-free-old"]:
        assert nodes[old]["retrieval_reason"] == "superseded" and old not in meta["excluded_nodes"]
    else:
        assert old not in nodes and meta["excluded_nodes"][old] == "superseded"
    if q["scenario"] in ["given-new-trace", "requirement-trace", "word-trace"]:
        assert approval not in nodes and meta["excluded_nodes"][approval] == "filtered_path"
        assert (approval, "APPROVES", old) in omitted
    if approval in nodes:
        assert (approval, "APPROVES", old) in edges or (approval, "APPROVES", old) in omitted
    assert (approval, "APPROVES", new) not in edges
    assert all(e["source"] in nodes and e["target"] in nodes for e in a["edges"])
    queries.append(
        dict(
            scenario=q["scenario"],
            status=x["status"],
            old_version_present=old in nodes,
            approval_present=approval in nodes,
            excluded_nodes=meta["excluded_nodes"],
            excluded_edges=meta["excluded_edges"],
            no_v2_approval=True,
        )
    )
created = [
    x
    for x in r["requests"]
    if x["path"] == "/v1/events" and x["status"] == 201 and x["output"]["status"] == "created"
]
assert len(created) == 4
m = json.loads((p / "reproduction-manifest.json").read_text())
rows = []
for name, sha in m["source_sha256"].items():
    actual = hashlib.sha256(
        subprocess.check_output(["git", "show", m["git_revision"] + ":" + name])
    ).hexdigest()
    assert actual == sha, name
    rows.append(dict(path=name, sha256=sha, matches=True))
(p / "recorded-source-audit.json").write_text(
    json.dumps(
        dict(git_revision=m["git_revision"], all_match=True, checks=len(rows), files=rows), indent=2
    )
    + "\n"
)
(p / "approval-exclusion-audit.json").write_text(
    json.dumps(
        dict(
            queries=queries,
            source_revision=m["git_revision"],
            created=4,
            final_checks=len(r["checks"]),
            provider_calls=len(r["provider_calls"]),
        ),
        indent=2,
    )
    + "\n"
)
print(
    dict(
        state=r["state"],
        checks=len(r["checks"]),
        requests=len(r["requests"]),
        provider_calls=len(r["provider_calls"]),
        source_hashes=len(rows),
        exact_query_audits=len(queries),
    )
)
