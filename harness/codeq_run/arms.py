"""E-20260928-19-r2 arms, packing and scoring over a frozen pool.

  python -m codeq_run.arms jev   --run <dir> --genigrep <checkout> [--repeat 20]
  python -m codeq_run.arms cross --run <dir> --model-dir <bge-reranker-v2-m3 snapshot>   (needs torch)
  python -m codeq_run.arms score --run <dir> --dataset <frozen CODEQ-ASF-80> [--keywords-blind]

<dir> holds pool.jsonl (from codeq_run.pool) and questions.jsonl (the keyword rows used). Arms:
  A        pool in IDF order (lexical floor)
  B        genigrep JevJudge file scores -> genigrep selectFiles (T1 0.6, min 8, max 16, top-5 lexical guard)
           -> JevJudge passage scores over P's windows in the selected files, rel >= T2 0.5, by rel
  B_noguard  B's scores, lexical guard off (no extra calls)
  C        same selection and filter with normalised lexical scores instead of Jev (the source's ablation)
  D        bge-reranker-v2-m3 over every window in P, by score
Packing: windows in score order until 12,000 tokens (o200k_base over the rendered block); a window
that would overflow is skipped. Gold spans are only read by `score`.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from gate_eval.common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl
from gate_eval.stats import cluster_bootstrap, mean

PACK_BUDGET = 12_000
T1, T2 = 0.6, 0.5
MIN_FILES, MAX_FILES, LEXICAL_GUARD = 8, 16, 5
HIT_LINES_PER_FILE, HIT_LINE_CHARS, MAX_LINE_CHARS = 3, 160, 400
COVERAGE = 0.8
MERGE_GAP = 3
ARMS = ("A", "B", "B_noguard", "C", "D")


def pool_by_question(run: Path) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for window in read_jsonl(run / "pool.jsonl"):
        grouped[window["question_id"]].append(window)
    for windows in grouped.values():
        windows.sort(key=lambda w: w["rank_idf"])
    return grouped


def render_window(window: dict) -> str:
    lines = window["text"].split("\n")
    return "\n".join(f"{window['start'] + i}| {line.replace(chr(9), '  ')[:MAX_LINE_CHARS]}" for i, line in enumerate(lines))


def files_in_lexical_order(windows: list[dict]) -> list[dict]:
    """File candidates from the pool: lexical score = sum of IDF of distinct keywords over its windows."""
    by_file: dict[str, list[dict]] = defaultdict(list)
    for w in windows:
        by_file[w["path"]].append(w)
    files = []
    for path, ws in by_file.items():
        keywords = {k for w in ws for k in w["keywords_present"]}
        idf_sum = max(w["lex"] for w in ws) if len(keywords) == 0 else None
        files.append({"path": path, "windows": ws, "keywords": keywords, "idf_sum_hint": idf_sum,
                      "best_rank": min(w["rank_idf"] for w in ws)})
    return files


def file_lex_scores(windows: list[dict], idf: dict[str, float]) -> list[dict]:
    files = files_in_lexical_order(windows)
    for f in files:
        f["lex"] = sum(idf.get(k, 0.0) for k in f["keywords"]) + 0.1 * math.log(1 + sum(len(w["hit_lines"]) for w in f["windows"]))
    files.sort(key=lambda f: (-f["lex"], f["best_rank"], f["path"]))
    return files


def file_descriptor(f: dict, idf: dict[str, float]) -> str:
    hit_lines = []
    for w in f["windows"]:
        lines = w["text"].split("\n")
        for h in w["hit_lines"]:
            text = lines[h - w["start"]] if 0 <= h - w["start"] < len(lines) else ""
            weight = sum(idf.get(k, 0.0) for k in f["keywords"] if k.lower() in text.lower())
            hit_lines.append((weight, h, text.strip()))
    best = sorted({(h, t): wgt for wgt, h, t in hit_lines}.items(), key=lambda kv: (-kv[1], kv[0][0]))[:HIT_LINES_PER_FILE]
    rendered = [f"  {h}: {t[:HIT_LINE_CHARS]}" for (h, t), _ in sorted(best, key=lambda kv: kv[0][0])]
    return "\n".join([f["path"], *rendered])


def select_files(files: list[dict], scores: dict[str, float], guard: bool) -> list[str]:
    """genigrep search.ts selectFiles at da10c5e, re-expressed: guard keeps the top lexical files,
    then files in judge-rank order join if score >= T1 or rank < minFiles, up to maxFiles."""
    ranked = sorted(range(len(files)), key=lambda i: (-(scores.get(files[i]["path"], 0.0)), -files[i]["lex"], i))
    selected: list[int] = []
    if guard:
        selected.extend(range(min(LEXICAL_GUARD, len(files))))
    for rank, i in enumerate(ranked):
        if len(selected) >= MAX_FILES or i in selected:
            continue
        if scores.get(files[i]["path"], 0.0) >= T1 or rank < MIN_FILES:
            selected.append(i)
    return [files[i]["path"] for i in selected]


def idf_for(run: Path) -> dict[str, dict[str, float]]:
    return {s["question_id"]: s["idf"] for s in read_jsonl(run / "pool_stats.jsonl")}


# ----------------------------------------------------------------------------- Jev (arm B)

def run_judge(genigrep: Path, jobs: list[dict], work: Path, label: str) -> list[dict]:
    jobs_path, out_path = work / f"jev_jobs_{label}.json", work / f"jev_out_{label}.json"
    jobs_path.write_text(json.dumps(jobs))
    env = {**os.environ, "GENIGREP_DIR": str(genigrep)}
    subprocess.run(["bun", str(Path(__file__).with_name("judge.ts")), str(jobs_path), str(out_path)],
                   env=env, check=True, stdin=subprocess.DEVNULL)
    results = json.loads(out_path.read_text())
    jobs_path.unlink()
    out_path.unlink()
    return results


def cmd_jev(args) -> int:
    pools = pool_by_question(args.run)
    idf = idf_for(args.run)
    questions = {q["question_id"]: q for q in read_jsonl(args.run / "questions.jsonl")}
    qids = sorted(pools)
    passes = [("main", qids)] + ([("repeat", qids[: args.repeat])] if args.repeat else [])
    all_calls: list[dict] = []
    scores: dict = {}
    for tag, ids in passes:
        file_jobs, file_meta = [], {}
        for qid in ids:
            files = file_lex_scores(pools[qid], idf[qid])
            max_lex = files[0]["lex"] or 1.0
            items = [{"id": f"f{i:03d}", "path": f["path"], "descriptor": file_descriptor(f, idf[qid]), "lex": f["lex"] / max_lex}
                     for i, f in enumerate(files)]
            file_meta[qid] = (files, {it["id"]: it["path"] for it in items})
            file_jobs.append({"question_id": qid, "question": questions[qid]["question"], "stage": "files", "files": items, "tag": tag})
        file_results = run_judge(args.genigrep, file_jobs, args.run, f"{tag}_files")
        passage_jobs = []
        for res in file_results:
            qid = res["question_id"]
            files, id_to_path = file_meta[qid]
            file_scores = {id_to_path[k]: v for k, v in res["scores"].items()}
            guarded = select_files(files, file_scores, guard=True)
            unguarded = select_files(files, file_scores, guard=False)
            scores.setdefault(tag, {})[qid] = {"file_scores": file_scores, "selected_guard": guarded,
                                               "selected_noguard": unguarded, "file_error": res["error"]}
            all_calls.append({"tag": tag, **{k: v for k, v in res.items() if k != "scores"}})
            chosen = set(guarded) | set(unguarded)
            windows = [w for w in pools[qid] if w["path"] in chosen]
            max_lex = max((w["lex"] for w in windows), default=1.0) or 1.0
            items = [{"id": w["window_id"], "path": w["path"], "start": w["start"], "end": w["end"],
                      "text": render_window(w), "lex": w["lex"] / max_lex, "lexCov": []} for w in windows]
            passage_jobs.append({"question_id": qid, "question": questions[qid]["question"], "stage": "passages", "passages": items, "tag": tag})
        for res in run_judge(args.genigrep, passage_jobs, args.run, f"{tag}_passages"):
            scores[tag][res["question_id"]]["passage_scores"] = res["scores"]
            scores[tag][res["question_id"]]["passage_error"] = res["error"]
            all_calls.append({"tag": tag, **{k: v for k, v in res.items() if k != "scores"}})
    write_jsonl(args.run / "jev_calls.jsonl", all_calls)
    write_json(args.run / "jev_scores.json", scores)
    errors = [c for c in all_calls if c["error"]]
    print(f"jev: {len(all_calls)} judge jobs, {len(errors)} errors")
    return 0 if not errors else 3


# ----------------------------------------------------------------------------- cross-encoder (arm D)

def cmd_cross(args) -> int:
    import torch
    from sentence_transformers import CrossEncoder
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = CrossEncoder(str(args.model_dir), device=device, max_length=args.max_length,
                         model_kwargs={"torch_dtype": torch.float16} if device == "mps" else {})
    pools = pool_by_question(args.run)
    questions = {q["question_id"]: q for q in read_jsonl(args.run / "questions.jsonl")}
    partial_path = args.run / "cross_scores.partial.jsonl"
    done = {r["question_id"]: r for r in read_jsonl(partial_path)} if partial_path.exists() else {}
    with open(partial_path, "a") as partial:
        for n, qid in enumerate(sorted(pools)):
            if qid in done:
                continue
            pairs = [(questions[qid]["question"], render_window(w)) for w in pools[qid]]
            tokens = sum(len(model.tokenizer(q, p, truncation=True, max_length=args.max_length)["input_ids"]) for q, p in pairs)
            values = model.predict(pairs, batch_size=16, show_progress_bar=False)
            row = {"question_id": qid, "tokens": tokens, "scores": {w["window_id"]: float(v) for w, v in zip(pools[qid], values)}}
            partial.write(json.dumps(row) + "\n")
            partial.flush()
            done[qid] = row
            print(f"{utc_now()} cross {n + 1}/{len(pools)} {qid} {len(pairs)}", file=sys.stderr, flush=True)
    write_json(args.run / "cross_scores.json", {"model": "BAAI/bge-reranker-v2-m3", "revision": args.model_dir.name,
                                                "device": device, "dtype": "float16" if device == "mps" else "float32",
                                                "max_length": args.max_length, "tokens": sum(r["tokens"] for r in done.values()),
                                                "scores": {q: r["scores"] for q, r in done.items()}})
    partial_path.unlink()
    return 0


# ----------------------------------------------------------------------------- packing and scoring

def token_counter():
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        return (lambda text: len(encoding.encode(text))), "tiktoken o200k_base"
    except ImportError:
        return (lambda text: math.ceil(len(text) / 3.2)), "chars / 3.2 (genigrep charsPerToken)"


def pack(ordered: list[dict], count_tokens) -> tuple[list[dict], int]:
    packed, used = [], 0
    for w in ordered:
        cost = count_tokens(f"== {w['path']}:{w['start']}-{w['end']}\n" + render_window(w))
        if used + cost > PACK_BUDGET:
            continue
        packed.append(w)
        used += cost
    return packed, used


def merged_spans(spans: list[dict]) -> list[tuple[str, int, int]]:
    by_path: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for s in spans:
        by_path[s["path"]].append((s["start_line"], s["end_line"]))
    merged = []
    for path, ranges in by_path.items():
        ranges.sort()
        current = list(ranges[0])
        for a, b in ranges[1:]:
            if a <= current[1] + MERGE_GAP + 1:
                current[1] = max(current[1], b)
            else:
                merged.append((path, current[0], current[1]))
                current = [a, b]
        merged.append((path, current[0], current[1]))
    return merged


def coverage(packed: list[dict], spans: list[tuple[str, int, int]]) -> dict:
    inside: dict[str, set[int]] = defaultdict(set)
    for w in packed:
        inside[w["path"]].update(range(w["start"], w["end"] + 1))
    covered, gold_lines, covered_lines = 0, 0, 0
    for path, a, b in spans:
        lines = set(range(a, b + 1))
        hit = len(lines & inside[path])
        gold_lines += len(lines)
        covered_lines += hit
        covered += 1 if hit / len(lines) >= COVERAGE else 0
    return {"span_recall": covered / len(spans), "line_recall": covered_lines / gold_lines,
            "full_coverage": 1.0 if covered == len(spans) else 0.0, "n_spans": len(spans)}


def arm_orders(qid: str, windows: list[dict], idf: dict, jev: dict | None, cross: dict | None) -> dict[str, list[dict] | None]:
    orders: dict[str, list[dict] | None] = {"A": sorted(windows, key=lambda w: w["rank_idf"])}
    files = file_lex_scores(windows, idf)
    max_file_lex = files[0]["lex"] or 1.0
    lex_file_scores = {f["path"]: f["lex"] / max_file_lex for f in files}
    chosen = set(select_files(files, lex_file_scores, guard=True))
    candidates = [w for w in windows if w["path"] in chosen]
    max_lex = max((w["lex"] for w in candidates), default=1.0) or 1.0
    orders["C"] = sorted([w for w in candidates if w["lex"] / max_lex >= T2], key=lambda w: (-w["lex"], w["rank_idf"]))
    if jev and qid in jev and not jev[qid].get("file_error") and not jev[qid].get("passage_error"):
        rel = jev[qid]["passage_scores"]
        for arm, key in (("B", "selected_guard"), ("B_noguard", "selected_noguard")):
            selected = set(jev[qid][key])
            orders[arm] = sorted([w for w in windows if w["path"] in selected and rel.get(w["window_id"], 0.0) >= T2],
                                 key=lambda w: (-rel[w["window_id"]], w["rank_idf"]))
    else:
        orders["B"] = orders["B_noguard"] = None
    if cross and qid in cross:
        orders["D"] = sorted(windows, key=lambda w: (-cross[qid][w["window_id"]], w["rank_idf"]))
    else:
        orders["D"] = None
    return orders


def cmd_score(args) -> int:
    pools = pool_by_question(args.run)
    idf = idf_for(args.run)
    questions = {q["question_id"]: q for q in read_jsonl(args.run / "questions.jsonl")}
    gold = {g["question_id"]: g for g in read_jsonl(args.dataset / "gold.jsonl")}
    jev_all = json.loads((args.run / "jev_scores.json").read_text()) if (args.run / "jev_scores.json").exists() else {}
    cross_file = args.run / "cross_scores.json"
    cross = json.loads(cross_file.read_text())["scores"] if cross_file.exists() else None
    count_tokens, tokenizer_name = token_counter()
    rows = []
    (args.run / "packs").mkdir(exist_ok=True)
    for qid in sorted(pools):
        spans = merged_spans(gold[qid]["spans"])
        orders = arm_orders(qid, pools[qid], idf[qid], jev_all.get("main"), cross)
        pack_record = {}
        for arm, ordered in orders.items():
            if ordered is None:
                continue
            packed, used = pack(ordered, count_tokens)
            cov = coverage(packed, spans)
            pack_record[arm] = {"windows": [w["window_id"] for w in packed], "tokens": used, "candidates_after_filter": len(ordered)}
            rows.append({"question_id": qid, "module": questions[qid]["module"], "arm": arm, **cov, "pack_tokens": used,
                         "windows_packed": len(packed)})
        write_json(args.run / "packs" / f"{qid}.json", pack_record)
    with open(args.run / "coverage.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    recall = defaultdict(dict)
    for r in rows:
        recall[r["arm"]][r["question_id"]] = r
    module_of = {qid: questions[qid]["module"] for qid in pools}

    def paired(x: str, y: str, field: str = "span_recall") -> dict:
        common = sorted(set(recall[x]) & set(recall[y]))
        diffs = [{"question_id": q, "module": module_of[q], "d": recall[x][q][field] - recall[y][q][field]} for q in common]
        if not diffs:
            return {}
        boot = cluster_bootstrap(diffs, "module", lambda xs: mean([d["d"] for d in xs]), args.resamples, args.seed)
        boot["n"] = len(diffs)
        return boot

    metrics = []
    for arm in ARMS:
        if not recall[arm]:
            continue
        values = list(recall[arm].values())
        metrics.append({"arm": arm, "n": len(values), "span_recall": mean([v["span_recall"] for v in values]),
                        "line_recall": mean([v["line_recall"] for v in values]),
                        "full_coverage_rate": mean([v["full_coverage"] for v in values]),
                        "mean_pack_tokens": mean([v["pack_tokens"] for v in values])})
    contrasts = {name: paired(x, y) for name, x, y in (("B_minus_C", "B", "C"), ("B_minus_A", "B", "A"),
                                                        ("D_minus_B", "D", "B"), ("B_minus_B_noguard", "B", "B_noguard"),
                                                        ("D_minus_C", "D", "C"), ("C_minus_A", "C", "A"))}
    contrasts_line = {name: paired(x, y, "line_recall") for name, x, y in (("B_minus_C", "B", "C"), ("D_minus_B", "D", "B"))}

    # Jev run-to-run: re-scored questions, pack agreement and recall difference
    repeat_rows = []
    for qid, rep in (jev_all.get("repeat") or {}).items():
        spans = merged_spans(gold[qid]["spans"])
        orders = arm_orders(qid, pools[qid], idf[qid], {qid: rep}, None)
        if orders["B"] is None:
            continue
        packed, _ = pack(orders["B"], count_tokens)
        first = set(json.loads((args.run / "packs" / f"{qid}.json").read_text())["B"]["windows"])
        second = {w["window_id"] for w in packed}
        repeat_rows.append({"question_id": qid, "recall_main": recall["B"][qid]["span_recall"],
                            "recall_repeat": coverage(packed, spans)["span_recall"],
                            "pack_jaccard": len(first & second) / max(1, len(first | second))})

    manifest = json.loads((args.run / "run_manifest.json").read_text()) if (args.run / "run_manifest.json").exists() else {}
    validity = manifest.get("validity", {})
    valid = all(validity.values()) if validity else False
    bc, db, ba = contrasts.get("B_minus_C", {}), contrasts.get("D_minus_B", {}), contrasts.get("B_minus_A", {})
    if not valid:
        outcome = "invalid"
    elif not bc:
        outcome = "invalid"
    elif bc["ci95_two_sided"][1] < 0.05:
        outcome = "negative"
    elif db and db["lb95"] > -0.03:
        outcome = "local_reranker_preferred"
    elif bc["point"] >= 0.05 and bc["ci95_two_sided"][0] > 0 and ba and ba["ci95_two_sided"][0] > 0:
        outcome = "positive"
    else:
        outcome = "inconclusive"
    # what the rule would say if the validity checks that fail were waived (reported, not the outcome)
    if not bc:
        outcome_if_valid = "n/a"
    elif bc["ci95_two_sided"][1] < 0.05:
        outcome_if_valid = "negative"
    elif db and db["lb95"] > -0.03:
        outcome_if_valid = "local_reranker_preferred"
    elif bc["point"] >= 0.05 and bc["ci95_two_sided"][0] > 0 and ba and ba["ci95_two_sided"][0] > 0:
        outcome_if_valid = "positive"
    else:
        outcome_if_valid = "inconclusive"

    def slim(b: dict) -> dict:
        return {k: b.get(k) for k in ("point", "ci95_two_sided", "lb95", "ub95", "G", "n")} if b else {}

    rule_inputs = {"validity": validity, "valid": valid, "contrasts_span_recall": {k: slim(v) for k, v in contrasts.items()},
                   "contrasts_line_recall": {k: slim(v) for k, v in contrasts_line.items()},
                   "guard_effect": slim(contrasts.get("B_minus_B_noguard", {})), "rule_outcome": outcome,
                   "rule_outcome_if_validity_waived": outcome_if_valid, "metrics": metrics,
                   "jev_repeat": {"n": len(repeat_rows),
                                  "mean_abs_recall_change": mean([abs(r["recall_main"] - r["recall_repeat"]) for r in repeat_rows]) if repeat_rows else None,
                                  "mean_pack_jaccard": mean([r["pack_jaccard"] for r in repeat_rows]) if repeat_rows else None},
                   "pack_budget_tokens": PACK_BUDGET, "tokenizer": tokenizer_name, "bootstrap": {"resamples": args.resamples, "seed": args.seed,
                                                                                               "cluster": "module (first two path components of first gold span)"}}
    write_json(args.run / "rule_inputs.json", rule_inputs)
    with open(args.run / "metrics.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(metrics[0].keys()))
        writer.writeheader()
        writer.writerows(metrics)
    write_jsonl(args.run / "jev_repeat.jsonl", repeat_rows)
    print(json.dumps({"rule_outcome": outcome, "if_validity_waived": outcome_if_valid, "metrics": metrics,
                      "B_minus_C": slim(bc), "D_minus_B": slim(db), "B_minus_A": slim(ba)}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeq_run.arms")
    sub = parser.add_subparsers(dest="command", required=True)
    p_jev = sub.add_parser("jev")
    p_jev.add_argument("--run", type=Path, required=True)
    p_jev.add_argument("--genigrep", type=Path, required=True)
    p_jev.add_argument("--repeat", type=int, default=20)
    p_cross = sub.add_parser("cross")
    p_cross.add_argument("--run", type=Path, required=True)
    p_cross.add_argument("--model-dir", type=Path, required=True)
    p_cross.add_argument("--max-length", type=int, default=512)
    p_score = sub.add_parser("score")
    p_score.add_argument("--run", type=Path, required=True)
    p_score.add_argument("--dataset", type=Path, required=True)
    p_score.add_argument("--resamples", type=int, default=10_000)
    p_score.add_argument("--seed", type=int, default=20261019)
    args = parser.parse_args(argv)
    return {"jev": cmd_jev, "cross": cmd_cross, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
