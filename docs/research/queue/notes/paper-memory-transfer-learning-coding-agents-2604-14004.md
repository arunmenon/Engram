---
schema_version: 1
artifact_id: N-SURVEY-20261005-05
artifact_type: note
producer: triage
run_id: survey-20261005T054504Z-d350
created_at: 2026-10-05T06:30:00Z
idempotency_key: note:survey:arxiv:2604.14004
input_refs: []
pillar_primary: R5
pillar_secondary: [R3]
memory_stage: consolidation
beliefs_affected:
  supports: []
  contradicts: [B16]
evidence:
  directness: 4
  control: 3
  independence: 3
  reproducibility: 3
  applicability: 4
evidence_scale: 1 (weak) to 5 (strong), per dimension
source_url: https://arxiv.org/abs/2604.14004
found_via: survey
---

# Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents

- **URL:** https://arxiv.org/abs/2604.14004 (tables read via https://arxiv.org/html/2604.14004; project page https://memorytransfer.github.io/)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** April 2026
- **Retrieved:** 2026-10-05
- **Cited by evidence:** survey query for B16 (raw trajectories vs distilled)
- **Relevance to a memory stack:** high. Same tasks, four memory representations, six coding benchmarks; directly the arm comparison B16 is about.

## TL;DR
- Four memory formats, one at a time: Trajectory, Workflow, Summary, Insight. Memories transferred across domains (from other benchmarks).
- Average pass@3: zero-shot 0.523, Trajectory 0.534, Workflow 0.538, Summary 0.546, Insight 0.560. The most abstract format wins on average; raw trajectories are the weakest memory arm.
- Trajectory memory falls below no memory on TerminalBench2 (0.270 vs 0.315) and MLGym-Bench (0.583 vs 0.667).
- Negative-transfer causes named: "domain-mismatched anchoring", "false validation confidence", "misapplied best-practice transfer".
- Differences are small (3.7 points average) on 100 tasks per benchmark with no reported intervals.

## What it claims / describes
Up to 100 randomly sampled tasks per benchmark (LiveCodeBench v6, Aider-Polyglot, SWE-Bench Verified, TerminalBench2, ReplicationBench, MLGym-Bench). Memories are built on other benchmarks and retrieved for the target, so this measures cross-domain transfer. Models in the study: GPT-5-mini, DeepSeek V3.2, Qwen3-Coder-480B-A35B-Instruct; which model produced the main table is not stated in the text read.

## Numbers (pass@3, verbatim)

| memory | LCB | Aider | SWE-V | TB2 | RepBench | MLGym | avg |
|---|---|---|---|---|---|---|---|
| zero-shot | 0.910 | 0.470 | 0.730 | 0.315 | 0.111 | 0.667 | 0.523 |
| Trajectory | 0.940 | 0.490 | 0.770 | 0.270 | 0.122 | 0.583 | 0.534 |
| Workflow | 0.920 | 0.470 | 0.770 | 0.348 | 0.111 | 0.583 | 0.538 |
| Summary | 0.930 | 0.460 | 0.760 | 0.371 | 0.133 | 0.667 | 0.546 |
| Insight | 0.930 | 0.470 | 0.770 | 0.360 | 0.189 | 0.750 | 0.560 |

Cost, latency, tokens per arm: not extracted. Judge: executable tests (pass@3), no LLM judge on the main metric.

## Mechanism details you could implement
- Keep representation the only variable: same source episodes rendered as trajectory, workflow, summary or insight.
- Track negative transfer per benchmark, not only averages.

## Limitations, caveats, counter-evidence
- Cross-domain setting. Within-project reuse (our main case) is not what this table measures; raw trajectories may still win when the task is near-identical (consistent with the EvoSkill evidence behind B16). (inference)
- ~100 tasks per cell, pass@3, no confidence intervals; MLGym and ReplicationBench cells are small, and several differences are one or two tasks.
- On SWE-Bench Verified, Trajectory, Workflow and Insight tie (0.770).

## Takeaways for tuning a memory stack
- Contradicts B16 as currently worded for cross-project transfer in coding agents: the most distilled form did best and raw trajectories were worst, with outright harm on two benchmarks.
- Suggests a split rule: raw episodes for same-task reuse, insights for cross-project reuse. Needs our own test.

## Open questions
- Which backbone the main table uses; per-model breakdown.
- Within-domain results, if reported elsewhere in the paper.
