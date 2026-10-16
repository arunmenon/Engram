"""P09 identical identities and refused routing probes through public HTTP."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from engram_experiment_support import read_owner
from engram_memory_actions_demo import identity
from engram_pilot_completion_fixtures import decoded_snapshot_cell as decode
from engram_pilot_completion_fixtures import p04_negative_proof
from engram_pilot_retrieval_proof import closed_response


def freeze(run_id):
    owner, session = run_id + ":same-owner", run_id + ":same-session"
    event_id = str(uuid5(NAMESPACE_URL, run_id + ":collision"))
    goal = identity("Goal", owner, "session", session, "delivery")
    occurred = (datetime.now(UTC) - timedelta(minutes=3)).isoformat()
    groups = []
    for t, text in [
        ("a", "Prepare the user research workshop"),
        ("b", "Prepare the payment settlement release"),
    ]:
        request = dict(
            event_id=event_id,
            event_type="memory.goal.created",
            occurred_at=occurred,
            session_id=session,
            agent_id=owner,
            trace_id=run_id,
            payload_ref="pilot-p09:collision",
            payload=dict(key="delivery", description=text),
        )
        groups.append(
            dict(
                name="p09-" + t,
                tenant=t,
                tenant_proof=True,
                steps=[dict(scenario="collision", expected_status=201, request=request)],
                queries=[],
                goal=goal,
                text=text,
                retained_negative_proofs=[p04_negative_proof()] if t == "a" else [],
            )
        )
    foreign = deepcopy(groups[1]["steps"][0])
    foreign["scenario"] = "foreign-only"
    foreign["request"]["event_id"] = str(uuid5(NAMESPACE_URL, run_id + ":foreign"))
    foreign["request"]["payload"] = dict(
        key="foreign", description="Only Tenant B has this reconciliation follow-up"
    )
    groups[1]["steps"].append(foreign)
    groups[1]["foreign"] = identity("Goal", owner, "session", session, "foreign")
    return dict(
        run_id=run_id,
        coverage=(
            "P09 public two-tenant collision, authenticated binding, roles and refused probes; "
            "no internal hierarchy policy"
        ),
        groups=groups,
    )


def memory_read_request(group):
    source = group["steps"][0]["request"]
    return dict(
        query="Inspect this explicit Memory state",
        intent="when",
        session_id=source["session_id"],
        agent_id=source["agent_id"],
        max_nodes=50,
        timeout_ms=30000,
    )


def retained_state_preserved(before, after):
    """Exact business/authority state and old derived structure; allow approved refresh only."""

    def normalized_nodes(state):
        result = {}
        for label, nid, raw in state["nodes"]:
            props = decode(raw).copy()
            for key in {
                "Event": {"importance_score", "access_count", "last_accessed_at"},
                "Entity": {"last_seen", "mention_count"},
                "Summary": {"content", "created_at"},
            }.get(label, set()):
                props.pop(key, None)
            result[(label, nid)] = props
        return result

    old, new = normalized_nodes(before), normalized_nodes(after)
    if not all(new.get(key) == value for key, value in old.items()):
        return False
    if {key for key in old if key[0] not in {"Episode", "Summary"}} != {
        key for key in new if key[0] not in {"Episode", "Summary"}
    }:
        return False

    def edge_map(state):
        return {
            tuple(r[:5]): {
                k: v
                for k, v in decode(r[5]).items()
                if not (r[0] == "Summary" and r[2] == "SUMMARIZES" and k == "created_at")
            }
            for r in state["edges"]
        }

    oe, ne = edge_map(before), edge_map(after)
    if not all(ne.get(key) == value for key, value in oe.items()):
        return False
    if {
        k: v
        for k, v in oe.items()
        if k[0] not in {"Summary", "Episode"} and k[3] not in {"Summary", "Episode"}
    } != {
        k: v
        for k, v in ne.items()
        if k[0] not in {"Summary", "Episode"} and k[3] not in {"Summary", "Episode"}
    }:
        return False
    old_episodes = {key[1] for key in old if key[0] == "Episode"}
    if {k: v for k, v in oe.items() if k[0] == "Episode" and k[1] in old_episodes} != {
        k: v for k, v in ne.items() if k[0] == "Episode" and k[1] in old_episodes
    }:
        return False
    old_summaries = {key[1] for key in old if key[0] == "Summary"}
    if {k: v for k, v in oe.items() if k[0] == "Summary" and k[1] in old_summaries} != {
        k: v for k, v in ne.items() if k[0] == "Summary" and k[1] in old_summaries
    }:
        return False
    for key in ("events", "pending", "dead_letters", "dead_letter_fields"):
        if sorted(json.dumps(r, sort_keys=True, default=str) for r in before[key]) != sorted(
            json.dumps(r, sort_keys=True, default=str) for r in after[key]
        ):
            return False
    return before["owner"] == after["owner"]


async def execute(plan, *, request, check, record, save, settle, databases, evidence_directory):
    a, b = plan["groups"]
    entries = record.setdefault("tenant_proof", [])
    receipts = {}

    async def capture():
        states = await settle()
        for t, db in databases.items():
            states[t]["owner"] = await asyncio.to_thread(read_owner, db)
        return states

    def preserve(name, before, after):
        proof = Path(evidence_directory) / (name + "-state-proof.json.gz")
        raw = json.dumps(dict(before=before, after=after), sort_keys=True, default=str).encode()
        proof.write_bytes(gzip.compress(raw))
        assert gzip.decompress(proof.read_bytes()) == raw
        return dict(
            file=proof.name,
            raw_sha256=hashlib.sha256(raw).hexdigest(),
            compressed_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),
        )

    async def read(g, node, label, **kw):
        body = memory_read_request(g)
        code, out = await request(g["tenant"], "/v1/query/subgraph", body, **kw)
        check(label + " public200", code == 200, code)
        states = await settle()
        check(label + " provenance closure", closed_response(out, states[g["tenant"]]))
        entries.append(dict(name=label, tenant=g["tenant"], response=out))
        save()
        return out, states

    async def admit(g, step):
        code, out = await request(g["tenant"], "/v1/events", step["request"])
        check(
            g["tenant"] + step["scenario"] + " admitted",
            code == 201 and out["status"] == "created",
            out,
        )
        receipts[(g["tenant"], step["request"]["event_id"])] = out["global_position"]
        await settle()

    async def own(g, label):
        out, states = await read(g, g["goal"], label)
        node = out["nodes"].get(g["goal"], {})
        eid = g["steps"][0]["request"]["event_id"]
        check(
            label + " own text and receipt",
            node.get("attributes", {}).get("description") == g["text"]
            and node.get("provenance", {}).get("event_id") == eid
            and node.get("provenance", {}).get("global_position") == receipts[(g["tenant"], eid)],
        )
        doc = next(r for r in states[g["tenant"]]["events"] if r[0] == eid)
        check(
            label + " exact source and bound acceptance",
            decode(doc[1])["payload"] == g["steps"][0]["request"]["payload"]
            and decode(doc[2])["tenant_id"] == "isolation-" + g["tenant"],
        )
        return out

    await admit(a, a["steps"][0])
    await own(a, "A before B write")
    await admit(b, b["steps"][0])
    await own(b, "B after own write")
    await own(a, "A after B write")
    await admit(b, b["steps"][1])
    positive, _ = await read(b, b["foreign"], "B foreign-only positive")
    check("foreign-only exists in B", b["foreign"] in positive["nodes"])
    negative, _ = await read(a, b["foreign"], "A foreign-only negative")
    check("foreign-only absent in A", b["foreign"] not in negative["nodes"])
    for g in (a, b):
        before = await capture()
        code, out = await request(g["tenant"], "/v1/events", g["steps"][0]["request"])
        after = await capture()
        entries.append(
            dict(
                name="replay-" + g["tenant"], proof=preserve("replay-" + g["tenant"], before, after)
            )
        )
        save()
        check(
            "replay exact prior receipt-" + g["tenant"],
            code == 201
            and out["status"] == "duplicate"
            and out["global_position"]
            == receipts[(g["tenant"], g["steps"][0]["request"]["event_id"])],
        )
        check(
            "replay both databases unchanged-" + g["tenant"],
            all(retained_state_preserved(before[t], after[t]) for t in before),
        )

    def fresh_probe(name):
        req = deepcopy(a["steps"][0]["request"])
        req["event_id"] = str(uuid5(NAMESPACE_URL, plan["run_id"] + ":refused:" + name))
        req["payload"]["key"] = "refused-" + name
        return req

    probes = [
        ("api-admin-refused", "/v1/admin/stats", None, dict(method="GET"), 403),
        (
            "foreign-tenant-header",
            "/v1/events",
            fresh_probe("foreign-header"),
            dict(tenant_hints=["isolation-b"]),
            401,
        ),
        (
            "duplicate-tenant-header",
            "/v1/events",
            fresh_probe("duplicate-header"),
            dict(tenant_hints=["isolation-a", "isolation-a"]),
            401,
        ),
        (
            "duplicate-auth",
            "/v1/events",
            fresh_probe("duplicate-auth"),
            dict(auth_mode="duplicate"),
            401,
        ),
        ("missing-auth", "/v1/events", fresh_probe("missing-auth"), dict(auth_mode="missing"), 401),
        ("invalid-auth", "/v1/events", fresh_probe("invalid-auth"), dict(auth_mode="invalid"), 401),
        (
            "reserved-body-routing",
            "/v1/events",
            {
                **fresh_probe("reserved-body"),
                "tenant_id": "isolation-b",
                "database_resource": (
                    "projects/portiq-mvp/instances/engram-experiment/databases/engram-g07-target"
                ),
            },
            dict(),
            422,
        ),
        ("unsupported-metrics", "/metrics", None, dict(method="GET"), 503),
        ("unsupported-webhook", "/v1/webhooks/github", {}, dict(), 503),
    ]
    for name, path, body, options, expected in probes:
        before = await capture()
        code, out = await request("a", path, body, **options)
        after = await capture()
        unchanged = all(retained_state_preserved(before[t], after[t]) for t in before)
        entries.append(
            dict(
                name=name,
                status=code,
                response=out,
                both_databases_materially_unchanged=unchanged,
                proof=preserve(name, before, after),
            )
        )
        save()
        check(name + " declared refusal", code == expected, code)
        check(name + " both databases unchanged", unchanged)
    code, out = await request("a", "/v1/admin/stats", None, method="GET", role="admin")
    check("rightful admin role works", code == 200, code)
    body = memory_read_request(a)
    code, out = await request(
        "a", "/v1/query/subgraph?tenant_id=isolation-b&database_id=engram-g07-target", body
    )
    check(
        "query hints do not override credential binding",
        code == 200
        and out.get("nodes", {}).get(a["goal"], {}).get("attributes", {}).get("description")
        == a["text"]
        and out["nodes"][a["goal"]]["provenance"]["global_position"]
        == receipts[("a", a["steps"][0]["request"]["event_id"])]
        and b["foreign"] not in out["nodes"],
    )
    entries.append(dict(name="ignored-query-routing-hints", status=code, response=out))
    save()
