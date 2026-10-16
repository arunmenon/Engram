---
schema_version: 1
artifact_id: N-20260927-03
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103826930181308720", "file_id": null, "sha256": null}, {"artifact_id": "post:2103842557230723403", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26891
claim_cluster: arxiv:2609.26891
feeds: ["memory", "decision"]
primary_source: https://arxiv.org/abs/2609.26891
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R3
pillar_secondary: ["R5", "R1"]
tags: {"mechanism": ["history as a programmable variable", "recursive invoke", "tail-recursive delegation with prev_history", "exact substring search over history", "hooks for budget and replay"], "workload": ["StuLife far-recall", "AppWorld continual self-improvement"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: pass rate and cost tables against Letta and ACE", "control": "medium: same executor model across methods, byte-identical prompts where possible, but ACE learned on only the first 10% of tasks for cost reasons", "independence": "medium: MIT CSAIL; Letta and ACE run by the authors", "reproducibility": "medium: code repos named (jaz-lang/jaz, jaz-evals), n=3 or n=6 runs with standard errors; commits not recorded", "applicability": "medium: long-horizon recall over one agent's own history; not multi-store or multi-agent"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["On a long-horizon far-recall task, keeping full history losslessly and letting the agent search it with code beat a purpose-built memory system (Letta) at less than half the cost"]}
claim_correction: "8% at half the cost" is 69.9 vs 61.8 pass rate (8.1 points, about 13% relative) on the 207-task far-recall subset only; on all 939 graded tasks the gap is 72.6 vs 70.9 (1.7 points); cost $18.3 vs $42.1 is for the whole run
---

# Harness as a Language: A Minimalist Agent Framework With Maximal Expressivity (JAZ, arXiv 2609.26891)

- **URL:** https://arxiv.org/abs/2609.26891 (full text read at https://arxiv.org/html/2609.26891)
- **Type:** paper
- **Author / org:** Zhening Li, Joshua Liu, Mateja Vukelic, Nicole Shen, Supriya Lall, Amitayush Thakur, Alex Zhang, Omar Khattab, Jonathan Light, Armando Solar-Lezama; MIT CSAIL and independent researchers
- **Date:** arXiv v1, 22 Sep 2026
- **Retrieved:** 2026-09-27, arXiv HTML v1; code at https://github.com/jaz-lang/jaz and https://github.com/jaz-lang/jaz-evals (not cloned, commit not recorded)
- **Cited by evidence:** @omarsar0 https://x.com/omarsar0/status/2103826930181308720 ; reply @mktpavlenko https://x.com/mktpavlenko/status/2103842557230723403
- **Relevance to a memory stack:** medium to high. A no-memory-system baseline (full history kept by reference, searched by agent-written code) beat Letta on the far-recall subset. It is the strongest argument yet that a lossless log plus programmable access is a serious baseline any memory layer must beat.

## TL;DR
- JAZ has one primitive, `invoke`: the LLM writes code as the body of the function, can call `invoke` recursively, and sees all inputs and its own REPL history as variables (`__history__`).
- StuLife (1,284 ordered tasks, 939 graded, 207 "far recall" needing information 50+ tasks back), GPT-5.4 nano: JAZ invoke far-recall pass 69.9 +/- 1.8 vs Letta 61.8 +/- 2.3; all-task pass 72.6 vs 70.9; cost $18.3 vs $42.1 (n=3).
- AppWorld continual self-improvement (417 test-challenge tasks): JAZ invoke TGC 74.2 +/- 2.1 vs ACE 69.9 +/- 1.4 at $20.9 vs $30.6 (n=6 for self-improving methods).
- "No memory system" means: no tools, no vector store, no file system; memory is `__history__` passed by reference through tail-recursive delegation (`prev_history`).
- Case study: a question needing lecture content from 497 tasks earlier; Letta's `conversation_search` "did not support" the exact substring match needed.

## What it claims / describes
- `invoke` is "a function whose implementation is provided at runtime by an LLM every time it is called". Everything the model sees is a variable it can reference; history is accessed by reference rather than copied.
- When the context fills, the agent delegates to a sub-invoke passing `prev_history` (accumulated full histories), `prev_progress_summary` and `next_steps`. This "losslessly preserves full conversation history by reference". The harness appends the tail-recursive call automatically because of Python memory inefficiency.
- Hooks: observability (PrintLogger, FileLogger, TrajectoryRecorder, LangfuseTracing, JaegerTracing), resumability (TrajectoryRecorder, TrajectoryReplay), resource control (BudgetPool, IterationLimit, RecursionLimit, BudgetForcing, ContextWindowWarning), validation (ReturnType, ValidateReturn, ValidateREPLCode). `scope` is a context manager that passes variables to all recursive sub-invokes.
- Evaluation protocol (Appendix C.1): instructions are method-agnostic, guidance is task-agnostic; self-improvement prompts carry "no workflow guidance". Distinct prompt-cache keys per run; at most 3 parallel runs per org; cache-related cost uncertainty estimated < 2%.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| StuLife far-recall pass % | JAZ invoke 69.9 +/- 1.8 | Letta (MemGPT) 61.8 +/- 2.3; CodeAct per-task 24.8 | Table 1, 207 far-recall tasks, GPT-5.4 nano, n=3, mean +/- SE | the post's "8%" is 8.1 points |
| StuLife far-recall score % | 73.6 +/- 1.5 | Letta 67.0 +/- 2.4 | Table 1 | |
| StuLife all-task pass % | 72.6 +/- 0.1 | Letta 70.9 +/- 0.5 | Table 1, 939 graded tasks | gap 1.7 points overall |
| StuLife cost | $18.3 +/- 0.3 | Letta $42.1 +/- 1.6 | Table 1 | whole run |
| AppWorld TGC % | 74.2 +/- 2.1 | ACE 69.9 +/- 1.4; CodeAct official 48.2 | Table 2, 417 tasks, solver GPT-5.4 nano, meta GPT-5.4, n=6 | ACE learned only on first 42 tasks (10%) for cost |
| AppWorld SGC % | 51.1 +/- 3.7 | ACE 47.1 +/- 1.3 | Table 2 | |
| AppWorld total cost | $20.9 +/- 3.7 | ACE $30.6 +/- 0.5 | Table 2 | full ACE estimated at "over $180" |

## Mechanism details you could implement
- Keep the full interaction log as an addressable object and give the agent programmatic search over it (exact substring, filters), not only a semantic `conversation_search` tool.
- On context overflow, delegate with `(prev_history, prev_progress_summary, next_steps)`; the summary is a convenience, the history is the record.
- Hooks for `TrajectoryRecorder` and `TrajectoryReplay` give replay of the whole agent run, relevant to R1 receipts (inference).
- Budget hooks (`BudgetPool`, `RecursionLimit`, recursion depth capped at 2 in the AppWorld runs) keep recursive agents bounded.

## Limitations, caveats, counter-evidence
- No explicit limitations section. Noted constraints: tail recursion appended by the harness; caching needs exact prefix relationships.
- One executor family (GPT-5.4 nano / GPT-5.4); n=3 for StuLife.
- Letta and ACE were run by the authors; ACE was deliberately restricted to learning on 10% of tasks.
- StuLife is a single simulated environment of one agent's own history; nothing on multiple stores, supersession, stale facts, or other agents' writes (inference).
- The overall StuLife gain over Letta is small (1.7 points); the advantage is concentrated in far recall.

## Takeaways for tuning a memory stack
- Treat "lossless log + programmable search" as a mandatory baseline for any memory feature; a memory layer that cannot beat it on far recall is not earning its cost.
- Exact-match access to history matters: semantic-only recall tools fail questions that need verbatim retrieval.
- Delegation summaries should travel with a reference to the full history, never replace it.

## Open questions
- How does JAZ-style history access scale when history is shared across agents or must respect permissions?
- Cost at much longer horizons (the reply post raises this)?
- Would Letta with an exact-match tool close the gap?

## Grading and labels
- Directness high; control medium (ACE restricted; same model family); independence medium; reproducibility medium; applicability medium.
- Pillars: R3 primary (request-time evidence selection from history); R5 secondary (AppWorld continual self-improvement); R1 secondary (trajectory record/replay hooks).
- Beliefs: none directly supported or contradicted. Would create: lossless history with programmable search beat a dedicated memory system on far recall at under half the cost (one benchmark).
- No contradiction rows.

## Origin chain
post 2103826930181308720 (@omarsar0) -> arXiv 2609.26891 v1 HTML -> Table 1 (StuLife), Table 2 (AppWorld), Appendix C.1 (protocol) -> this note. Independence: MIT CSAIL; no shared authors with other catalogue sources; Letta is a vendor in our landscape list.
