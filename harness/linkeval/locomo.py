"""E-20260928-18-r2 first cut (LoCoMo only): Jev deciding links at write time.

  python -m linkeval.locomo build   --run <dir> --locomo <locomo10.json> --extracted <terra extracted.jsonl> \
        --conversations conv-47,conv-49
  python -m linkeval.locomo jev     --run <dir>                 (Jev scores every candidate pair and type)
  python -m linkeval.locomo answer  --run <dir> --arm {A_paper,C,N} (Claude reader, batched)
  python -m linkeval.locomo judge   --run <dir> --arm …          (Codex judge, batched)
  python -m linkeval.locomo score   --run <dir>

Nodes (NODES-v1 here): the memory items our production extractor (gpt-5.6-terra) already wrote for the
two LoCoMo conversations of the frozen LINK-ASF-LOCOMO selection, in write order (session, item index),
each rendered with its session date and speaker (quote matched to the transcript turn).
Candidates (frozen, at most 10 per new node, earlier nodes of the same conversation only): nodes that
share the exact entity key, most recent first, then BM25 neighbours of the node text.
Edges:
  C (deterministic floor): temporal FOLLOWS to the previous node in the same session; ENTITY to the most
    recent earlier node with the same entity key. No model.
  A_paper: C's edges plus Jev-confirmed typed edges (semantic, caused_by, same_episode) on candidate pairs
    with probability >= 0.60 (the paper's fixed threshold; no labelled dev slice exists for a refit).
  N: no edges (control).
Retrieval (identical for every arm): BM25 over the conversation's nodes with the question as query; the
top 5 seeds are served, then each seed's one-hop neighbours along the arm's edges (seed order, Jev
probability order), then further BM25 ranks, until 4,000 tokens (o200k_base).
Reader: claude-sonnet-5-5 (headless, no tools), 10 questions per call, each with its own memory block.
Judge: Codex gpt-6-astra (reasoning medium), a different family from Jev and from the reader.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gate_eval.common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl  # noqa: E402
from gate_eval.stats import cluster_bootstrap, mean  # noqa: E402
from seatswap.answer import BM25, SESSION_OF, conversation_index, normalise  # noqa: E402

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"
THRESHOLD = 0.60
MAX_CANDIDATES = 10
SERVED_TOKENS = 4000
SEEDS = 5
READER_MODEL = "claude-sonnet-5-5"
READER_BATCH = 10
JUDGE_BATCH = 40
LINK_TYPES = {
    "semantic": "Is `new_memory` about the same topic, fact, preference or plan as `candidates.{cid}`, so that reading one helps interpret the other?",
    "caused_by": "Does `new_memory` describe something caused by, motivated by, or a direct consequence of what `candidates.{cid}` describes?",
    "same_episode": "Do `new_memory` and `candidates.{cid}` describe the same event, activity or episode in a person's life?",
}
JEV_TASK = ("Memory linking for a personal assistant. `new_memory` was just written from a conversation; `candidates` are earlier "
            "memories from the same conversation. Judge each question independently from the memory texts only.")


def entity_key(item: dict) -> str:
    fields = item["fields"]
    for key in ("about_entity", "entity_name", "name"):
        if fields.get(key):
            return normalise(str(fields[key]))
    return ""


def render(item: dict, sessions: dict) -> tuple[str, str, int]:
    sample_id, session_key = item["session_id"].split(":")
    session_no = int(session_key.split("_")[1])
    date, turns = sessions[sample_id][session_no]
    quote = normalise(item.get("source_quote") or "")
    speaker = next((who for who, text in turns if quote and quote in normalise(text)), "")
    fields = {k: v for k, v in item["fields"].items() if k not in ("confidence", "source_turn_index", "source_quote") and v not in (None, "")}
    body = "; ".join(f"{k}: {v}" for k, v in fields.items())
    quote_part = f' (quote: "{item["source_quote"]}")' if item.get("source_quote") else ""
    return sample_id, f"[{date}{', ' + speaker if speaker else ''}] {item['item_kind']}: {body}{quote_part}", session_no


# ----------------------------------------------------------------------------- build: nodes, candidates, C edges, questions

def cmd_build(args) -> int:
    locomo = json.loads(args.locomo.read_text())
    sessions = conversation_index(locomo)
    wanted = args.conversations.split(",")
    items = [r for r in read_jsonl(args.extracted) if r["session_id"].split(":")[0] in wanted]
    items.sort(key=lambda r: (r["session_id"].split(":")[0], int(r["session_id"].split("_")[-1]), r["item_kind"], r["item_index"]))
    nodes = []
    for position, item in enumerate(items):
        sample_id, text, session_no = render(item, sessions)
        nodes.append({"node_id": f"n{position:05d}", "sample_id": sample_id, "session_no": session_no, "text": text,
                      "entity_key": entity_key(item), "item_kind": item["item_kind"], "source_session": item["session_id"]})
    write_jsonl(args.run / "nodes.jsonl", nodes)

    candidates, c_edges = [], []
    by_conv = defaultdict(list)
    for n in nodes:
        by_conv[n["sample_id"]].append(n)
    for conv_nodes in by_conv.values():
        for i, node in enumerate(conv_nodes):
            earlier = conv_nodes[:i]
            if not earlier:
                continue
            chosen = [e for e in reversed(earlier) if node["entity_key"] and e["entity_key"] == node["entity_key"]][:MAX_CANDIDATES]
            if len(chosen) < MAX_CANDIDATES:
                bm = BM25([e["text"] for e in earlier])
                scores = bm.scores(node["text"])
                for j in sorted(range(len(earlier)), key=lambda j: (-scores[j], -j)):
                    if len(chosen) >= MAX_CANDIDATES:
                        break
                    if earlier[j] not in chosen and scores[j] > 0:
                        chosen.append(earlier[j])
            candidates.append({"node_id": node["node_id"], "candidates": [c["node_id"] for c in chosen]})
            previous_same_session = [e for e in earlier if e["session_no"] == node["session_no"]]
            if previous_same_session:
                c_edges.append({"source": node["node_id"], "target": previous_same_session[-1]["node_id"], "edge_type": "FOLLOWS", "weight": 1.0})
            same_entity = [e for e in earlier if node["entity_key"] and e["entity_key"] == node["entity_key"]]
            if same_entity:
                c_edges.append({"source": node["node_id"], "target": same_entity[-1]["node_id"], "edge_type": "ENTITY", "weight": 1.0})
    write_jsonl(args.run / "candidates.jsonl", candidates)
    write_jsonl(args.run / "edges_C.jsonl", c_edges)

    extracted_sessions = {n["source_session"] for n in nodes}
    by_id = {c["sample_id"]: c for c in locomo}
    questions = []
    for sample_id in wanted:
        for k, qa in enumerate(by_id[sample_id]["qa"]):
            needed = {int(m.group(1)) for e in qa.get("evidence", []) for m in [SESSION_OF.match(e.strip())] if m}
            if needed and all(f"{sample_id}:session_{s}" in extracted_sessions for s in needed):
                questions.append({"qa_id": f"{sample_id}#qa{k:03d}", "sample_id": sample_id, "category": qa["category"],
                                  "question": qa["question"], "answer": qa.get("answer"), "adversarial_answer": qa.get("adversarial_answer")})
    write_jsonl(args.run / "questions.jsonl", questions)
    manifest = {"built_at": utc_now(), "conversations": wanted, "extracted_source": str(args.extracted),
                "extracted_sha256": sha256_file(args.extracted), "nodes": len(nodes), "nodes_sha256": sha256_file(args.run / "nodes.jsonl"),
                "candidate_pairs": sum(len(c["candidates"]) for c in candidates), "candidates_sha256": sha256_file(args.run / "candidates.jsonl"),
                "edges_C": len(c_edges), "edges_C_twice_identical": None, "questions": len(questions),
                "questions_sha256": sha256_file(args.run / "questions.jsonl"), "extracted_sessions": len(extracted_sessions)}
    write_json(args.run / "build_manifest.json", manifest)
    print(json.dumps(manifest, indent=1))
    return 0


# ----------------------------------------------------------------------------- Jev link decisions

def jev_call(body: bytes) -> dict:
    last = None
    for attempt in range(5):
        request = urllib.request.Request(JEV_ENDPOINT, data=body, method="POST", headers={
            "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}", "Content-Type": "application/json",
            "User-Agent": "memory-rsi-signals/1.0 (research harness)"})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read())
            return {"ok": True, "payload": payload, "latency_ms": (time.perf_counter() - started) * 1000, "attempts": attempt + 1}
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = str(exc)
            time.sleep(2 ** attempt)
    return {"ok": False, "error": last, "attempts": 5}


def cmd_jev(args) -> int:
    nodes = {n["node_id"]: n for n in read_jsonl(args.run / "nodes.jsonl")}
    candidates = [c for c in read_jsonl(args.run / "candidates.jsonl") if c["candidates"]]

    def one(entry: dict) -> dict:
        cids = {f"c{k + 1}": nid for k, nid in enumerate(entry["candidates"])}
        state = {"task": JEV_TASK, "new_memory": nodes[entry["node_id"]]["text"],
                 "candidates": {cid: nodes[nid]["text"] for cid, nid in cids.items()}}
        questions = {f"{t}::{cid}": {"type": "noul", "instructions": q.format(cid=cid)} for cid in cids for t, q in LINK_TYPES.items()}
        body = json.dumps({"state": state, "model": JEV_MODEL, "questions": questions}).encode()
        result = jev_call(body)
        row = {"node_id": entry["node_id"], "n_candidates": len(cids), "request_bytes": len(body), "ok": result["ok"],
               "attempts": result["attempts"], "latency_ms": result.get("latency_ms"), "error": result.get("error")}
        if result["ok"]:
            payload = result["payload"]
            row.update({"model_reported": payload.get("model"), "usage": payload.get("usage"),
                        "scores": [{"target": cids[key.split("::")[1]], "link_type": key.split("::")[0],
                                    "probability": answer.get("noul", answer.get("probability"))} for key, answer in payload["answers"].items()]})
        return row

    started = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(one, candidates))
    wall = time.time() - started
    write_jsonl(args.run / "jev_link_calls.jsonl", rows)
    c_edges = read_jsonl(args.run / "edges_C.jsonl")
    jev_edges = [{"source": r["node_id"], "target": s["target"], "edge_type": s["link_type"].upper(), "weight": s["probability"]}
                 for r in rows if r["ok"] for s in r["scores"] if s["probability"] is not None and s["probability"] >= THRESHOLD]
    write_jsonl(args.run / "edges_A_paper.jsonl", c_edges + jev_edges)
    ok = [r for r in rows if r["ok"]]
    summary = {"calls": len(rows), "ok": len(ok), "writes_scored": len(ok), "pairs_scored": sum(r["n_candidates"] for r in ok),
               "input_tokens": sum((r["usage"] or {}).get("input_tokens", 0) for r in ok),
               "output_tokens": sum((r["usage"] or {}).get("output_tokens", 0) for r in ok),
               "wall_s": round(wall, 1), "latency_ms_mean": mean([r["latency_ms"] for r in ok]),
               "jev_edges_at_0_60": len(jev_edges), "by_type": {t.upper(): sum(1 for e in jev_edges if e["edge_type"] == t.upper()) for t in LINK_TYPES},
               "models_reported": sorted({r.get("model_reported") for r in ok})}
    summary["usd"] = summary["input_tokens"] / 1e6 * 0.042
    summary["usd_per_1000_writes"] = summary["usd"] / max(1, len(ok)) * 1000
    summary["seconds_per_1000_writes_sequential"] = summary["latency_ms_mean"] / 1000 * 1000
    write_json(args.run / "jev_link_summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if len(ok) == len(rows) else 3


# ----------------------------------------------------------------------------- answering

def served_memory(question: dict, conv_nodes: list[dict], adjacency: dict, encoding) -> tuple[list[str], int]:
    bm = BM25([n["text"] for n in conv_nodes])
    scores = bm.scores(question["question"])
    ranked = [conv_nodes[i] for i in sorted(range(len(conv_nodes)), key=lambda i: (-scores[i], i))]
    order, seen = [], set()

    def push(node):
        if node["node_id"] not in seen:
            seen.add(node["node_id"])
            order.append(node)

    by_id = {n["node_id"]: n for n in conv_nodes}
    for seed in ranked[:SEEDS]:
        push(seed)
    for seed in ranked[:SEEDS]:
        for neighbour_id, _weight in adjacency.get(seed["node_id"], []):
            if neighbour_id in by_id:
                push(by_id[neighbour_id])
    for node in ranked[SEEDS:]:
        push(node)
    served, used = [], 0
    for node in order:
        cost = len(encoding.encode(node["text"])) + 1
        if used + cost > SERVED_TOKENS:
            continue
        served.append(node["text"])
        used += cost
    return served, used


READER_PROMPT = """Answer each question about a long conversation between two people, using only that question's memory records.
Records were extracted from the conversation and show the session date and, when known, the speaker.
Answer briefly (a few words or one short sentence); for time questions give the date or period.
If a question's records do not contain the answer, answer exactly: Not mentioned.
Reply with JSON only: {"answers": [{"id": "<id>", "answer": "<answer>"}, ...]} covering every id.

