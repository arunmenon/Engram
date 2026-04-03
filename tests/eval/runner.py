"""Autoresearch experiment runner for scoring parameter optimization.

Autonomous loop that mutates scoring parameters, evaluates against the
ground-truth dataset, and keeps improvements. Inspired by Karpathy's
autoresearch pattern: one editable asset, one scalar metric, one loop.

Usage:
    python tests/eval/runner.py                    # Run 100 experiments
    python tests/eval/runner.py --iterations=500   # Run 500 experiments
    python tests/eval/runner.py --resume           # Resume from last best
    python tests/eval/runner.py --strategy=grid    # Grid search instead of random

Zero framework dependencies — pure Python 3.12+ stdlib.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.eval.harness import ScoringParams, evaluate, EvalResult


# Parameter ranges (hard constraints)
PARAM_RANGES = {
    "s_base": (12.0, 2000.0),         # 12 hours to ~83 days
    "s_boost": (0.0, 200.0),          # 0 to 200 hours per access
    "entity_s_base": (24.0, 5000.0),  # 1 day to ~208 days
    "entity_s_boost": (0.0, 200.0),
    "w_recency": (0.0, 5.0),
    "w_importance": (0.0, 5.0),
    "w_relevance": (0.0, 5.0),
    "w_user_affinity": (0.0, 5.0),
    "access_boost_coeff": (0.0, 0.3),
    "access_boost_cap": (0.0, 0.5),
    "degree_boost_coeff": (0.0, 0.3),
    "degree_boost_cap": (0.0, 0.5),
    # Intent-aware weight modifiers
    "intent_recency_bias": (0.5, 8.0),
    "intent_importance_bias": (0.5, 8.0),
    "intent_relevance_bias": (0.5, 8.0),
    "intent_affinity_bias": (0.5, 8.0),
    "relevance_exponent": (0.3, 5.0),
    "node_type_event_bonus": (0.5, 3.0),
    "node_type_profile_bonus": (0.5, 3.0),
}


@dataclass
class ExperimentRecord:
    """A single experiment record to log."""

    experiment_id: int
    timestamp: str
    strategy: str
    params: dict
    score: float
    mean_ndcg: float
    mean_violation_rate: float
    mean_precision: float
    mean_recall: float
    intent_ndcg: dict
    accepted: bool
    improvement: float
    best_score_so_far: float
    elapsed_ms: int
    mutated_params: list[str]


def _clamp_param(name: str, value: float) -> float:
    """Clamp parameter to its valid range."""
    min_val, max_val = PARAM_RANGES[name]
    return max(min_val, min(value, max_val))


def _clamp_params(params: ScoringParams) -> ScoringParams:
    """Clamp all parameters to their valid ranges."""
    for name in PARAM_RANGES:
        value = getattr(params, name)
        clamped = _clamp_param(name, value)
        setattr(params, name, clamped)
    return params


def _enforce_constraints(params: ScoringParams) -> ScoringParams:
    """Enforce hard constraints on parameters."""
    # s_base must be > s_boost
    if params.s_base <= params.s_boost:
        params.s_base = params.s_boost + 10.0

    # entity_s_base >= s_base
    if params.entity_s_base < params.s_base:
        params.entity_s_base = params.s_base

    # All weights must be > 0
    if params.w_recency <= 0:
        params.w_recency = 0.1
    if params.w_importance <= 0:
        params.w_importance = 0.1
    if params.w_relevance <= 0:
        params.w_relevance = 0.1
    if params.w_user_affinity <= 0:
        params.w_user_affinity = 0.05

    return _clamp_params(params)


def mutate_random(
    params: ScoringParams, magnitude: float = 0.3, num_params: int | None = None
) -> tuple[ScoringParams, list[str]]:
    """Apply random perturbation to 1-3 random parameters.

    Args:
        params: Current best parameters
        magnitude: Perturbation magnitude (default 0.3 = 30%)
        num_params: Number of parameters to mutate (default random 1-3)

    Returns:
        (mutated_params, list of mutated parameter names)
    """
    mutated = copy.deepcopy(params)
    if num_params is None:
        num_params = random.randint(1, 3)

    param_names = list(PARAM_RANGES.keys())
    chosen = random.sample(param_names, min(num_params, len(param_names)))

    for name in chosen:
        current = getattr(mutated, name)
        factor = 1.0 + random.uniform(-magnitude, magnitude)
        new_value = current * factor
        setattr(mutated, name, new_value)

    mutated = _enforce_constraints(mutated)
    return mutated, chosen


def mutate_grid(
    params: ScoringParams, iteration: int, grid_size: int = 5
) -> tuple[ScoringParams, list[str]]:
    """Grid search strategy: walk through parameter combinations.

    Uses a deterministic ordering based on iteration number to explore
    different regions of the parameter space systematically.

    Args:
        params: Current best parameters (used as center point)
        iteration: Current iteration number
        grid_size: Number of values per parameter (default 5)

    Returns:
        (mutated_params, list of parameters varied this iteration)
    """
    mutated = copy.deepcopy(params)
    param_names = list(PARAM_RANGES.keys())

    # Cycle through parameters deterministically
    param_idx = iteration % len(param_names)
    param_name = param_names[param_idx]
    min_val, max_val = PARAM_RANGES[param_name]

    # Grid value index within this parameter
    grid_idx = (iteration // len(param_names)) % grid_size
    grid_points = [
        min_val + (max_val - min_val) * (i / (grid_size - 1))
        for i in range(grid_size)
    ]
    new_value = grid_points[grid_idx]
    setattr(mutated, param_name, new_value)

    mutated = _enforce_constraints(mutated)
    return mutated, [param_name]


def mutate_focused(
    params: ScoringParams, eval_result: EvalResult, magnitude: float = 0.2
) -> tuple[ScoringParams, list[str]]:
    """Focused strategy: adjust weights based on worst-performing intents.

    Picks randomly from the bottom-3 intents and applies randomized
    magnitude to avoid deterministic loops.

    Args:
        params: Current best parameters
        eval_result: Most recent evaluation result
        magnitude: Base perturbation magnitude (actual varies ±50%)

    Returns:
        (mutated_params, list of mutated parameter names)
    """
    mutated = copy.deepcopy(params)

    # Find worst-performing intents
    if not eval_result.intent_ndcg:
        return mutate_random(params, magnitude, 2)

    # Sort intents by score ascending (worst first)
    sorted_intents = sorted(eval_result.intent_ndcg.items(), key=lambda kv: kv[1])

    # Pick randomly from bottom-3 intents (not always the single worst)
    pick_from = sorted_intents[: min(3, len(sorted_intents))]
    target_intent, target_score = random.choice(pick_from)

    # Randomize magnitude ±50% to avoid repeating the same mutation
    actual_mag = magnitude * random.uniform(0.5, 1.5)

    # Randomly choose direction — usually increase, but sometimes decrease
    direction = 1.0 if random.random() < 0.8 else -1.0

    mutated_names = []

    if target_intent == "why":
        mutated.w_relevance *= 1.0 + direction * actual_mag
        mutated.w_importance *= 1.0 + direction * actual_mag * 0.5
        mutated_names = ["w_relevance", "w_importance"]

    elif target_intent == "when":
        mutated.w_recency *= 1.0 + direction * actual_mag
        mutated.s_base *= 1.0 - direction * actual_mag * 0.3
        mutated_names = ["w_recency", "s_base"]

    elif target_intent in ("who_is", "personalize"):
        mutated.w_user_affinity *= 1.0 + direction * actual_mag
        mutated.w_relevance *= 1.0 + direction * actual_mag * 0.5
        mutated_names = ["w_user_affinity", "w_relevance"]

    elif target_intent == "related":
        mutated.w_relevance *= 1.0 + direction * actual_mag * 1.5
        mutated.w_importance *= 1.0 + direction * actual_mag * 0.5
        mutated_names = ["w_relevance", "w_importance"]

    elif target_intent in ("what", "general"):
        mutated.w_relevance *= 1.0 + direction * actual_mag
        mutated.s_base *= 1.0 + direction * actual_mag * 0.2
        mutated_names = ["w_relevance", "s_base"]

    elif target_intent == "how_does":
        mutated.w_importance *= 1.0 + direction * actual_mag
        mutated.w_relevance *= 1.0 + direction * actual_mag * 0.5
        mutated_names = ["w_importance", "w_relevance"]

    else:
        mutated.s_base *= 1.0 - direction * actual_mag * 0.3
        mutated.w_relevance *= 1.0 + direction * actual_mag
        mutated_names = ["s_base", "w_relevance"]

    # Add one random extra param perturbation for exploration diversity
    extra_params = [p for p in PARAM_RANGES if p not in mutated_names]
    if extra_params:
        extra = random.choice(extra_params)
        extra_mag = random.uniform(-actual_mag * 0.3, actual_mag * 0.3)
        current_val = getattr(mutated, extra)
        setattr(mutated, extra, current_val * (1.0 + extra_mag))
        mutated_names.append(extra)

    mutated = _enforce_constraints(mutated)
    return mutated, mutated_names


def _results_dir() -> Path:
    """Get results directory, creating it if needed."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    return results_dir


