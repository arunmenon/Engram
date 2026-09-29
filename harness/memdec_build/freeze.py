"""Freeze MEMDEC-ASF-6200 from the assembled candidates and the labelling-loop output.

  python -m memdec_build.freeze --build <build dir> --out ~/MemoryRSI-Signals/work/datasets/frozen/MEMDEC-ASF-6200/ \
      [--parquet-python <python with pyarrow>]

Frozen files:
  items.jsonl, pairs.jsonl, splits.json   memdec.export shape (items keep extractor fields; labellers never saw them)
  labels.jsonl                             memdec.targets shape: one row per labeller per id
                                           (claude-opus-5-5 final label, gpt-6-astra-codex final label)
  labels_detail.jsonl                      per id: first-pass and final labels of both, contested flag, rounds
  rubrics/                                 the frozen labelling instructions
  manifest.json                            per-record sha256, project, split, labeller ids, sources, counts, kappas
  parquet/                                 Parquet copies of items, pairs and labels (when pyarrow is available)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from gate_eval.common import read_jsonl, record_sha256, sha256_file, utc_now, write_json, write_jsonl
from labelling.loop import cohen_kappa

CLAUDE_ID = "claude-opus-5-5"
CODEX_ID = "gpt-6-astra-codex"
HERE = Path(__file__).parent


def kappa_block(rows: list[dict], split_of: dict[str, str]) -> dict:
    out = {}
    for scope in ("all", "train", "val", "test"):
        sel = [r for r in rows if scope == "all" or split_of[r["id"]] == scope]
        if not sel:
            continue
        out[scope] = {
            "n": len(sel),
            "kappa_first_pass": cohen_kappa([r["first_claude"]["label"] for r in sel], [r["first_codex"]["label"] for r in sel]),
            "kappa_final": cohen_kappa([r["labels"]["label"] for r in sel], [r["final_codex"]["label"] for r in sel]),
            "agreement_first_pass": sum(r["first_claude"]["label"] == r["first_codex"]["label"] for r in sel) / len(sel),
            "agreement_final": sum(r["labels"]["label"] == r["final_codex"]["label"] for r in sel) / len(sel),
            "contested": sum(1 for r in sel if r["contested"]),
            "final_distribution_claude": dict(Counter(r["labels"]["label"] for r in sel)),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="memdec_build.freeze")
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--parquet-python", type=Path)
    args = parser.parse_args()
    build, out = args.build, args.out
    assembled = build / "assembled"
    items = read_jsonl(assembled / "items.jsonl")
    pairs = read_jsonl(assembled / "pairs.jsonl")
    loop_rows = {"store_skip": read_jsonl(build / "labels" / "store_skip.jsonl"),
                 "supersedes": read_jsonl(build / "labels" / "supersedes.jsonl")}
    split_of = {r["item_id"]: r["split"] for r in items} | {r["pair_id"]: r["split"] for r in pairs}
    id_key = {"store_skip": "item_id", "supersedes": "pair_id"}
    for kind, rows in loop_rows.items():
        expected = {r["item_id"] for r in items} if kind == "store_skip" else {r["pair_id"] for r in pairs}
        got = {r["id"] for r in rows}
        if expected != got:
            raise SystemExit(f"{kind}: label ids do not match candidates (missing {len(expected - got)}, extra {len(got - expected)})")
    labels, detail = [], []
    for kind, rows in loop_rows.items():
        for r in rows:
            for labeller, value in ((CLAUDE_ID, r["labels"]["label"]), (CODEX_ID, r["final_codex"]["label"])):
                labels.append({id_key[kind]: r["id"], "labeller_id": labeller, "label": value, "decision_type": kind,
                               "split": split_of[r["id"]]})
            detail.append({"id": r["id"], "decision_type": kind, "split": split_of[r["id"]],
                           "claude_first": r["first_claude"]["label"], "codex_first": r["first_codex"]["label"],
                           "claude_final": r["labels"]["label"], "codex_final": r["final_codex"]["label"],
                           "gold": r["labels"]["label"], "contested": r["contested"],
                           "rounds": max((h["round"] for h in r["history"]["label"]), default=1)})
    out.mkdir(parents=True, exist_ok=False)
    write_jsonl(out / "items.jsonl", items)
    write_jsonl(out / "pairs.jsonl", pairs)
    splits = json.loads((build / "export" / "splits.json").read_text())
    write_json(out / "splits.json", splits)
    write_jsonl(out / "labels.jsonl", labels)
    write_jsonl(out / "labels_detail.jsonl", detail)
    shutil.copytree(HERE / "rubrics", out / "rubrics")
    shutil.copyfile(HERE / "projects.yaml", out / "projects.yaml")
    report = json.loads((assembled / "assemble_report.json").read_text())
    fetch = json.loads((build / "fetch_manifest.json").read_text())
    extraction = json.loads((build / "extraction_manifest.json").read_text())
    rounds_used = {kind: json.loads((build / "labels" / f"{kind}.summary.json").read_text())["rounds_used_max"] for kind in loop_rows}
    counts = Counter()
    for r in items:
        counts[f"items/{r['split']}"] += 1
    for r in pairs:
        counts[f"pairs/{r['split']}"] += 1
    parquet_note = "not written"
    if args.parquet_python:
        pq_dir = out / "parquet"
        pq_dir.mkdir()
        script = ("import json,sys,pyarrow as pa,pyarrow.parquet as pq\n"
                  "for name in ('items','pairs','labels','labels_detail'):\n"
                  "    rows=[json.loads(l) for l in open(sys.argv[1]+'/'+name+'.jsonl')]\n"
                  "    rows=[{k:(json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v) for k,v in r.items()} for r in rows]\n"
                  "    pq.write_table(pa.Table.from_pylist(rows), sys.argv[2]+'/'+name+'.parquet')\n")
        subprocess.run([str(args.parquet_python), "-c", script, str(out), str(pq_dir)], check=True)
        parquet_note = "parquet/ holds Parquet copies (nested fields as JSON strings); the JSONL files are canonical and hashed per record"
    manifest = {
        "dataset": "MEMDEC-ASF-6200", "spec": "E-20260928-12-r2", "frozen_at": utc_now(),
        "render_version": items[0]["render_version"] if items else None,
        "counts": dict(counts), "repositories": len(splits["repositories"]),
        "split_repositories": {s: sorted(k for k, v in splits["repositories"].items() if v == s) for s in ("train", "val", "test")},
        "items": [{"item_id": r["item_id"], "repository_id": r["repository_id"], "split": r["split"], "sha256": record_sha256(r)} for r in items],
        "pairs": [{"pair_id": r["pair_id"], "repository_id": r["repository_id"], "split": r["split"], "pair_rule": r.get("pair_rule"),
                   "sha256": record_sha256(r)} for r in pairs],
        "labels": [{"id": r.get("item_id") or r.get("pair_id"), "labeller_id": r["labeller_id"], "sha256": record_sha256(r)} for r in labels],
        "file_sha256": {name: sha256_file(out / name) for name in ("items.jsonl", "pairs.jsonl", "splits.json", "labels.jsonl", "labels_detail.jsonl", "projects.yaml")},
        "rubric_sha256": {p.name: sha256_file(p) for p in sorted((out / "rubrics").iterdir())},
        "labellers": [CLAUDE_ID, CODEX_ID],
        "label_provenance": f"Claude labels, Codex review, up to 3 rounds (store_skip used {rounds_used['store_skip']}, supersedes used {rounds_used['supersedes']}); model labels, counted as gold for the fast-track queue (CTO, 2026-09-29). Every item and pair carries both labellers' final labels (double-labelled); `gold` in labels_detail is Claude's final label; contested rows are those Codex still disputed after the last round.",
        "kappa": {kind: kappa_block(rows, split_of) for kind, rows in loop_rows.items()},
        "sources": {"projects": "projects.yaml (public ASF GitHub repositories, Apache-2.0)", "cutoff": fetch["cutoff"],
                    "selection": fetch["selection"], "sessions_fetched": fetch["sessions_total"],
                    "per_repo": fetch["per_repo"], "commit_note": "sources are issue and pull-request threads fetched through the GitHub API with a creation cutoff, not repository commits; each item's session_id names repository, kind and number"},
        "pseudonymisation": fetch["pseudonymisation"], "distinct_handles_pseudonymised": fetch.get("distinct_handles_pseudonymised"),
        "secret_scan": {"patterns": fetch["secret_scan"], "threads_dropped": fetch["dropped_secret_total"]},
        "extraction": extraction,
        "assembly": {k: report[k] for k in ("turn_index_fill", "pool", "drawn", "drawn_pairs_by_rule", "test_dropped_13gram_overlap",
                                            "pair_rule_topic", "draw_rule", "overlap_rule", "export_manifest_sha256")},
        "parquet": parquet_note,
        "known_gaps": [
            "Supersession candidates: memdec.export's exact-key rule yields almost no pairs because preference keys are free text; most pairs come from the recorded same-repository nearest-earlier TF-IDF rule (pair_rule per pair).",
            "Labels are model labels (Claude and Codex), not human labels; kappa is between the two models.",
            "The spec's 600 single-labelled training items plus double-labelled subset is exceeded: every row carries two labels.",
            "Pseudonymisation covers GitHub handles, @mentions, emails and sign-off trailers; plain-text given names inside comment bodies are not rewritten.",
        ],
    }
    write_json(out / "manifest.json", manifest)
    print(json.dumps({"counts": manifest["counts"], "kappa": manifest["kappa"]}, indent=1))


if __name__ == "__main__":
    main()
