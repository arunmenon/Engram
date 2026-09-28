"""E-20260928-06-r2 metric script.

  python -m gate_eval.naming_score --run runs/E-20260928-06-r2/ --labels data/frozen/H5-labelled-90/labels.jsonl \
      [--noise-floor-f1 0.05] [--resamples 10000] [--seed 20260928]

Computes, per model and template: flip(i, cell), floor(i, set), E[set, t],
M[t] = E[N, t] - E[R, t], per-template F1 (Noul binary F1 positive "supports";
Choice macro-F1 over four classes, null-gold items excluded), ECE, top-two gap,
all with a cluster bootstrap over source documents, then applies the spec's
machine-checkable rule. This is the only module that reads labels.

The rule output is written to verdict.json because the spec names that file.
It is the machine result of the predeclared rule, not a bus verdict: the
verdict role decides, the executor does not.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from .common import read_jsonl, write_json, write_receipts
from .stats import binary_f1, cluster_bootstrap, design_effect, expected_calibration_error, macro_f1, mean

M_R = 0.10
TEMPLATES = {"noul_quote_supports_item": "gold_quote_supports_item", "choice_source_type": "gold_source_type"}


def _index_calls(calls: list[dict]) -> dict:
    """(model, template, name_set, item) -> {(binding, order, run): rubric_id}"""
    idx: dict = defaultdict(dict)
    for r in calls:
        if r["status"] != "ok" or r["payload_check"] == "invalid":
            continue
        idx[(r["model"], r["template"], r["name_set"], r["item_id"])][(r["binding"], r["order"], r["run"])] = r
    return idx


def per_item_flip_floor(cell_rows: dict, template: str) -> dict | None:
    """flip over reassigned cells vs aligned run 1 of same order; floor from aligned run 2."""
    orders = ["canonical", "reversed"]
    ref = {o: cell_rows.get(("aligned", o, 1)) for o in orders}
    if any(v is None for v in ref.values()):
        return None
    reassigned = ["reassigned"] if template.startswith("noul") else ["shift1", "shift2", "shift3"]
    flips, floors = [], []
    for o in orders:
        r1 = ref[o]["rubric_id"]
        for b in reassigned:
            row = cell_rows.get((b, o, 1))
            if row is None:
                return None
            flips.append(1.0 if row["rubric_id"] != r1 else 0.0)
        r2 = cell_rows.get(("aligned", o, 2))
        if r2 is None:
            return None
        floors.append(1.0 if r2["rubric_id"] != r1 else 0.0)
    return {"flip": mean(flips), "floor": mean(floors), "excess": mean(flips) - mean(floors),
            "ref": ref, "gap_min": min(float(ref[o]["top_two_gap"] or 0) for o in orders)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gate_eval.naming_score")
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--noise-floor-f1", type=float, default=None, help="H5 measured F1 noise floor; omit for provisional 0.05")
    p.add_argument("--resamples", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260928)
    args = p.parse_args(argv)

    nf = args.noise_floor_f1 if args.noise_floor_f1 is not None else 0.05
    nf_origin = "H5 measured" if args.noise_floor_f1 is not None else "provisional 0.05 (H5 floor not measured at freeze)"
    manifest = json.loads((args.run / "run_manifest.json").read_text(encoding="utf-8"))
    calls = read_jsonl(args.run / "calls.jsonl")
    labels = {r["item_id"]: r for r in read_jsonl(args.labels)}
    doc_of = {r["item_id"]: r["source_document_id"] for r in calls}
    idx = _index_calls(calls)
    models = sorted({r["model"] for r in calls})
    G = manifest["G"]
    valid_run = manifest.get("stop_reason") is None and manifest.get("rows_ok", 0) > 0

    flips_rows, mitig_rows, f1_rows = [], [], []
    E: dict = defaultdict(dict)      # E[model][template][set] -> bootstrap dict
    M: dict = defaultdict(dict)      # M[model][template]
    F1: dict = defaultdict(dict)     # F1[model][template][arm]
    for model in models:
        for template, gold_col in TEMPLATES.items():
            per_set_items: dict[str, list[dict]] = {}
            for name_set in ("N", "R", "L"):
                rows = []
                for item_id in labels:
                    cell_rows = idx.get((model, template, name_set, item_id))
                    if not cell_rows:
                        continue
                    ff = per_item_flip_floor(cell_rows, template)
                    if ff is None:
                        continue
                    rows.append({"item_id": item_id, "doc": doc_of[item_id], **ff})
                per_set_items[name_set] = rows
                if not rows:
                    continue
                boot = cluster_bootstrap(rows, "doc", lambda xs: mean([x["excess"] for x in xs]), args.resamples, args.seed)
                boot["deff"] = design_effect(boot["bootstrap_var"], [x["excess"] for x in rows])
                E[model].setdefault(template, {})[name_set] = boot
                small_gap = [x for x in rows if x["gap_min"] < 0.2]
                flips_rows.append({
                    "model": model, "template": template, "name_set": name_set,
                    "flip_rate": mean([x["flip"] for x in rows]), "floor": mean([x["floor"] for x in rows]),
                    "E": boot["point"], "lb975": boot["lb975"], "ub95": boot["ub95"], "G": boot["G"], "DEFF": boot["deff"],
                    "n_items": len(rows), "excess_small_gap_items": mean([x["excess"] for x in small_gap]) if small_gap else float("nan"),
                    "n_small_gap": len(small_gap),
                })
            # Mitigation M[t] = E[N] - E[R], paired by item
            n_rows = {x["item_id"]: x for x in per_set_items.get("N", [])}
            r_rows = {x["item_id"]: x for x in per_set_items.get("R", [])}
            paired = [{"item_id": k, "doc": doc_of[k], "m": n_rows[k]["excess"] - r_rows[k]["excess"]} for k in n_rows if k in r_rows]
            if paired:
                boot = cluster_bootstrap(paired, "doc", lambda xs: mean([x["m"] for x in xs]), args.resamples, args.seed)
                M[model][template] = boot
                mitig_rows.append({"model": model, "template": template, "M": boot["point"], "lb975": boot["lb975"], "ub95": boot["ub95"], "G": boot["G"], "n": len(paired)})
            # Quality per arm: R-aligned run 1 vs N-aligned run 1 (both orders pooled), F1 against gold
            for arm_set in ("N", "R", "L"):
                scored = []
                for item_id, lab in labels.items():
                    gold = lab.get(gold_col)
                    if gold is None:
                        continue
                    cell_rows = idx.get((model, template, arm_set, item_id), {})
                    for order in ("canonical", "reversed"):
                        row = cell_rows.get(("aligned", order, 1))
                        if row:
                            scored.append({"item_id": item_id, "doc": doc_of[item_id], "pred": row["rubric_id"], "gold": gold,
                                           "p": row["rubric_probabilities"].get("supports", max(row["rubric_probabilities"].values()))})
                if not scored:
                    continue
                if template.startswith("noul"):
                    stat = lambda xs: binary_f1([x["pred"] for x in xs], [x["gold"] for x in xs], "supports")
                    ece = expected_calibration_error([x["p"] for x in scored], [x["pred"] == x["gold"] for x in scored], 10)
                    excluded = []
                else:
                    classes = [c["rubric_id"] for c in json.loads((args.run / "models.lock.json").read_text())
                               .get("choice_classes", [{"rubric_id": c} for c in ("user_stated", "tool_result", "inferred", "imported")])]
                    stat = lambda xs: macro_f1([x["pred"] for x in xs], [x["gold"] for x in xs], classes)["macro_f1"]
                    ece = expected_calibration_error([max(0.0, x["p"]) for x in scored], [x["pred"] == x["gold"] for x in scored], 10)
                    excluded = macro_f1([x["pred"] for x in scored], [x["gold"] for x in scored], classes)["classes_excluded_zero_support"]
                boot = cluster_bootstrap(scored, "doc", stat, args.resamples, args.seed)
                F1[model].setdefault(template, {})[f"{arm_set}_aligned_r1"] = {"rows": scored, "boot": boot}
                f1_rows.append({"model": model, "template": template, "arm": f"{arm_set}_aligned_r1",
                                "f1_definition": "binary F1 positive=supports" if template.startswith("noul") else "macro-F1 over 4 classes",
                                "n_scored": len(scored), "classes_excluded": ";".join(excluded), "f1": boot["point"],
                                "lb95": boot["lb95"], "ub95": boot["ub95"], "ece": ece})
            # non-inferiority: paired F1 difference R - N via bootstrap over the union
            f1t = F1[model].get(template, {})
            if "R_aligned_r1" in f1t and "N_aligned_r1" in f1t:
                r_by = {(x["item_id"]): x for x in f1t["R_aligned_r1"]["rows"]}
                n_by = {(x["item_id"]): x for x in f1t["N_aligned_r1"]["rows"]}
                common = [k for k in n_by if k in r_by]
                pairs = [{"doc": doc_of[k], "pr": r_by[k]["pred"], "pn": n_by[k]["pred"], "gold": n_by[k]["gold"]} for k in common]
                if template.startswith("noul"):
                    diff = lambda xs: binary_f1([x["pr"] for x in xs], [x["gold"] for x in xs], "supports") - binary_f1([x["pn"] for x in xs], [x["gold"] for x in xs], "supports")
                else:
                    diff = lambda xs: macro_f1([x["pr"] for x in xs], [x["gold"] for x in xs], classes)["macro_f1"] - macro_f1([x["pn"] for x in xs], [x["gold"] for x in xs], classes)["macro_f1"]
                boot = cluster_bootstrap(pairs, "doc", diff, args.resamples, args.seed)
                F1[model][template]["R_minus_N"] = boot
                f1_rows.append({"model": model, "template": template, "arm": "R_minus_N", "f1_definition": "paired difference",
                                "n_scored": len(pairs), "classes_excluded": "", "f1": boot["point"], "lb95": boot["lb95"], "ub95": boot["ub95"], "ece": float("nan")})

    # ---- kill rule (Jev only is decisive; the decisive model is the first in models.lock)
    decisive = manifest["models_lock"]["jev_model"]
    T = list(TEMPLATES)
    verdict: dict = {"decisive_model": decisive, "m_r": M_R, "nf": nf, "nf_origin": nf_origin, "confirmatory": G >= 30, "G": G}
    if not valid_run:
        verdict.update({"verdict": "void", "reason": manifest.get("stop_reason") or "no ok rows"})
    else:
        def has(t, s):
            return t in E.get(decisive, {}) and s in E[decisive][t]
        risk_confirmed = {t: has(t, "N") and E[decisive][t]["N"]["lb975"] > M_R for t in T}
        risk_excluded = {t: has(t, "N") and E[decisive][t]["N"]["ub95"] < M_R for t in T}
        mitigates = {t: (t in M.get(decisive, {}) and M[decisive][t]["lb975"] > M_R and has(t, "R") and E[decisive][t]["R"]["ub95"] < M_R) for t in T}
        noninferior = {t: ("R_minus_N" in F1.get(decisive, {}).get(t, {}) and F1[decisive][t]["R_minus_N"]["lb95"] > -nf) for t in T}
        complete = all(has(t, "N") and has(t, "R") for t in T)
        if not complete:
            v = "void"; reason = "not every template has N and R cells scored"
        elif any(risk_confirmed.values()):
            if all(noninferior[t] and E[decisive][t]["R"]["ub95"] < M_R for t in T) and all(mitigates[t] for t in T if risk_confirmed[t]):
                v = "positive"; reason = "risk confirmed and neutral names mitigate without quality loss"
            else:
                v = "inconclusive"; reason = "risk confirmed but neutral names fail mitigates or noninferior on a template"
        elif all(risk_excluded.values()):
            v = "negative"; reason = "risk excluded on both templates"
        else:
            v = "inconclusive"; reason = "neither confirmed nor excluded on both templates"
        exploratory = False
        if G < 30 and v in ("positive", "negative"):
            v = "inconclusive"; exploratory = True; reason += "; downgraded: G < 30"
        verdict.update({"risk_confirmed": risk_confirmed, "risk_excluded": risk_excluded, "mitigates": mitigates,
                        "noninferior": noninferior, "exploratory": exploratory, "verdict": v, "reason": reason,
                        "note": "machine rule output for the verdict role; Laya and letters (L) are reported, never decisive"})

    def dump_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8"); return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    dump_csv(args.run / "flips.csv", flips_rows)
    dump_csv(args.run / "mitigation.csv", mitig_rows)
    dump_csv(args.run / "f1_ece.csv", f1_rows)
    write_json(args.run / "verdict.json", verdict)
    write_receipts(args.run)
    print(json.dumps({k: verdict[k] for k in ("verdict", "reason", "confirmatory")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
