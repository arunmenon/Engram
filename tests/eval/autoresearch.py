#!/usr/bin/env python3
"""Autoresearch loop — LLM-in-the-loop scoring optimization.

This is the REAL Karpathy-style autoresearch script. It calls an LLM
(Claude or GPT) each cycle to REASON about results and propose changes.
Unlike runner.py (blind hill-climbing), this script can propose
STRUCTURAL changes to the scoring algorithm, not just parameter tweaks.

Architecture:
    ┌─────────────────────────────────────────────┐
    │              program.md                      │
    │  (strategy doc the LLM reads each cycle)     │
    └──────────────────┬──────────────────────────┘
                       │ reads once at start
                       ▼
    ┌─────────────────────────────────────────────┐
    │           LLM Agent (Claude/GPT)             │
    │                                              │
    │  Each cycle:                                 │
    │  1. Receive: last params, last score,        │
    │     per-intent breakdown, cycle history       │
    │  2. REASON in natural language about          │
    │     what to change and why                    │
    │  3. Output: new params as JSON                │
    │  4. Eval runs, score is computed              │
    │  5. Decision: accept/reject logged            │
    │  6. Repeat until target or budget exhausted   │
    └──────────────────┬──────────────────────────┘
                       │ produces JSON params
                       ▼
    ┌─────────────────────────────────────────────┐
    │  params.json          harness.py --json      │
    │  (editable asset)     (scalar metric)        │
    └─────────────────────────────────────────────┘

Usage:
    # With Anthropic (Claude)
    ANTHROPIC_API_KEY=sk-... python tests/eval/autoresearch.py

    # With OpenAI (GPT-4)
    OPENAI_API_KEY=sk-... python tests/eval/autoresearch.py --provider=openai

    # Custom settings
    python tests/eval/autoresearch.py --cycles=20 --target=0.65

Requirements:
    pip install anthropic   # or: pip install openai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.eval.harness import ScoringParams, evaluate


# ============================================================================
# LLM Clients — thin wrappers for Claude and OpenAI
# ============================================================================


def call_claude(system_prompt: str, user_prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Call Anthropic Claude API. Returns the text response."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: `pip install anthropic` required for Claude provider")
        sys.exit(1)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def call_openai(system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
    """Call OpenAI API. Returns the text response."""
    try:
        import openai
    except ImportError:
        print("ERROR: `pip install openai` required for OpenAI provider")
        sys.exit(1)

    client = openai.OpenAI()  # reads OPENAI_API_KEY from env
    # Newer models (gpt-5.x, o3, o4) require max_completion_tokens
    # instead of max_tokens
    token_param = "max_completion_tokens" if any(
        model.startswith(p) for p in ("gpt-5", "o3", "o4")
    ) else "max_tokens"
    response = client.chat.completions.create(
        model=model,
        **{token_param: 2048},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# Map provider name → call function
LLM_PROVIDERS = {
    "anthropic": call_claude,
    "openai": call_openai,
}


# ============================================================================
# The System Prompt — what makes this "autoresearch" not "random search"
# ============================================================================


SYSTEM_PROMPT = """You are a scoring optimization agent. Your job is to maximize
a retrieval quality metric by tuning scoring parameters.

You operate in a loop:
1. You receive the current best parameters, the score, and per-intent breakdown
2. You REASON about what to change and why
3. You output new parameters as JSON

