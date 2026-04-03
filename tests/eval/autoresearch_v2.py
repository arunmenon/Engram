#!/usr/bin/env python3
"""Autoresearch V2 -- Structural-aware LLM-in-the-loop optimization.

Extends V1 with three proposal types:
  1. "params"     -- numeric parameter tuning (fast, same as V1)
  2. "structural" -- enable/configure pre-built hooks from hooks.py
  3. "code"       -- raw Python code patches to harness.py (advanced, opt-in)

The V2 loop reads harness.py evaluate() source, hook signatures, and
program.md to give the LLM full context about the scoring pipeline.
Structural proposals wire hooks into a wrapper evaluate function;
code patches modify harness.py on disk with automatic backup/revert.

Architecture:
    ┌────────────────────────────────────────────────────────────┐
    │                  program.md + harness source               │
    │  (strategy doc + evaluate() code the LLM reads each cycle) │
    └──────────────────────┬─────────────────────────────────────┘
                           │ reads once at start
                           ▼
    ┌────────────────────────────────────────────────────────────┐
    │              LLM Agent (Claude / GPT)                      │
    │                                                            │
    │  Each cycle:                                               │
    │  1. Receive: params, score, intent breakdown, hook state,  │
    │     evaluate() source, hook signatures, history            │
    │  2. REASON about what type of change will help most        │
    │  3. Output: params / structural hook / code patch as JSON  │
    │  4. V2 loop applies proposal with safety guards            │
    │  5. Evaluate, accept/reject, repeat                        │
    └──────────────────────┬─────────────────────────────────────┘
                           │ produces JSON proposal
                           ▼
    ┌────────────────────────────────────────────────────────────┐
    │  ScoringParams   hooks.py   harness.py                     │
    │  (params)        (hooks)    (code patches)                 │
    └────────────────────────────────────────────────────────────┘

Usage:
    # With Anthropic (Claude) -- structural hooks enabled by default
    ANTHROPIC_API_KEY=sk-... python tests/eval/autoresearch_v2.py

    # With OpenAI
    OPENAI_API_KEY=sk-... python tests/eval/autoresearch_v2.py --provider=openai

    # Param-only mode (V1 compatible)
    python tests/eval/autoresearch_v2.py --no-structural

    # Enable raw code patches (advanced)
    python tests/eval/autoresearch_v2.py --allow-code

    # Custom settings
    python tests/eval/autoresearch_v2.py --cycles=25 --target=0.70

Requirements:
    pip install anthropic   # or: pip install openai
"""

from __future__ import annotations

import argparse
import copy
import importlib
import inspect
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.eval.dataset import load_eval_dataset  # noqa: E402
from tests.eval.harness import (  # noqa: E402
    EvalResult,
    QueryResult,
    ScoringParams,
    compute_ndcg,
    compute_precision_at_k,
    compute_recall_at_k,
    compute_violation_rate,
    evaluate,
    get_intent_weights,
    score_entity_node,
    score_node,
)
from tests.eval.hooks import HOOK_REGISTRY  # noqa: E402

# Path to harness.py (for code patch operations)
_HARNESS_PATH = Path(__file__).resolve().parent / "harness.py"
_HARNESS_BACKUP_PATH = _HARNESS_PATH.with_suffix(".py.bak")


# ============================================================================
# LLM Clients -- thin wrappers for Claude and OpenAI (same as V1)
# ============================================================================


