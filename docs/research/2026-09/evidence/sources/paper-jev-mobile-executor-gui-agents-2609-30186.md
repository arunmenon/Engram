---
schema_version: 1
artifact_id: N-20260930-07
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2103800578476245261", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.30186
claim_cluster: arxiv:2609.30186
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.30186
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R9
pillar_secondary: ["R4"]
tags: {"mechanism": ["planner sets local goal, Jev picks action id", "DONE and BLOCKED handback options", "candidates regenerated after every action"], "workload": ["mobile GUI agents", "AndroidWorld"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
memory_stage: routing
priority: 1
evidence_grade: {"directness": "high: full AndroidWorld run with an independent terminal-state evaluator", "control": "medium: two baselines on the same suite, but no ablation against a small VLM executor and cost/time reported on successful trajectories only", "independence": "medium: single author, no stated tie to TypeSafe", "reproducibility": "low: no code link in the manuscript; runs and seeds not stated", "applicability": "low: GUI control, not memory; the planner-plus-picker split transfers to retrieval planning (inference)"}
beliefs_affected: {"supports": ["B12"], "contradicts": [], "would_create": []}
claim_correction: The post's cost and time savings (-73.4% API cost, -32.7% wall time) are measured on successful trajectories only and against the step-wise VLM, which has the higher success rate (84% vs 79%); versus SeeAct-V success is 79% vs 78%.
---

# Jev-Mobile: Jev as an Executor for Mobile GUI Agents (arXiv 2609.30186)

- **URL:** https://arxiv.org/abs/2609.30186 (HTML read: https://arxiv.org/html/2609.30186v1)
- **Type:** paper
- **Author / org:** Linghua Zhang (affiliation not captured). Licence CC0 1.0. Categories cs.AI, cs.SE.
- **Date:** submitted 2026-09-24
- **Retrieved:** 2026-09-30. No code repository linked in the manuscript.
- **Cited by evidence:** memory feed 2026-09-26, @runbywren (https://x.com/runbywren/status/2103800578476245261); memory digest 2026-09-30 ("Where the decider has measured value, it is a sensor or a picker, not the planner").
- **Relevance to a memory stack:** medium. A second controlled result, after the StarCraft II report behind B12, that a typed decision model works in an open loop when a larger model sets the goal and the decision model only picks from freshly generated candidates.

## TL;DR
- A VLM (Qwen3.8-Max) reads instruction, screenshot and accessibility tree and sets a local goal plus exact input text; Jev then picks one candidate action id per step or returns DONE or BLOCKED; control returns to the VLM on DONE or BLOCKED.
- Candidates are generated deterministically from the accessibility tree (click, long-press, scroll, focus on visible, enabled nodes with valid bounds) and regenerated after every action, "invalidating stale IDs".
- AndroidWorld full suite, independent evaluator: success 79% (Jev-Mobile) vs 78% SeeAct-V (UI-TARS-1.5-7B grounder) vs 84% step-wise VLM.
- On successful trajectories: mean total time 132.67 s vs 197.21 s step-wise (-32.7%); mean model API cost $0.073 vs $0.274 (-73.4%); executor time 5.16 s vs 94.30 s.

## What it claims / describes
Separation of planning from execution: the VLM is called sparingly to set goals and decide delegate / finish / blocked; Jev, "a typed decision service" used without training, executes multiple actions under one local goal. Failure modes: coverage failures "when a visual target has no executable tree candidate"; no coordinate-producing visual fallback; ASCII-only text input; possible need for long-history compaction.

## Numbers
Table 1, AndroidWorld full suite.

| metric | step-wise VLM | SeeAct-V | Jev-Mobile |
|---|---|---|---|
| success rate | 84% | 78% | 79% |
| mean total time (successful) | 197.21 s | 162.63 s | 132.67 s |
| mean executor time | 94.30 s | 12.37 s | 5.16 s |
| mean model API cost | $0.274 | $0.193 | $0.073 |

Runs, seeds and intervals: not stated. Jev version and thresholds: not stated.

## Mechanism details you could implement
- Planner-picker loop: the large model writes a local goal; the decision model chooses among ids the harness just generated, plus DONE and BLOCKED; the harness executes and regenerates candidates.
- Give the picker explicit handback options (DONE, BLOCKED) instead of forcing a choice, so coverage gaps return to the planner.
- Regenerate the option list after each state change so stale ids cannot be chosen (the same rule as the mika_systems blueprint in the synthesis, section 5).

## Limitations, caveats, counter-evidence
- No ablation against a small VLM executor; Android only; web untested.
- Time and cost averaged over successful trajectories only, so failures (which may be cheap or expensive) are excluded.
- Success is 5 points below the step-wise VLM.
- Single benchmark, single run as far as stated; no code.

## Takeaways for tuning a memory stack
- For graph traversal at retrieval time (inference): let the LLM set retrieval intent once, let the decision model pick the next node or edge from the harness-generated frontier, with DONE (sufficient) and BLOCKED (need the planner) as options.
- Budget the cost comparison on all trajectories, not successes only, when we run our own version.

## Open questions
- Success and cost on failed trajectories; number of VLM handbacks per task.
- Which Jev question type was used (choice over ids presumably; not stated in the extraction).

## Grading and labels
- Directness high; control medium; independence medium; reproducibility low; applicability low.
- Pillars: R9 primary (System One model as executor under a planner), R4 (when to hand back). Memory stage: routing. Priority 1.
- Beliefs: supports B12 (a typed decision model works under a planner; here 79% vs 84% at a quarter of the API cost, with a documented method and an independent evaluator, stronger than the StarCraft II report).
- Contradiction rows: none.

## Origin chain
@runbywren post (2103800578476245261) -> arXiv 2609.30186 abstract and HTML v1 -> system design sections and Table 1, limitations -> this note. Independence: single author; AndroidWorld evaluator independent of the system; no shared authors with TypeSafe known.