"""


def claude_json(prompt: str, model: str) -> dict | None:
    for attempt in range(4):
        with tempfile.TemporaryDirectory() as empty:
            proc = subprocess.run(["claude", "-p", "--model", model, "--output-format", "json", "--tools", ""],
                                  input=prompt, capture_output=True, text=True, timeout=900, cwd=empty)
        try:
            envelope = json.loads(proc.stdout)
            text = envelope["result"]
            return {"parsed": json.loads(text[text.index("{"): text.rindex("}") + 1]), "usage": envelope.get("usage"),
                    "cost_usd": envelope.get("total_cost_usd")}
        except (ValueError, KeyError, json.JSONDecodeError):
            time.sleep(2 ** attempt)
    return None


def cmd_answer(args) -> int:
    import tiktoken
    encoding = tiktoken.get_encoding("o200k_base")
    nodes = read_jsonl(args.run / "nodes.jsonl")
    by_conv = defaultdict(list)
    for n in nodes:
        by_conv[n["sample_id"]].append(n)
    adjacency: dict = defaultdict(list)
    if args.arm != "N":
        for e in read_jsonl(args.run / f"edges_{args.arm}.jsonl"):
            adjacency[e["source"]].append((e["target"], e["weight"]))
            adjacency[e["target"]].append((e["source"], e["weight"]))
        for key in adjacency:
            adjacency[key].sort(key=lambda t: -t[1])
    questions = read_jsonl(args.run / "questions.jsonl")
    prepared = []
    for q in questions:
        served, used = served_memory(q, by_conv[q["sample_id"]], adjacency, encoding)
        prepared.append({**q, "served": served, "served_tokens": used})
    batches = [prepared[i:i + READER_BATCH] for i in range(0, len(prepared), READER_BATCH)]

    def one(batch: list[dict]) -> list[dict]:
        blocks = [f"### id: {q['qa_id']}\nQuestion: {q['question']}\nMemory records:\n" + ("\n".join(q["served"]) or "(none)") for q in batch]
        result = claude_json(READER_PROMPT + "\n\n".join(blocks), READER_MODEL)
        answers = {a["id"]: a["answer"] for a in (result or {}).get("parsed", {}).get("answers", [])} if result else {}
        return [{"qa_id": q["qa_id"], "arm": args.arm, "answer": answers.get(q["qa_id"]), "served_items": len(q["served"]),
                 "served_tokens": q["served_tokens"], "batch_cost_usd": (result or {}).get("cost_usd")} for q in batch]

    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = [r for batch_rows in pool.map(one, batches) for r in batch_rows]
    (args.run / "answers").mkdir(exist_ok=True)
    write_jsonl(args.run / "answers" / f"{args.arm}.jsonl", rows)
    print(f"{args.arm}: {len(rows)} answers, {sum(1 for r in rows if r['answer'] is None)} missing")
    return 0


JUDGE_PROMPT = """Grade each answer to a question about a conversation against its reference. Scoring per item: 1 if the answer is correct and matches the reference in substance (wording, format and extra detail do not matter; a matching date or period counts); 0.5 if partly correct; 0 if wrong, or if it says the information is not available when the reference gives an answer. Items marked adversarial have a false premise: score 1 if the answer says the information is not mentioned or not known, 0 if it gives a substantive answer.
Write JSON only to your final message: {"grades": [{"id": "<id>", "score": 1 | 0.5 | 0}, ...]} covering every id.

