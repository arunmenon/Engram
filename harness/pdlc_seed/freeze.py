"""Freeze PDLC-SEED-ASF, LINK-ASF-LOCOMO and SEATSWAP-LOCOMO-PDLC.

  python3 -m pdlc_seed.freeze --build <build dir> --locomo <locomo10.json> --out <frozen root>

Refuses to overwrite an existing frozen directory. Every JSONL record gets a
sha256 (canonical JSON, sorted keys) in the manifest; labels live in their own
files, apart from the items.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from gate_eval.common import record_sha256, sha256_file, utc_now

PIN = json.loads((Path.home() / "MemoryRSI-Signals/work/datasets/PDLC-SEED-ASF.pin.json").read_text())
LOCOMO_SHA = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
LOCOMO_SOURCE = {"url": "https://github.com/snap-research/locomo", "commit": "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376",
                 "file": "data/locomo10.json", "sha256": LOCOMO_SHA, "licence": "CC BY-NC 4.0 (Attribution-NonCommercial 4.0 International)"}
LOCOMO_SEED = "linkeval-locomo-2-v1"
PROVENANCE = "Claude labels (claude-opus-5-5), Codex review (gpt-6-astra, reasoning medium), up to 3 rounds; model labels, used as gold for the fast-track experiments"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def file_entry(path: Path, id_field: str | None) -> dict:
    entry = {"sha256": sha256_file(path)}
    if id_field:
        rows = read_jsonl(path)
        entry["n"] = len(rows)
        entry["records"] = [{"id": r[id_field], "sha256": record_sha256(r)} for r in rows]
    return entry


def write_manifest(d: Path, manifest: dict) -> str:
    path = d / "manifest.json"
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_file(path)


def harness_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent).stdout.strip()


def freeze_seed(build: Path, out: Path) -> str:
    d = out / "PDLC-SEED-ASF"
    d.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(build / "records.jsonl", d / "records.jsonl")
    drafts = {q["question_id"]: q for q in json.loads((build / "questions/drafts.json").read_text())}
    loop = {r["id"]: r for r in read_jsonl(build / "questions/labels_loop.jsonl")}
    summary = json.loads((build / "questions/labels_loop.summary.json").read_text())
    questions, gold = [], []
    for qid in sorted(drafts):
        q, lab = drafts[qid], loop[qid]
        questions.append({"question_id": qid, "family": q["family"], "question": q["question"], "slice_rfcs": q["group_rfcs"]})
        ids = [s.strip() for s in str(lab["labels"]["supporting_record_ids"] or "").replace(";", ",").split(",") if s.strip()]
        gold.append({"question_id": qid, "labeller_id": "adjudicated", "gold_answer": lab["labels"]["gold_answer"],
                     "supporting_record_ids": ids, "answerable": lab["labels"]["answerable"], "family_fit": lab["labels"]["family_fit"],
                     "contested": lab["contested"], "contested_columns": lab["contested_columns"],
                     "author_draft_answer": q["gold_answer"], "author_supporting_record_ids": q["supporting_record_ids"],
                     "first_pass": {"claude": lab["first_claude"], "codex": lab["first_codex"]}, "final_codex": lab["final_codex"]})
    write_jsonl(d / "questions.jsonl", questions)
    write_jsonl(d / "questions_gold.jsonl", gold)
    shutil.copyfile(build / "questions/labels_loop.jsonl", d / "questions_label_history.jsonl")
    report = json.loads((build / "build_report.json").read_text())
    manifest = {
        "dataset": "PDLC-SEED-ASF", "frozen_at": utc_now(), "harness_commit": harness_commit(),
        "source": {"project": PIN["project"], "repository": PIN["repository"], "commit": PIN["commit"], "pinned_date": PIN["pinned_date"],
                   "licence": PIN["licence"], "fetched_with": "gh api (REST), cached; harness/pdlc_seed/fetch.py",
                   "slice": "26 RFCs (design proposals) with their RFC PRs, tracking issues, cross-referencing PRs and issues created on or before the pinned date, CI check runs on each PR head, and the 40 most-touched code modules at the pinned commit"},
        "records": report["records"], "records_by_type": report["by_type"],
        "record_types_note": "No Constraint records: the sources carry no separate constraint documents and none were invented. Requirement records are feature-request issues (4); other issues are Tickets.",
        "pseudonymisation": {"method": "HMAC-SHA256 keyed pseudonyms (key kept outside the dataset) for GitHub logins, @mentions and e-mail addresses; Signed-off-by/Co-authored-by trailers blanked", **report["pseudonymisation"]},
        "secret_scan": {"method": "regex patterns (no gitleaks/trufflehog installed on this host)", "patterns": report["secret_scan"]["patterns"],
                        "records_dropped": len(report["secret_scan"]["dropped"])},
        "questions": {"n": len(questions), "by_family": dict(collections.Counter(q["family"] for q in questions)),
                      "authoring": "Claude (claude-opus-5-5) wrote 20 questions per group of RFC slices (4 per family) from the records; a fresh Claude call then answered each question from its cited records plus 3 same-slice distractors (never seeing the draft answer), and Codex reviewed every answer and judgement",
                      "answerable": dict(collections.Counter(g["answerable"] for g in gold)),
                      "family_fit": dict(collections.Counter(g["family_fit"] for g in gold)),
                      "contested": sum(1 for g in gold if g["contested"])},
        "label_provenance": PROVENANCE, "label_agreement": summary,
        "files": {"records.jsonl": file_entry(d / "records.jsonl", "record_id"),
                  "questions.jsonl": file_entry(d / "questions.jsonl", "question_id"),
                  "questions_gold.jsonl": file_entry(d / "questions_gold.jsonl", "question_id"),
                  "questions_label_history.jsonl": file_entry(d / "questions_label_history.jsonl", None)},
        "gold_isolation": "questions_gold.jsonl and questions_label_history.jsonl are for scorers only; runners render from records.jsonl and questions.jsonl",
    }
    return write_manifest(d, manifest)


def pick_locomo(locomo: list[dict]) -> list[str]:
    ids = sorted(c["sample_id"] for c in locomo)
    return sorted(ids, key=lambda s: hashlib.sha256(f"{LOCOMO_SEED}|{s}".encode()).hexdigest())[:2]


def freeze_link(build: Path, locomo_path: Path, out: Path, seed_manifest_sha: str) -> str:
    d = out / "LINK-ASF-LOCOMO"
    (d / "locomo").mkdir(parents=True, exist_ok=False)
    shutil.copyfile(locomo_path, d / "locomo/locomo10.json")
    assert sha256_file(d / "locomo/locomo10.json") == LOCOMO_SHA
    locomo = json.loads(locomo_path.read_text())
    chosen = pick_locomo(locomo)
    (d / "locomo/conversations_2.json").write_text(json.dumps({"seed_rule": f"sort sample_id by sha256('{LOCOMO_SEED}|'+sample_id), take the first 2", "sample_ids": chosen}, indent=1) + "\n")
    links = build / "links"
    for name in ("pairs_test.jsonl", "pairs_dev.jsonl", "rubric.md"):
        shutil.copyfile(links / name, d / name)
    meta = {m["pair_id"]: m for m in read_jsonl(links / "pairs_meta.jsonl")}
    write_jsonl(d / "pairs_candidates_meta.jsonl", [meta[k] for k in sorted(meta)])
    loop = read_jsonl(links / "label/labels_loop.jsonl")
    summary = json.loads((links / "label/labels_loop.summary.json").read_text())
    labels = [{"pair_id": r["id"], "labeller_id": "adjudicated", "link_type": r["labels"]["link_type"], "contested": r["contested"],
               "claude_first": r["first_claude"]["link_type"], "codex_first": r["first_codex"]["link_type"],
               "codex_final": r["final_codex"]["link_type"], "split": "test" if r["id"].startswith("link-test") else "dev"} for r in loop]
    labels.sort(key=lambda r: r["pair_id"])
    write_jsonl(d / "labels.jsonl", labels)
    shutil.copyfile(links / "label/labels_loop.jsonl", d / "labels_history.jsonl")
    per_split = {s: {"n": sum(1 for l in labels if l["split"] == s),
                     "by_link_type": dict(collections.Counter(l["link_type"] for l in labels if l["split"] == s)),
                     "by_generator": dict(collections.Counter(meta[l["pair_id"]]["generator"] for l in labels if l["split"] == s))}
                 for s in ("test", "dev")}
    manifest = {
        "dataset": "LINK-ASF-LOCOMO", "frozen_at": utc_now(), "harness_commit": harness_commit(), "spec": "E-20260928-18",
        "pdlc_seed": {"dataset": "PDLC-SEED-ASF", "manifest_sha256": seed_manifest_sha, "path": "../PDLC-SEED-ASF/"},
        "locomo": {**LOCOMO_SOURCE, "path": "locomo/locomo10.json", "conversations_2": chosen, "seed": LOCOMO_SEED},
        "pairs": {"generators": "explicit_ref (issue/PR/RFC numbers in title, body or branch), ci_head (CI record to the PR it ran on and that PR's tickets), module_touch (PR or its CI to a changed code module), dependency_phrase (none found in this slice), lexical (top TF-IDF near misses without explicit reference)",
                  "draw": "stratified by generator with seed 'pdlc-seed-asf-links-v1' (sha256 order), 300 test + 100 dev", "splits": per_split,
                  "clustering_unit": "write_record_id (the later-created record of the pair)"},
        "label_provenance": PROVENANCE, "label_agreement": summary,
        "label_scheme": "single choice per ordered pair: implements | verifies | refines | satisfies | blocks | none (rubric.md)",
        "gaps": ["The spec draws pairs from the union of pairs each arm proposes plus deterministic candidates; arm outputs (Jev A, extractor B) do not exist yet, so this pool holds deterministic and lexical candidates only. The executor may need to label arm-proposed pairs outside this pool (same rubric) before scoring recall-sensitive metrics.",
                 "LoCoMo link pairs (300 test + 100 dev on the 2 conversations) are not built: they require arm outputs and are out of scope for the labelling session. The LoCoMo QA for answer accuracy is in locomo10.json.",
                 "The 120 PDLC questions live in PDLC-SEED-ASF (questions.jsonl, gold apart).",
                 "blocks is rare: the slice has no in-slice dependency phrases; blocks can only come from labeller judgement on CI or explicit-reference pairs.",
                 "Labels are a single choice per pair, not independent binary labels per link type."],
        "files": {"pairs_test.jsonl": file_entry(d / "pairs_test.jsonl", "pair_id"), "pairs_dev.jsonl": file_entry(d / "pairs_dev.jsonl", "pair_id"),
                  "pairs_candidates_meta.jsonl": file_entry(d / "pairs_candidates_meta.jsonl", "pair_id"),
                  "labels.jsonl": file_entry(d / "labels.jsonl", "pair_id"), "labels_history.jsonl": file_entry(d / "labels_history.jsonl", None),
                  "rubric.md": file_entry(d / "rubric.md", None), "locomo/locomo10.json": file_entry(d / "locomo/locomo10.json", None),
                  "locomo/conversations_2.json": file_entry(d / "locomo/conversations_2.json", None)},
        "gold_isolation": "labels.jsonl, labels_history.jsonl and pairs_candidates_meta.jsonl are for scorers only",
    }
    return write_manifest(d, manifest)


def freeze_seatswap(locomo_path: Path, out: Path, seed_manifest_sha: str) -> str:
    d = out / "SEATSWAP-LOCOMO-PDLC"
    (d / "locomo").mkdir(parents=True, exist_ok=False)
    shutil.copyfile(locomo_path, d / "locomo/locomo10.json")
    locomo = json.loads(locomo_path.read_text())
    index = [{"qa_id": f"{c['sample_id']}#qa{n:03d}", "sample_id": c["sample_id"], "qa_index": n, "category": qa.get("category"),
              "decision_set": "answerable_cat1_4" if qa.get("category") in (1, 2, 3, 4) else "adversarial_reported_separately"}
             for c in locomo for n, qa in enumerate(c["qa"])]
    write_jsonl(d / "locomo/qa_index.jsonl", index)
    seed = out / "PDLC-SEED-ASF"
    (d / "pdlc").mkdir()
    for name in ("records.jsonl", "questions.jsonl", "questions_gold.jsonl"):
        shutil.copyfile(seed / name, d / "pdlc" / name)
    manifest = {
        "dataset": "SEATSWAP-LOCOMO-PDLC", "frozen_at": utc_now(), "harness_commit": harness_commit(), "spec": "E-20260928-20",
        "locomo": {**LOCOMO_SOURCE, "path": "locomo/locomo10.json",
                   "qa": {"total": len(index), "answerable_cat1_4": sum(1 for q in index if q["decision_set"] == "answerable_cat1_4"),
                          "adversarial_cat5": sum(1 for q in index if q["decision_set"] != "answerable_cat1_4")},
                   "note": "LoCoMo carries its own questions and answers; qa_index.jsonl only enumerates them and marks the decision set (categories 1-4) versus adversarial (category 5, reported separately)."},
        "pdlc": {"dataset": "PDLC-SEED-ASF", "manifest_sha256": seed_manifest_sha, "copied": ["records.jsonl", "questions.jsonl", "questions_gold.jsonl"],
                 "role": "harm screen: 120 questions, gold in questions_gold.jsonl (scorers only)"},
        "label_provenance": PROVENANCE + " (PDLC question gold); LoCoMo gold is the benchmark's own",
        "files": {"locomo/locomo10.json": file_entry(d / "locomo/locomo10.json", None),
                  "locomo/qa_index.jsonl": file_entry(d / "locomo/qa_index.jsonl", "qa_id"),
                  "pdlc/records.jsonl": file_entry(d / "pdlc/records.jsonl", "record_id"),
                  "pdlc/questions.jsonl": file_entry(d / "pdlc/questions.jsonl", "question_id"),
                  "pdlc/questions_gold.jsonl": file_entry(d / "pdlc/questions_gold.jsonl", "question_id")},
        "gaps": ["The LoCoMo 'extractor set' is the benchmark itself; extraction outputs per arm are produced by the executor's seatswap harness, not frozen here."],
    }
    return write_manifest(d, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--locomo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only", choices=["all", "seed", "link", "seatswap"], default="all")
    args = parser.parse_args()
    seed_manifest = args.out / "PDLC-SEED-ASF" / "manifest.json"
    if args.only in ("all", "seed"):
        print("PDLC-SEED-ASF", freeze_seed(args.build, args.out))
    sha = sha256_file(seed_manifest)
    if args.only in ("all", "link"):
        print("LINK-ASF-LOCOMO", freeze_link(args.build, args.locomo, args.out, sha))
    if args.only in ("all", "seatswap"):
        print("SEATSWAP-LOCOMO-PDLC", freeze_seatswap(args.locomo, args.out, sha))


if __name__ == "__main__":
    main()
