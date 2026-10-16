---
schema_version: 1
artifact_id: N-20260926-15
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103507226094940275", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:sanity.io/engineering/the-0-5-second-agent
claim_cluster: url:sanity.io/engineering/the-0-5-second-agent
feeds: ["decision", "memory"]
primary_source: https://www.sanity.io/engineering/the-0-5-second-agent
source_commit: n/a
strength: builder-report
pillar_primary: R3
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision-model entry choice", "probability-mass multi-read", "speculative prefetch while typing", "model routing"], "workload": ["documentation QA agent"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-step latency LLM vs Jev and answer correctness counts", "control": "low: one corpus, one week, 22 to 26 answers, Haiku/Sonnet as the LLM baselines", "independence": "medium: Sanity engineers, no stated TypeSafe tie", "reproducibility": "low: no code or dataset", "applicability": "medium: choosing which knowledge-base entries to read before answering is our curate step; docs QA, not engineering tasks"}
beliefs_affected: {"supports": ["B11"], "contradicts": [], "would_create": []}
claim_correction: none
---

# The 0.5-second agent (Sanity engineering blog)

- **URL:** https://www.sanity.io/engineering/the-0-5-second-agent
- **Type:** builder writeup (vendor engineering blog)
- **Author / org:** John Siciliano, Knut Melvaer (Sanity)
- **Date:** 2026-09-24
- **Retrieved:** 2026-09-26 (web; no code)
- **Cited by evidence:** https://x.com/kmelve/status/2103507226094940275 (@kmelve). The pre-cluster also held @askalphaxiv x:2103368968014848400 and @KunalSin9h x:2103779974281089321, which refer to a separate "JEV-as-a-Judge: Accept When Confident, Escalate When Unsure" paper; split out and parked (image only).
- **Relevance to a memory stack:** medium. A small, concrete read path where a decision model picks which knowledge entries to read, and reads several when probability mass is split, instead of a fixed top-k.

## TL;DR
- Docs agent answering in about 0.5 s median using four constrained Jev decisions instead of LLM calls per step.
- Step latencies, LLM vs Jev: entry choice 1,328 ms -> 282 ms; model routing 818 ms -> ~300 ms; MCP choice 829 ms -> 170 ms; speculative prefetch while the user types saves 1,828 ms.
- Cost "$1.91 vs. $5.26 per 1,000 answers"; entry choice "26 out of 26 correct"; final demo 20/22 answers fully grounded.
- Authors call results "indicative and not a true benchmark" ("a week of testing on one corpus").

## What it claims / describes
- Jev chooses the knowledge-base entry; when probability mass is split, several entries are read (example: Next.js 0.74 and Live Preview 0.19, both read).
- Jev also routes the model and picks the MCP server; the answer is written by an LLM.
- No escalation thresholds or LLM-judge fallback are described.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| entry choice latency | 282 ms | LLM 1,328 ms | Haiku/Sonnet baselines | |
| routing latency | ~300 ms | LLM 818 ms | | |
| MCP choice latency | 170 ms | LLM 829 ms | | |
| speculative prefetch | saves 1,828 ms | | while typing | |
| cost per 1,000 answers | $1.91 | $5.26 | | |
| entry choice correct | 26/26 | | | tiny n |
| fully grounded answers | 20/22 | | final demo | |

## Mechanism details you could implement
- Read-set by probability mass: read every entry above a floor (e.g. 0.19 was read), not a fixed k; a middle path between fixed top-k and a stop rule.
- Speculative retrieval on partial input (prefetch while the user types), then confirm.

## Limitations, caveats, counter-evidence
- One corpus, one week, n = 22 to 26; the floor for the multi-read is not stated.
- Zero errors in 26 bounds the error rate at about 11% (rule of three, B21).

## Takeaways for tuning a memory stack
- A mass-based multi-read is a cheap alternative to a sufficiency controller worth a matched-budget test against fixed top-k (B9 area).
- Always return at least one entry (consistent with B11: the selector is a ranker, not an admission gate).

## Open questions
- Threshold for reading a second entry? Not stated.

## Grading and labels
- Directness high; control low; independence medium; reproducibility low; applicability medium.
- Pillar R3 (request-time evidence selection). Secondary R4.
- Beliefs: supports B11 (the chooser always picks something and reads more when unsure; no "none" option described). No contradictions.

## Origin chain
post 2103507226094940275 (@kmelve) -> sanity.io engineering post (2026-09-24) -> latency table, cost line, accuracy lines -> this note. Independence: Sanity engineers; model under test jev (version not stated).