def _load_last_best() -> tuple[ScoringParams, float, int] | None:
    """Load the best score and params from the results log.

    Returns:
        (best_params, best_score, last_experiment_id) or None if no results
    """
    results_file = _results_dir() / "experiments.jsonl"
    if not results_file.exists():
        return None

    best_params = None
    best_score = -1.0
    last_id = -1

    with open(results_file) as f:
        for line in f:
            try:
                record = json.loads(line)
                last_id = record.get("experiment_id", last_id)
                score = record.get("score", 0.0)
                if score > best_score:
                    best_score = score
                    params_dict = record.get("params", {})
                    best_params = ScoringParams(**params_dict)
            except (json.JSONDecodeError, TypeError):
                continue

    if best_params is None:
        return None
    return best_params, best_score, last_id


def _save_record(record: ExperimentRecord) -> None:
    """Append a record to the results JSONL file."""
    results_file = _results_dir() / "experiments.jsonl"
    with open(results_file, "a") as f:
        record_dict = asdict(record)
        f.write(json.dumps(record_dict) + "\n")


def _format_params_diff(old_params: ScoringParams, new_params: ScoringParams) -> str:
    """Format the difference between two param sets (for logging)."""
    diffs = []
    for name in PARAM_RANGES:
        old_val = getattr(old_params, name)
        new_val = getattr(new_params, name)
        if abs(old_val - new_val) > 1e-6:
            diffs.append(f"{name}={new_val:.2f}")
    return ", ".join(diffs[:3]) if diffs else "none"


