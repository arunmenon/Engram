"""E-20260928-07-r2 runner.

  python -m linkstale.run --manifest <run_manifest.json>

The run manifest names the frozen LINK-STALE-200 directory, the policy file,
the models lock and the output directory. Preflight verifies every frozen
file's sha256 against dataset_manifest.json, the git tree, the policy status
and caps. Gold and probe-answer files are opened only after all calls finish;
probes.jsonl planted text is read through a view that drops planted_answer
(REV-20260928-28 [packet]).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from gate_eval.common import (BudgetGuard, PreflightError, env_api_key, parse_policy, read_jsonl, repo_root_from,
                              require_clean_tree, require_policy_set, sha256_bytes, sha256_file, utc_now,
                              write_json, write_jsonl, write_receipts)
from gate_eval.typesafe_client import TypeSafeClient

from . import render as R

FROZEN_FILES = ("items.jsonl", "gold.jsonl", "probes.jsonl", "canary.jsonl", "opinion_rule.json", "state_template.json")


def verify_dataset(dataset_dir: Path) -> dict:
    manifest = json.loads((dataset_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
    for name in FROZEN_FILES:
        expected = manifest["files"].get(name)
        actual = sha256_file(dataset_dir / name)
        if expected != actual:
            raise PreflightError(f"{name}: sha256 {actual} differs from dataset_manifest {expected}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="linkstale.run")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--render-only", action="store_true")
    p.add_argument("--allow-dirty", action="store_true")
    args = p.parse_args(argv)
    cfg = json.loads(args.manifest.read_text(encoding="utf-8"))
    dataset_dir = Path(cfg["dataset_dir"])
    out = Path(cfg["out_dir"])
    started = time.time()
    try:
        repo_root = repo_root_from(args.manifest.resolve())
        git = require_clean_tree(repo_root, allow_dirty=args.allow_dirty)
        policy = parse_policy(Path(cfg["policy_path"]))
        require_policy_set(policy)
        ds = verify_dataset(dataset_dir)
        lock = json.loads(Path(cfg["models_lock"]).read_text(encoding="utf-8"))
        if not args.render_only and not env_api_key():
            raise PreflightError("TYPESAFE_API_KEY not set")
        if out.exists() and any(out.iterdir()):
            raise PreflightError(f"{out} not empty; rerun needs a new spec revision")
    except PreflightError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    tpl = R.load_state_template(dataset_dir / "state_template.json")
    rule = R.load_opinion_rule(dataset_dir / "opinion_rule.json")
    items = read_jsonl(dataset_dir / "items.jsonl")
    probes_view = [{k: v for k, v in r.items() if k != "planted_answer"} for r in read_jsonl(dataset_dir / "probes.jsonl")]
    canaries = read_jsonl(dataset_dir / "canary.jsonl")
    model = lock["jev_model"]
    p5_landed = bool(cfg.get("p5_landed", False))
    run_manifest = {
        "spec": "E-20260928-07-r2", "command": " ".join(sys.argv), "harness_commit": git["commit"], "git_clean": git["clean"],
        "dataset_manifest_sha256": sha256_file(dataset_dir / "dataset_manifest.json"), "dataset": ds.get("dataset"),
        "jev_model": model, "jev_model_version_pinned": lock.get("jev_model_version_pinned"),
        "request_schema_version": lock.get("request_schema_version"), "decoding": lock.get("decoding"),
        "template_sha256": ds["files"]["state_template.json"], "opinion_rule_sha256": ds["files"]["opinion_rule.json"],
        "source_class_provenance": "P5" if p5_landed else "event-type", "policy_snapshot": policy.snapshot(),
        "render_only": args.render_only, "started_at": utc_now(),
    }
    write_json(out / "run_manifest.json", run_manifest)
    guard = BudgetGuard(cfg.get("max_calls", 2500), policy.tokens_per_run, policy.wall_clock_h_per_run * 3600,
                        policy.cost_usd_per_run, cfg.get("usd_per_call"), started)
    client = None if args.render_only else TypeSafeClient(env_api_key(), lock.get("api_endpoint", "https://api.typesafe.ai/v1/systemone"),
                                                          pinned_model_version=lock.get("jev_model_version_pinned") or None)
    calls: list[dict] = []
    stop_reason = None

    def do_call(row: dict, request: dict, neighbour_text: str | None) -> None:
        body = R.request_bytes(request)
        row.update({"request_sha256": sha256_bytes(body), "request_bytes_len": len(body),
                    "bytes_present": (neighbour_text.encode("utf-8") in body) if neighbour_text is not None else None,
                    "status": "rendered", "decision": None, "probabilities": None, "confidence": None,
                    "billed_input_tokens": None, "billed_output_tokens": None, "model_reported": None, "latency_ms": None, "error": None})
        if client is None:
            calls.append(row); return
        guard.check_before_call(time.time())
        res = client.call(body)
        row.update({"status": res.status, "billed_input_tokens": res.input_tokens, "billed_output_tokens": res.output_tokens,
                    "model_reported": res.model_reported, "latency_ms": round(res.latency_ms, 2), "error": res.error})
        if res.status == "ok":
            guard.record(res.input_tokens or 0, res.output_tokens or 0)
            ans = next(iter(res.response["answers"].values()))
            row.update({"decision": ans.get("choice"), "probabilities": ans.get("probabilities"), "confidence": ans.get("confidence")})
        elif res.status == "version_mismatch":
            raise PreflightError(res.error or "version mismatch")
        else:
            guard.calls += 1
        calls.append(row)

    try:
        for item in items:
            nbrs = item["neighbours"][:5]
            ref = None
            for arm in R.ARMS:
                real_arm = "A" if arm == "A_prime" else arm
                req = R.render_request(tpl, item, real_arm, nbrs, rule, p5_landed, model)
                # identity assertions across arms
                q = req["questions"]["decision"]
                sig = (q["instructions"], json.dumps(q["criteria"], sort_keys=True))
                ref = ref or sig
                if sig != ref:
                    raise PreflightError(f"question/option bytes differ across arms for {item['item_id']}")
                ntext = None
                if real_arm in R.NEIGHBOUR_ARMS:
                    rendered = req["state"].get("neighbours_text", req["state"].get("neighbours"))
                    ntext = R.strip_labels(rendered)
                    if arm == "B":
                        b_text = ntext
                    elif ntext != b_text:
                        raise PreflightError(f"neighbour text differs between B and {arm} for {item['item_id']}")
                do_call({"arm": arm, "item_id": item["item_id"], "thread_id": item["thread_id"], "kind": "item"}, req,
                        b_text if real_arm in R.NEIGHBOUR_ARMS else None)
            for probe in [x for x in probes_view if x["item_id"] == item["item_id"]]:
                rank = 0 if probe["position"] == "p1" else 4
                planted = list(nbrs)
                planted[rank] = {"text": probe["planted_text"], "originating_event_type": "extraction.output"}
                for arm in R.NEIGHBOUR_ARMS:
                    req = R.render_request(tpl, item, arm, planted, rule, p5_landed, model)
                    do_call({"arm": arm, "item_id": item["item_id"], "thread_id": item["thread_id"], "kind": "probe",
                             "variant": probe["variant_id"], "position": probe["position"]}, req, R.strip_labels(req["state"].get("neighbours_text", req["state"].get("neighbours"))))
        for canary in canaries:
            item = next(x for x in items if x["item_id"] == canary["item_id"])
            nbrs = list(item["neighbours"][:5])
            nbrs[canary["neighbour_rank"]] = {"text": nbrs[canary["neighbour_rank"]]["text"] + f" Nonce: {canary['nonce']}.",
                                              "originating_event_type": nbrs[canary["neighbour_rank"]].get("originating_event_type", "")}
            for arm in R.NEIGHBOUR_ARMS:
                req = R.render_canary_request(tpl, item, arm, nbrs, canary["nonce"], rule, p5_landed, model)
                do_call({"arm": arm, "item_id": item["item_id"], "thread_id": item["thread_id"], "kind": "canary", "nonce": canary["nonce"]}, req, canary["nonce"])
    except PreflightError as exc:
        stop_reason = str(exc)
    finally:
        write_jsonl(out / "calls.jsonl", calls)
        run_manifest.update({"ended_at": utc_now(), "call_count": guard.calls, "budget": guard.snapshot(), "stop_reason": stop_reason,
                             "rows_rendered": len(calls)})
        write_json(out / "run_manifest.json", run_manifest)
        write_receipts(out)
    if stop_reason:
        print(f"STOPPED: {stop_reason}", file=sys.stderr); return 3
    print(f"done: {len(calls)} rows, {guard.calls} calls"); return 0


if __name__ == "__main__":
    sys.exit(main())
