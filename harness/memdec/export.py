"""Export memory-decision candidates from Engram extraction output.

  python -m memdec.export --extractions extractions.jsonl --transcripts transcripts.jsonl \
      --repos session_repos.json --out data/frozen/MEMDEC-OD/ --seed 20260928 \
      [--train-repos 10 --val-repos 2 --test-repos 8] [--window 3]

Inputs (all produced by Engram, none authored here):
  extractions.jsonl  one SessionExtractionResult per line (worker/extraction.py output)
  transcripts.jsonl  {"session_id", "turns": [{"index", "role", "text"}]}
  session_repos.json {"<session_id>": "<repository_id>"}

Outputs: items.jsonl (store/skip candidates), pairs.jsonl (supersession candidate
pairs), splits.json (whole repositories -> train/val/test), manifest.json with
per-record sha256. The production state rendering is the same {transcript_excerpt,
item, quote} shape the naming-audit templates consume; its sha256 is recorded.

Engram has no Jev write gate yet, so there is no "logged write-gate candidate"
stream: the candidates are the extraction worker's preference items, which is
the population the gate would see.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from gate_eval.common import PreflightError, read_jsonl, record_sha256, sha256_bytes, utc_now, write_json, write_jsonl

RENDER_VERSION = "memdec-state-v1"


def render_item_text(pref: dict) -> str:
    """Item text as the write gate would see it (deterministic, no model)."""
    polarity = pref.get("polarity", "neutral")
    about = f" about {pref['about_entity']}" if pref.get("about_entity") else ""
    return f"{pref['category']} preference ({polarity}, strength {pref.get('strength', 0):.2f}): {pref['key']}{about}"


def transcript_excerpt(turns: list[dict], turn_index: int | None, window: int) -> str:
    if turn_index is None:
        return "\n".join(f"[{t['role']}] {t['text']}" for t in turns[: 2 * window + 1])
    lo, hi = max(0, turn_index - window), turn_index + window + 1
    return "\n".join(f"[{t['role']}] {t['text']}" for t in turns[lo:hi])


def assign_splits(repos: list[str], seed: int, n_train: int, n_val: int, n_test: int) -> dict[str, str]:
    if len(repos) < n_train + n_val + n_test:
        raise PreflightError(f"{len(repos)} repositories; need at least {n_train + n_val + n_test} for the declared splits")
    rng = random.Random(seed)
    order = sorted(repos)
    rng.shuffle(order)
    split: dict[str, str] = {}
    for i, repo in enumerate(order):
        if i < n_test:
            split[repo] = "test"
        elif i < n_test + n_val:
            split[repo] = "val"
        else:
            split[repo] = "train"
    return split


def build(extractions: list[dict], transcripts: dict[str, list[dict]], session_repo: dict[str, str], window: int) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    by_repo_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for ex in extractions:
        sid = ex["session_id"]
        repo = session_repo.get(sid)
        if repo is None:
            raise PreflightError(f"session {sid} has no repository in session_repos.json")
        turns = transcripts.get(sid)
        if turns is None:
            raise PreflightError(f"session {sid} has no transcript")
        for n, pref in enumerate(ex.get("preferences", [])):
            item = {
                "item_id": f"{sid}:pref:{n}",
                "repository_id": repo,
                "session_id": sid,
                "decision_type": "store_skip",
                "transcript_excerpt": transcript_excerpt(turns, pref.get("source_turn_index"), window),
                "item": render_item_text(pref),
                "quote": pref["source_quote"],
                "extractor_confidence": pref.get("confidence"),
                "extractor_source": pref.get("source"),
                "render_version": RENDER_VERSION,
            }
            items.append(item)
            by_repo_key[(repo, pref["key"])].append({**item, "_order": (ex.get("ended_at") or sid, n)})
    pairs: list[dict] = []
    for (repo, key), rows in sorted(by_repo_key.items()):
        rows = sorted(rows, key=lambda r: r["_order"])
        for a, b in zip(rows, rows[1:]):
            pairs.append({
                "pair_id": f"{a['item_id']}=>{b['item_id']}",
                "repository_id": repo,
                "decision_type": "supersedes",
                "memory_a": {"item": a["item"], "quote": a["quote"], "session_id": a["session_id"]},
                "memory_b": {"item": b["item"], "quote": b["quote"], "session_id": b["session_id"]},
                "preference_key": key,
                "render_version": RENDER_VERSION,
            })
    return items, pairs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="memdec.export")
    p.add_argument("--extractions", type=Path, required=True)
    p.add_argument("--transcripts", type=Path, required=True)
    p.add_argument("--repos", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20260928)
    p.add_argument("--train-repos", type=int, default=10)
    p.add_argument("--val-repos", type=int, default=2)
    p.add_argument("--test-repos", type=int, default=8)
    p.add_argument("--window", type=int, default=3)
    args = p.parse_args(argv)
    try:
        extractions = read_jsonl(args.extractions)
        transcripts = {r["session_id"]: r["turns"] for r in read_jsonl(args.transcripts)}
        session_repo = json.loads(args.repos.read_text(encoding="utf-8"))
        items, pairs = build(extractions, transcripts, session_repo, args.window)
        repos = sorted({i["repository_id"] for i in items})
        splits = assign_splits(repos, args.seed, args.train_repos, args.val_repos, args.test_repos)
        for row in items + pairs:
            row["split"] = splits[row["repository_id"]]
        args.out.mkdir(parents=True, exist_ok=False)
        write_jsonl(args.out / "items.jsonl", items)
        write_jsonl(args.out / "pairs.jsonl", pairs)
        write_json(args.out / "splits.json", {"seed": args.seed, "repositories": splits})
        counts = defaultdict(int)
        for r in items:
            counts[f"items/{r['split']}"] += 1
        for r in pairs:
            counts[f"pairs/{r['split']}"] += 1
        manifest = {
            "dataset": "MEMDEC-OD", "frozen_at": utc_now(), "render_version": RENDER_VERSION,
            "render_sha256": sha256_bytes(Path(__file__).read_bytes()), "counts": dict(counts),
            "repositories": len(repos), "items": [{"item_id": r["item_id"], "repository_id": r["repository_id"], "split": r["split"], "sha256": record_sha256(r)} for r in items],
            "pairs": [{"pair_id": r["pair_id"], "repository_id": r["repository_id"], "split": r["split"], "sha256": record_sha256(r)} for r in pairs],
        }
        write_json(args.out / "manifest.json", manifest)
        print(json.dumps({"repositories": len(repos), **counts}))
    except PreflightError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
