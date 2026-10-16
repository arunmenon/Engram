"""P07 exact-source, actual-provider Summary proof; no runtime or graph writes."""

from __future__ import annotations

import asyncio
import json
import time

from engram_pilot_episode_bridge import (
    decode,
    episode,
    probe,
    public_context_ids,
    verify_public_membership,
    verify_snapshot,
)


def source_records(messages):
    """Parse the production prompt's JSON source lines, never substring-match IDs."""
    records = []
    for message in messages:
        content = message.get("content", "")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(row, dict) and "event_id" in row and "source_content" in row:
                try:
                    source = json.loads(row["source_content"])
                except (ValueError, TypeError):
                    return None
                records.append((row["event_id"], source))
    return records


def matching_calls(calls, steps):
    expected = {s["request"]["event_id"]: s["request"]["payload"] for s in steps}
    found = []
    for call in calls:
        rows = source_records(call.get("input_messages", []))
        if (
            call.get("state") == "returned"
            and call.get("model") == "gpt-6-luna"
            and rows is not None
            and len(rows) == len(expected)
            and len({eid for eid, _ in rows}) == len(expected)
            and dict(rows) == expected
        ):
            found.append(call)
    return found


async def execute(plan, *, request, check, databases, record, save, settle):
    from engram_pilot_spectrum import summary_contrast_matches

    groups = plan["groups"]
    if len(groups) != 4 or {(g["tenant"], g["contrast"]) for g in groups} != {
        (t, c) for t in ("a", "b") for c in ("forward", "inverse")
    }:
        raise ValueError("P07 requires all four tenant/outcome combinations")
    expected = {
        g["name"]: episode(g["session"], [s["request"] for s in g["steps"]]) for g in groups
    }
    initial = await settle()
    positions = {}
    entries = record.setdefault("summary_proof", [])
    for g in groups:
        e = expected[g["name"]]
        check(
            g["name"] + " frozen snapshot identity and source membership",
            e["id"] == g["episode"]
            and e["summary"] == g["summary"]
            and e["members"] == g["members"],
        )
        check(
            g["name"] + " fresh session and snapshot",
            not any(
                decode(r[1]).get("session_id") == g["session"]
                for r in initial[g["tenant"]]["events"]
            )
            and not {e["id"], e["summary"]} & {r[1] for r in initial[g["tenant"]]["nodes"]},
        )
        for s in g["steps"]:
            code, body = await request(g["tenant"], "/v1/events", s["request"])
            check(g["name"] + ":" + s["scenario"] + " admitted", code == 201)
            positions[s["request"]["event_id"]] = body["global_position"]
    await settle()
    deadline = time.monotonic() + min(g["phase_wait_seconds"] for g in groups)
    while True:
        ready = await asyncio.gather(
            *(
                asyncio.to_thread(probe, databases[g["tenant"]], [expected[g["name"]]])
                for g in groups
            )
        )
        if all(ready):
            states = await settle()
            if all(
                next(
                    (
                        decode(r[2]).get("complete") is True
                        for r in states[g["tenant"]]["nodes"]
                        if r[0] == "Episode" and r[1] == expected[g["name"]]["id"]
                    ),
                    False,
                )
                for g in groups
            ):
                break
        if time.monotonic() >= deadline:
            check("all four complete scheduled Summary snapshots available", False, ready)
        await asyncio.sleep(1)
    check("all four complete scheduled Summary snapshots available", True)
    for g in groups:
        t = g["tenant"]
        e = expected[g["name"]]
        candidates = [episode(g["session"], [s["request"]]) for s in g["steps"]]
        known_nodes = {(r[0], r[1]): decode(r[2]) for r in states[t]["nodes"]}
        history = [h for h in candidates if ("Episode", h["id"]) in known_nodes]
        chosen = [*history, e]
        private = {
            h["id"]: verify_snapshot(states[t], h, positions, check, g["name"]) for h in chosen
        }
        stored = next(
            decode(r[2])["content"]
            for r in states[t]["nodes"]
            if r[0] == "Summary" and r[1] == e["summary"]
        )
        calls = matching_calls(record["provider_calls"], g["steps"])
        check(g["name"] + " actual returned Luna call with exact accepted sources", bool(calls))
        check(
            g["name"] + " stored text equals actual returned provider text",
            any(c["output"] == stored for c in calls),
        )
        body = dict(
            query="What happened in this session, and what remains uncertain?",
            intent="when",
            session_id=g["session"],
            agent_id=g["owner"],
            max_nodes=100,
            timeout_ms=30000,
        )
        entry = dict(
            name=g["name"],
            storage=private,
            stored_text=stored,
            matching_provider_calls=calls,
            reads=[],
        )
        entries.append(entry)
        save()
        while True:
            code, answer = await request(t, "/v1/query/subgraph", body)
            entry["reads"].append(dict(status=code, request=body, response=answer))
            save()
            ep, summaries = public_context_ids(answer)
            check(
                g["name"] + " public session context excludes other outcomes",
                code == 200
                and ep <= {h["id"] for h in chosen}
                and summaries <= {h["summary"] for h in chosen},
            )
            if {
                nid for h in chosen for nid in (h["id"], h["summary"], *h["members"])
            } <= answer.get("nodes", {}).keys() and not answer.get("meta", {}).get("truncated"):
                break
            if time.monotonic() >= deadline:
                check(g["name"] + " public complete context convergence", False)
            await asyncio.sleep(1)
        verify_public_membership(answer, chosen, check, g["name"])
        public = answer["nodes"][e["summary"]]["attributes"]["content"]
        check(
            g["name"] + " stored/public/provider text identical",
            public == stored and any(c["output"] == public for c in calls),
        )
        check(
            g["name"] + " narrow outcome and uncertainty contrast",
            summary_contrast_matches(public, g["contrast"]),
        )
        for h in chosen:
            for nid in (h["id"], h["summary"], *h["members"]):
                source = nid if nid in h["members"] else h["anchor"]
                p = answer["nodes"][nid].get("provenance") or {}
                check(
                    g["name"] + " exact public source position " + nid,
                    p.get("source") == "spanner"
                    and p.get("event_id") == source
                    and p.get("global_position") == positions[source],
                )
        other_ids = {
            s["request"]["event_id"]
            for other in groups
            if other["tenant"] == t and other["name"] != g["name"]
            for s in other["steps"]
        }
        entry["general_event_recall_diagnostic"] = dict(
            opposite_session_source_events_present=sorted(other_ids & answer["nodes"].keys())
        )
        entry["state"] = "passed exact source, actual text and narrow contrast checks"
        save()