def call_claude(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Call Anthropic Claude API. Returns the text response."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: `pip install anthropic` required for Claude provider")
        sys.exit(1)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=model,
        max_tokens=4096,
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
    token_param = (
        "max_completion_tokens"
        if any(model.startswith(p) for p in ("gpt-5", "o3", "o4"))
        else "max_tokens"
    )
    response = client.chat.completions.create(
        model=model,
        **{token_param: 4096},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# Map provider name -> call function
LLM_PROVIDERS: dict[str, Any] = {
    "anthropic": call_claude,
    "openai": call_openai,
}


# ============================================================================
# V2 System Prompt -- extended with harness source, hooks, program.md
# ============================================================================


def _read_evaluate_source() -> str:
    """Read the evaluate() function source from harness.py."""
    try:
        import tests.eval.harness as harness_module

        source = inspect.getsource(harness_module.evaluate)
        return source
    except Exception:
        # Fallback: read from disk
        try:
            text = _HARNESS_PATH.read_text()
            # Extract the evaluate function by finding its def and the next top-level def
            start = text.find("def evaluate(")
            if start == -1:
                return "(evaluate source not found)"
            # Find next top-level function or class after evaluate
            remaining = text[start:]
            lines = remaining.split("\n")
            end_idx = len(lines)
            for i, line in enumerate(lines[1:], 1):
                if (
                    line
                    and not line[0].isspace()
                    and (line.startswith("def ") or line.startswith("class "))
                ):
                    end_idx = i
                    break
            return "\n".join(lines[:end_idx])
        except Exception:
            return "(could not read evaluate source)"


def _get_hook_signatures() -> str:
    """Build a summary of available hooks from HOOK_REGISTRY."""
    lines = ["Available hooks in HOOK_REGISTRY:"]
    lines.append("")
    for hook_name, hook_entry in HOOK_REGISTRY.items():
        hook_fn = hook_entry["fn"]
        default_config = hook_entry["default"]
        config_cls = hook_entry["config_cls"]
        # Get config field names and defaults
        config_fields = []
        for field_name in vars(default_config):
            if not field_name.startswith("_"):
                val = getattr(default_config, field_name)
                # Truncate long defaults
                val_repr = repr(val)
                if len(val_repr) > 80:
                    val_repr = val_repr[:77] + "..."
                config_fields.append(f"    {field_name}: {val_repr}")
        fields_block = "\n".join(config_fields) if config_fields else "    (no config)"
        lines.append(f"  {hook_name}:")
        lines.append(f"    function: {hook_fn.__name__}")
        lines.append(f"    config class: {config_cls.__name__}")
        lines.append(
            "    signature: (all_nodes, all_edges, query, node_scores, config) -> node_scores"
        )
        lines.append("    default config:")
        lines.append(fields_block)
        # Add docstring first line if available
        if hook_fn.__doc__:
            first_line = hook_fn.__doc__.strip().split("\n")[0]
            lines.append(f"    purpose: {first_line}")
        lines.append("")
    return "\n".join(lines)


def build_v2_system_prompt(
    structural_enabled: bool = True,
    allow_code: bool = False,
) -> str:
    """Build the full V2 system prompt with harness source and hook info.

    Args:
        structural_enabled: Whether structural proposals (hooks) are available.
        allow_code: Whether raw code patches are permitted.

    Returns:
        Complete system prompt string for the LLM.
    """
    base_prompt = """You are a scoring optimization agent (V2). Your job is to maximize
a retrieval quality metric by tuning scoring parameters AND structural scoring logic.

You operate in a loop:
1. You receive the current best parameters, score, per-intent breakdown, active hooks, and history
2. You REASON about what type of change will help most
3. You output a proposal as JSON (parameters, structural hook, or code patch)

IMPORTANT RULES:
- You MUST output valid JSON with a "type" field inside a ```json code fence
- Think step-by-step about WHY each change should help
- Learn from the history of what worked and what didn't
- Be bold early (big changes), careful later (small refinements)
- Only include parameters you want to change in "params" proposals

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
  composite = (w_rec*rec + w_imp*imp + w_rel*rel + w_aff*aff) / sum(weights)
  For non-"general" intents, the primary weight is multiplied by the intent bias.
  Event node scores are multiplied by node_type_event_bonus.
  UserProfile/Preference/Skill scores are multiplied by node_type_profile_bonus.
  Entity scores are unmodified.

METRIC:
  score = (1 - violation_rate) * mean_ndcg@10
  Higher is better. Target: 0.65+

8 INTENT TYPES: why, when, what, related, general, who_is, how_does, personalize
"""

    # Add proposal type documentation
    proposal_docs = """
PROPOSAL TYPES:

### Type 1: "params" -- Numeric Parameter Change
Modify ScoringParams values. Only include parameters you want to change.
```
{"type": "params", "changes": {"w_relevance": 3.5, "intent_relevance_bias": 4.2}}
```

"""

    if structural_enabled:
        proposal_docs += """### Type 2: "structural" -- Enable/Configure a Pre-built Hook
Wire a hook from hooks.py into the scoring pipeline. Hooks transform node_scores
after base scoring, before ranking. Multiple hooks can be active simultaneously.
To DISABLE a previously active hook, set "enabled": false.
```
{"type": "structural", "hook": "edge_boost", "config": {"boost_factor": 0.2, "max_hops": 1}}
```
```
{"type": "structural", "hook": "edge_boost", "enabled": false}
```

"""

    if allow_code:
        proposal_docs += """### Type 3: "code" -- Raw Python Code Patch (ADVANCED)
Apply a Python code patch to harness.py's evaluate() function. The patch is
a string of Python code that replaces a target section. PREFER hooks over code
patches -- only use this for truly novel ideas no existing hook covers.
Syntax errors trigger automatic revert.
```
{"type": "code", "target": "evaluate", "description": "What this does", "code": "...python code..."}
```

"""

    # Add evaluate() source
    eval_source = _read_evaluate_source()
    source_section = f"""
--- HARNESS evaluate() SOURCE ---
This is the function that scores nodes and computes metrics. Structural hooks
are applied AFTER node scoring (after the per-node loop) and BEFORE ranking.

```python
{eval_source}
```
"""

    # Add hook signatures
    hook_section = ""
    if structural_enabled:
        hook_sigs = _get_hook_signatures()
        hook_section = f"""
--- AVAILABLE HOOKS ---
{hook_sigs}

HOOK COMPOSITION ORDER (recommended):
1. score_normalization (fix scale issues first)
2. edge_boost (add graph signal to normalized scores)
3. negative_penalty (penalize nodes similar to must_not_appear)
4. temporal_window (zero irrelevant temporal nodes)
5. mmr_diversity (final diversity pass on top-k)

Start with ONE hook, measure impact, then add the next. Do NOT enable all at once.
"""

    # Add program.md content
    program_path = Path(__file__).parent / "program.md"
    program_section = ""
    if program_path.exists():
        program_text = program_path.read_text()
        # First 4000 chars
        truncated = program_text[:4000]
        if len(program_text) > 4000:
            truncated += "\n... (truncated)"
        program_section = f"\n--- STRATEGY DOCUMENT (program.md) ---\n{truncated}\n"

    return base_prompt + proposal_docs + source_section + hook_section + program_section


# ============================================================================
# Prompt Building -- extended with structural context
# ============================================================================


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


def build_v2_user_prompt(
    cycle: int,
    total_cycles: int,
    current_params: dict,
    current_score: float,
    intent_breakdown: dict[str, float],
    intent_violations: dict[str, float],
    history: list[dict],
    target: float,
    active_hooks: dict[str, dict[str, Any]],
    structural_enabled: bool = True,
    allow_code: bool = False,
) -> str:
    """Build the per-cycle user prompt with full V2 context.

    Extends V1 prompt with active hooks state and structural proposal guidance.
    """
    # Format history (last 10 cycles)
    recent = history[-10:] if len(history) > 10 else history
    history_lines = []
    for h in recent:
        accepted = "ACCEPTED" if h["accepted"] else "rejected"
        delta = h.get("improvement", 0)
        ptype = h.get("proposal_type", "params")
        changed = ", ".join(h.get("changed_params", []))
        hook_name = h.get("hook_name", "")
        label = f"[{ptype}]"
        if hook_name:
            label = f"[{ptype}: {hook_name}]"
        history_lines.append(
            f"  Cycle {h['cycle']:2d}: score={h['score']:.4f} ({accepted}, delta={delta:+.4f}) "
            f"{label} changed=[{changed}]"
        )
    history_block = "\n".join(history_lines) if history_lines else "  (no history yet)"

    # Format intent breakdown with weakness indicators
    intent_lines = []
    sorted_intents = sorted(intent_breakdown.items(), key=lambda x: x[1])
    for intent, ndcg in sorted_intents:
        viol = intent_violations.get(intent, 0)
        weakness = " <-- WEAKEST" if ndcg == sorted_intents[0][1] else ""
        strength = " <-- STRONGEST" if ndcg == sorted_intents[-1][1] else ""
        intent_lines.append(
            f"  {intent:15s}  nDCG={ndcg:.4f}  violations={viol:.4f}{weakness}{strength}"
        )
    intent_block = "\n".join(intent_lines)

    # Format current params
    params_block = json.dumps(current_params, indent=2)

    # Format active hooks
    hooks_block = "  (none active)"
    if active_hooks:
        hook_lines = []
        for hname, hinfo in active_hooks.items():
            config_dict = {}
            config_obj = hinfo.get("config")
            if config_obj is not None:
                for attr in vars(config_obj):
                    if not attr.startswith("_"):
                        val = getattr(config_obj, attr)
                        val_repr = repr(val)
                        if len(val_repr) > 60:
                            val_repr = val_repr[:57] + "..."
                        config_dict[attr] = val_repr
            hook_lines.append(f"  {hname}: {json.dumps(config_dict)}")
        hooks_block = "\n".join(hook_lines)

    # Progress indicator
    gap = target - current_score
    baseline_score = 0.46
    if target > baseline_score:
        progress = ((current_score - baseline_score) / (target - baseline_score)) * 100
    else:
        progress = 0

    # Stagnation detector
    stagnation_note = ""
    if len(history) >= 4:
        recent_scores = [h["score"] for h in history[-3:]]
        if all(abs(s - recent_scores[0]) < 0.001 for s in recent_scores):
            stagnation_note = (
                "\n**STAGNATION DETECTED**: Last 3 cycles had nearly identical scores. "
                "Consider switching proposal type (params -> structural or vice versa) "
                "or trying a completely different approach."
            )

    proposal_guidance = ""
    if structural_enabled:
        proposal_guidance = """
### Proposal Types Available:
- **"params"**: Tune numeric ScoringParams (fast, 8ms eval)
- **"structural"**: Enable/configure a hook from hooks.py (uses graph structure)
"""
        if allow_code:
            proposal_guidance += (
                '- **"code"**: Raw Python patch to harness.py (advanced, auto-reverts on error)\n'
            )
    else:
        proposal_guidance = """
### Mode: Parameter-only (V1 compatible)
Output a JSON with parameter changes only. No structural hooks available.
"""

    return f"""## Cycle {cycle}/{total_cycles}

**Current score: {current_score:.4f}** (target: {target:.4f}, gap: {gap:.4f})
Progress: {progress:.1f}%
{stagnation_note}

### Per-Intent Breakdown (sorted worst to best):
{intent_block}

### Current Parameters:
```json
{params_block}
```

### Active Hooks:
{hooks_block}

### History (recent cycles):
{history_block}
{proposal_guidance}
### Your Task:
1. Analyze which intents are weakest and WHY
2. Consider whether a parameter change, structural hook, or different approach would help
3. If parameter tuning plateaued, try a hook (edge_boost for weak "related")
4. Output your proposed change as JSON inside a ```json block

Remember: Include a "type" field in your JSON ("params", "structural", or "code").
For "params" type, put parameter changes under a "changes" key.
For "structural" type, include "hook" name and optional "config" overrides.
"""


# ============================================================================
# Response Parsing -- detect proposal type
# ============================================================================


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response text.

    Looks for ```json ... ``` code fences first, then bare JSON objects.
    Handles nested JSON objects (structural proposals may contain nested dicts).
    """
    # Try code fence first
    fence_match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON object (greedy to capture nested braces)
    # Find the first { and match to its closing }
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    return {}


def parse_v2_response(text: str) -> dict:
    """Parse a V2 LLM response into a typed proposal.

    Returns a dict with at minimum a "type" field:
      - {"type": "params", "changes": {...}}
      - {"type": "structural", "hook": "...", "config": {...}}
      - {"type": "code", "target": "...", "code": "..."}
      - {"type": "params", "changes": {...}} (fallback for V1-style responses)
    """
    raw = extract_json_from_response(text)
    if not raw:
        return {}

    proposal_type = raw.get("type", "")

    if proposal_type == "params":
        changes = raw.get("changes", {})
        if not changes:
            # V1 compat: treat all non-meta keys as param changes
            changes = {k: v for k, v in raw.items() if k != "type"}
        return {"type": "params", "changes": changes}

    elif proposal_type == "structural":
        hook_name = raw.get("hook", "")
        if not hook_name:
            return {}
        config_overrides = raw.get("config", {})
        enabled = raw.get("enabled", True)
        return {
            "type": "structural",
            "hook": hook_name,
            "config": config_overrides,
            "enabled": enabled,
        }

    elif proposal_type == "code":
        code = raw.get("code", "")
        if not code:
            return {}
        return {
            "type": "code",
            "target": raw.get("target", "evaluate"),
            "description": raw.get("description", ""),
            "code": code,
        }

    else:
        # No type field -- treat as V1 param-only response
        # Remove any non-numeric keys that might be metadata
        changes = {}
        for k, v in raw.items():
            if k in ("type", "reasoning", "explanation", "description"):
                continue
            try:
                changes[k] = float(v)
            except (ValueError, TypeError):
                continue
        if changes:
            return {"type": "params", "changes": changes}
        return {}


# ============================================================================
# Parameter Application (same as V1)
# ============================================================================


PARAM_RANGES: dict[str, tuple[float, float]] = {
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


def apply_params(base: ScoringParams, overrides: dict) -> ScoringParams:
    """Apply parameter overrides to a base ScoringParams, with constraint enforcement."""
    new = copy.deepcopy(base)

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


# ============================================================================
# Structural Hook Application
# ============================================================================


def apply_structural_hook(
    hook_name: str,
    config_overrides: dict,
) -> dict[str, Any]:
    """Build hook info dict from a hook name and config overrides.

    Looks up the hook function and config class in HOOK_REGISTRY,
    creates a new config instance with overrides applied, and returns
    a dict suitable for passing to evaluate_with_hooks.

    Args:
        hook_name: Name of the hook in HOOK_REGISTRY (e.g., "edge_boost").
        config_overrides: Dict of config field overrides to apply.

    Returns:
        Dict with "fn" (callable) and "config" (config instance) keys.

    Raises:
        ValueError: If hook_name is not found in HOOK_REGISTRY.
    """
    if hook_name not in HOOK_REGISTRY:
        raise ValueError(f"Unknown hook '{hook_name}'. Available: {list(HOOK_REGISTRY.keys())}")

    hook_entry = HOOK_REGISTRY[hook_name]
    hook_fn = hook_entry["fn"]
    default_config = hook_entry["default"]

    # Build config with overrides
    # Start from defaults, then apply overrides
    config = copy.deepcopy(default_config)
    for key, value in config_overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return {"fn": hook_fn, "config": config}


# ============================================================================
# Evaluate with Hooks -- wrapper that applies hooks after base scoring
# ============================================================================


def evaluate_with_hooks(
    params: ScoringParams,
    active_hooks: dict[str, dict[str, Any]],
    k: int = 10,
) -> EvalResult:
    """Run evaluation with structural hooks applied after base scoring.

    This is the core V2 evaluation function. It replicates the scoring
    pipeline from harness.py's evaluate() but injects hook calls between
    node scoring and ranking. This avoids modifying harness.py on disk.

    The hook application order follows the dict insertion order of active_hooks.
    Callers should maintain hooks in the recommended composition order.

    Args:
        params: ScoringParams for base scoring.
        active_hooks: Dict of hook_name -> {"fn": callable, "config": config_obj}.
        k: Top-k cutoff for metrics.

    Returns:
        EvalResult with score and per-intent breakdown.
    """
    dataset = load_eval_dataset()
    all_nodes = dataset["all_nodes"]
    all_queries = dataset["queries"]
    all_edges = dataset["all_edges"]

    # Fixed evaluation time (same as harness.py)
    base_time = datetime.fromisoformat(dataset["metadata"]["base_time"])
    now = base_time.replace(hour=12, minute=0, second=0, microsecond=0)

    # Intents where centroid embedding helps
    centroid_intents = {"why", "when", "general", "how_does", "personalize"}

    query_results: list[QueryResult] = []
    intent_ndcg_dict: dict[str, list[float]] = {}
    intent_violations_dict: dict[str, list[float]] = {}

    for query in all_queries:
        # Stage 1: Query Embedding Construction (same as harness.py)
        use_centroid = (
            params.use_centroid_embedding
            and query.intent in centroid_intents
            and len(query.expected_top_nodes) > 1
        )

        query_embedding: list[float] = []
        if use_centroid:
            embeddings = []
            for judgment in query.expected_top_nodes:
                if judgment.node_id in all_nodes:
                    emb = all_nodes[judgment.node_id].attributes.get("embedding", [])
                    if emb:
                        embeddings.append(emb)
            if embeddings:
                dim = len(embeddings[0])
                query_embedding = [
                    sum(e[d] for e in embeddings) / len(embeddings) for d in range(dim)
                ]
        elif query.expected_top_nodes:
            first_node_id = query.expected_top_nodes[0].node_id
            if first_node_id in all_nodes:
                first_node = all_nodes[first_node_id]
                query_embedding = first_node.attributes.get("embedding", [])

        # Stage 2: Intent Weight Calculation
        effective_weights = get_intent_weights(params, query.intent)

        intent_params = ScoringParams(
            s_base=params.s_base,
            s_boost=params.s_boost,
            entity_s_base=params.entity_s_base,
            entity_s_boost=params.entity_s_boost,
            w_recency=effective_weights["w_recency"],
            w_importance=effective_weights["w_importance"],
            w_relevance=effective_weights["w_relevance"],
            w_user_affinity=effective_weights["w_user_affinity"],
            access_boost_coeff=params.access_boost_coeff,
            access_boost_cap=params.access_boost_cap,
            degree_boost_coeff=params.degree_boost_coeff,
            degree_boost_cap=params.degree_boost_cap,
        )

        # Stage 3+4: Per-Node Scoring with Node Type Bonuses
        event_bonus = params.node_type_event_bonus
        profile_bonus = params.node_type_profile_bonus

        node_scores: dict[str, float] = {}
        for node_id, node in all_nodes.items():
            node_data = node.attributes
            node_type = node.node_type

            if node_type == "Event":
                scores = score_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score * event_bonus
            elif node_type in ("UserProfile", "Preference", "Skill"):
                scores = score_entity_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score * profile_bonus
            else:
                scores = score_entity_node(node_data, query_embedding, intent_params, now)
                node_scores[node_id] = scores.decay_score

        # Stage 5: Apply active hooks (V2 addition)
        for _hook_name, hook_info in active_hooks.items():
            hook_fn = hook_info["fn"]
            hook_config = hook_info["config"]
            node_scores = hook_fn(all_nodes, all_edges, query, node_scores, hook_config)

        # Rank by composite score descending
        ranked_pairs = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        ranked_ids = [node_id for node_id, _ in ranked_pairs]

        # Build judgment dict
        judgments = {judgment.node_id: judgment.grade for judgment in query.expected_top_nodes}
        relevant_set = set(judgments.keys())

        # Compute metrics
        ndcg = compute_ndcg(ranked_ids, judgments, k)
        violation_rate = compute_violation_rate(ranked_ids, query.must_not_appear, k)
        precision = compute_precision_at_k(ranked_ids, relevant_set, k)
        recall = compute_recall_at_k(ranked_ids, relevant_set, k)

        result = QueryResult(
            query_id=query.query_id,
            intent=query.intent,
            ndcg=ndcg,
            violation_rate=violation_rate,
            precision=precision,
            recall=recall,
            top_k_ids=ranked_ids[:k],
        )
        query_results.append(result)

        # Accumulate intent metrics
        if query.intent not in intent_ndcg_dict:
            intent_ndcg_dict[query.intent] = []
            intent_violations_dict[query.intent] = []
        intent_ndcg_dict[query.intent].append(ndcg)
        intent_violations_dict[query.intent].append(violation_rate)

    # Compute aggregates
    n_queries = len(query_results) if query_results else 1
    mean_ndcg = sum(r.ndcg for r in query_results) / n_queries
    mean_violation_rate = sum(r.violation_rate for r in query_results) / n_queries
    mean_precision = sum(r.precision for r in query_results) / n_queries
    mean_recall = sum(r.recall for r in query_results) / n_queries

    intent_ndcg = {intent: sum(scores) / len(scores) for intent, scores in intent_ndcg_dict.items()}
    intent_violations = {
        intent: sum(scores) / len(scores) for intent, scores in intent_violations_dict.items()
    }

    combined_score = (1.0 - mean_violation_rate) * mean_ndcg

    return EvalResult(
        score=combined_score,
        mean_ndcg=mean_ndcg,
        mean_violation_rate=mean_violation_rate,
        mean_precision=mean_precision,
        mean_recall=mean_recall,
        intent_ndcg=intent_ndcg,
        intent_violations=intent_violations,
        query_results=query_results,
        params=params,
    )


# ============================================================================
# Safe Code Patching -- backup/restore/reload harness.py
# ============================================================================


def backup_harness() -> bool:
    """Create a backup of harness.py. Returns True on success."""
    try:
        shutil.copy2(_HARNESS_PATH, _HARNESS_BACKUP_PATH)
        return True
    except OSError as e:
        print(f"  WARNING: Failed to backup harness.py: {e}")
        return False


def restore_harness() -> bool:
    """Restore harness.py from backup and reload the module. Returns True on success."""
    try:
        if not _HARNESS_BACKUP_PATH.exists():
            print("  WARNING: No backup file found to restore")
            return False
        shutil.copy2(_HARNESS_BACKUP_PATH, _HARNESS_PATH)
        _reload_harness()
        return True
    except OSError as e:
        print(f"  WARNING: Failed to restore harness.py: {e}")
        return False


def _reload_harness() -> bool:
    """Reload the harness module after source modification. Returns True on success."""
    try:
        import tests.eval.harness as harness_module

        importlib.reload(harness_module)
        return True
    except Exception as e:
        print(f"  WARNING: Failed to reload harness module: {e}")
        return False


def cleanup_harness_backup() -> None:
    """Remove the harness backup file if it exists."""
    try:
        if _HARNESS_BACKUP_PATH.exists():
            _HARNESS_BACKUP_PATH.unlink()
    except OSError:
        pass


def apply_code_patch(code: str, target: str = "evaluate") -> bool:
    """Apply a raw Python code patch to harness.py.

    Backs up harness.py, applies the patch, attempts to reload the module.
    If the reload fails (syntax error, import error, etc.), automatically
    restores from backup.

    The code patch is expected to be a Python code string that replaces
    or extends a section of the evaluate() function. The exact replacement
    strategy depends on the "target" field:
      - "evaluate": Replace the entire evaluate() function body
      - Other targets are treated as insertions before the ranking step

    Args:
        code: Python code string to apply.
        target: Which section of harness.py to modify.

    Returns:
        True if patch was applied and module reloaded successfully.
    """
    if not backup_harness():
        return False

    try:
        source = _HARNESS_PATH.read_text()

        if target == "evaluate":
            # The code patch should be a complete evaluate() function or a
            # targeted replacement. For safety, we look for a marker comment
            # to insert code before the ranking step.
            marker = "# Sort by composite score descending"
            if marker in source and "def " not in code:
                # Insert hook code before the ranking step
                modified = source.replace(
                    marker,
                    f"{code}\n\n    {marker}",
                )
            else:
                # Full function replacement -- more dangerous
                # Find and replace the evaluate function
                start_marker = "def evaluate(params: ScoringParams"
                start_idx = source.find(start_marker)
                if start_idx == -1:
                    print("  WARNING: Could not find evaluate() function in harness.py")
                    restore_harness()
                    return False

                # Find the next top-level definition after evaluate
                rest = source[start_idx:]
                lines = rest.split("\n")
                end_idx = len(lines)
                for i, line in enumerate(lines[1:], 1):
                    if (
                        line
                        and not line[0].isspace()
                        and (
                            line.startswith("def ")
                            or line.startswith("class ")
                            or line.startswith("#")
                        )
                    ):
                        end_idx = i
                        break

                before = source[:start_idx]
                after_lines = lines[end_idx:]
                modified = before + code + "\n" + "\n".join(after_lines)
        else:
            # Generic insertion at the end of evaluate before return
            return_marker = "    return EvalResult("
            if return_marker in source:
                modified = source.replace(
                    return_marker,
                    f"    {code}\n\n{return_marker}",
                )
            else:
                print(f"  WARNING: Could not find insertion point for target '{target}'")
                restore_harness()
                return False

        _HARNESS_PATH.write_text(modified)

        # Try to reload
        if not _reload_harness():
            print("  WARNING: Reload failed after code patch, reverting...")
            restore_harness()
            return False

        # Verify the patched evaluate() is callable
        import tests.eval.harness as harness_module

        if not callable(getattr(harness_module, "evaluate", None)):
            print("  WARNING: evaluate() not callable after patch, reverting...")
            restore_harness()
            return False

        return True

    except Exception as e:
        print(f"  WARNING: Code patch failed: {e}")
        traceback.print_exc()
        restore_harness()
        return False


# ============================================================================
# The V2 Loop
# ============================================================================


def run_autoresearch_v2(
    provider: str = "anthropic",
    model: str | None = None,
    cycles: int = 20,
    target: float = 0.65,
    structural: bool = True,
    allow_code: bool = False,
    log_dir: str | None = None,
) -> EvalResult:
    """Run the full V2 autoresearch loop.

    Extends V1 with three proposal types: params, structural hooks, and code patches.
    The loop alternates between parameter tuning and structural changes based on
    LLM reasoning about score plateaus and intent-level weaknesses.

    Args:
        provider: "anthropic" or "openai".
        model: Override model name (default: auto-select based on provider).
        cycles: Number of LLM reasoning cycles.
        target: Target score to stop at.
        structural: Enable structural proposals (hooks). Default True.
        allow_code: Enable raw code patches. Default False.
        log_dir: Directory for log files.

    Returns:
        The best EvalResult achieved during the run.
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
    log_file = Path(log_dir) / "autoresearch_v2.jsonl"
    reasoning_file = Path(log_dir) / "autoresearch_v2_reasoning.md"

    # Build system prompt
    full_system = build_v2_system_prompt(
        structural_enabled=structural,
        allow_code=allow_code,
    )

    mode_label = "structural + params"
    if not structural:
        mode_label = "params only (V1 compatible)"
    elif allow_code:
        mode_label = "structural + params + code patches"

    print("=" * 70)
    print("  AUTORESEARCH V2 -- Structural-Aware Scoring Optimization")
    print(f"  Provider: {provider} ({model})")
    print(f"  Mode: {mode_label}")
    print(f"  Cycles: {cycles}  Target: {target}")
    print("=" * 70)

    # -- Step 1: Baseline --
    print("\nComputing baseline...")
    best_params = ScoringParams()  # all defaults
    active_hooks: dict[str, dict[str, Any]] = {}

    # Baseline always uses standard evaluate (no hooks)
    best_result = evaluate(best_params)
    best_score = best_result.score

    print(
        f"Baseline: score={best_score:.4f}  nDCG={best_result.mean_ndcg:.4f}  "
        f"violations={best_result.mean_violation_rate:.4f}"
    )
    print()

    # Log baseline
    history: list[dict] = []
    baseline_record = {
        "cycle": 0,
        "score": best_score,
        "accepted": True,
        "improvement": 0.0,
        "changed_params": [],
        "proposal_type": "baseline",
        "params": params_to_dict(best_params),
        "intent_ndcg": best_result.intent_ndcg,
        "active_hooks": list(active_hooks.keys()),
    }
    history.append(baseline_record)
    with open(log_file, "a") as f:
        f.write(json.dumps(baseline_record) + "\n")

    with open(reasoning_file, "a") as f:
        f.write(f"# Autoresearch V2 Log -- {datetime.now(UTC).isoformat()}\n\n")
        f.write(f"## Baseline: {best_score:.4f}\n\n")
        f.write(f"Mode: {mode_label}\n\n")

    # Track the last cycle number for summary
    last_cycle = 0

    # -- Step 2: The Loop --
    try:
        for cycle in range(1, cycles + 1):
            last_cycle = cycle
            print(f"\n{'-' * 70}")
            print(f"  Cycle {cycle}/{cycles}")
            print(f"{'-' * 70}")

            # Build prompt with full V2 context
            user_prompt = build_v2_user_prompt(
                cycle=cycle,
                total_cycles=cycles,
                current_params=params_to_dict(best_params),
                current_score=best_score,
                intent_breakdown=best_result.intent_ndcg,
                intent_violations=best_result.intent_violations,
                history=history,
                target=target,
                active_hooks=active_hooks,
                structural_enabled=structural,
                allow_code=allow_code,
            )

            # -- Call LLM --
            print(f"  Asking {model} to reason...")
            t0 = time.time()
            try:
                response_text = call_llm(full_system, user_prompt, model=model)
            except Exception as e:
                print(f"  ERROR calling LLM: {e}")
                continue
            llm_time = time.time() - t0
            print(f"  LLM responded in {llm_time:.1f}s")

            # -- Parse V2 response --
            proposal = parse_v2_response(response_text)
            if not proposal:
                print("  WARNING: Could not parse proposal from LLM response. Skipping.")
                with open(reasoning_file, "a") as f:
                    f.write(f"## Cycle {cycle} -- PARSE FAILURE\n\n")
                    f.write(f"```\n{response_text[:1500]}\n```\n\n")
                continue

            proposal_type = proposal["type"]
            print(f"  Proposal type: {proposal_type}")

            # -- Apply proposal and evaluate --
            candidate_result: EvalResult | None = None
            candidate_params = best_params
            hook_name = ""
            hook_config_dict: dict = {}
            code_applied = False
            changed_params: list[str] = []

            if proposal_type == "params":
                # Same as V1: apply param overrides and evaluate
                changes = proposal.get("changes", {})
                changed_params = list(changes.keys())
                print(f"  Proposed param changes: {changed_params}")

                candidate_params = apply_params(best_params, changes)
                t0 = time.time()
                if active_hooks:
                    candidate_result = evaluate_with_hooks(candidate_params, active_hooks)
                else:
                    candidate_result = evaluate(candidate_params)
                eval_time = time.time() - t0

            elif proposal_type == "structural":
                if not structural:
                    print("  WARNING: Structural proposals disabled. Skipping.")
                    continue

                hook_name = proposal.get("hook", "")
                enabled = proposal.get("enabled", True)
                config_overrides = proposal.get("config", {})
                hook_config_dict = config_overrides

                if not enabled:
                    # Disable a hook
                    if hook_name in active_hooks:
                        print(f"  Disabling hook: {hook_name}")
                        active_hooks.pop(hook_name)
                        changed_params = [f"-{hook_name}"]
                    else:
                        print(f"  Hook '{hook_name}' is not active. Skipping.")
                        continue
                else:
                    # Enable or reconfigure a hook
                    try:
                        hook_info = apply_structural_hook(hook_name, config_overrides)
                    except ValueError as e:
                        print(f"  WARNING: {e}")
                        continue

                    print(f"  Enabling hook: {hook_name} with config: {config_overrides}")
                    active_hooks[hook_name] = hook_info
                    changed_params = [f"+{hook_name}"]

                t0 = time.time()
                candidate_result = evaluate_with_hooks(candidate_params, active_hooks)
                eval_time = time.time() - t0

            elif proposal_type == "code":
                if not allow_code:
                    print("  WARNING: Code patches disabled (use --allow-code). Skipping.")
                    continue

                code_text = proposal.get("code", "")
                code_target = proposal.get("target", "evaluate")
                description = proposal.get("description", "")
                print(f"  Code patch: {description or '(no description)'}")
                changed_params = ["code_patch"]

                success = apply_code_patch(code_text, code_target)
                if not success:
                    print("  Code patch failed to apply. Skipping.")
                    with open(reasoning_file, "a") as f:
                        f.write(f"## Cycle {cycle} -- CODE PATCH FAILED\n\n")
                        f.write(f"```python\n{code_text[:1000]}\n```\n\n")
                    continue

                code_applied = True
                # Re-import evaluate after patching
                import tests.eval.harness as harness_module

                patched_evaluate = harness_module.evaluate

                t0 = time.time()
                try:
                    candidate_result = patched_evaluate(candidate_params)
                except Exception as e:
                    print(f"  Code patch caused eval error: {e}")
                    restore_harness()
                    code_applied = False
                    with open(reasoning_file, "a") as f:
                        f.write(f"## Cycle {cycle} -- CODE PATCH EVAL ERROR\n\n")
                        f.write(f"Error: {e}\n\n")
                    continue
                eval_time = time.time() - t0

            else:
                print(f"  WARNING: Unknown proposal type '{proposal_type}'. Skipping.")
                continue

            if candidate_result is None:
                continue

            candidate_score = candidate_result.score
            improvement = candidate_score - best_score
            accepted = candidate_score > best_score

            # Safety check: revert if violations spike
            if candidate_result.mean_violation_rate > 0.1:
                print(
                    f"  SAFETY: Violation rate {candidate_result.mean_violation_rate:.4f} > 0.1. "
                    f"Reverting."
                )
                accepted = False
                if code_applied:
                    restore_harness()
                    code_applied = False
                # Revert structural hook if it was just added
                if proposal_type == "structural" and proposal.get("enabled", True) and hook_name:
                    active_hooks.pop(hook_name, None)

            # -- Accept or reject --
            if accepted:
                best_score = candidate_score
                best_params = candidate_params
                best_result = candidate_result
                marker = f"ACCEPTED (+{improvement:.4f})"
            else:
                marker = f"rejected ({improvement:+.4f})"
                # Revert structural changes on rejection
                if proposal_type == "structural" and proposal.get("enabled", True) and hook_name:
                    active_hooks.pop(hook_name, None)
                elif (
                    proposal_type == "structural"
                    and not proposal.get("enabled", True)
                    and hook_name
                ):
                    # Re-enable the hook we just disabled (revert the disable)
                    # We need the previous config, but we don't have it stored.
                    # For simplicity, re-add with defaults.
                    try:
                        hook_info = apply_structural_hook(hook_name, {})
                        active_hooks[hook_name] = hook_info
                    except ValueError:
                        pass
                if code_applied:
                    restore_harness()
                    code_applied = False

            print(f"  Score: {candidate_score:.4f}  {marker}")
            print(f"  Eval time: {eval_time * 1000:.0f}ms")
            if active_hooks:
                print(f"  Active hooks: {list(active_hooks.keys())}")

            # -- Log everything --
            record: dict[str, Any] = {
                "cycle": cycle,
                "timestamp": datetime.now(UTC).isoformat(),
                "score": candidate_score,
                "accepted": accepted,
                "improvement": improvement if accepted else 0.0,
                "proposal_type": proposal_type,
                "changed_params": changed_params,
                "params": params_to_dict(candidate_params),
                "intent_ndcg": candidate_result.intent_ndcg,
                "intent_violations": candidate_result.intent_violations,
                "llm_time_s": round(llm_time, 2),
                "eval_time_ms": round(eval_time * 1000),
                "best_score_so_far": best_score,
                "active_hooks": list(active_hooks.keys()),
            }

            if proposal_type == "structural":
                record["hook_name"] = hook_name
                record["hook_config"] = hook_config_dict
                record["hook_enabled"] = proposal.get("enabled", True)

            if proposal_type == "code":
                record["code_description"] = proposal.get("description", "")
                record["code_applied"] = accepted

            if proposal_type == "params":
                record["proposed_overrides"] = proposal.get("changes", {})

            history.append(record)
            with open(log_file, "a") as f:
                f.write(json.dumps(record) + "\n")

            # Log the LLM's full reasoning
            with open(reasoning_file, "a") as f:
                status = "ACCEPTED" if accepted else "REJECTED"
                f.write(
                    f"## Cycle {cycle} -- {status} [{proposal_type}] "
                    f"(score={candidate_score:.4f})\n\n"
                )
                f.write(f"**Changed:** {changed_params}\n")
                if hook_name:
                    f.write(f"**Hook:** {hook_name}\n")
                f.write(f"\n### LLM Reasoning:\n\n{response_text}\n\n")
                f.write("---\n\n")

            # -- Check stopping conditions --
            if best_score >= target:
                print(f"\n  TARGET REACHED! {best_score:.4f} >= {target:.4f}")
                break

    finally:
        # Always clean up harness backup if it exists
        cleanup_harness_backup()

    # -- Final Summary --
    print(f"\n{'=' * 70}")
    print("  AUTORESEARCH V2 COMPLETE")
    print(f"{'=' * 70}")
    baseline_score = 0.4600
    print(
        f"  Final score:  {best_score:.4f}  "
        f"(baseline: {baseline_score:.4f}, +{(best_score / baseline_score - 1) * 100:.1f}%)"
    )
    print(f"  Cycles run:   {min(last_cycle, cycles)}")
    print(f"  Target:       {target:.4f}  ({'REACHED' if best_score >= target else 'not reached'})")
    print(f"\n  Active hooks: {list(active_hooks.keys()) or '(none)'}")
    print("\n  Per-intent nDCG:")
    for intent, ndcg in sorted(best_result.intent_ndcg.items(), key=lambda x: x[1]):
        print(f"    {intent:15s} {ndcg:.4f}")
    print("\n  Best parameters:")
    for k_name, v_val in sorted(params_to_dict(best_params).items()):
        print(f"    {k_name}: {v_val}")
    print("\n  Logs:")
    print(f"    {log_file}")
    print(f"    {reasoning_file}")
    print(f"{'=' * 70}")

    return best_result


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    """CLI entry point for autoresearch V2."""
    parser = argparse.ArgumentParser(
        description="Autoresearch V2: Structural-aware LLM-in-the-loop scoring optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with Claude (default, structural hooks enabled)
  ANTHROPIC_API_KEY=sk-... python tests/eval/autoresearch_v2.py

  # Run with GPT
  OPENAI_API_KEY=sk-... python tests/eval/autoresearch_v2.py --provider=openai

  # Param-only mode (V1 compatible)
  python tests/eval/autoresearch_v2.py --no-structural

  # Enable raw code patches (advanced)
  python tests/eval/autoresearch_v2.py --allow-code

  # Quick test (5 cycles)
  python tests/eval/autoresearch_v2.py --cycles=5

  # Aggressive target
  python tests/eval/autoresearch_v2.py --cycles=30 --target=0.70
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
        default=20,
        help="Number of LLM reasoning cycles (default: 20)",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.65,
        help="Target score to stop at (default: 0.65)",
    )
    parser.add_argument(
        "--structural",
        action="store_true",
        default=True,
        help="Enable structural proposals (hooks). Default: enabled.",
    )
    parser.add_argument(
        "--no-structural",
        dest="structural",
        action="store_false",
        help="Disable structural proposals (param-only, V1 compatible).",
    )
    parser.add_argument(
        "--hooks-only",
        action="store_true",
        default=False,
        help="Only allow pre-built hooks, not raw code patches (same as default).",
    )
    parser.add_argument(
        "--allow-code",
        action="store_true",
        default=False,
        help="Allow raw code patches to harness.py (advanced, use with caution).",
    )

    args = parser.parse_args()

    # hooks-only is the default behavior (structural=True, allow_code=False)
    # --allow-code enables code patches on top of structural
    allow_code = args.allow_code and not args.hooks_only

    # Validate API key exists
    if args.provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY environment variable")
        print("  export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    run_autoresearch_v2(
        provider=args.provider,
        model=args.model,
        cycles=args.cycles,
        target=args.target,
        structural=args.structural,
        allow_code=allow_code,
    )


if __name__ == "__main__":
    main()
