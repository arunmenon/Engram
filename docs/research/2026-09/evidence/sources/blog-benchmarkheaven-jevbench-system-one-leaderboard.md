---
schema_version: 1
artifact_id: N-20260928-17
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104418350973743229", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:benchmarkheaven.com/jev-models
claim_cluster: url:benchmarkheaven.com/jev-models
feeds: ["memory"]
primary_source: https://benchmarkheaven.com/jev-models
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R6"]
memory_stage: evaluation
priority: 2
tags: {"mechanism": ["composite leaderboard", "harmonic mean with axis gates", "sealed items"], "workload": ["generic typed decisions"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: a rendered leaderboard with axis scores; per-item data not inspected", "control": "medium: same public plus sealed items for all systems, one request at a time from one server, but composite weights and gates are design choices", "independence": "medium: third-party leaderboard operator; model makers submit", "reproducibility": "low: harness said to be MIT on GitHub but the repo was not identified on the page; 308 items are sealed", "applicability": "low: generic decisions, no memory stages"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Several open-weight 4B decision models now match Jev 1.13 on accuracy and beat it on a speed-and-cost-weighted composite (JevBench v1.4.2.2)"]}
claim_correction: The post says the open models "are already right up there"; on the page, three open-weight 4B models rank above Jev on the composite, but on the Intelligence axis Jev 1.13.0 is highest of the top five (53.1 vs 52.2, 53.0, 49.4, 48.9); the open models lead on speed and cost.
---

# JevBench v1.4.2.2 (Benchmark Heaven): a leaderboard for System One decision models

- **URL:** https://benchmarkheaven.com/jev-models
- **Type:** third-party leaderboard page
- **Author / org:** Benchmark Heaven; harness described as "protocol `jevbench::v1.4`", MIT (repository not identified on the page)
- **Date:** "Scored 27 Sept 2026"
- **Retrieved:** 2026-09-28 via WebFetch (two passes) and raw HTML link scan. The page links many builder repos (for example github.com/Mapika/decider, github.com/JoshuaSP/open-jev, github.com/Contrastive-LM/CLM) but none was confirmed as the harness. Values below are as rendered; the WebFetch rendering is a summary and was not cross-checked against page source for every cell.
- **Cited by evidence:** @SavantNimit 2026-09-28 https://x.com/SavantNimit/status/2104418350973743229
- **Relevance to a memory stack:** medium for priority 2: the only leaderboard seen that ranks hosted Jev against many open-weight decision models on accuracy, calibration, speed and cost together.

## TL;DR
- Items: 534 public decisions in Easy, Standard, Judge and Hard tiers plus 308 sealed items; "842 decisions measured" (one pass reported 231 public items; the page figures are not fully consistent).
- Four equal axes (25% each): Intelligence (accuracy, 0 to 100), Calibration (ECE mapped to 0 to 100), Speed (log median latency; 2x Jev's latency = 50 points), Cost (2x Jev's cost per 1,000 decisions = 50 points), combined by a "weighted harmonic mean" with "low-axis gates".
- "Jev-class" gate: cost <= $0.080 per 1,000 decisions and median latency <= 1.30 s (2x Jev 1.13.0).
- Top five: Imajev-4B 67.4, Plumb-4B 65.8, decider-4b v2 64.1, Jev 1.13.0 63.3, JevK5 v0.2.0 62.0. Jev has the highest Intelligence among them (53.1).

## What it claims / describes
- "state and a bounded rubric in, a typed answer out"; one request at a time from a server in Germany.
- Labels: rendered as "human expert annotation paired with teacher-model outputs" (exact labelling procedure not verified).
- 91 ranked systems including zero-shot classifiers and rerankers lower down.

## Numbers

| rank | model | type | score | intelligence | calibration | speed | cost |
|---|---|---|---|---|---|---|---|
| 1 | Imajev-4B | open-weight | 67.4 | 52.2 | 80.4 | 90.6 | 59.7 |
| 2 | Plumb-4B | open-weight | 65.8 | 53.0 | 75.5 | 93.5 | 55.8 |
| 3 | decider-4b v2 | open-weight | 64.1 | 49.4 | 75.0 | 92.9 | 60.9 |
| 4 | Jev 1.13.0 | hosted API | 63.3 | 53.1 | 76.3 | 83.3 | 52.0 |
| 5 | JevK5 v0.2.0 | open-weight | 62.0 | 48.9 | 74.5 | 91.1 | 59.5 |
| 6 | Cygnet | open-weight | 61.8 | 49.5 | 74.9 | 90.7 | 52.8 |
| 7 | Hopper | open-weight | 59.4 | 48.0 | 79.1 | 86.8 | 58.7 |
| 8 | Winnow-12B Q8 | open-weight | 55.6 | 48.3 | 64.8 | 82.3 | 52.9 |
| 9 | reflex 4B | open-weight | 54.0 | 47.5 | 70.4 | 68.0 | 59.7 |
| 10 | djev | hosted API | 52.2 | 47.0 | 55.4 | 91.4 | 57.6 |

Where Laya, Intern-Decision, CLM, this-that-model or Julia-1 rank was not captured.

## Mechanism details you could implement
- A composite with gates (a system cannot win on cost if an axis is below a floor) and a "class" filter relative to a reference model's cost and latency is a reasonable template for our own Jev vs open-weight bake-off (priority 2), with weights set by our own cost of error.
- Keep a sealed item set to limit overfitting to the public items.

## Limitations, caveats, counter-evidence
- Intelligence scores around 50 suggest a hard item set, but item content is not inspected here.
- Composite weights favour speed and cost; the open models lead mostly there.
- Speed of self-hosted models depends on the operator's hardware, not stated.
- Harness repo not identified; sealed items cannot be checked.

## Takeaways for tuning a memory stack
- The field now has several 4B open decision models within a point or two of Jev on accuracy; a priority-2 bake-off on our own memory decisions should include at least the top open rows here alongside Laya and Intern-Decision.
- Decide our axis weights explicitly (error cost per stage) rather than adopting a leaderboard composite.

## Open questions
- Which harness repo and labelling procedure? Where do Laya and Intern-Decision rank?

## Grading and labels
- Directness medium; control medium; independence medium; reproducibility low; applicability low.
- Pillars: R9 primary, R6 secondary. Memory stage: evaluation. Priority 2. Product named: Jev.
- Beliefs: would create the belief in the frontmatter; nothing held is contradicted.
- Contradiction rows: none.

## Origin chain
- Post 2104418350973743229 (@SavantNimit) -> https://benchmarkheaven.com/jev-models (leaderboard table, methodology text) -> this note.
- Independence: third-party operator; model makers overlap with the typed-decisions and Open Decider community (decider-4b may relate to github.com/Mapika/decider; not verified).
