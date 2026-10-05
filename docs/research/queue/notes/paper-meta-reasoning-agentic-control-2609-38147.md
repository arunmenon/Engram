---
schema_version: 1
artifact_id: N-20261001-09
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105214161429106963", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.38147
claim_cluster: arxiv:2609.38147
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.38147
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R3
pillar_secondary: ["R5"]
tags: {"mechanism": ["controller with compact state", "artifact memory", "assess-propose-evaluate-dispatch", "budget-aware control"], "workload": ["coding agent", "math proofs", "ARC"], "lifecycle_stage": ["assembly"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: benchmark table, budget sweep, state-size measurements", "control": "medium: same workers under direct control as the main baseline, budget sweep, but no component ablation (paper says combined design prevents attribution)", "independence": "medium: large multi-institution author list; production baselines (Codex, Claude Code) run by the authors", "reproducibility": "low: seeds and repeats not stated in the extraction", "applicability": "medium: long-running coding work where context accumulation is the cost driver"}
beliefs_affected: {"supports": ["B7"], "contradicts": [], "would_create": ["A controller that keeps a compact textual state (thousands to tens of thousands of characters) and stores worker outputs as artifacts keeps improving with budget where accumulated-history control plateaus, but loses at small budgets"]}
claim_correction: none (the post's ProgramBench numbers, 71.5 vs Codex 58.0 and direct control 63.7 at 1,200 calls, match; the paper also reports a loss at 400 calls, 56.6 vs 62.7, which the post mentions only as "overhead can lose at small budgets")
memory_stage: assembly
---

# Thinking Before Thinking: Scaling Agentic Inference Through Meta-Reasoning (arXiv 2609.38147)

- **URL:** https://arxiv.org/abs/2609.38147 (HTML: https://arxiv.org/html/2609.38147)
- **Type:** paper
- **Author / org:** Paras Dahal, Anton Bakhtin, Taco Cohen, Zhengxing Chen, Carole-Jean Wu, Rob Fergus, Scott Yih, Gabriel Synnaeve, Ruslan Salakhutdinov, Sanjeev Arora, Jason Weston, Anirudh Goyal (affiliations not listed on the abstract page)
- **Date:** submitted 2026-09-29
- **Retrieved:** 2026-10-01 (abstract and HTML: architecture, Table 1, budget scaling, artifact graph, state compression, limitations)
- **Cited by evidence:** @runbywren, 2026-09-30, https://x.com/runbywren/status/2105214161429106963
- **Relevance to a memory stack:** medium. It is a context-assembly result: replace an ever-growing history with a compact controller state plus an artifact store the controller dispatches from.

## TL;DR
- Controller loop per step: Assess (update compact state from new artifacts), Propose (candidate next computations), Evaluate (weigh against remaining budget), Dispatch (run the chosen work "with selected context"). Workers write artifacts to persistent memory; the controller keeps "only a compact textual account rather than full history".
- Table 1, meta-reasoning vs direct control (same workers): IMO ProofBench-Adv (Gemini 3.1 Pro) 91.3 vs 82.7; ARC-AGI-2 (GPT-5.5) 79.2 vs 75.8; LongCoT-mini (Opus 4.8) 66.5 vs 65.3; ProgramBench (GPT-5.5) 71.5 vs 63.7. Abstract: mean gains 3.6 and 4.2 points over direct control across three frontier models.
- ProgramBench vs production harnesses: 71.5 vs Codex 58.0 (GPT-5.5); 67.2 vs Claude Code 65.5 (Opus 4.8).
- State size: direct control's history exceeds 1 million characters on longer runs; meta-reasoning state stays "on order of thousands to tens of thousands of characters".
- Budget: at 1,200 calls 71.5 vs about 64 (direct control plateaus); at 400 calls it loses, 56.6 vs 62.7.

## What it claims / describes
Agentic meta-reasoning separates control from object-level work. The controller consolidates progress into a compact state, generates options, evaluates them against the remaining call budget, and dispatches workers with selected context. Worker outputs and dependencies form an artifact graph (ProgramBench at 1,200 calls: 2.5x more nodes and 4x more edges than direct control; IMO ProofBench: about 2x artifacts, an order of magnitude more dependencies). Baselines: Recursive Language Model, Mini-SWE Agent, Codex, Claude Code, and a Direct Control Agent with the same workers.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| IMO ProofBench-Adv | 91.3% | direct control 82.7% | Gemini 3.1 Pro, Table 1 | |
| ARC-AGI-2 | 79.2% | 75.8% | GPT-5.5 | |
| LongCoT-mini | 66.5% | 65.3% | Opus 4.8 | "unproductive reconsideration" on a chess subset |
| ProgramBench | 71.5% | direct control 63.7%; Codex 58.0% | GPT-5.5, 1,200-call budget | |
| ProgramBench | 67.2% | Claude Code 65.5% | Opus 4.8 | |
| ProgramBench at 400 calls | 56.6% | direct control 62.7% | GPT-5.5 | overhead loses at small budget |
| controller state size | thousands to tens of thousands of chars | direct control history > 1M chars | longer runs | |
| artifact graph, ProgramBench 1,200 calls | 2.5x nodes, 4x edges | direct control | | |

## Mechanism details you could implement
- Keep a bounded controller state (a running account: what is done, open hypotheses, budget left) separate from an artifact store; dispatch each worker with selected artifacts rather than the full history.
- Make the budget an explicit input to each control decision (Evaluate step).
- Record dependencies between artifacts so the controller can select context by provenance (inference: this is a natural fit for a context graph with produced-by and depends-on edges).

## Limitations, caveats, counter-evidence
- Paper: overhead hurts at small budgets; unproductive reconsideration on a chess subset; gains are model-dependent; "Combined design prevents component-level attribution", so the compact state's own contribution is not isolated.
- Seeds and repeated runs not stated in what was read; task counts per benchmark not extracted.
- Production baselines (Codex, Claude Code) run under the authors' settings.

## Takeaways for tuning a memory stack
- For long engineering runs, assemble context per dispatch from an artifact store plus a compact state, instead of letting history accumulate; expect a cost at small budgets.
- Store worker outputs as addressable artifacts with dependencies, so selection and replay can cite them (fits R1 receipts).

## Open questions
- What is the gain with the compact state but without the propose/evaluate stages, and vice versa?
- How is "selected context" chosen: by the controller's text, by artifact links, or by retrieval?

## Grading and labels
- **Directness: high.** **Control: medium.** **Independence: medium.** **Reproducibility: low.** **Applicability: medium.**
- **Pillars:** R3 primary (context assembly under a budget); R5 secondary. **Memory stage:** assembly.
- **Beliefs:** supports B7 in direction (task-conditioned, read-time selection of context per step beats carrying everything), with the caveat that the compact state is not ablated. **Contradictions:** none.

## Origin chain
Post @runbywren 2105214161429106963 (2026-09-30) -> arXiv 2609.38147 -> Table 1, budget scaling section, artifact graph analysis, state compression paragraph, limitations -> this note. Independence: authors span several labs; no overlap with JITMem (B7's source) as far as shown.
