"""E-20260928-06-r2 naming audit runner.

  python -m gate_eval.naming_audit --manifest data/frozen/H5-labelled-90/manifest.json \
      --templates templates/naming_audit/ --models models.lock.json --policy <policy.md> \
      --out runs/E-20260928-06-r2/ [--max-items 5] [--max-calls N] [--render-only]

Preflight (all must pass, else the command refuses and writes nothing):
  1. git working tree clean; commit hash recorded.
  2. policy.md status is `set`; caps read from it, never from code.
  3. frozen manifest verifies (per-item hashes).
  4. models.lock.json pins model version, decoding parameters and template hashes.
  5. TYPESAFE_API_KEY present unless --render-only.
Then: render every cell for every item, assert byte equality, call, run the
payload-delivery check, map answers to rubric ids, write the output manifest.
Labels are never read here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import render as R
from .common import (BudgetGuard, PreflightError, env_api_key, parse_policy, read_jsonl, repo_root_from,
                     require_clean_tree, require_policy_set, sha256_file, utc_now, write_json, write_jsonl,
                     write_receipts)
from .freeze import verify_manifest
from .typesafe_client import TypeSafeClient


def load_models_lock(path: Path, template_dir: Path) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    for key in ("jev_model", "jev_model_version_pinned", "api_endpoint", "decoding"):
        if key not in lock:
            raise PreflightError(f"models.lock.json lacks {key}")
    lock_hashes = lock.get("template_sha256", {})
    for tpl in sorted(template_dir.glob("*.json")):
        actual = sha256_file(tpl)
        if lock_hashes.get(tpl.name) != actual:
            raise PreflightError(f"models.lock.json template hash for {tpl.name} is {lock_hashes.get(tpl.name)}; file is {actual}")
    return lock


def payload_delivery_check(rows_for_item: list[dict], template: dict) -> list[str]:
    """Spec check (4), fallback form: billed input tokens of two cells of one item
    may differ by no more than the local token delta of the name strings plus
    2 per option. Returns the list of violating cell pairs (empty = pass).
    REV-20260928-24 notes this relative check cannot detect rubrics dropped
    identically in every cell; that limitation is recorded in the manifest."""
    violations: list[str] = []
    n_options = len(template["rubrics"])
    ok_rows = [r for r in rows_for_item if r["status"] == "ok" and r["billed_input_tokens"] is not None]
    for i in range(len(ok_rows)):
        for j in range(i + 1, len(ok_rows)):
            a, b = ok_rows[i], ok_rows[j]
            allowed = R.name_token_delta(template["name_sets"][a["name_set"]], template["name_sets"][b["name_set"]]) + 2 * n_options
            if abs(a["billed_input_tokens"] - b["billed_input_tokens"]) > allowed:
                violations.append(f"{a['cell_id']} vs {b['cell_id']}: {a['billed_input_tokens']} vs {b['billed_input_tokens']} (> {allowed})")
    return violations


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gate_eval.naming_audit")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--templates", type=Path, required=True)
    p.add_argument("--models", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-items", type=int, default=None, help="dry run: first N items only")
    p.add_argument("--max-calls", type=int, default=9072, help="hard call cap from the spec (9,072)")
    p.add_argument("--usd-per-call", type=float, default=None, help="list price per call for the cost cap")
    p.add_argument("--render-only", action="store_true", help="render and hash every request, make no calls")
    p.add_argument("--allow-dirty", action="store_true", help="engineering only; a real run must be clean")
    args = p.parse_args(argv)

    started_wall = time.time()
    try:
        repo_root = repo_root_from(args.manifest.resolve())
        git = require_clean_tree(repo_root, allow_dirty=args.allow_dirty)
        policy = parse_policy(args.policy)
        require_policy_set(policy)
        manifest = verify_manifest(args.manifest)
        lock = load_models_lock(args.models, args.templates)
        api_key = None if args.render_only else env_api_key()
        if not args.render_only and not api_key:
            raise PreflightError("TYPESAFE_API_KEY not set (use --render-only to render without calls)")
        if args.out.exists() and any(args.out.iterdir()):
            raise PreflightError(f"output directory {args.out} is not empty; a rerun needs a new spec revision")
    except PreflightError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    templates = {tpl.stem: R.load_template(tpl) for tpl in sorted(args.templates.glob("*.json"))}
    items = read_jsonl(args.manifest.parent / "items.jsonl")
    if args.max_items:
        items = items[: args.max_items]
    model = lock["jev_model"]
    guard = BudgetGuard(
        max_calls=args.max_calls,
        max_tokens=policy.tokens_per_run,
        max_wall_clock_s=policy.wall_clock_h_per_run * 3600,
        max_cost_usd=policy.cost_usd_per_run,
        usd_per_call=args.usd_per_call,
        started_at=started_wall,
    )
    run_manifest = {
        "spec": "E-20260928-06-r2",
        "command": " ".join(sys.argv),
        "harness_commit": git["commit"],
        "git_clean": git["clean"],
        "dataset_manifest_sha256": sha256_file(args.manifest),
        "dataset": manifest["dataset"],
        "G": manifest["G_source_documents"],
        "mean_cluster_size": manifest["mean_items_per_document"],
        "items_per_document_distribution": manifest["items_per_document_distribution"],
        "n_items_this_run": len(items),
        "models_lock": lock,
        "template_render_modes": {k: v.get("render_as") for k, v in templates.items()},
        "policy_snapshot": policy.snapshot(),
        "render_only": args.render_only,
        "payload_check_limitation": "relative token check only; identical rubric loss in all cells is undetectable (REV-20260928-24)",
        "started_at": utc_now(),
    }
    write_json(args.out / "run_manifest.json", run_manifest)  # written before the first call
    write_json(args.out / "models.lock.json", lock)

    client = None if args.render_only else TypeSafeClient(api_key, lock["api_endpoint"], pinned_model_version=lock["jev_model_version_pinned"] or None)
    calls: list[dict] = []
    invalid: list[dict] = []
    stop_reason = None
    try:
        for item in items:
            for tid, template in templates.items():
                cells = R.enumerate_cells(template)
                R.assert_byte_equality(template, item, model, cells)
                rows_for_item: list[dict] = []
                for cell in cells:
                    request = R.render_request(template, cell, item, model)
                    body = R.request_bytes(request)
                    row = {
                        "item_id": item["item_id"], "source_document_id": item["source_document_id"],
                        "model": model, "template": tid, "name_set": cell.name_set, "binding": cell.binding,
                        "order": cell.order, "run": cell.run, "cell_id": cell.cell_id,
                        "request_sha256": R.sha256_bytes(body), "request_bytes_len": len(body),
                        "status": "rendered", "answer": None, "rubric_id": None, "rubric_probabilities": None,
                        "top_two_gap": None, "confidence": None, "billed_input_tokens": None,
                        "billed_output_tokens": None, "latency_ms": None, "model_reported": None,
                        "payload_check": "not_run", "error": None,
                    }
                    if client is not None:
                        guard.check_before_call(time.time())
                        result = client.call(body)
                        row.update({
                            "status": result.status, "billed_input_tokens": result.input_tokens,
                            "billed_output_tokens": result.output_tokens, "latency_ms": round(result.latency_ms, 2),
                            "model_reported": result.model_reported, "error": result.error,
                        })
                        if result.status == "ok":
                            guard.record(result.input_tokens or 0, result.output_tokens or 0)
                            answer = result.response["answers"][tid]
                            mapped = R.map_answer(template, cell, answer)
                            row.update({"answer": answer.get("choice"), **mapped})
                        elif result.status == "version_mismatch":
                            raise PreflightError(result.error or "version mismatch")
                        else:
                            guard.calls += 1
                    rows_for_item.append(row)
                if client is not None:
                    violations = payload_delivery_check(rows_for_item, template)
                    verdict = "invalid" if violations else "pass"
                    for row in rows_for_item:
                        row["payload_check"] = verdict
                    if violations:
                        invalid.append({"item_id": item["item_id"], "template": tid, "violations": violations})
                calls.extend(rows_for_item)
    except PreflightError as exc:
        stop_reason = str(exc)
    finally:
        write_jsonl(args.out / "calls.jsonl", calls)
        with open(args.out / "invalid_items.csv", "w", encoding="utf-8") as fh:
            fh.write("item_id,template,violations\n")
            for row in invalid:
                fh.write(f"{row['item_id']},{row['template']},\"{'; '.join(row['violations'])}\"\n")
        run_manifest.update({
            "ended_at": utc_now(), "call_count": guard.calls, "budget": guard.snapshot(),
            "stop_reason": stop_reason, "rows_rendered": len(calls),
            "rows_ok": sum(1 for r in calls if r["status"] == "ok"),
        })
        write_json(args.out / "run_manifest.json", run_manifest)
        write_receipts(args.out)
    if stop_reason:
        print(f"STOPPED: {stop_reason}", file=sys.stderr)
        return 3
    print(f"done: {len(calls)} rows, {guard.calls} calls, out={args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
