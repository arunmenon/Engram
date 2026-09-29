"""H5 scorer: does an independent Jev gate beat the extractor's own confidence?

  python -m gate_eval.h5_score --run runs/<run id>/ --dataset <frozen H5-labelled-90 dir> \
      [--resamples 10000] [--seed 20260928]

Reads the naming-audit calls (no new Jev calls). The gate score of an item is
Jev's P(supports) on the current H5 wording: name set N, aligned binding, run 1,
canonical order. The comparison score is the extractor's self-reported
`extractor_confidence`. An item is "accepted" when its score is at or above a
threshold. Gold: `gold_quote_supports_item == "supports"` (model labels).

Discovery plan H5: fit thresholds on half the items, test on the other half.
Halves are drawn by source document (sha256 of seed + document id) so that no
document straddles the split. Fold A (fit on half 0, test on half 1) is the
predeclared primary; fold B (swapped) is reported.

Kill (discovery plan): F1 not better than self-reported confidence + noise, or
ECE > 0.15 on the test half. "Better than noise" is read as the one-sided 95%
lower bound of the paired test-half F1 difference (Jev minus confidence, cluster
bootstrap over source documents) above zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from .common import read_jsonl, write_json
from .stats import cluster_bootstrap, expected_calibration_error, mean

ECE_KILL = 0.15
GATE_TEMPLATE = "noul_quote_supports_item"


def prf(scores: list[float], gold: list[bool], threshold: float) -> dict:
    accepted = [s >= threshold for s in scores]
    tp = sum(1 for a, g in zip(accepted, gold) if a and g)
    fp = sum(1 for a, g in zip(accepted, gold) if a and not g)
    fn = sum(1 for a, g in zip(accepted, gold) if not a and g)
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "accepted": sum(accepted), "n": len(scores),
            "tp": tp, "fp": fp, "fn": fn}


def fit_threshold(scores: list[float], gold: list[bool]) -> float:
    """Threshold maximising F1 on the fit half; ties go to the higher threshold (stricter gate)."""
    candidates = sorted(set(scores)) + [math.inf]
    best_threshold, best_f1 = candidates[0], -1.0
    for threshold in candidates:
        f1 = prf(scores, gold, threshold)["f1"]
        if f1 >= best_f1:
            best_threshold, best_f1 = threshold, f1
    return best_threshold


def auc(scores: list[float], gold: list[bool]) -> float:
    positives = [s for s, g in zip(scores, gold) if g]
    negatives = [s for s, g in zip(scores, gold) if not g]
    if not positives or not negatives:
        return float("nan")
    wins = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def half_of(document_id: str, seed: int) -> int:
    return int(hashlib.sha256(f"{seed}:{document_id}".encode()).hexdigest(), 16) % 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gate_eval.h5_score")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260928)
    args = parser.parse_args(argv)

    items = {row["item_id"]: row for row in read_jsonl(args.dataset / "items.jsonl")}
    labels = {row["item_id"]: row for row in read_jsonl(args.dataset / "labels.jsonl")}
    jev_supports_probability: dict[str, dict[str, float]] = {}
    jev_source_type: dict[str, str] = {}
    for call in read_jsonl(args.run / "calls.jsonl"):
        if call["status"] != "ok" or call["name_set"] != "N" or call["binding"] != "aligned" or call["run"] != 1:
            continue
        if call["template"] == GATE_TEMPLATE:
            jev_supports_probability.setdefault(call["item_id"], {})[call["order"]] = call["rubric_probabilities"]["supports"]
        elif call["order"] == "canonical":
            jev_source_type[call["item_id"]] = call["rubric_id"]

    rows = []
    for item_id, item in items.items():
        if "canonical" not in jev_supports_probability.get(item_id, {}):
            continue
        probabilities = jev_supports_probability[item_id]
        rows.append({
            "item_id": item_id, "doc": item["source_document_id"], "bucket": item["bucket"],
            "gold": labels[item_id]["gold_quote_supports_item"] == "supports",
            "contested": labels[item_id].get("contested", False),
            "jev": probabilities["canonical"],
            "jev_both_orders": mean(list(probabilities.values())),
            "confidence": float(item["extractor_confidence"]),
            "half": half_of(item["source_document_id"], args.seed),
        })

    def evaluate(fit_rows: list[dict], test_rows: list[dict], score_key: str) -> dict:
        threshold = fit_threshold([r[score_key] for r in fit_rows], [r["gold"] for r in fit_rows])
        test = prf([r[score_key] for r in test_rows], [r["gold"] for r in test_rows], threshold)
        return {"threshold": threshold, "fit": prf([r[score_key] for r in fit_rows], [r["gold"] for r in fit_rows], threshold),
                "test": test, "test_auc": auc([r[score_key] for r in test_rows], [r["gold"] for r in test_rows])}

    folds = {}
    for fold_name, fit_half in (("A_primary", 0), ("B_swapped", 1)):
        fit_rows = [r for r in rows if r["half"] == fit_half]
        test_rows = [r for r in rows if r["half"] != fit_half]
        result = {"n_fit": len(fit_rows), "n_test": len(test_rows),
                  "G_test": len({r["doc"] for r in test_rows})}
        for score_key in ("jev", "jev_both_orders", "confidence"):
            result[score_key] = evaluate(fit_rows, test_rows, score_key)
        jev_threshold = result["jev"]["threshold"]
        confidence_threshold = result["confidence"]["threshold"]

        def f1_difference(sample: list[dict]) -> float:
            gold = [r["gold"] for r in sample]
            return (prf([r["jev"] for r in sample], gold, jev_threshold)["f1"]
                    - prf([r["confidence"] for r in sample], gold, confidence_threshold)["f1"])

        result["f1_difference_jev_minus_confidence"] = cluster_bootstrap(
            test_rows, "doc", f1_difference, args.resamples, args.seed)
        result["jev_ece_test"] = expected_calibration_error([r["jev"] for r in test_rows], [r["gold"] for r in test_rows], 10)
        result["confidence_ece_test"] = expected_calibration_error([r["confidence"] for r in test_rows], [r["gold"] for r in test_rows], 10)
        folds[fold_name] = result

    by_bucket = {}
    for bucket in sorted({r["bucket"] for r in rows}):
        subset = [r for r in rows if r["bucket"] == bucket]
        by_bucket[bucket] = {
            "n": len(subset), "gold_supports": sum(r["gold"] for r in subset),
            "jev_default_accuracy": mean([1.0 if (r["jev"] >= 0.5) == r["gold"] else 0.0 for r in subset]),
            "mean_jev_p_supports": mean([r["jev"] for r in subset]),
            "mean_extractor_confidence": mean([r["confidence"] for r in subset]),
        }

    everything = {
        "n_items": len(rows), "G": len({r["doc"] for r in rows}),
        "gold_supports": sum(r["gold"] for r in rows),
        "auc_all": {"jev": auc([r["jev"] for r in rows], [r["gold"] for r in rows]),
                    "confidence": auc([r["confidence"] for r in rows], [r["gold"] for r in rows])},
        "jev_default_0_5": prf([r["jev"] for r in rows], [r["gold"] for r in rows], 0.5),
        "confidence_distinct_values": sorted({r["confidence"] for r in rows}),
        "ece_all": {"jev": expected_calibration_error([r["jev"] for r in rows], [r["gold"] for r in rows], 10),
                    "confidence": expected_calibration_error([r["confidence"] for r in rows], [r["gold"] for r in rows], 10)},
    }

    primary = folds["A_primary"]
    better_than_noise = primary["f1_difference_jev_minus_confidence"]["lb95"] > 0
    ece_ok = primary["jev_ece_test"] <= ECE_KILL
    killed = not (better_than_noise and ece_ok)
    verdict = {
        "hypothesis": "H5 (discovery plan): independent typed gate beats extractor self-reported confidence",
        "gate_score": "Jev jev-1.13.0 P(supports), current H5 wording (N aligned, run 1, canonical order), from the naming-audit run",
        "labels": "model labels (Claude labels, Codex review, max 3 rounds), used as gold per policy v2",
        "kill_rule": "killed if test-half F1(Jev) - F1(confidence) has one-sided 95% lower bound <= 0, or Jev test-half ECE > 0.15",
        "better_than_noise": better_than_noise, "ece_ok": ece_ok,
        "verdict": "killed" if killed else "survives",
        "primary_fold": "A_primary",
        "f1_test": {"jev": primary["jev"]["test"]["f1"], "confidence": primary["confidence"]["test"]["f1"]},
        "f1_difference_lb95": primary["f1_difference_jev_minus_confidence"]["lb95"],
        "jev_ece_test": primary["jev_ece_test"],
        "exploratory": "90 items, G = 76; test half is about 45 items, so bounds are wide",
    }
    write_json(args.run / "h5_score.json", {"all_items": everything, "folds": folds, "by_bucket": by_bucket})
    write_json(args.run / "h5_verdict.json", verdict)
    print(json.dumps(verdict, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
