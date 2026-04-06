#!/usr/bin/env python3
"""Thin eval CLI for agent-driven autoresearch.

This is the "run eval and print results" command that Claude Code or Codex
calls each cycle. It evaluates the current harness.py scoring algorithm
with given parameters and optional hooks, then prints a structured report
the agent can parse.

Usage:
    # Baseline (default params, no hooks)
    uv run python tests/eval/run_eval.py

    # With custom params
    uv run python tests/eval/run_eval.py --w_relevance=3.2 --intent_relevance_bias=4.2

    # With hooks enabled (inline config per hook)
    uv run python tests/eval/run_eval.py --hook=edge_boost:boost_factor=0.05,top_n_seeds=5

    # Multiple hooks with per-hook config
    uv run python tests/eval/run_eval.py --hook=edge_boost:boost_factor=0.05 --hook=normalization

    # JSON output (machine-readable)
    uv run python tests/eval/run_eval.py --json

    # Compare two param sets
    uv run python tests/eval/run_eval.py --compare-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.eval.harness import ScoringParams, evaluate  # noqa: E402

# hooks is imported lazily -- only when --hook or --list-hooks is used.
# This keeps the default (param-only) path fast.


def build_params_from_args(args: argparse.Namespace) -> ScoringParams:
    """Build ScoringParams from CLI args, using defaults for unspecified values."""
    kwargs = {}
    for field_name in [
        "s_base", "s_boost", "entity_s_base", "entity_s_boost",
        "w_recency", "w_importance", "w_relevance", "w_user_affinity",
        "access_boost_coeff", "access_boost_cap",
        "degree_boost_coeff", "degree_boost_cap",
        "intent_recency_bias", "intent_importance_bias",
        "intent_relevance_bias", "intent_affinity_bias",
        "node_type_event_bonus", "node_type_profile_bonus",
    ]:
        val = getattr(args, field_name, None)
        if val is not None:
            kwargs[field_name] = val
    return ScoringParams(**kwargs)


def _get_hook_registry():
    """Lazy import of HOOK_REGISTRY -- avoids loading hooks.py at module level."""
    from tests.eval.hooks import HOOK_REGISTRY
    return HOOK_REGISTRY


def parse_hook_spec(spec: str) -> tuple[str, dict]:
    """Parse a hook spec like 'edge_boost:boost_factor=0.05,top_n_seeds=5'.

    Returns (hook_name, config_overrides_dict).
    Plain 'edge_boost' returns ('edge_boost', {}).
    """
    if ":" not in spec:
        return spec.strip(), {}
    name, config_str = spec.split(":", 1)
    overrides = {}
    for pair in config_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        # Auto-convert numeric strings
        try:
            overrides[key.strip()] = int(val.strip())
        except ValueError:
            try:
                overrides[key.strip()] = float(val.strip())
            except ValueError:
                overrides[key.strip()] = val.strip()
    return name.strip(), overrides


def run_with_hooks(params: ScoringParams, hook_specs: list[tuple[str, dict]]):
    """Run evaluate_with_hooks with hooks applied."""
    from tests.eval.autoresearch_v2 import evaluate_with_hooks
    from tests.eval.hooks import apply_structural_hook

    active_hooks = {}
    for hook_name, hook_config in hook_specs:
        hook_info = apply_structural_hook(hook_name, hook_config)
        active_hooks[hook_name] = hook_info

    return evaluate_with_hooks(params, active_hooks)


def format_report(result, params: ScoringParams, hook_names: list[str],
                   dataset_mode: str = "original") -> str:
    """Format a clean report the agent can parse."""
    lines = []
    lines.append("=" * 70)
    lines.append("  EVAL RESULT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Dataset: {dataset_mode}")
    lines.append(f"  SCORE: {result.score:.4f}")
    lines.append(f"  nDCG@10: {result.mean_ndcg:.4f}")
    lines.append(f"  Violation Rate: {result.mean_violation_rate:.4f}")
    lines.append(f"  Precision@10: {result.mean_precision:.4f}")
    lines.append(f"  Recall@10: {result.mean_recall:.4f}")
    lines.append("")

    if hook_names:
        lines.append(f"  Active Hooks: {', '.join(hook_names)}")
        lines.append("")

    lines.append("  Per-Intent nDCG (worst to best):")
    for intent, ndcg in sorted(result.intent_ndcg.items(), key=lambda x: x[1]):
        viol = result.intent_violations.get(intent, 0)
        lines.append(f"    {intent:15s}  nDCG={ndcg:.4f}  violations={viol:.4f}")
    lines.append("")

    # Worst queries
    worst = sorted(result.query_results, key=lambda q: q.ndcg)[:5]
    lines.append("  Worst Queries:")
    for q in worst:
        lines.append(f"    {q.query_id:25s}  nDCG={q.ndcg:.4f}  intent={q.intent}")
    lines.append("")

    lines.append("  Parameters:")
    for k, v in sorted(vars(params).items()):
        if not k.startswith("_"):
            default_val = getattr(ScoringParams(), k, None)
            marker = " *" if v != default_val else ""
            lines.append(f"    {k}: {v}{marker}")
    lines.append("")
    lines.append("  (* = changed from default)")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_json(result, params: ScoringParams, hook_names: list[str],
                dataset_mode: str = "original") -> str:
    """Format as JSON for machine parsing."""
    output = {
        "dataset": dataset_mode,
        "score": round(result.score, 6),
        "mean_ndcg": round(result.mean_ndcg, 6),
        "mean_violation_rate": round(result.mean_violation_rate, 6),
        "mean_precision": round(result.mean_precision, 6),
        "mean_recall": round(result.mean_recall, 6),
        "intent_ndcg": {k: round(v, 6) for k, v in result.intent_ndcg.items()},
        "intent_violations": {k: round(v, 6) for k, v in result.intent_violations.items()},
        "active_hooks": hook_names,
        "params": {
            k: v for k, v in vars(params).items() if not k.startswith("_")
        },
        "worst_queries": [
            {"query_id": q.query_id, "intent": q.intent, "ndcg": round(q.ndcg, 4)}
            for q in sorted(result.query_results, key=lambda q: q.ndcg)[:5]
        ],
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Run eval with current harness.py scoring (agent-driven autoresearch)",
    )

    # Scoring params
    for name, default in vars(ScoringParams()).items():
        if name.startswith("_"):
            continue
        if isinstance(default, bool):
            parser.add_argument(f"--{name}", type=lambda x: x.lower() == "true", default=None)
        elif isinstance(default, (int, float)):
            parser.add_argument(f"--{name}", type=type(default), default=None)

    # Hooks -- supports inline config: --hook=edge_boost:boost_factor=0.05,top_n_seeds=5
    parser.add_argument(
        "--hook", action="append", default=[],
        help="Hook with optional inline config. E.g., --hook=edge_boost:boost_factor=0.05",
    )

    # Output
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--compare-baseline", action="store_true",
                        help="Also run baseline and show delta")

    # Dataset mode
    parser.add_argument(
        "--dataset",
        choices=["original", "extended", "generated-only"],
        default="original",
        help="Dataset mode: original (3 scenarios, 59 nodes), "
             "extended (10 scenarios, ~226 nodes), "
             "generated-only (7 generated scenarios)",
    )

    # Available hooks listing
    parser.add_argument("--list-hooks", action="store_true",
                        help="List available hooks and exit")

    args = parser.parse_args()

    if args.list_hooks:
        registry = _get_hook_registry()
        print("Available hooks:")
        for name, entry in registry.items():
            fn = entry["fn"]
            doc = fn.__doc__.strip().split("\n")[0] if fn.__doc__ else "(no description)"
            config = entry["default"]
            print(f"\n  {name}:")
            print(f"    {doc}")
            print(f"    Config: {entry['config_cls'].__name__}")
            for attr in vars(config):
                if not attr.startswith("_"):
                    print(f"      {attr}: {getattr(config, attr)!r}")
        return

    # Set dataset mode before loading anything
    if args.dataset != "original":
        from tests.eval.dataset import DatasetMode, set_dataset_mode

        set_dataset_mode(DatasetMode(args.dataset))
        # Clear harness cache so it reloads with new mode
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

    params = build_params_from_args(args)

    # Parse hook specs -- each --hook value carries its own inline config
    hook_specs: list[tuple[str, dict]] = []
    for hook_raw in args.hook:
        hook_name, hook_cfg = parse_hook_spec(hook_raw)
        hook_specs.append((hook_name, hook_cfg))

    # Run eval
    result = run_with_hooks(params, hook_specs) if hook_specs else evaluate(params)

    hook_names = [h[0] for h in hook_specs]

    # Compare baseline if requested
    if args.compare_baseline:
        baseline = evaluate(ScoringParams())
        delta = result.score - baseline.score
        pct = (delta / baseline.score) * 100 if baseline.score > 0 else 0

    dataset_mode = args.dataset

    if args.json:
        output = format_json(result, params, hook_names, dataset_mode)
        if args.compare_baseline:
            parsed = json.loads(output)
            parsed["baseline_score"] = round(baseline.score, 6)
            parsed["delta"] = round(delta, 6)
            parsed["improvement_pct"] = round(pct, 2)
            output = json.dumps(parsed, indent=2)
        print(output)
    else:
        print(format_report(result, params, hook_names, dataset_mode))
        if args.compare_baseline:
            print(f"\n  Baseline: {baseline.score:.4f}")
            print(f"  Delta:    {delta:+.4f} ({pct:+.1f}%)")


if __name__ == "__main__":
    main()