Items (JSON lines):
"""


def cmd_judge(args) -> int:
    questions = {q["qa_id"]: q for q in read_jsonl(args.run / "questions.jsonl")}
    answers = read_jsonl(args.run / "answers" / f"{args.arm}.jsonl")
    items = []
    for a in answers:
        q = questions[a["qa_id"]]
        adversarial = q["category"] == 5
        items.append({"id": a["qa_id"], "question": q["question"], "adversarial": adversarial,
                      "reference": "Not mentioned (false premise)" if adversarial else str(q["answer"]), "answer": a["answer"] or "(no answer)"})
    batches = [items[i:i + JUDGE_BATCH] for i in range(0, len(items), JUDGE_BATCH)]

    def one(batch: list[dict]) -> dict:
        for attempt in range(3):
            with tempfile.TemporaryDirectory() as work:
                out = Path(work) / "grades.json"
                prompt = JUDGE_PROMPT + "\n".join(json.dumps(i, ensure_ascii=False) for i in batch)
                subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-c", "model_reasoning_effort=medium", "-s", "read-only",
                                "--skip-git-repo-check", "--ephemeral", "-C", work, "-o", str(out), prompt],
                               capture_output=True, text=True, timeout=1200, stdin=subprocess.DEVNULL)
                try:
                    text = out.read_text()
                    grades = json.loads(text[text.index("{"): text.rindex("}") + 1])["grades"]
                    return {g["id"]: float(g["score"]) for g in grades}
                except (OSError, ValueError, KeyError, json.JSONDecodeError):
                    time.sleep(2 ** attempt)
        return {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        grades = {}
        for part in pool.map(one, batches):
            grades.update(part)
    rows = [{**a, "category": questions[a["qa_id"]]["category"], "sample_id": questions[a["qa_id"]]["sample_id"],
             "score": grades.get(a["qa_id"]) if grades.get(a["qa_id"]) in (0.0, 0.5, 1.0) else None, "judge": "codex gpt-6-astra (medium)"}
            for a in answers]
    (args.run / "judged").mkdir(exist_ok=True)
    write_jsonl(args.run / "judged" / f"{args.arm}.jsonl", rows)
    print(f"{args.arm}: judged {len(rows)}, {sum(1 for r in rows if r['score'] is None)} ungraded")
    return 0


def cmd_score(args) -> int:
    arms = [a for a in ("A_paper", "C", "N") if (args.run / "judged" / f"{a}.jsonl").exists()]
    judged = {a: {r["qa_id"]: r for r in read_jsonl(args.run / "judged" / f"{a}.jsonl")} for a in arms}
    summary = {}
    for a in arms:
        vals = [r for r in judged[a].values() if r["score"] is not None]
        summary[a] = {"n": len(vals), "accuracy": mean([r["score"] for r in vals]),
                      "answerable_cat1_4": mean([r["score"] for r in vals if r["category"] != 5]),
                      "adversarial_cat5": mean([r["score"] for r in vals if r["category"] == 5]),
                      "mean_served_tokens": mean([r["served_tokens"] for r in judged[a].values()])}

    def paired(x: str, y: str) -> dict:
        common = sorted(k for k in judged[x] if k in judged[y] and judged[x][k]["score"] is not None and judged[y][k]["score"] is not None)
        diffs = [{"qa_id": k, "d": judged[x][k]["score"] - judged[y][k]["score"]} for k in common]
        boot = cluster_bootstrap(diffs, "qa_id", lambda xs: mean([d["d"] for d in xs]), 10_000, 20261026)
        return {k: boot[k] for k in ("point", "ci95_two_sided", "lb95", "ub95")} | {"n": len(diffs),
                "discordant": sum(1 for d in diffs if d["d"] != 0)}

    contrasts = {f"{x}_minus_{y}": paired(x, y) for x, y in (("A_paper", "C"), ("A_paper", "N"), ("C", "N")) if x in arms and y in arms}
    jev = json.loads((args.run / "jev_link_summary.json").read_text())
    an = contrasts.get("A_paper_minus_N", {})
    cn = contrasts.get("C_minus_N", {})
    edges_inert = bool(an and cn and abs(an["point"]) <= 0.01 and abs(cn["point"]) <= 0.01)
    ac = contrasts.get("A_paper_minus_C", {})
    if ac and ac["ci95_two_sided"][1] < 0:
        outcome = "negative (answer accuracy: A below C, interval wholly below zero)"
    elif edges_inert:
        outcome = "edges_inert (answers do not depend on links on this harness)"
    else:
        outcome = "inconclusive (first cut: no labelled link pairs and no LLM-linker arm B, so the link-metric rules cannot be evaluated)"
    verdict = {"first_cut": "LoCoMo only, answer accuracy and build cost; link precision/recall need labelled pairs, arm B needs gpt-5.6-terra",
               "outcome": outcome, "edges_inert": edges_inert, "summary": summary, "contrasts": contrasts, "jev_build": jev}
    write_json(args.run / "verdict.json", verdict)
    with open(args.run / "metrics.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["arm", *next(iter(summary.values())).keys()])
        writer.writeheader()
        for a, s in summary.items():
            writer.writerow({"arm": a, **s})
    print(json.dumps(verdict, indent=1, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linkeval.locomo")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--run", type=Path, required=True)
    b.add_argument("--locomo", type=Path, required=True)
    b.add_argument("--extracted", type=Path, required=True)
    b.add_argument("--conversations", default="conv-47,conv-49")
    for name in ("jev", "score"):
        s = sub.add_parser(name)
        s.add_argument("--run", type=Path, required=True)
    for name in ("answer", "judge"):
        s = sub.add_parser(name)
        s.add_argument("--run", type=Path, required=True)
        s.add_argument("--arm", required=True, choices=["A_paper", "C", "N"])
    args = parser.parse_args(argv)
    args.run.mkdir(parents=True, exist_ok=True)
    return {"build": cmd_build, "jev": cmd_jev, "answer": cmd_answer, "judge": cmd_judge, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
