"""Freeze a labelled dataset: per-item hashes, cluster counts, manifest.

Usage:
  python -m gate_eval.freeze build  --items items.jsonl --labels labels.jsonl --out data/frozen/<name>/
  python -m gate_eval.freeze verify --manifest data/frozen/<name>/manifest.json

The freezer never edits items or labels. It copies them byte-for-byte into the
frozen directory, hashes every record, and writes manifest.json. Labels are kept
in labels.jsonl, which the renderer never opens (only the scorer does).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

from .common import PreflightError, read_jsonl, record_sha256, sha256_file, utc_now, write_json

REQUIRED_ITEM_FIELDS = ("item_id", "source_document_id")
REQUIRED_LABEL_FIELDS = ("item_id", "labeller_id")


def build_manifest(items_path: Path, labels_path: Path, dataset_name: str, gold_columns: list[str]) -> dict:
    items = read_jsonl(items_path)
    labels = read_jsonl(labels_path)
    for row in items:
        for f in REQUIRED_ITEM_FIELDS:
            if f not in row:
                raise PreflightError(f"item lacks {f}: {row}")
    for row in labels:
        for f in REQUIRED_LABEL_FIELDS:
            if f not in row:
                raise PreflightError(f"label lacks {f}: {row}")
    item_ids = [r["item_id"] for r in items]
    if len(set(item_ids)) != len(item_ids):
        raise PreflightError("duplicate item_id in items")
    label_ids = {r["item_id"] for r in labels}
    unlabelled = sorted(set(item_ids) - label_ids)
    extra = sorted(label_ids - set(item_ids))
    if unlabelled or extra:
        raise PreflightError(f"label/item mismatch; unlabelled={unlabelled[:5]} extra={extra[:5]}")
    docs = Counter(r["source_document_id"] for r in items)
    G = len(docs)
    gold_counts = {}
    for col in gold_columns:
        gold_counts[col] = sum(1 for r in labels if r.get(col) is not None)
    return {
        "dataset": dataset_name,
        "frozen_at": utc_now(),
        "n_items": len(items),
        "G_source_documents": G,
        "mean_items_per_document": len(items) / G if G else float("nan"),
        "items_per_document_distribution": sorted(docs.values(), reverse=True),
        "gold_counts": gold_counts,
        "items_sha256": sha256_file(items_path),
        "labels_sha256": sha256_file(labels_path),
        "items": [{"item_id": r["item_id"], "source_document_id": r["source_document_id"], "sha256": record_sha256(r)} for r in items],
        "labels": [{"item_id": r["item_id"], "sha256": record_sha256(r)} for r in labels],
    }


def verify_manifest(manifest_path: Path) -> dict:
    import json
    if not manifest_path.exists():
        raise PreflightError(f"frozen manifest not found: {manifest_path} (dataset not frozen)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    d = manifest_path.parent
    problems = []
    for name in ("items.jsonl", "labels.jsonl"):
        if not (d / name).exists():
            raise PreflightError(f"frozen file missing: {d / name}")
    if sha256_file(d / "items.jsonl") != manifest["items_sha256"]:
        problems.append("items.jsonl hash differs from manifest")
    if sha256_file(d / "labels.jsonl") != manifest["labels_sha256"]:
        problems.append("labels.jsonl hash differs from manifest")
    items = {r["item_id"]: record_sha256(r) for r in read_jsonl(d / "items.jsonl")}
    for entry in manifest["items"]:
        if items.get(entry["item_id"]) != entry["sha256"]:
            problems.append(f"item {entry['item_id']} hash differs")
    if problems:
        raise PreflightError("frozen dataset verification failed: " + "; ".join(problems))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gate_eval.freeze")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--items", type=Path, required=True)
    b.add_argument("--labels", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--name", required=True)
    b.add_argument("--gold-column", action="append", default=[])
    v = sub.add_parser("verify")
    v.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "build":
            args.out.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(args.items, args.out / "items.jsonl")
            shutil.copyfile(args.labels, args.out / "labels.jsonl")
            manifest = build_manifest(args.out / "items.jsonl", args.out / "labels.jsonl", args.name, args.gold_column)
            write_json(args.out / "manifest.json", manifest)
            print(f"frozen {manifest['n_items']} items, G={manifest['G_source_documents']}, manifest sha256 {sha256_file(args.out / 'manifest.json')}")
        else:
            m = verify_manifest(args.manifest)
            print(f"ok: {m['dataset']} n={m['n_items']} G={m['G_source_documents']}")
    except PreflightError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
