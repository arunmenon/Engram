"""Re-run the naming audit's payload-delivery check offline from recorded billed tokens.

  python -m gate_eval.payload_recheck --run runs/<run id>/ --templates templates/naming_audit/

No calls. Keeps the runner's verdict per row as `payload_check_runner` and writes the recomputed
one to `payload_check`, with the tokenizer used, then rewrites invalid_items.csv. Needs tiktoken.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from . import render as R
from .common import read_jsonl, write_jsonl
from .naming_audit import payload_delivery_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gate_eval.payload_recheck")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--templates", type=Path, required=True)
    args = parser.parse_args(argv)
    import tiktoken  # noqa: F401  (required: the recheck exists to use a real tokenizer)
    templates = {t.stem: R.load_template(t) for t in sorted(args.templates.glob("*.json"))}
    calls = read_jsonl(args.run / "calls.jsonl")
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in calls:
        groups[(row["item_id"], row["template"])].append(row)
    invalid = []
    for (item_id, template_id), rows in groups.items():
        violations = payload_delivery_check(rows, templates[template_id])
        verdict = "invalid" if violations else "pass"
        for row in rows:
            row.setdefault("payload_check_runner", row["payload_check"])
            row["payload_check"] = verdict
            row["payload_check_tokenizer"] = "tiktoken o200k_base"
        if violations:
            invalid.append((item_id, template_id, violations))
    write_jsonl(args.run / "calls.jsonl", calls)
    with open(args.run / "invalid_items.csv", "w", encoding="utf-8") as fh:
        fh.write("item_id,template,violations\n")
        for item_id, template_id, violations in invalid:
            fh.write(f"{item_id},{template_id},\"{'; '.join(violations)}\"\n")
    print(f"recheck: {len(groups)} item-template groups, {len(invalid)} invalid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
