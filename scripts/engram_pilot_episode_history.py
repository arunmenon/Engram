"""P06 worker-free history recheck pinned to a retained failed full-flow run."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

from engram_pilot_completion_fixtures import recovery_documents
from engram_pilot_episode_bridge import (
    decode,
    episode,
    public_context_ids,
    verify_public_membership,
    verify_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "results.json",
    "fixtures.json",
    "reproduction-manifest.json",
    "recorded-source-audit.json",
    "a-final-state.json",
    "b-final-state.json",
}


def connected_candidates(group):
    """Independent finite oracle: only frozen-source, temporally connected subsets."""
    from datetime import datetime

    records = [
        s["request"] for s in group["steps"] if s["request"]["session_id"] == group["session"]
    ]
    result = {}
    for size in range(1, len(records) + 1):
        for subset in combinations(records, size):
            stamps = sorted(datetime.fromisoformat(r["occurred_at"]) for r in subset)
            if any(
                (b - a).total_seconds() > 1800 for a, b in zip(stamps, stamps[1:], strict=False)
            ):
                continue
            item = episode(group["session"], subset)
            result[item["id"]] = item
    return result


def pin_proof(directory, root=ROOT):
    relative = directory.resolve().relative_to(root.resolve())
    return dict(
        directory=str(relative),
        sha256={
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in sorted(FILES)
        },
    )


def load_proof(proof, root=ROOT):
    directory = (root / proof["directory"]).resolve()
    if not directory.is_relative_to(root.resolve()) or set(proof["sha256"]) != FILES:
        raise ValueError("History proof must pin exactly the retained run evidence inside checkout")
    docs = {}
    for name, digest in proof["sha256"].items():
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("History proof changed: " + name)
        docs[name] = json.loads(raw)
    r = docs["results.json"]
    audit = docs["recorded-source-audit.json"]
    manifest = docs["reproduction-manifest.json"]
    failed = [c["name"] for c in r["checks"] if not c["passed"]]
    if (
        r["state"] != "failed"
        or r.get("shutdown_errors") != []
        or failed != ["a:bridged public read and Episode context isolation"]
        or not audit.get("all_match")
        or audit["git_revision"] != manifest["git_revision"]
        or len(audit["files"]) != len(manifest["source_sha256"])
        or not all(
            f["matches"]
            and f["expected_sha256"]
            == f["committed_sha256"]
            == manifest["source_sha256"].get(f["path"])
            for f in audit["files"]
        )
    ):
        raise ValueError(
            "Prior run is not the exact retained oracle failure with clean source/shutdown"
        )
    groups = docs["fixtures.json"]["spectrum"]["groups"]
    if {g["tenant"] for g in groups} != {"a", "b"} or len(groups) != 2:
        raise ValueError("History proof must cover both original tenant groups")
    from collections import Counter

    successful = Counter(c["name"] for c in r["checks"] if c["passed"])
    required = {
        "published scheduled Episode snapshots available": 1,
        "actual provider calls returned after cooperative shutdown": 1,
    }
    for t in ("a", "b"):
        for suffix in (
            "final exact ledger append and retained owner",
            "prior graph preserved except approved derived refresh",
            "exact prior Episode membership retained",
            "final zero pending and exactly declared DLQ",
        ):
            required[t + " " + suffix] = 1
        for suffix, count in (
            ("public read and Episode context isolation", 2),
            ("complete public Episode membership history", 2),
            ("exact Episode context", 2),
            ("exact public directed membership", 3),
            ("exact public Summary targets", 3),
            ("exact snapshot source anchor", 6),
            ("exact member source position", 3),
        ):
            required[t + ":published " + suffix] = count
    for g in groups:
        for e in [*g["initial"], g["control"]]:
            for suffix in (
                "Episode identity, complete membership and bounds",
                "exact linked Summary structure",
                "exact CONTAINS",
                "membership method CONTAINS",
                "exact DERIVED_FROM",
                "membership method DERIVED_FROM",
                "Summary exact source and Episode links",
                "exact admitted source positions",
            ):
                required[g["tenant"] + ":published:" + e["id"] + " " + suffix] = 1
    if r.get("finalization_errors", []) or any(
        successful[name] < n for name, n in required.items()
    ):
        raise ValueError("Original named publication/preservation prerequisites missing")
    worker_set = {(w["tenant"], w["type"]) for w in r["workers"]}
    if worker_set != {
        (t, k)
        for t in ("a", "b")
        for k in ("projection", "enrichment", "extraction", "consolidation", "pack_extraction")
    }:
        raise ValueError("Original full-flow worker evidence incomplete")
    phases = r["episode_bridge"]["phases"]
    if [p["phase"] for p in phases] != ["published", "bridged"] or set(phases[0]["tenants"]) != {
        "a",
        "b",
    }:
        raise ValueError("Both initial publication checkpoints are required")
    accepted = {}
    late = {g["steps"][3]["request"]["event_id"] for g in groups}
    late_indices = []
    for i, q in enumerate(r["requests"]):
        if q["path"] != "/v1/events":
            continue
        if q["status"] != 201:
            raise ValueError("Original source was not accepted")
        key = (q["tenant"], q["input"]["event_id"])
        if key in accepted:
            raise ValueError("Duplicate original input receipt")
        accepted[key] = q
        if q["input"]["event_id"] in late:
            late_indices.append(i)
    expected = {(g["tenant"], s["request"]["event_id"]) for g in groups for s in g["steps"]}
    if set(accepted) != expected or len(late_indices) != 2:
        raise ValueError("All eight exact receipts required")
    for g in groups:
        for step in g["steps"]:
            if accepted[g["tenant"], step["request"]["event_id"]]["input"] != step["request"]:
                raise ValueError("Original receipt input differs from frozen source")
        sessions = {g["session"], g["control_session"]}
        published = {
            q["input"].get("session_id")
            for q in r["requests"][: min(late_indices)]
            if q["tenant"] == g["tenant"]
            and q["path"] == "/v1/query/subgraph"
            and q["status"] == 200
        }
        if not sessions <= published:
            raise ValueError("Late source preceded initial public publication")
    return docs, groups, accepted


def validated_inventory(state, group, positions, prior, check):
    candidates = connected_candidates(group)
    control = group["control"]
    candidates[control["id"]] = control
    sessions = {group["session"], group["control_session"]}
    observed = {
        r[1]
        for r in state["nodes"]
        if r[0] == "Episode" and decode(r[2]).get("session_id") in sessions
    }
    mandatory = {e["id"] for e in [*group["initial"], group["merged"], control]}
    check(
        group["name"] + " bounded source-valid history inventory",
        mandatory <= observed <= candidates.keys(),
    )
    selected = {nid: candidates[nid] for nid in sorted(observed)}
    summary_ids = {e["summary"] for e in selected.values()}
    attached = {
        r[1]
        for r in state["nodes"]
        if r[0] == "Summary"
        and decode(r[2]).get("scope") == "episode"
        and decode(r[2]).get("scope_id") in observed
    }
    check(group["name"] + " exact stored episode Summary inventory", attached == summary_ids)
    proofs = {
        nid: verify_snapshot(state, e, positions, check, group["name"] + ":history:" + nid)
        for nid, e in selected.items()
    }
    check(
        group["name"] + " pre-bridge Episode properties/membership preserved",
        all(proofs[e["id"]] == prior[e["id"]] for e in [*group["initial"], control]),
    )
    return selected, proofs


async def execute(plan, *, request, check, record, save, settle):
    if len(plan["groups"]) != 2 or not all(
        g.get("episode_history_retained") for g in plan["groups"]
    ):
        raise ValueError("Retained history requires both tenant groups only")
    proof = plan["groups"][0]["episode_history_proof"]
    if any(g["episode_history_proof"] != proof for g in plan["groups"]):
        raise ValueError("Inconsistent history proofs")
    docs, original, accepted = load_proof(proof)
    selected_groups = {g["tenant"]: g for g in plan["groups"]}
    check(
        "retained history submits no business writes or worker/model work",
        not record["workers"] and not record["provider_calls"],
    )
    states = await settle()
    report = record.setdefault(
        "episode_history_retained", dict(original_verdict="failed", proof=proof, tenants={})
    )
    for group in original:
        t = group["tenant"]
        candidates = connected_candidates(group)
        candidates[group["control"]["id"]] = group["control"]
        check(
            t + " frozen candidate snapshots match original sources",
            selected_groups[t]["candidate_snapshots"]
            == [candidates[k] for k in sorted(candidates)],
        )
        positions = {
            eid: q["output"]["global_position"]
            for (tenant, eid), q in accepted.items()
            if tenant == t
        }
        inputs = [s["request"] for s in group["steps"]]
        frozen_documents = recovery_documents(docs[t + "-final-state.json"]["snapshot"], inputs)
        check(
            t + " original authenticated source documents unchanged",
            recovery_documents(states[t], inputs) == frozen_documents,
        )
        for state in (docs[t + "-final-state.json"]["snapshot"], states[t]):
            documents = recovery_documents(state, inputs)
            check(
                t + " exact original source and admission positions",
                all(d["global_position"] == positions[d["event_id"]] for d in documents),
            )
        prior = docs["results.json"]["episode_bridge"]["phases"][0]["tenants"][t]["storage"]
        final_selection, final_proofs = validated_inventory(
            docs[t + "-final-state.json"]["snapshot"], group, positions, prior, check
        )
        selected, proofs = validated_inventory(states[t], group, positions, prior, check)
        check(
            t + " retained published history unchanged since original shutdown",
            selected == final_selection and proofs == final_proofs,
        )
        entry = dict(storage=proofs, reads=[])
        report["tenants"][t] = entry
        save()
        for control in (False, True):
            session = group["control_session"] if control else group["session"]
            chosen = [e for e in selected.values() if e["session"] == session]
            body = dict(
                query="Show the recorded activity and its membership history",
                intent="when",
                session_id=session,
                agent_id=group["owner"],
                max_nodes=100,
                timeout_ms=30000,
            )
            frozen_body = selected_groups[t]["queries"][int(control)]["request"]
            check(t + " query unchanged from frozen publication question", body == frozen_body)
            code, answer = await request(t, "/v1/query/subgraph", frozen_body)
            entry["reads"].append(dict(control=control, status=code, request=body, response=answer))
            save()
            ep, summaries = public_context_ids(answer)
            check(
                t + " exact public validated history and opposite-session exclusion",
                code == 200
                and not answer.get("meta", {}).get("truncated")
                and ep == {e["id"] for e in chosen}
                and summaries == {e["summary"] for e in chosen},
            )
            verify_public_membership(answer, chosen, check, t + ":retained-history")
            for e in chosen:
                for nid in (e["id"], e["summary"], *e["members"]):
                    source = nid if nid in e["members"] else e["anchor"]
                    p = answer["nodes"][nid].get("provenance") or {}
                    check(
                        t + " exact public original receipt " + nid,
                        p.get("source") == "spanner"
                        and p.get("event_id") == source
                        and p.get("global_position") == positions[source],
                    )
                    if nid in e["members"]:
                        check(
                            t + " member is Event", answer["nodes"][nid].get("node_type") == "Event"
                        )
        entry["state"] = "passed exact source-valid membership history and public evidence"
        save()
    report["state"] = "passed retained-read checkpoint; original full-flow attempt remains failed"
    save()
