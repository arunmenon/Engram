---
schema_version: 1
artifact_id: N-SURVEY-20261003-01
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2608.01285
input_refs: []
pillar_primary: R3
pillar_secondary: [R4, R9]
memory_stage: assembly
priority: 1
beliefs_affected:
  supports: [B9]
  contradicts: []
evidence: {directness: high, control: medium, independence: high, reproducibility: low, applicability: medium}
source_url: https://arxiv.org/abs/2608.01285
found_via: survey
---

# Stop When Memory Suffices: Evidence-Conditioned Progressive Execution for LLM Agents (Router-Mem)

- **URL:** https://arxiv.org/abs/2608.01285 (HTML v1 read; local copy out/log/raw/2608.01285.html)
- **Type:** paper
- **Author / org:** Yidan Lin, Kaixiang Wang, Jiong Lou, Jie Li (affiliations not stated)
- **Date:** 2026-08-02
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, B9 / H8
- **Relevance to a memory stack:** high. First independent ablation of a learned sufficiency stop over a fast-path retrieval, with a threshold sweep against always-stop and never-stop endpoints.

## TL;DR
- A small causal LM reads (query, first-pass retrieved context) and emits yes/no "sufficient"; if P(yes) >= tau the agent answers from the fast path, else it runs a slow multi-block memory agent.
- On AMA-Bench (DeepSeek-V4-Flash) tau=0.5 scores 55.17 vs 56.49 for always-slow, stops early on 30.0% of queries, and cuts memory time 11.341 s to 8.248 s.
- On BEAM the stop rule never reaches the always-slow score (best 42.09 at tau=0.9 vs 43.26).
- Training the router matters: an untrained router on BEAM stops early 86.5% of the time and scores 29.62 vs 38.77 trained.
- No false-sufficiency rate, no token counts in the main text, no code.

## What it claims / describes
Shared retrieval returns C_f. Router outputs one token; score = P(yes) normalised over grouped yes/no tokens; stop if s >= tau. If C_f exceeds the router input budget, continue (conservative default). Continuation expands hits into overlapping memory blocks plus temporal neighbours, a memory agent analyses each block, an aggregator merges. Router training: positives keep all required evidence plus random distractors; negatives drop evidence and add hard distractors, filtered so that no answer model still answers correctly; teacher-written rationales; classification loss plus intermediate-layer distillation. Training trajectories include software engineering; evaluation does not.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Score / early-stop % / T_mem s | tau=0.5: 55.17 / 30.0 / 8.248 | Full Completion (Slow) 56.49 / 0.0 / 11.341; Fast Prefix Only 44.91 / 100.0 / 0.054 | AMA-Bench, DeepSeek-V4-Flash | n not stated |
| same | tau=0.9: 55.89 / 12.3 / 10.273 | as above | AMA-Bench | |
| same | tau=0.5: 55.06 / 30.2 / 10.581 | Slow 56.41 / 0.0 / 15.816 | AMA-Bench, Qwen3.5-35B-A3B | |
| same | tau=0.5: 38.77 / 26.6 / 10.883; tau=0.9: 42.09 / 8.0 / 13.422 | Slow 43.26 / 0.0 / 14.611; Fast 30.02; RAG 30.29; Long Context 38.01 | BEAM | stop rule never matches slow |
| Untrained vs trained router | BEAM 29.62 (ET 86.5) vs 38.77 (ET 26.6); AMA 55.52 (ET 4.9) vs 55.17 (ET 30.0) | | Table 3, tau=0.5 | untrained router is either too eager or too timid |
| Claimed time cut | "27.3% and 25.5%" | | abstract | matches T_mem, not end-to-end; paper gives 20.0% e2e on AMA; BEAM e2e 18.43 to 14.11 (about 23.4%, our arithmetic) |

Judge: "official LLM judge provided by each benchmark", identity not stated, so judge vs system overlap unknown.

## Mechanism details you could implement
- Router input: (q, C_f) only; output a single yes/no token; threshold tau on normalised P(yes).
- Overflow rule: if C_f does not fit the router, continue (never stop on an unread context).
- Negative construction: drop gold evidence, add hard distractors, keep only negatives no answer model can still solve.

## Limitations, caveats, counter-evidence
- No false-sufficiency rate: we cannot tell how many early stops were wrong.
- Token cost deferred to a supplement; matched hard caps not stated; no fixed top-k arm.
- Router base model and size not stated; no code.
- Text overstates latency gain (memory time quoted as total time).

## Takeaways for tuning a memory stack
- Supports B9 directionally: a trained sufficiency stop keeps about 98% of always-deep quality on one benchmark while skipping deep work on 30% of queries, but loses 1.2 to 4.5 points on the other.
- H8 must report false-sufficiency explicitly; this paper shows why (the score gap is the only trace of wrong stops).
- An untrained (prompted) router is a poor stand-in; H8's Jev-Mem thresholds need fitting on Engram data.

## Open questions
- Router size and latency share; error rate of early stops by question type.
