---
schema_version: 1
artifact_id: N-SURVEY-20261009-08
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2610.05176
input_refs: []
pillar_primary: R2
pillar_secondary: [R8]
memory_stage: consolidation
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: 3, control: 3, independence: 3, reproducibility: 1, applicability: 3}
source_url: https://arxiv.org/abs/2610.05176
found_via: survey
---

# AECG: Asymmetric Experience Consolidation and Governance in Multi-Agent Systems

- **URL:** https://arxiv.org/abs/2610.05176 (HTML v1 read through an extractor; local copy kept); code link https://github.com/fenhg297/AECG returned HTTP 404 on 2026-10-09
- **Type:** paper
- **Author / org:** Ao Tian (Beihang), Jialong Liu (Wuhan University), Daqi Zheng (ModelBest), and others
- **Date:** 2026-10-04
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2610.05176.html)
- **Cited by evidence:** top-down survey, R2 consolidation question (B5) and scope serving (PC-20260927-01)
- **Relevance to a memory stack:** medium. Procedural-skill consolidation governed by reliability tracking; its biggest ablation is about scope, which bears on a pending card rather than on summarising consolidation.

## TL;DR
- Treats consolidated skills as hypotheses: fast and slow Beta reliability beliefs per skill, review of the highest-risk skills under a budget, and revised skills reactivated only after paired replay shows the fix without regression (epsilon_reg = 0.05).
- Best in 11 of 12 framework-benchmark settings; up to +10.23 points over the strongest memory baseline (MacNet ScienceWorld, ConMem 61.36 to AECG 71.59).
- Removing scope preservation costs -16.89 (ScienceWorld) and -8.34 (MBPP-Plus) points; in the flat-scope variant 36.5% of skill uses cross their supported scope and success falls below no memory.

## Numbers

| Ablation (ScienceWorld / MBPP-Plus) | Delta |
|---|---|
| minus scope preservation | -16.89 / -8.34 |
| minus dual-timescale beliefs | -4.76 / -6.26 |
| minus exposure weighting | -3.36 / -2.58 |

Setup: PDDL, FEVER, ScienceWorld, MBPP-Plus; AutoGen, MacNet, AgentNet; baselines No-Memory, MacNet-M, MemoryBank, ConMem, G-Memory; gpt-4.1-mini executes, gpt-4o-mini consolidates; dual LLM judges for failure attribution. Cost not stated; Breview value not recovered.

## Mechanism details you could implement
- Drift score from fast-minus-slow belief difference above a noise baseline; priority H = exposure x drift.
- Reactivation gate: fix confirmed and regression score >= parent - 0.05; revised skill never overwrites the active one until it passes.

## Limitations, caveats, counter-evidence
- Code link dead; numbers read through an extractor and only spot-checked.
- Consolidation here is skill extraction from trajectories, not summarisation of facts, so it says nothing about B5's summarising consolidation (inference).

## Takeaways for tuning a memory stack
- Independent support for PC-20260927-01 (serve a lesson only within the task family that produced it): a large ablation in the same direction.
- "Candidate until paired replay passes" is a usable R2 semantic for revising procedural memory.

## Open questions
- Does scope preservation still dominate when tasks are drawn from one codebase rather than four unrelated benchmarks?
