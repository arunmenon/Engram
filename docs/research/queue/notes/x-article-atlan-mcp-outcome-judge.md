---
schema_version: 1
artifact_id: N-20261010-07
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2102885375639507087", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x-article:2102869389762867200
claim_cluster: x-article:2102869389762867200
feeds: ["decision"]
primary_source: https://x.com/i/article/2102869389762867200
source_commit: n/a
strength: builder-report
pillar_primary: R6
pillar_secondary: ["R5"]
memory_stage: evaluation
tags: {"mechanism": ["llm-judge", "trace-context-depth", "deterministic-persona-classifier"], "workload": ["mcp-server", "multi-turn-agent-traces"], "lifecycle_stage": ["evaluate"], "cross_cutting": []}
evidence_grade: {"directness": "medium: reports judge pass rates against a hand-labelled reference", "control": "medium: model held constant, only trace depth varied, fixed 264-trace benchmark", "independence": "medium: Atlan's own product and labels", "reproducibility": "low: private traces, judge prompt not released", "applicability": "high: grading long multi-step agent traces is our evaluation problem"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["An LLM judge of agent outcomes must read the whole multi-step trace; truncating steps biases it toward failing long successful conversations"]}
claim_correction: The post says the judge "scores every MCP outcome for real user value"; the validation is aggregate pass rate (v3 79% vs human 85%) on 264 traces, not per-trace agreement.
---

# Empathy at Scale: an LLM judge for Atlan MCP outcomes, validated on 264 hand-graded traces (@rishigb, Atlan)

- **URL:** https://x.com/i/article/2102869389762867200 (post https://x.com/rishigb/status/2102885375639507087)
- **Type:** X article (first-hand)
- **Author / org:** @rishigb, head of research, Atlan
- **Date:** 2026-09-23
- **Retrieved:** 2026-10-10 via the fxtwitter mirror API
- **Cited by evidence:** https://x.com/rishigb/status/2102885375639507087 (@rishigb)
- **Relevance to a memory stack:** medium. How much trace a judge must see to grade multi-step agent outcomes, measured against human labels; relevant to our own PDLC benchmark grading.

## TL;DR
- 1,000 conversations read by hand to define value; a two-part judge: deterministic persona and break-stage classifier (retrieval, synthesis, selection, formulation, infra) plus an LLM judge over the full trace with nine outcome labels.
- Fixed benchmark: 264 real traces sampled from about 6,300, stacked with hard cases (11+ tool calls; redacted outputs). Human truth: 224 of 264 (about 85%) delivered value.
- Same model, only trace depth changed: judge pass rate v1 45%, v2 60%, v3 79%; v3 "caught successes v1 had wrongly failed and failures v1 had wrongly passed".

## What it claims / describes
"More than 80%" of MCP traffic is multi-turn. v2 truncated each step to a sliver and was worst on the longest conversations; v3 read whole traces and improved as conversations got longer. Grouping by an outcome ID sent by clients (Glean, Claude) makes whole-conversation judging possible.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| human-labelled value delivered | 224 of 264 (about 85%) | | 264 traces from about 6,300 | single labeller (author) |
| judge pass rate v1 / v2 / v3 | 45% / 60% / 79% | human 85% | same; model constant | aggregate rate, not per-trace agreement; model not named |

## Mechanism details you could implement
- Deterministic pre-classification (persona, break stage) before the LLM verdict.
- Give the judge the full conversation grouped by outcome ID; avoid per-step truncation.

## Limitations, caveats, counter-evidence
- Per-trace agreement, kappa or confusion matrix not given; matching pass rates does not mean matching labels.
- Judge model unnamed; one labeller.

## Takeaways for tuning a memory stack
- When we grade agent runs that use memory, give the judge the whole trace and validate per-trace agreement against our own labels.

## Open questions
- Per-trace agreement for v3; false-pass rate on the 40 failures.

## Grading and labels
- Directness medium, control medium, independence medium, reproducibility low, applicability high.
- Pillar R6, secondary R5. Stage: evaluation. No priority match (not a System One model; not a memory benchmark).
- Would create: judge context depth is a first-order variable.

## Origin chain
post 2102885375639507087 (@rishigb) -> X article 2102869389762867200, section "How much of the trace to show it" -> this note. The relayed Atlan thread in decision-trends (gippp69, 2026-09-28) is about alert triage, a different claim.
