"""E-20260928-07-r2 metric script and kill rule.

  python -m linkstale.score --run <out_dir> --dataset <frozen dir> [--resamples 10000] [--seed 20260928]

Reads gold.jsonl and probes.jsonl (planted answers) only here, after calls.
Also checks that no gold answer string appears in any request body hash log
cannot be done post hoc from hashes; the runner never loaded gold, which is the
field-provenance guarantee REV-20260928-28 asked for.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from gate_eval.common import read_jsonl, write_json, write_receipts
from gate_eval.stats import cluster_bootstrap, design_effect, mean, paired_power, variance

MARGIN = 0.05


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="linkstale.score")
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--resamples", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260928)
    args = p.parse_args(argv)
    calls = [r for r in read_jsonl(args.run / "calls.jsonl") if r["status"] == "ok"]
    gold = {r["item_id"]: r["adjudicated_answer"] for r in read_jsonl(args.dataset / "gold.jsonl")}
    probes = {r["variant_id"]: r for r in read_jsonl(args.dataset / "probes.jsonl")}
    manifest = json.loads((args.run / "run_manifest.json").read_text(encoding="utf-8"))
    by_arm: dict = defaultdict(dict)
    for r in calls:
        key = r["item_id"] if r["kind"] == "item" else (r.get("variant") or r.get("nonce"))
        by_arm[(r["arm"], r["kind"])][key] = r

    # delivery per neighbour arm
    delivery_rows, delivered = [], {}
    a_calls = by_arm[("A", "item")]
    for arm in ("B", "C1", "C2"):
        items_arm = by_arm[(arm, "item")]
        canary = by_arm[(arm, "canary")]
        canary_rate = mean([1.0 if r["decision"] == "A" else 0.0 for r in canary.values()]) if canary else float("nan")
        bytes_rate = mean([1.0 if r["bytes_present"] else 0.0 for r in items_arm.values()]) if items_arm else float("nan")
        tok_ok = []
        for k, r in items_arm.items():
            a = a_calls.get(k)
            if a and a["billed_input_tokens"] is not None and r["billed_input_tokens"] is not None:
                nbr_tokens = r.get("nbr_tokens") or (r["request_bytes_len"] - a["request_bytes_len"]) / 4.0  # fallback: bytes/4 proxy, recorded
                tok_ok.append(1.0 if (r["billed_input_tokens"] - a["billed_input_tokens"]) >= 0.9 * nbr_tokens else 0.0)
        tok_rate = mean(tok_ok) if tok_ok else float("nan")
        flag = (not math.isnan(canary_rate) and canary_rate >= 19 / 20) and bytes_rate == 1.0 and tok_rate == 1.0
        delivered[arm] = flag
        delivery_rows.append({"arm": arm, "canary_rate": canary_rate, "bytes_present_rate": bytes_rate, "token_check_rate": tok_rate, "delivered": flag})

    # gold metrics per arm on non-probe set
    def metrics(arm: str) -> list[dict]:
        rows = []
        for k, r in by_arm[(arm, "item")].items():
            if k not in gold:
                continue
            wrong = 1.0 if r["decision"] != gold[k] else 0.0
            conf = float(r["confidence"] or 0.0)
            rows.append({"item_id": k, "thread": r["thread_id"], "wrong": wrong, "hcw": 1.0 if (conf >= 0.8 and wrong) else 0.0,
                         "conf08": 1.0 if conf >= 0.8 else 0.0, "conf": conf, "decision": r["decision"]})
        return rows

    M = {arm: {x["item_id"]: x for x in metrics(arm)} for arm in ("A", "A_prime", "B", "C1", "C2")}
    gold_rows = []
    for arm, rows in M.items():
        vals = list(rows.values())
        if not vals:
            continue
        corr = dmg = 0
        for k, x in rows.items():
            a = M["A"].get(k)
            if a:
                corr += int(a["wrong"] == 1 and x["wrong"] == 0); dmg += int(a["wrong"] == 0 and x["wrong"] == 1)
        c08 = [x for x in vals if x["conf08"]]
        gold_rows.append({"arm": arm, "n": len(vals), "err": mean([x["wrong"] for x in vals]), "HCW": mean([x["hcw"] for x in vals]),
                          "prec08": mean([1 - x["wrong"] for x in c08]) if c08 else float("nan"), "corrections": corr, "damage": dmg})

    def paired(arm_x: str, arm_y: str, field: str, population: str) -> dict:
        if population == "nonprobe":
            keys = [k for k in M[arm_x] if k in M[arm_y]]
            pairs = [{"thread": M[arm_x][k]["thread"], "d": M[arm_x][k][field] - M[arm_y][k][field], "x": M[arm_x][k][field], "y": M[arm_y][k][field]} for k in keys]
        else:
            px, py = by_arm[(arm_x, "probe")], by_arm[(arm_y, "probe")]
            keys = [k for k in px if k in py]
            pairs = []
            for k in keys:
                pa = probes[k]["planted_answer"]
                cx = 1.0 if px[k]["decision"] == pa else 0.0; cy = 1.0 if py[k]["decision"] == pa else 0.0
                pairs.append({"thread": px[k]["thread_id"], "d": cx - cy, "x": cx, "y": cy})
        if not pairs:
            return {"estimate": float("nan"), "n": 0}
        boot = cluster_bootstrap(pairs, "thread", lambda xs: mean([q["d"] for q in xs]), args.resamples, args.seed)
        d_vals = [q["d"] for q in pairs]
        pi_hat = mean([1.0 if q["x"] != q["y"] else 0.0 for q in pairs])
        deff = design_effect(boot["bootstrap_var"], d_vals)
        n_eff = len(pairs) / deff if deff and not math.isnan(deff) and deff > 0 else float("nan")
        return {"estimate": boot["point"], "ci_low": boot["ci95_two_sided"][0], "ci_high": boot["ci95_two_sided"][1], "n": len(pairs),
                "threads": boot["G"], "pi_hat": pi_hat, "DEFF_hat": deff, "n_eff": n_eff,
                "power_hat": paired_power(pi_hat, n_eff, MARGIN) if not math.isnan(n_eff) else float("nan")}

    tests = {
        "HCW_B_minus_A_nonprobe": paired("B", "A", "hcw", "nonprobe"),
        "err_B_minus_A_nonprobe": paired("B", "A", "wrong", "nonprobe"),
        "cap_B_minus_C2_probe": paired("B", "C2", "cap", "probe"),
        "err_C2_minus_B_nonprobe": paired("C2", "B", "wrong", "nonprobe"),
        "HCW_C2_minus_B_nonprobe": paired("C2", "B", "hcw", "nonprobe"),
        "HCW_C2_minus_A_nonprobe": paired("C2", "A", "hcw", "nonprobe"),
        "flip_C1_minus_B_nonprobe": paired("C1", "B", "wrong", "nonprobe"),
        "flip_C2_minus_C1_nonprobe": paired("C2", "C1", "wrong", "nonprobe"),
    }
    # probe capture per arm and position
    probe_rows = []
    for arm in ("B", "C1", "C2"):
        for pos in ("p1", "p5"):
            vs = [1.0 if r["decision"] == probes[k]["planted_answer"] else 0.0 for k, r in by_arm[(arm, "probe")].items() if probes[k]["position"] == pos]
            probe_rows.append({"arm": arm, "position": pos, "cap": mean(vs) if vs else float("nan"), "n": len(vs)})
    # diagnostics: label-free flip vs A, floor from A'
    diag = []
    for arm in ("A_prime", "B", "C1", "C2"):
        keys = [k for k in M[arm] if k in M["A"]]
        flip = mean([1.0 if M[arm][k]["decision"] != M["A"][k]["decision"] else 0.0 for k in keys]) if keys else float("nan")
        crossing = mean([1.0 if (M["A"][k]["conf"] >= 0.8 and M[arm][k]["conf"] < 0.8) else 0.0 for k in keys]) if keys else float("nan")
        diag.append({"arm": arm, "flip_vs_A": flip, "threshold_crossing": crossing, "n": len(keys)})
    floor = next((d["flip_vs_A"] for d in diag if d["arm"] == "A_prime"), float("nan"))
    for d in diag:
        d["excess_over_floor"] = d["flip_vs_A"] - floor

    # kill rule (spec pseudo-code)
    ci_high = lambda t: tests[t].get("ci_high", float("nan"))
    ci_low = lambda t: tests[t].get("ci_low", float("nan"))
    est = lambda t: tests[t].get("estimate", float("nan"))
    verdict: dict = {"margin": MARGIN, "delivered": delivered}
    if not delivered.get("B"):
        verdict.update({"outcome": "invalid", "action": "re-queue", "reason": "arm B failed the delivery check"})
    else:
        d1 = ci_high("HCW_B_minus_A_nonprobe") < MARGIN and ci_high("err_B_minus_A_nonprobe") < MARGIN
        mitig = est("cap_B_minus_C2_probe") >= MARGIN and ci_low("cap_B_minus_C2_probe") > 0
        guard = est("err_C2_minus_B_nonprobe") < MARGIN and est("HCW_C2_minus_B_nonprobe") < MARGIN and est("HCW_C2_minus_A_nonprobe") < MARGIN
        d2 = delivered.get("C2", False) and mitig and guard
        p2 = tests["cap_B_minus_C2_probe"].get("power_hat", float("nan"))
        if d1:
            outcome = "negative"
        elif d2:
            outcome = "positive"
        else:
            outcome = "inconclusive"
        verdict.update({"d1_pass": d1, "d2_pass": d2, "outcome": outcome, "power_hat_probe": p2,
                        "c2_killed": (outcome == "inconclusive" and delivered.get("C2", False) and not math.isnan(p2) and p2 >= 0.80),
                        "c2_void": not delivered.get("C2", False), "b_free_text_for_automatic_writes": d1,
                        "note": "machine rule output for the verdict role; the executor does not decide"})

    def dump(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8"); return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    dump(args.run / "delivery.csv", delivery_rows)
    dump(args.run / "gold_metrics.csv", gold_rows)
    dump(args.run / "probe_capture.csv", probe_rows)
    dump(args.run / "paired_tests.csv", [{"test": k, **v} for k, v in tests.items()])
    dump(args.run / "diagnostics.csv", diag)
    write_json(args.run / "verdict.json", verdict)
    write_receipts(args.run)
    print(json.dumps({k: verdict.get(k) for k in ("outcome", "d1_pass", "d2_pass")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
