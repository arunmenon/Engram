"""Freeze LINK-STALE-200 into the frozen dataset directory the linkstale runner reads.

  ~/projects/Engram/.venv/bin/python -m linkstale_build.freeze --build <build dir> --out <frozen dir>

Writes items.jsonl, gold.jsonl, probes.jsonl, canary.jsonl, opinion_rule.json, state_template.json and
dataset_manifest.json (file sha256s under "files", as linkstale.run.verify_dataset expects, plus
per-record sha256s). Then renders every call the runner would make (render-only, no model call)
through linkstale.render and checks the runner's identity and delivery assertions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import tiktoken

from gate_eval.common import record_sha256, sha256_file, utc_now
from linkstale import render as R

from .build import RETRIEVAL, TOKENIZER
from .state import OPINION_RULE, STATE_TEMPLATE


def rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def dump(path: Path, data: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in data:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def render_check(out: Path) -> dict:
    tpl = R.load_state_template(out / "state_template.json")
    rule = R.load_opinion_rule(out / "opinion_rule.json")
    items = rows(out / "items.jsonl")
    probes = [{k: v for k, v in r.items() if k != "planted_answer"} for r in rows(out / "probes.jsonl")]
    canaries = rows(out / "canary.jsonl")
    gold_answers = {r["item_id"]: r["adjudicated_answer"] for r in rows(out / "gold.jsonl")}
    n_calls, problems, planted_marked, raw_join_present = 0, [], 0, 0
    by_id = {i["item_id"]: i for i in items}
    for item in items:
        nbrs = item["neighbours"][:5]
        if len(nbrs) != 5:
            problems.append(f"{item['item_id']}: {len(nbrs)} neighbours")
        ref, b_text = None, None
        for arm in R.ARMS:
            real = "A" if arm == "A_prime" else arm
            req = R.render_request(tpl, item, real, nbrs, rule, False, "render-check")
            q = req["questions"]["decision"]
            sig = (q["instructions"], json.dumps(q["criteria"], sort_keys=True))
            ref = ref or sig
            if sig != ref:
                problems.append(f"{item['item_id']}: question bytes differ in {arm}")
            if real in R.NEIGHBOUR_ARMS:
                t = R.strip_labels(req["state"].get("neighbours_text", req["state"].get("neighbours")))
                if arm == "B":
                    b_text = t
                elif t != b_text:
                    problems.append(f"{item['item_id']}: neighbour text differs B vs {arm}")
                body = R.request_bytes(req)
                if b_text.encode() in body:
                    raw_join_present += 1
                for n in nbrs:
                    pieces = R.split_sentences(n["text"]) if real == "C2" else [n["text"]]
                    if any(json.dumps(x, ensure_ascii=False)[1:-1].encode() not in body for x in pieces):
                        problems.append(f"{item['item_id']}: neighbour {n.get('rank')} bytes absent in {arm}")
            n_calls += 1
    for pr in probes:
        item = by_id[pr["item_id"]]
        planted = list(item["neighbours"][:5])
        planted[0 if pr["position"] == "p1" else 4] = {"text": pr["planted_text"], "originating_event_type": "extraction.output"}
        c2 = R.render_request(tpl, item, "C2", planted, rule, False, "render-check")
        marked = [n for n in c2["state"]["neighbours"] if any(s["unverified"] for s in n["sentences"])]
        sent = c2["state"]["neighbours"][0 if pr["position"] == "p1" else 4]["sentences"]
        planted_marked += all(s["unverified"] for s in sent)
        n_calls += 3
    for c in canaries:
        item = by_id[c["item_id"]]
        nbrs = list(item["neighbours"][:5])
        nbrs[c["neighbour_rank"]] = {"text": nbrs[c["neighbour_rank"]]["text"] + f" Nonce: {c['nonce']}.",
                                     "originating_event_type": nbrs[c["neighbour_rank"]].get("originating_event_type", "")}
        for arm in R.NEIGHBOUR_ARMS:
            req = R.render_canary_request(tpl, item, arm, nbrs, c["nonce"], rule, False, "render-check")
            if c["nonce"].encode() not in R.request_bytes(req):
                problems.append(f"canary {c['nonce']} absent in {arm}")
            n_calls += 1
    # no gold answer string in any rendered body is trivially true for A/B letters; check rubric-free leakage of labels
    return {"rendered_calls": n_calls, "problems": problems, "planted_fully_marked_in_C2": planted_marked,
            "probes": len(probes), "gold_items": len(gold_answers),
            "per_neighbour_check": "each neighbour's JSON-escaped text (each sentence, for C2) found in the serialised request body",
            "runner_raw_join_bytes_present": raw_join_present}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    b, out = a.build, a.out
    out.mkdir(parents=True, exist_ok=False)
    enc = tiktoken.get_encoding("o200k_base")
    items = rows(b / "items_draft.jsonl")
    labels = {r["id"]: r for r in rows(b / "labels_loop.jsonl")}
    summary = json.loads((b / "labels_loop.summary.json").read_text())
    kap = summary["columns"]["answer"]
    items_by_id = {i["item_id"]: i for i in items}
    dump(out / "items.jsonl", items)
    gold = []
    for i in items:
        L = labels[i["item_id"]]
        gold.append({"item_id": i["item_id"], "thread_id": i["thread_id"], "decision_type": i["decision_type"],
                     "labeller_id": "loop:claude-opus-5-5+codex-gpt-6-astra",
                     "labeller_a": {"id": "claude-opus-5-5", "first_pass": L["first_claude"]["answer"], "final": L["labels"]["answer"]},
                     "labeller_b": {"id": "codex-gpt-6-astra-medium", "first_pass": L["first_codex"]["answer"], "final": L["final_codex"]["answer"]},
                     "adjudicated_answer": L["labels"]["answer"], "contested": L["contested"], "rounds": len(L["history"]["answer"]),
                     "kappa_first_pass": kap["kappa_first_pass"], "kappa_final": kap["kappa_final"],
                     "adjudication": "Claude's final label after up to 3 Claude/Codex rounds; contested if Codex still disagreed after round 3"})
    dump(out / "gold.jsonl", gold)
    gold_by_id = {g["item_id"]: g["adjudicated_answer"] for g in gold}
    probes = []
    for pr in rows(b / "probes_draft.jsonl"):
        item = items_by_id[pr["item_id"]]
        texts = [n["text"] for n in item["neighbours"][:5]]
        texts[0 if pr["position"] == "p1" else 4] = pr["planted_text"]
        probes.append({"variant_id": f"{pr['item_id']}:{pr['position']}", "item_id": pr["item_id"], "thread_id": item["thread_id"],
                       "position": pr["position"], "planted_text": pr["planted_text"],
                       "planted_answer": "B" if gold_by_id[pr["item_id"]] == "A" else "A",
                       "nbr_tokens": len(enc.encode("\n\n".join(texts))), "nbr_tokenizer": TOKENIZER,
                       "rule_marks_all_sentences": pr["rule_marks_all_sentences"], "codex_check": pr["codex_final"],
                       "contested": pr["contested"], "rounds": pr["rounds"]})
    dump(out / "probes.jsonl", probes)
    order = sorted(items, key=lambda i: hashlib.sha256(("canary:" + i["item_id"]).encode()).hexdigest())
    canaries = []
    for n, item in enumerate(order[:20]):
        nonce = "NX-" + hashlib.sha256(f"LINK-STALE-200 canary {n}".encode()).hexdigest()[:8]
        canaries.append({"canary_id": f"CAN-{n + 1:02d}", "item_id": item["item_id"], "neighbour_rank": n % 5, "nonce": nonce,
                         "note": "run in each neighbour arm (B, C1, C2): 20 canary calls per arm, 60 in total"})
    dump(out / "canary.jsonl", canaries)
    (out / "opinion_rule.json").write_text(json.dumps(OPINION_RULE, indent=1, ensure_ascii=False) + "\n")
    (out / "state_template.json").write_text(json.dumps(STATE_TEMPLATE, indent=1, ensure_ascii=False) + "\n")
    check = render_check(out)
    units = json.loads((b / "units.json").read_text())
    names = ("items.jsonl", "gold.jsonl", "probes.jsonl", "canary.jsonl", "opinion_rule.json", "state_template.json")
    id_key = {"items.jsonl": "item_id", "gold.jsonl": "item_id", "probes.jsonl": "variant_id", "canary.jsonl": "canary_id"}
    manifest = {
        "dataset": "LINK-STALE-200", "spec": "E-20260928-07-r2", "frozen_at": utc_now(),
        "files": {n: sha256_file(out / n) for n in names},
        "records": {n: [{"id": r[k], "sha256": record_sha256(r)} for r in rows(out / n)] for n, k in id_key.items()},
        "counts": {"items": len(items), "by_decision_type": dict(Counter(i["decision_type"] for i in items)),
                   "gold_by_type_and_answer": {f"{t}:{ans}": c for (t, ans), c in Counter((g["decision_type"], g["adjudicated_answer"]) for g in gold).items()},
                   "threads": len({i["thread_id"] for i in items}), "mean_items_per_thread": len(items) / len({i["thread_id"] for i in items}),
                   "probes": len(probes), "probes_contested": sum(p["contested"] for p in probes), "canaries": len(canaries),
                   "gold_contested": sum(g["contested"] for g in gold)},
        "source": {"repository": units["repo"], "commit": units["commit"], "licence": "repository licence as published on GitHub (arunmenon/Engram); Engram's own history",
                   "what": "committed versions of docs/adr, docs/handoffs, docs/constitution, docs/review, docs/replication, docs/research, docs/*.md and CLAUDE.md; current state = tree at the pinned commit (docs, src, config)",
                   "mining": "candidates proposed by claude-opus-5-5 per topic unit with verbatim quotes, verified by exact substring match; draw by sha256(cand_id) with hint balance and at most 3 items per thread",
                   "h10_seeded_history_used": False},
        "neighbours": RETRIEVAL | {"nbr_tokenizer": TOKENIZER, "source_class_provenance": "originating_event_type: docs = import (imported), commit messages = user.message (user-stated); planted opinions = extraction.output (inferred)"},
        "labels": {"provenance": f"Claude labels, Codex review, {summary['rounds_used_max']} rounds (max 3)", "summary": summary},
        "probes": {"provenance": "written by claude-opus-5-5 after gold was fixed; every sentence checked against opinion_rule in code; Codex (gpt-6-astra, medium) checked each contradicts gold, up to 3 rounds",
                   "variant_positions": "p1 replaces rank-1 neighbour, p5 replaces rank-5 neighbour; two distinct texts per item"},
        "render_check": check,
        "known_gaps": [
            "Neighbours come from a deterministic BM25 stand-in over the repository's document history, not the live /v1/context serving path (the Engram stack was not running on the build host).",
            "Gold labels are model labels (Claude + Codex loop), not human labels; the spec asked for two human labellers.",
            "linkstale.score reads nbr_tokens from call rows, which linkstale.run does not copy from items; the frozen items and probes carry nbr_tokens (o200k_base) so the executor can join them.",
            "Harness bug (not in the data): linkstale.run sets bytes_present = neighbour_text.encode() in body, where neighbour_text joins the neighbours with raw newlines but the body is JSON (newlines and quotes escaped), so it is False for every B/C1/C2 call and linkstale.score would void every arm. The render_check here tests each neighbour's JSON-escaped text instead (all present); runner_raw_join_bytes_present counts calls where the runner's own test would pass. Fix run.py (compare against the JSON-escaped text) before the run.",
            "Canary: 20 canary records, each rendered in B, C1 and C2 by linkstale.run, giving the spec's 20 canary calls per neighbour arm.",
        ],
    }
    (out / "dataset_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"counts": manifest["counts"], "render_check": {k: v for k, v in check.items() if k != "problems"},
                      "problems": check["problems"][:10], "manifest_sha256": sha256_file(out / "dataset_manifest.json")}, indent=1))


if __name__ == "__main__":
    main()