IMPORTANT RULES:
- You MUST output valid JSON with parameter values
- Your JSON must be inside a ```json code fence
- Only include parameters you want to change (others keep current values)
- Think step-by-step about WHY each change should help
- Learn from the history of what worked and what didn't
- Be bold early (big changes), careful later (small refinements)

PARAMETER RANGES (hard constraints):
  s_base: [12.0, 2000.0]         # event decay base (hours)
  s_boost: [0.0, 200.0]          # per-access stability boost
  entity_s_base: [24.0, 5000.0]  # entity decay base (hours)
  entity_s_boost: [0.0, 200.0]
  w_recency: [0.01, 5.0]         # weight for recency factor
  w_importance: [0.01, 5.0]      # weight for importance factor
  w_relevance: [0.01, 5.0]       # weight for semantic similarity
  w_user_affinity: [0.01, 5.0]   # weight for user context
  access_boost_coeff: [0.0, 0.3]
  access_boost_cap: [0.0, 0.5]
  degree_boost_coeff: [0.0, 0.3]
  degree_boost_cap: [0.0, 0.5]
  intent_recency_bias: [0.5, 8.0]     # multiplier on w_recency for "when" queries
  intent_importance_bias: [0.5, 8.0]   # multiplier on w_importance for "why" queries
  intent_relevance_bias: [0.5, 8.0]    # multiplier on w_relevance for "related/what/how_does"
  intent_affinity_bias: [0.5, 8.0]     # multiplier on w_user_affinity for "who_is/personalize"
  node_type_event_bonus: [0.5, 3.0]    # composite score multiplier for Event nodes
  node_type_profile_bonus: [0.5, 3.0]  # composite score multiplier for UserProfile/Pref/Skill

CONSTRAINTS:
  s_base > s_boost
  entity_s_base >= s_base
  All weights > 0

SCORING FORMULA:
  composite = (w_recency*recency + w_importance*importance + w_relevance*relevance + w_user_affinity*affinity) / sum(weights)
  For non-"general" intents, the primary weight is multiplied by the intent bias.
  Event node scores are multiplied by node_type_event_bonus.
  UserProfile/Preference/Skill scores are multiplied by node_type_profile_bonus.
  Entity scores are unmodified.

METRIC:
  score = (1 - violation_rate) * mean_ndcg@10
  Higher is better. Target: 0.60+

8 INTENT TYPES: why, when, what, related, general, who_is, how_does, personalize
"""


# ============================================================================
# The Core Loop
# ============================================================================


def build_user_prompt(
    cycle: int,
    total_cycles: int,
    current_params: dict,
    current_score: float,
    intent_breakdown: dict[str, float],
    intent_violations: dict[str, float],
    history: list[dict],
    target: float,
) -> str:
    """Build the per-cycle prompt with context the LLM needs to reason."""

    # Format history (last 10 cycles)
    recent = history[-10:] if len(history) > 10 else history
    history_lines = []
    for h in recent:
        accepted = "✓ ACCEPTED" if h["accepted"] else "✗ rejected"
        delta = h.get("improvement", 0)
        changed = ", ".join(h.get("changed_params", []))
        history_lines.append(
            f"  Cycle {h['cycle']:2d}: score={h['score']:.4f} ({accepted}, Δ={delta:+.4f}) changed=[{changed}]"
        )
    history_block = "\n".join(history_lines) if history_lines else "  (no history yet — this is the first cycle)"

    # Format intent breakdown with weakness indicators
    intent_lines = []
    sorted_intents = sorted(intent_breakdown.items(), key=lambda x: x[1])
    for intent, ndcg in sorted_intents:
        viol = intent_violations.get(intent, 0)
        weakness = " ← WEAKEST" if ndcg == sorted_intents[0][1] else ""
        strength = " ← STRONGEST" if ndcg == sorted_intents[-1][1] else ""
        intent_lines.append(
            f"  {intent:15s}  nDCG={ndcg:.4f}  violations={viol:.4f}{weakness}{strength}"
        )
    intent_block = "\n".join(intent_lines)

    # Format current params
    params_block = json.dumps(current_params, indent=2)

    # Progress indicator
    gap = target - current_score
    progress = ((current_score - 0.46) / (target - 0.46)) * 100 if target > 0.46 else 0

    return f"""## Cycle {cycle}/{total_cycles}

**Current score: {current_score:.4f}**  (target: {target:.4f}, gap: {gap:.4f}, progress: {progress:.1f}%)

### Per-Intent Breakdown (sorted worst→best):
{intent_block}

### Current Parameters:
```json
{params_block}
```

### History (recent cycles):
{history_lines and chr(10).join(history_lines) or '  (first cycle)'}

### Your Task:
1. Analyze which intents are weakest and WHY
2. Reason about what parameter changes would help
3. Consider the history — what patterns have you seen?
4. Output your proposed parameters as JSON

Think step-by-step, then output your changes in a ```json block.
Only include the parameters you want to CHANGE (unchanged ones will be kept).
"""


def extract_json_from_response(text: str) -> dict:
    """Extract JSON parameters from LLM response text.

    Looks for ```json ... ``` code fences first, then bare JSON objects.
    """
    # Try code fence first
    fence_match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON object
    brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def apply_params(base: ScoringParams, overrides: dict) -> ScoringParams:
    """Apply parameter overrides to a base ScoringParams, with constraint enforcement."""
    import copy
    new = copy.deepcopy(base)

    # Known numeric params
    PARAM_RANGES = {
        "s_base": (12.0, 2000.0),
        "s_boost": (0.0, 200.0),
        "entity_s_base": (24.0, 5000.0),
        "entity_s_boost": (0.0, 200.0),
        "w_recency": (0.01, 5.0),
        "w_importance": (0.01, 5.0),
        "w_relevance": (0.01, 5.0),
        "w_user_affinity": (0.01, 5.0),
        "access_boost_coeff": (0.0, 0.3),
        "access_boost_cap": (0.0, 0.5),
        "degree_boost_coeff": (0.0, 0.3),
        "degree_boost_cap": (0.0, 0.5),
        "intent_recency_bias": (0.5, 8.0),
        "intent_importance_bias": (0.5, 8.0),
        "intent_relevance_bias": (0.5, 8.0),
        "intent_affinity_bias": (0.5, 8.0),
        "node_type_event_bonus": (0.5, 3.0),
        "node_type_profile_bonus": (0.5, 3.0),
    }

    for key, value in overrides.items():
        if not hasattr(new, key):
            continue
        if key in PARAM_RANGES:
            lo, hi = PARAM_RANGES[key]
            value = max(lo, min(hi, float(value)))
        setattr(new, key, value)

    # Enforce constraints
    if new.s_base <= new.s_boost:
        new.s_base = new.s_boost + 10.0
    if new.entity_s_base < new.s_base:
        new.entity_s_base = new.s_base

    return new


def params_to_dict(p: ScoringParams) -> dict:
    """Convert ScoringParams to a dict of the tunable numeric fields."""
    return {
        "s_base": p.s_base,
        "s_boost": p.s_boost,
        "entity_s_base": p.entity_s_base,
        "entity_s_boost": p.entity_s_boost,
        "w_recency": p.w_recency,
        "w_importance": p.w_importance,
        "w_relevance": p.w_relevance,
        "w_user_affinity": p.w_user_affinity,
        "access_boost_coeff": p.access_boost_coeff,
        "access_boost_cap": p.access_boost_cap,
        "degree_boost_coeff": p.degree_boost_coeff,
        "degree_boost_cap": p.degree_boost_cap,
        "intent_recency_bias": p.intent_recency_bias,
        "intent_importance_bias": p.intent_importance_bias,
        "intent_relevance_bias": p.intent_relevance_bias,
        "intent_affinity_bias": p.intent_affinity_bias,
        "node_type_event_bonus": p.node_type_event_bonus,
        "node_type_profile_bonus": p.node_type_profile_bonus,
    }


def run_autoresearch(
    provider: str = "anthropic",
    model: str | None = None,
    cycles: int = 15,
    target: float = 0.60,
    log_dir: str | None = None,
) -> None:
    """Run the full autoresearch loop.

    This is the main entry point. It:
    1. Computes baseline score
    2. For each cycle, asks the LLM to reason and propose changes
    3. Evaluates the proposed changes
    4. Accepts or rejects based on score improvement
    5. Logs everything to JSONL

    Args:
        provider: "anthropic" or "openai"
        model: Override model name (default: claude-sonnet-4-20250514 or gpt-4o)
        cycles: Number of LLM reasoning cycles
        target: Target score to stop at
        log_dir: Directory for log files
    """
    # Select LLM call function
    call_llm = LLM_PROVIDERS.get(provider)
    if not call_llm:
        print(f"ERROR: Unknown provider '{provider}'. Use 'anthropic' or 'openai'.")
        sys.exit(1)

    if model is None:
        model = "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o"

    # Set up logging
    if log_dir is None:
        log_dir = str(Path(__file__).parent / "results")
    Path(log_dir).mkdir(exist_ok=True)
    log_file = Path(log_dir) / "autoresearch.jsonl"
    reasoning_file = Path(log_dir) / "autoresearch_reasoning.md"

    # Load program.md for the system prompt context
    program_path = Path(__file__).parent / "program.md"
    program_context = ""
    if program_path.exists():
        program_context = program_path.read_text()

    full_system = SYSTEM_PROMPT
    if program_context:
        full_system += f"\n\n--- STRATEGY DOCUMENT ---\n{program_context[:3000]}"

    print("═" * 70)
    print("  AUTORESEARCH — LLM-in-the-Loop Scoring Optimization")
    print(f"  Provider: {provider} ({model})")
    print(f"  Cycles: {cycles}  Target: {target}")
    print("═" * 70)

    # ── Step 1: Baseline ──
    print("\nComputing baseline...")
    best_params = ScoringParams()  # all defaults
    best_result = evaluate(best_params)
    best_score = best_result.score

    print(f"Baseline: score={best_score:.4f}  nDCG={best_result.mean_ndcg:.4f}  violations={best_result.mean_violation_rate:.4f}")
    print()

    # Log baseline
    history: list[dict] = []
    baseline_record = {
        "cycle": 0,
        "score": best_score,
        "accepted": True,
        "improvement": 0.0,
        "changed_params": [],
        "params": params_to_dict(best_params),
        "intent_ndcg": best_result.intent_ndcg,
    }
    history.append(baseline_record)
    with open(log_file, "a") as f:
        f.write(json.dumps(baseline_record) + "\n")

    with open(reasoning_file, "a") as f:
        f.write(f"# Autoresearch Log — {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(f"## Baseline: {best_score:.4f}\n\n")

    # ── Step 2: The Loop ──
    for cycle in range(1, cycles + 1):
        print(f"\n{'─' * 70}")
        print(f"  Cycle {cycle}/{cycles}")
        print(f"{'─' * 70}")

        # Build prompt with full context
        user_prompt = build_user_prompt(
            cycle=cycle,
            total_cycles=cycles,
            current_params=params_to_dict(best_params),
            current_score=best_score,
            intent_breakdown=best_result.intent_ndcg,
            intent_violations=best_result.intent_violations,
            history=history,
            target=target,
        )

        # ── Call LLM ──
        print(f"  Asking {model} to reason...")
        t0 = time.time()
        try:
            response_text = call_llm(full_system, user_prompt, model=model)
        except Exception as e:
            print(f"  ERROR calling LLM: {e}")
            continue
        llm_time = time.time() - t0
        print(f"  LLM responded in {llm_time:.1f}s")

        # ── Extract proposed params ──
        proposed_overrides = extract_json_from_response(response_text)
        if not proposed_overrides:
            print("  WARNING: Could not extract JSON params from LLM response. Skipping.")
            # Log the reasoning anyway
            with open(reasoning_file, "a") as f:
                f.write(f"## Cycle {cycle} — PARSE FAILURE\n\n")
                f.write(f"```\n{response_text[:1000]}\n```\n\n")
            continue

        changed_params = list(proposed_overrides.keys())
        print(f"  Proposed changes: {changed_params}")

        # ── Apply and evaluate ──
        candidate_params = apply_params(best_params, proposed_overrides)
        t0 = time.time()
        candidate_result = evaluate(candidate_params)
        eval_time = time.time() - t0

        candidate_score = candidate_result.score
        improvement = candidate_score - best_score
        accepted = candidate_score > best_score

        # ── Accept or reject ──
        if accepted:
            best_score = candidate_score
            best_params = candidate_params
            best_result = candidate_result
            marker = f"✓ ACCEPTED (+{improvement:.4f})"
        else:
            marker = f"✗ rejected ({improvement:+.4f})"

        print(f"  Score: {candidate_score:.4f}  {marker}")
        print(f"  Eval time: {eval_time*1000:.0f}ms")

        # ── Log everything ──
        record = {
            "cycle": cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": candidate_score,
            "accepted": accepted,
            "improvement": improvement if accepted else 0.0,
            "changed_params": changed_params,
            "proposed_overrides": proposed_overrides,
            "params": params_to_dict(candidate_params),
            "intent_ndcg": candidate_result.intent_ndcg,
            "intent_violations": candidate_result.intent_violations,
            "llm_time_s": round(llm_time, 2),
            "eval_time_ms": round(eval_time * 1000),
            "best_score_so_far": best_score,
        }
        history.append(record)
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Log the LLM's full reasoning
        with open(reasoning_file, "a") as f:
            f.write(f"## Cycle {cycle} — {'ACCEPTED' if accepted else 'REJECTED'} (score={candidate_score:.4f})\n\n")
            f.write(f"**Changed:** {changed_params}\n\n")
            f.write(f"### LLM Reasoning:\n\n{response_text}\n\n")
            f.write(f"---\n\n")

        # ── Check stopping conditions ──
        if best_score >= target:
            print(f"\n  TARGET REACHED! {best_score:.4f} >= {target:.4f}")
            break

    # ── Final Summary ──
    print(f"\n{'═' * 70}")
    print(f"  AUTORESEARCH COMPLETE")
    print(f"{'═' * 70}")
    print(f"  Final score:  {best_score:.4f}  (baseline: 0.4600, +{(best_score/0.4600 - 1)*100:.1f}%)")
    print(f"  Cycles run:   {min(cycle, cycles)}")
    print(f"  Target:       {target:.4f}  ({'REACHED' if best_score >= target else 'not reached'})")
    print(f"\n  Per-intent nDCG:")
    for intent, ndcg in sorted(best_result.intent_ndcg.items(), key=lambda x: x[1]):
        print(f"    {intent:15s} {ndcg:.4f}")
    print(f"\n  Best parameters:")
    for k, v in sorted(params_to_dict(best_params).items()):
        print(f"    {k}: {v}")
    print(f"\n  Logs:")
    print(f"    {log_file}")
    print(f"    {reasoning_file}")
    print(f"{'═' * 70}")


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch: LLM-in-the-loop scoring optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with Claude (default)
  ANTHROPIC_API_KEY=sk-... python tests/eval/autoresearch.py

  # Run with GPT-4
  OPENAI_API_KEY=sk-... python tests/eval/autoresearch.py --provider=openai

  # Quick test (5 cycles)
  python tests/eval/autoresearch.py --cycles=5

  # Aggressive target
  python tests/eval/autoresearch.py --cycles=30 --target=0.65
        """,
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model name (default: auto-select based on provider)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=15,
        help="Number of LLM reasoning cycles (default: 15)",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.60,
        help="Target score to stop at (default: 0.60)",
    )

    args = parser.parse_args()

    # Validate API key exists
    if args.provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY environment variable")
        print("  export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    run_autoresearch(
        provider=args.provider,
        model=args.model,
        cycles=args.cycles,
        target=args.target,
    )


if __name__ == "__main__":
    main()
