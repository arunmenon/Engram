"""H5-labelled-90: labelling sheet for the loop, then labels.jsonl from its output.

  python -m gate_eval.h5_labels sheet  --items items.jsonl --out sheet.jsonl
  python -m gate_eval.h5_labels labels --loop labels_loop.jsonl --out labels.jsonl

The sheet carries only item_id, transcript_excerpt, item and quote (no bucket, no
extractor confidence). labels.jsonl follows the recipe's shape, with the two model
labellers in place of labellers a and b.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import read_jsonl, write_jsonl
from labelling.loop import cohen_kappa

SHEET_FIELDS = ("item_id", "transcript_excerpt", "item", "quote")
COLUMNS = ("gold_quote_supports_item", "gold_source_type")


def make_sheet(items: Path, out: Path) -> None:
    write_jsonl(out, [{"id": r["item_id"], **{k: r[k] for k in SHEET_FIELDS if k != "item_id"}} for r in read_jsonl(items)])


def make_labels(loop_rows: Path, out: Path) -> dict:
    rows = read_jsonl(loop_rows)
    enc = lambda v: "<null>" if v is None else v
    kappas = {}
    for c in COLUMNS:
        kappas[c] = {
            "first_pass": cohen_kappa([enc(r["first_claude"][c]) for r in rows], [enc(r["first_codex"][c]) for r in rows]),
            "final": cohen_kappa([enc(r["labels"][c]) for r in rows], [enc(r["final_codex"][c]) for r in rows]),
        }
    labels = []
    for r in rows:
        labels.append({
            "item_id": r["id"],
            "labeller_id": "adjudicated",
            "gold_quote_supports_item": r["labels"]["gold_quote_supports_item"],
            "gold_source_type": r["labels"]["gold_source_type"],
            "labeller_a": "claude-opus-5-5 (first pass)",
            "labeller_a_labels": r["first_claude"],
            "labeller_b": "codex gpt-6-astra reasoning medium (first-pass review)",
            "labeller_b_labels": r["first_codex"],
            "adjudication": "Claude's label after up to 3 Claude/Codex rounds",
            "contested": r["contested"],
            "contested_columns": r["contested_columns"],
            "kappa_supports": kappas["gold_quote_supports_item"]["first_pass"],
            "kappa_source_type": kappas["gold_source_type"]["first_pass"],
        })
    write_jsonl(out, labels)
    return {"kappas": kappas, "contested_rows": sum(1 for r in rows if r["contested"])}


def main() -> None:
    parser = argparse.ArgumentParser(prog="gate_eval.h5_labels")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet"); s.add_argument("--items", type=Path, required=True); s.add_argument("--out", type=Path, required=True)
    l = sub.add_parser("labels"); l.add_argument("--loop", type=Path, required=True); l.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "sheet":
        make_sheet(args.items, args.out)
    else:
        print(json.dumps(make_labels(args.loop, args.out), indent=1))


if __name__ == "__main__":
    main()
