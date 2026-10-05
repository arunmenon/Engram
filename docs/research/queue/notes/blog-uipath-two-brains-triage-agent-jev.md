---
schema_version: 1
artifact_id: N-20260930-08
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2105086527172694443", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:engineering.uipath.com/two-brains-are-better-than-one-building-a-faster-cheaper-triage-agent-with-uipath-and-jev-adbc0a2723eb
claim_cluster: url:engineering.uipath.com/two-brains-are-better-than-one-building-a-faster-cheaper-triage-agent-with-uipath-and-jev-adbc0a2723eb
feeds: ["decision"]
primary_source: https://engineering.uipath.com/two-brains-are-better-than-one-building-a-faster-cheaper-triage-agent-with-uipath-and-jev-adbc0a2723eb
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
tags: {"mechanism": ["choice plus noul plus score in one Jev call", "escalation to human on urgency, frustration or low routing confidence", "LLM writes replies only after routing"], "workload": ["support ticket triage"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
memory_stage: routing
priority: 1
evidence_grade: {"directness": "low: one demonstrated ticket and latency multiples; no dataset", "control": "low: latency compared with two unnamed 'fast, cheap' LLMs; no accuracy baseline", "independence": "medium: UiPath engineering, not TypeSafe", "reproducibility": "low: no code, thresholds not disclosed", "applicability": "low: customer support triage, not memory; the escalation pattern transfers"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": []}
claim_correction: The post says Jev "made ticket triage 13-23x faster at p50"; the blog measures latency of the decision call against two unnamed fast LLMs on what it calls "this one sample", with no triage accuracy, escalation rate or ticket volume reported.
---

# Two Brains Are Better Than One: a triage agent with UiPath and Jev (TypeSafe) (UiPath engineering blog)

- **URL:** https://engineering.uipath.com/two-brains-are-better-than-one-building-a-faster-cheaper-triage-agent-with-uipath-and-jev-adbc0a2723eb
- **Type:** builder write-up (enterprise engineering blog)
- **Author / org:** Akshaya Vishnu Shanbhogue, UiPath
- **Date:** 2026-09-23
- **Retrieved:** 2026-09-30 via a reader proxy (direct fetch returned HTTP 403)
- **Cited by evidence:** decision feed 2026-09-30, @govindprabhu (https://x.com/govindprabhu/status/2105086527172694443); decision digest 2026-09-30 "Jev in production".
- **Relevance to a memory stack:** low to medium. A named-enterprise usage report for priority 1 (who uses System One models where): routing and escalation only, no measured quality.

## TL;DR
- One Jev call per ticket with three typed questions: choice (department: billing, technical, sales), noul (urgent, 0 to 1), score (frustration: Calm, Frustrated, Very angry).
- Escalate to a human in UiPath Action Center on "High urgency, high frustration, or a routing decision Jev isn't confident about"; otherwise a department-specific LLM (System 2) drafts the reply.
- Latency: p50 "13-23x faster", p99 "16-32x" faster than two models "marketed as the fast, cheap end"; one urgent ticket's Jev call took 168 ms.
- No dataset, no accuracy, no escalation rate; thresholds "not disclosed"; the author calls the result illustrative ("this one sample").

## What it claims / describes
A two-stage agent in a live UiPath tenant: System 1 (Jev) classifies and scores; code applies escalation rules; System 2 (an LLM) writes. Sample output: urgency 0.99, frustration 1.85 on a 0 to 2 scale.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| p50 latency speedup | 13-23x | two unnamed fast LLMs | ticket triage decision | sample size not stated |
| p99 latency speedup | 16-32x | same | same | |
| one Jev call | 168 ms | | single urgent ticket | |
| accuracy / agreement / escalation rate / cost | not stated | | | |

## Mechanism details you could implement
- Batch routing, urgency and sentiment as three typed questions in one call on the same state.
- Escalation as code over typed outputs: any of (urgency high, frustration high, routing confidence low) sends to a human; this is the same pattern as the synthesis section 5 advice to keep thresholds in code.

## Limitations, caveats, counter-evidence
- No quality measurement at all; latency only. Similar to Deel (synthesis section 8), the other named-enterprise report, which also turned out narrower on a primary read.
- Baseline models unnamed.

## Takeaways for tuning a memory stack
- Evidence of adoption, not of accuracy. Do not cite it for quality; cite it for the escalation pattern and for latency multiples.

## Open questions
- Triage accuracy vs the LLM baseline, and the escalation rate, on UiPath's ticket volume.

## Grading and labels
- Directness low; control low; independence medium; reproducibility low; applicability low.
- Pillars: R9 primary (System One at the routing stage, named enterprise), R4 (escalation rule). Memory stage: routing. Priority 1: a first-hand usage report from a named team, noted under the priority rule even though it implies no test.
- Beliefs: none affected directly.
- Contradiction rows: none.

## Origin chain
@govindprabhu post (2105086527172694443) -> UiPath engineering blog (2026-09-23) -> architecture and performance sections -> this note. Independence: UiPath authors; no TypeSafe co-authorship stated.