def run_experiments(
    iterations: int = 100,
    strategy: str = "perturb",
    magnitude: float = 0.3,
    seed: int | None = None,
    resume: bool = False,
    k: int = 10,
) -> tuple[ScoringParams, float]:
    """Run the autoresearch experiment loop.

    Args:
        iterations: Number of experiments to run
        strategy: Mutation strategy ("perturb", "grid", or "focused")
        magnitude: Perturbation magnitude (default 0.3)
        seed: Random seed for reproducibility
        resume: Resume from last best result if available
        k: Top-k cutoff for evaluation

    Returns:
        (best_params, best_score)
    """
    if seed is not None:
        random.seed(seed)

    # Print banner
    print("\n" + "═" * 80)
    print("  AUTORESEARCH: Context Graph Scoring Optimization")
    print("═" * 80 + "\n")

    # Initialize baseline
    if resume:
        loaded = _load_last_best()
        if loaded:
            current_params, best_score, last_id = loaded
            next_id = last_id + 1
            print(f"Resumed from experiment {last_id}")
            print(f"  Best score so far: {best_score:.4f}")
            print(f"  Next experiment: {next_id}\n")
        else:
            current_params = ScoringParams()
            best_score = 0.0
            next_id = 1
            print("No previous results found; starting from baseline\n")
    else:
        # Evaluate baseline
        print("Computing baseline...")
        baseline_result = evaluate(ScoringParams(), k=k)
        current_params = baseline_result.params
        best_score = baseline_result.score
        next_id = 1

        print(f"Baseline (experiment 0):")
        print(f"  Score: {baseline_result.score:.4f}  nDCG: {baseline_result.mean_ndcg:.4f}  "
              f"Violations: {baseline_result.mean_violation_rate:.4f}\n")

        # Log baseline
        baseline_record = ExperimentRecord(
            experiment_id=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            strategy="baseline",
            params=asdict(baseline_result.params),
            score=baseline_result.score,
            mean_ndcg=baseline_result.mean_ndcg,
            mean_violation_rate=baseline_result.mean_violation_rate,
            mean_precision=baseline_result.mean_precision,
            mean_recall=baseline_result.mean_recall,
            intent_ndcg=baseline_result.intent_ndcg,
            accepted=True,
            improvement=0.0,
            best_score_so_far=best_score,
            elapsed_ms=0,
            mutated_params=[],
        )
        _save_record(baseline_record)

    # Run experiments
    num_accepted = 0
    num_no_improvement = 0
    start_time = time.time()

    for exp_num in range(iterations):
        exp_id = next_id + exp_num
        iter_start = time.time()

        # Mutate based on strategy
        if strategy == "grid":
            mutated_params, mutated_names = mutate_grid(current_params, exp_num)
        elif strategy == "focused":
            # Focused needs the last eval result
            # Fallback to perturb if we don't have it
            if exp_num == 0:
                mutated_params, mutated_names = mutate_random(current_params, magnitude)
            else:
                # Get last result by re-evaluating current_params
                # (In practice, we'd cache this, but for simplicity we mutate)
                mutated_params, mutated_names = mutate_focused(
                    current_params, last_eval_result, magnitude
                )
        else:  # "perturb" (default)
            mutated_params, mutated_names = mutate_random(current_params, magnitude)

        # Evaluate
        eval_result = evaluate(mutated_params, k=k)
        last_eval_result = eval_result

        # Decide: accept if improved
        improvement = eval_result.score - best_score
        accepted = improvement > 0

        if accepted:
            current_params = mutated_params
            best_score = eval_result.score
            num_accepted += 1
            num_no_improvement = 0
        else:
            num_no_improvement += 1

        # Timing
        elapsed_ms = int((time.time() - iter_start) * 1000)

        # Log record
        record = ExperimentRecord(
            experiment_id=exp_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            strategy=strategy,
            params=asdict(eval_result.params),
            score=eval_result.score,
            mean_ndcg=eval_result.mean_ndcg,
            mean_violation_rate=eval_result.mean_violation_rate,
            mean_precision=eval_result.mean_precision,
            mean_recall=eval_result.mean_recall,
            intent_ndcg=eval_result.intent_ndcg,
            accepted=accepted,
            improvement=improvement,
            best_score_so_far=best_score,
            elapsed_ms=elapsed_ms,
            mutated_params=mutated_names,
        )
        _save_record(record)

        # Print progress line
        status = "✓" if accepted else "✗"
        improvement_str = f"(+{improvement:.4f})" if improvement > 0 else ""
        mutated_str = ", ".join(mutated_names) if mutated_names else "none"

        print(
            f"[{exp_id:3d}/{next_id + iterations - 1:3d}] {strategy:<6s} [{mutated_str:<30s}] "
            f"Score: {eval_result.score:.4f} {status} {improvement_str:<12s} "
            f"best={best_score:.4f}"
        )

        # Early stopping: no improvement for 50+ iterations
        if num_no_improvement > 50 and exp_num > 50:
            print(f"\n  No improvement for 50 iterations; stopping early.\n")
            break

        # Violation rate sanity check
        if eval_result.mean_violation_rate > 0.1:
            print(f"  WARNING: Violation rate = {eval_result.mean_violation_rate:.4f} > 0.1")

    # Final summary
    elapsed_total = time.time() - start_time
    total_exps = exp_num + 1
    avg_time = elapsed_total / total_exps if total_exps > 0 else 0

    print("\n" + "═" * 80)
    print("  RESULTS")
    print("═" * 80)
    print(f"Experiments: {total_exps}")
    print(f"Improvements: {num_accepted}")
    improvement_pct = ((best_score - ScoringParams().s_base * 0) / 0.46) * 100  # Rough baseline
    baseline_score = 0.46  # Default baseline from harness
    if baseline_score > 0:
        improvement_pct = ((best_score - baseline_score) / baseline_score) * 100
    else:
        improvement_pct = 0.0

    print(f"Best score: {best_score:.4f} (from ~0.4600, +{improvement_pct:.1f}%)")
    print(f"\nBest params:")
    p = current_params
    print(f"  s_base={p.s_base:.1f}  s_boost={p.s_boost:.1f}  "
          f"entity_s_base={p.entity_s_base:.1f}  entity_s_boost={p.entity_s_boost:.1f}")
    print(f"  w_recency={p.w_recency:.2f}  w_importance={p.w_importance:.2f}  "
          f"w_relevance={p.w_relevance:.2f}  w_user_affinity={p.w_user_affinity:.2f}")
    print(f"\nTime: {elapsed_total:.1f}s ({avg_time*1000:.0f}ms/experiment)")
    print(f"\nResults saved to: {_results_dir() / 'experiments.jsonl'}")
    print("=" * 80 + "\n")

    return current_params, best_score


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autoresearch experiment runner for scoring parameter optimization"
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of experiments to run (default 100)",
    )
    parser.add_argument(
        "--strategy",
        choices=["perturb", "grid", "focused"],
        default="perturb",
        help="Mutation strategy (default: perturb)",
    )
    parser.add_argument(
        "--magnitude",
        type=float,
        default=0.3,
        help="Perturbation magnitude (default 0.3 = 30%%)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last best result",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-k cutoff for evaluation (default 10)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    try:
        best_params, best_score = run_experiments(
            iterations=args.iterations,
            strategy=args.strategy,
            magnitude=args.magnitude,
            seed=args.seed,
            resume=args.resume,
            k=args.k,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Results have been saved.")
        sys.exit(130)


if __name__ == "__main__":
    main()
