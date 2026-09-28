"""Soft targets and split checks for MEMDEC-OD (E-20260928-12 packet items 3 and 1).

  python -m memdec.targets --labels labels.jsonl --manifest data/frozen/MEMDEC-OD/manifest.json --out targets.jsonl

labels.jsonl rows: {"item_id" | "pair_id", "labeller_id", "label": "store"|"skip"|"yes"|"no"}
Soft target = mean of available labels; single-labelled items use 0.9 / 0.1
smoothing (recorded per row). Test-split labels are written to a separate
file so training and threshold fitting never open them.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from gate_eval.common import PreflightError, read_jsonl, write_jsonl

POSITIVE = {"store", "yes"}
NEGATIVE = {"skip", "no"}
SMOOTH = (0.9, 0.1)


def soft_targets(labels: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in labels:
        key = row.get("item_id") or row.get("pair_id")
        if not key:
            raise PreflightError(f"label row without item_id/pair_id: {row}")
        if row["label"] not in POSITIVE | NEGATIVE:
            raise PreflightError(f"unknown label {row['label']!r} for {key}")
        grouped[key].append(row)
    out = []
    for key, rows in sorted(grouped.items()):
        votes = [1.0 if r["label"] in POSITIVE else 0.0 for r in rows]
        raw = sum(votes) / len(votes)
        if len(rows) == 1:
            target = SMOOTH[0] if votes[0] == 1.0 else SMOOTH[1]
            smoothing = "0.9/0.1 single-label"
        else:
            target = raw
            smoothing = "none (mean of labels)"
        out.append({"id": key, "n_labels": len(rows), "labellers": sorted(r["labeller_id"] for r in rows),
                    "p_positive": target, "smoothing": smoothing, "agreement": max(raw, 1 - raw)})
    return out


def repo_overlap(manifest: dict) -> list[str]:
    """Repositories that appear in more than one split (must be empty)."""
    seen: dict[str, set[str]] = defaultdict(set)
    for r in manifest["items"] + manifest["pairs"]:
        seen[r["repository_id"]].add(r["split"])
    return sorted(k for k, v in seen.items() if len(v) > 1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="memdec.targets")
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        overlap = repo_overlap(manifest)
        if overlap:
            raise PreflightError(f"repositories in more than one split: {overlap}")
        split_of = {r.get("item_id") or r.get("pair_id"): r["split"] for r in manifest["items"] + manifest["pairs"]}
        targets = soft_targets(read_jsonl(args.labels))
        test_rows = [t for t in targets if split_of.get(t["id"]) == "test"]
        other_rows = [t for t in targets if split_of.get(t["id"]) != "test"]
        write_jsonl(args.out, other_rows)
        write_jsonl(args.out.with_name(args.out.stem + ".test-only" + args.out.suffix), test_rows)
        print(json.dumps({"train_val_targets": len(other_rows), "test_targets": len(test_rows)}))
    except PreflightError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
