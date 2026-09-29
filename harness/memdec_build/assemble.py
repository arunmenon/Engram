"""Assemble MEMDEC-ASF-6200 candidates from the extraction output (no model).

  python -m memdec_build.assemble --build <build dir>

Steps, all deterministic (seed 20260928):
1. transcripts.jsonl and session_repos.json in memdec.export's input shape.
2. extractions.jsonl: the client's results with `source_turn_index` filled, when the
   extractor left it null, by the first turn containing the quote verbatim
   (lowercased, whitespace-collapsed); counts recorded. extractions_raw.jsonl is kept.
3. `python -m memdec.export` unchanged -> export/ (items, exact-key pairs, splits).
4. Supersession candidates: memdec.export pairs only exact repeats of a free-text
   preference key, which almost never recur, so a second, recorded candidate rule
   adds for every preference b its most similar earlier preference a in the same
   repository and a different thread (TF-IDF cosine over key tokens, about_entity,
   context and quote; cosine >= MIN_COSINE). Same pair shape, plus `pair_rule`.
5. Draw per split, round-robin across repositories in sha256(id) order. Train and
   val are drawn first; test candidates sharing >= 50% of their word 13-grams with any
   drawn training state are dropped (count recorded) before the test draw.
6. Labelling sheets without model outputs (no extractor confidence or source).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from gate_eval.common import read_jsonl, record_sha256, sha256_file, utc_now, write_json, write_jsonl

SEED = 20260928
MIN_COSINE = 0.25
TARGETS = {"train": {"store_skip": 2000, "supersedes": 1000},
           "val": {"store_skip": 250, "supersedes": 150},
           "test": {"store_skip": 1200, "supersedes": 1200}}
SPLIT_REPOS = {"train": 14, "val": 2, "test": 10}
TOKEN = re.compile(r"[a-z0-9]+")


def norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def prepare_inputs(build: Path) -> dict:
    sessions = read_jsonl(build / "sessions.jsonl")
    transcripts = [{"session_id": s["session_id"],
                    "turns": [{"index": i, "role": t["speaker"], "text": t["text"]} for i, t in enumerate(s["turns"])]}
                   for s in sessions]
    write_jsonl(build / "transcripts.jsonl", transcripts)
    write_json(build / "session_repos.json", {s["session_id"]: s["repository_id"] for s in sessions})
    turns_by_session = {t["session_id"]: t["turns"] for t in transcripts}
    counts = Counter()
    rows = []
    for ex in read_jsonl(build / "extractions_raw.jsonl"):
        turns = turns_by_session[ex["session_id"]]
        for pref in ex.get("preferences", []):
            if isinstance(pref.get("source_turn_index"), int):
                counts["turn_index_from_extractor"] += 1
                continue
            q = norm(pref.get("source_quote"))
            found = next((t["index"] for t in turns if q and q in norm(t["text"])), None)
            pref["source_turn_index"] = found
            counts["turn_index_derived" if found is not None else "turn_index_unresolved"] += 1
        rows.append(ex)
    write_jsonl(build / "extractions.jsonl", rows)
    return dict(counts)


def run_export(build: Path) -> Path:
    out = build / "export"
    if out.exists():
        return out
    cmd = [sys.executable, "-m", "memdec.export", "--extractions", str(build / "extractions.jsonl"),
           "--transcripts", str(build / "transcripts.jsonl"), "--repos", str(build / "session_repos.json"),
           "--out", str(out), "--seed", str(SEED), "--train-repos", str(SPLIT_REPOS["train"]),
           "--val-repos", str(SPLIT_REPOS["val"]), "--test-repos", str(SPLIT_REPOS["test"])]
    subprocess.run(cmd, check=True)
    return out


def tfidf_vectors(docs: list[list[str]]) -> list[dict[str, float]]:
    df = Counter(tok for doc in docs for tok in set(doc))
    n = len(docs)
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: (1 + math.log(c)) * math.log((1 + n) / (1 + df[t])) for t, c in tf.items()}
        length = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / length for t, v in vec.items()})
    return vectors


def cosine(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def topic_pairs(build: Path, items: list[dict], existing: set[str]) -> list[dict]:
    extractions = {e["session_id"]: e for e in read_jsonl(build / "extractions.jsonl")}
    by_repo = defaultdict(list)
    for item in items:
        sid = item["session_id"]
        n = int(item["item_id"].rsplit(":", 1)[1])
        pref = extractions[sid]["preferences"][n]
        text = " ".join([pref["key"].replace("_", " "), pref.get("about_entity") or "", pref.get("context") or "", pref["source_quote"]])
        by_repo[item["repository_id"]].append({"item": item, "pref": pref, "order": (extractions[sid].get("ended_at") or sid, n),
                                                "tokens": TOKEN.findall(text.lower())})
    pairs = []
    for repo, rows in sorted(by_repo.items()):
        rows.sort(key=lambda r: r["order"])
        vectors = tfidf_vectors([r["tokens"] for r in rows])
        for j, b in enumerate(rows):
            best, best_score = None, MIN_COSINE
            for i in range(j):
                a = rows[i]
                if a["item"]["session_id"] == b["item"]["session_id"] or a["order"][0] == b["order"][0]:
                    continue
                score = cosine(vectors[i], vectors[j])
                if score >= best_score:
                    best, best_score = a, score
            if best is None:
                continue
            a_item, b_item = best["item"], b["item"]
            pair_id = f"{a_item['item_id']}=>{b_item['item_id']}"
            if pair_id in existing:
                continue
            pairs.append({"pair_id": pair_id, "repository_id": repo, "decision_type": "supersedes",
                          "memory_a": {"item": a_item["item"], "quote": a_item["quote"], "session_id": a_item["session_id"]},
                          "memory_b": {"item": b_item["item"], "quote": b_item["quote"], "session_id": b_item["session_id"]},
                          "preference_key": b["pref"]["key"], "render_version": b_item["render_version"],
                          "split": b_item["split"], "pair_rule": "nearest_earlier_same_repo_tfidf",
                          "pair_similarity": round(best_score, 4)})
    return pairs


def state_text(row: dict) -> str:
    if row["decision_type"] == "store_skip":
        return f"{row['transcript_excerpt']}\n{row['item']}\n{row['quote']}"
    return f"{row['memory_a']['item']}\n{row['memory_a']['quote']}\n{row['memory_b']['item']}\n{row['memory_b']['quote']}"


def ngrams(text: str, n: int = 13) -> set[tuple]:
    words = TOKEN.findall(text.lower())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def draw(rows: list[dict], key: str, target: int) -> list[dict]:
    by_repo = defaultdict(list)
    for r in rows:
        by_repo[r["repository_id"]].append(r)
    for repo in by_repo:
        by_repo[repo].sort(key=lambda r: hashlib.sha256(f"{SEED}:{r[key]}".encode()).hexdigest())
    chosen, depth = [], 0
    while len(chosen) < target and any(len(v) > depth for v in by_repo.values()):
        for repo in sorted(by_repo):
            if depth < len(by_repo[repo]) and len(chosen) < target:
                chosen.append(by_repo[repo][depth])
        depth += 1
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(prog="memdec_build.assemble")
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    build = args.build
    turn_counts = prepare_inputs(build)
    export = run_export(build)
    items = read_jsonl(export / "items.jsonl")
    exact_pairs = [{**p, "pair_rule": "exact_key_memdec_export"} for p in read_jsonl(export / "pairs.jsonl")]
    near_pairs = topic_pairs(build, items, {p["pair_id"] for p in exact_pairs})
    all_pairs = exact_pairs + near_pairs
    drawn: dict[str, dict[str, list]] = defaultdict(dict)
    for split in ("train", "val"):
        drawn[split]["store_skip"] = draw([r for r in items if r["split"] == split], "item_id", TARGETS[split]["store_skip"])
        drawn[split]["supersedes"] = draw([r for r in all_pairs if r["split"] == split], "pair_id", TARGETS[split]["supersedes"])
    train_grams = set()
    for rows in drawn["train"].values():
        for r in rows:
            train_grams |= ngrams(state_text(r))
    overlap_dropped = Counter()

    def clean(rows):
        kept = []
        for r in rows:
            grams = ngrams(state_text(r))
            if grams and len(grams & train_grams) / len(grams) >= 0.5:
                overlap_dropped[r["decision_type"]] += 1
                continue
            kept.append(r)
        return kept

    drawn["test"]["store_skip"] = draw(clean([r for r in items if r["split"] == "test"]), "item_id", TARGETS["test"]["store_skip"])
    drawn["test"]["supersedes"] = draw(clean([r for r in all_pairs if r["split"] == "test"]), "pair_id", TARGETS["test"]["supersedes"])
    out = build / "assembled"
    out.mkdir(exist_ok=True)
    final_items = [r for s in ("train", "val", "test") for r in drawn[s]["store_skip"]]
    final_pairs = [r for s in ("train", "val", "test") for r in drawn[s]["supersedes"]]
    write_jsonl(out / "items.jsonl", final_items)
    write_jsonl(out / "pairs.jsonl", final_pairs)
    write_jsonl(out / "store_skip_sheet.jsonl", [{"id": r["item_id"], "transcript_excerpt": r["transcript_excerpt"],
                                                  "item": r["item"], "quote": r["quote"]} for r in final_items])
    write_jsonl(out / "supersedes_sheet.jsonl", [{"id": r["pair_id"], "memory_a": {"item": r["memory_a"]["item"], "quote": r["memory_a"]["quote"]},
                                                  "memory_b": {"item": r["memory_b"]["item"], "quote": r["memory_b"]["quote"]}}
                                                 for r in final_pairs])
    report = {
        "assembled_at": utc_now(), "seed": SEED, "targets": TARGETS,
        "turn_index_fill": turn_counts,
        "pool": {"items": dict(Counter(r["split"] for r in items)),
                 "pairs_exact_key": dict(Counter(r["split"] for r in exact_pairs)),
                 "pairs_topic": dict(Counter(r["split"] for r in near_pairs))},
        "drawn": {s: {k: len(v) for k, v in drawn[s].items()} for s in drawn},
        "drawn_pairs_by_rule": dict(Counter(r["pair_rule"] for r in final_pairs)),
        "drawn_by_repo": {s: {k: dict(Counter(r["repository_id"] for r in v)) for k, v in drawn[s].items()} for s in drawn},
        "test_dropped_13gram_overlap": dict(overlap_dropped),
        "pair_rule_topic": f"for each preference b, the most similar earlier preference a in the same repository and a different thread, TF-IDF cosine over key tokens + about_entity + context + quote, cosine >= {MIN_COSINE}",
        "draw_rule": "per split and decision type, round-robin over repositories (sorted), each repository's candidates in sha256('20260928:'+id) order",
        "overlap_rule": "test state dropped when >= 50% of its word 13-grams occur in any drawn training state (states: excerpt+item+quote; pair: both items and quotes)",
        "export_manifest_sha256": sha256_file(export / "manifest.json"),
        "splits": json.loads((export / "splits.json").read_text()),
    }
    write_json(out / "assemble_report.json", report)
    print(json.dumps({k: report[k] for k in ("pool", "drawn", "drawn_pairs_by_rule", "test_dropped_13gram_overlap", "turn_index_fill")}, indent=1))


if __name__ == "__main__":
    main()
