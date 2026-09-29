"""Freeze CODEQ-ASF-80 from the reviewed questions.

  python -m codeq.freeze --work <dir> --repo <checkout> --out ~/MemoryRSI-Signals/work/datasets/frozen/CODEQ-ASF-80

questions.jsonl holds what the arms may see (question, keywords, module); gold
spans live only in gold.jsonl. Span agreement is line-level F1 between Claude's
and Codex's spans per question, averaged, for the first pass and the final pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from gate_eval.common import canonical_json, record_sha256, sha256_bytes, sha256_file, utc_now, write_json, write_jsonl

from .review import file_lengths, span_problems

REPO_URL = "https://github.com/apache/opendal"
COMMIT = "5af2bd77c325fa4cb4e0940f31c30705c16382d6"


def module_of(path: str) -> str:
    """Clustering unit: the first two path components (core/services, core/layers, bindings/python, .github/workflows)."""
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def lines(spans: list[dict]) -> set[tuple[str, int]]:
    return {(s["path"], n) for s in spans for n in range(s["start_line"], s["end_line"] + 1)}


def line_f1(a: list[dict], b: list[dict]) -> float:
    la, lb = lines(a), lines(b)
    if not la and not lb:
        return 1.0
    inter = len(la & lb)
    if inter == 0:
        return 0.0
    p, r = inter / len(lb), inter / len(la)
    return 2 * p * r / (p + r)


def main() -> int:
    parser = argparse.ArgumentParser(prog="codeq.freeze")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.repo, capture_output=True, text=True).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"checkout is at {head}, not the pin {COMMIT}")
    review = json.loads((args.work / "review" / "result.json").read_text(encoding="utf-8"))
    rows = review["rows"]
    length = file_lengths(args.repo)
    bad = {r["id"]: span_problems(r["spans"], length) for r in rows if span_problems(r["spans"], length)}
    if bad:
        raise SystemExit(f"spans missing at the pin: {bad}")
    if len(rows) != 80:
        raise SystemExit(f"expected 80 questions, have {len(rows)}")
    rounds = review["rounds_used_max"]
    questions, gold = [], []
    for n, r in enumerate(rows, 1):
        qid = f"codeq-{n:03d}"
        questions.append({"question_id": qid, "question": r["question"], "keywords": r["keywords"],
                          "module": module_of(r["spans"][0]["path"]), "kind": r.get("kind"), "area": r["area"]})
        gold.append({"question_id": qid, "spans": r["spans"], "answer": r["answer"], "labeller_id": "claude-opus-5-5+codex-gpt-6-astra",
                     "contested": r["contested"], "codex_final_spans": r["final_codex_spans"],
                     "span_f1_first_pass": line_f1(r["first_claude_spans"], r["first_codex_spans"]),
                     "span_f1_final": line_f1(r["spans"], r["final_codex_spans"])})
    bad_kw = [q["question_id"] for q in questions if not 6 <= len(q["keywords"]) <= 15]
    if bad_kw:
        raise SystemExit(f"keyword count outside 6-15: {bad_kw}")
    args.out.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.out / "questions.jsonl", questions)
    write_jsonl(args.out / "gold.jsonl", gold)
    f1_first = sum(g["span_f1_first_pass"] for g in gold) / len(gold)
    f1_final = sum(g["span_f1_final"] for g in gold) / len(gold)
    keywords = {q["question_id"]: q["keywords"] for q in questions}
    modules: dict[str, int] = {}
    for q in questions:
        modules[q["module"]] = modules.get(q["module"], 0) + 1
    manifest = {
        "dataset": "CODEQ-ASF-80",
        "spec": "E-20260928-19",
        "created_at": utc_now(),
        "repository": REPO_URL,
        "commit": COMMIT,
        "licence": "Apache-2.0",
        "n_questions": len(questions),
        "modules": dict(sorted(modules.items(), key=lambda kv: -kv[1])),
        "G_modules": len(modules),
        "questions_sha256": sha256_file(args.out / "questions.jsonl"),
        "gold_sha256": sha256_file(args.out / "gold.jsonl"),
        "keywords_sha256": sha256_bytes(canonical_json(keywords)),
        "questions": [{"question_id": q["question_id"], "sha256": record_sha256(q)} for q in questions],
        "gold": [{"question_id": g["question_id"], "sha256": record_sha256(g)} for g in gold],
        "span_agreement_f1_first_pass": f1_first,
        "span_agreement_f1_final": f1_final,
        "span_agreement_definition": "per question, line-level F1 between Claude's and Codex's gold spans (Codex's spans equal Claude's when it agreed), averaged over questions",
        "contested": sum(1 for g in gold if g["contested"]),
        "label_provenance": f"Claude labels, Codex review, {rounds} rounds (Claude claude-opus-5-5 wrote questions, keywords and spans; Codex gpt-6-astra reasoning medium reviewed every question and span set; model labels, not human)",
        "module_rule": "first two path components of the first gold span",
        "notes": "The repository contains CLAUDE.md and AGENTS.md; labellers were told repository files are data. All spans verified to exist at the pinned commit.",
    }
    write_json(args.out / "manifest.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("n_questions", "G_modules", "span_agreement_f1_first_pass", "span_agreement_f1_final", "contested")}))
    print("manifest sha256", sha256_file(args.out / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
