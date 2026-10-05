---
schema_version: 1
artifact_id: N-SURVEY-20261003-03
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2608.06811
input_refs: []
pillar_primary: R3
pillar_secondary: [R6]
memory_stage: assembly
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: medium, control: high, independence: high, reproducibility: medium, applicability: high}
source_url: https://arxiv.org/abs/2608.06811
found_via: survey
---

# Coupling Planning with Episodic Memory in LLM Agents for Software Issue Resolution (PMCoder)

- **URL:** https://arxiv.org/abs/2608.06811 (HTML v1 read; local copy out/log/raw/2608.06811.html); code https://doi.org/10.5281/zenodo.21035632 (anonymised package, not run)
- **Type:** paper
- **Author / org:** Jiahao Zhang, Yifan Zhang, Yu Huang (Vanderbilt University)
- **Date:** 2026-08-07
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, R3 thesis gap (assembly on engineering tasks)
- **Relevance to a memory stack:** high for assembly design. A budgeted, model-free, within-episode memory injection on SWE-bench Verified with a 2x2 ablation and three runs per arm.

## TL;DR
- Memory is within one repair episode only (no cross-task recall); every message is mirrored into a node; injection is a budgeted MMR selection, no embeddings, no model call.
- SWE-bench Verified n=500, Qwen3-Coder-30B-A3B-FP8: baseline mean 142.3 (28.5%), plan plus memory 167.3 (33.5%); bootstrap 95% CI of the gain [+14.3, +35.7].
- Memory alone is small: 150.67 (30.1%) vs 142.33; plan alone 148.67; interaction +10.3, F(1,8)=10.92, p=0.011.
- Gains hold on stronger models (single run): DeepSeek-V4-Flash +16, Claude Haiku 4.5 +14, OpenHands port +23.

## What it claims / describes
Node fields: role, recency id, compressed content, summary, edited-files flag, files touched. "The graph stores raw observations only"; injected text never re-enters the graph. Selection: fixed core (task statement, recent tail, anchor node seeded from the active sub-task keywords) plus budgeted MMR by beam search. Relevance = 0.5 IDF-weighted lexical + 0.5 code-structure proximity (same file, AST import edges, trajectory adjacency); MMR lambda 0.7. Injection: a marker-delimited block appended to the latest tool result, only when the plan state changes; history never rewritten; a novelty filter replaces already-shown nodes with a one-line stub.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Resolved /500 | 170/164/168 (mean 167.3, 33.5%) | 139/144/144 (mean 142.3, 28.5%) | SWE-bench Verified, Qwen3-Coder-30B-A3B-FP8, T=0, 250 turns | FP8 serving not bit-reproducible, hence 3 runs |
| Memory only | 150.67 (30.1%) | 142.33 | Table VIII | |
| Plan only | 148.67 (29.7%) | 142.33 | Table VIII | |
| DeepSeek-V4-Flash | 341 to 357 | | 1 run | no CI |
| Claude Haiku 4.5 | 313 to 327 | | 1 run | no CI |
| TerminalWorld | 5/20 to 7/20 | | 1 run | tiny n |
| Budgets | memory 16k tokens; per-node 4k chars; phase budgets 20k/16k/12k/16k/20k; context 65,536 | | | no budget sweep |

Cost cap $3.0 per instance; per-arm tokens not stated. No LLM judge (executable tests).

## Mechanism details you could implement
- Raw-only store; read-time selection with a fixed core plus MMR (lambda 0.7) under a token budget; inject on plan-state change, not every turn; novelty stubs for already-served items.
- Phase-dependent budgets (smallest during implementation).

## Limitations, caveats, counter-evidence
- No cross-task memory, so says nothing about recalling earlier projects.
- No ablation of raw vs distilled, budget size, or retrieval method; injection placement from a pilot only.
- Pilot set used to fix thresholds not stated.

## Takeaways for tuning a memory stack
- On build-time work, retrieved memory without a plan that tells it what to fetch was worth about +8 resolves of 500; with a plan, +25. Context assembly keyed to the current sub-task is where the value is (inference).
- Supports "verbatim first, select at read time" without a model call in the read path; a cheap lexical plus code-structure scorer is a fair baseline arm for H1/H2 on SE tasks.

## Open questions
- Does the same selection help across sessions (DreamBench-SWE style)?
