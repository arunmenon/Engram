---
schema_version: 1
artifact_id: N-SURVEY-20261005-01
artifact_type: note
producer: triage
run_id: survey-20261005T054504Z-d350
created_at: 2026-10-05T06:30:00Z
possible_duplicate_of: N-20261001-03 (jev 0.91, shadow, not enforced)
idempotency_key: note:survey:github:suranjaychandra/jev-state@3c30e89
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R6]
memory_stage: evaluation
priority: 1
beliefs_affected:
  supports: []
  contradicts: []
  refines: [B14]
refines_note: N-20261001-03
evidence:
  directness: 4
  control: 2
  independence: 2
  reproducibility: 5
  applicability: 1
evidence_scale: 1 (weak) to 5 (strong), per dimension, no single ladder
source_url: https://github.com/suranjaychandra/jev-state/tree/3c30e89/bench
found_via: survey
answers_watch_request: WR-20261001-03
---

# jev-state benchmark at commit 3c30e89: per-call results, labels and cost arithmetic (audit of N-20261001-03)

- **URL:** https://github.com/suranjaychandra/jev-state/tree/3c30e89/bench (files read: results.md, results.json, run.ts, scenarios.ts via raw.githubusercontent.com at 3c30e89)
- **Type:** repo
- **Author / org:** suranjaychandra (GitHub)
- **Date:** results.md dated 2026-09-29
- **Retrieved:** 2026-10-05
- **Cited by evidence:** WR-20261001-03 (challenger), target E-20261001-03, earlier note N-20261001-03
- **Relevance to a memory stack:** medium. It is the only pinned, per-call result we have for "project state into labels before a System One call", but the task is synthetic NPC control and the projection is built from the label rules themselves.

## TL;DR
- The headline numbers in N-20261001-03 match the pinned files exactly: raw 74.3% vs projected 100.0% accuracy, 210 calls per arm, model `jev-1.13.0`, 0 errors.
- The 100% is close to by-construction: the projection schema bands health at cuts `[0.2, 0.5]` with labels `["critical", "low", "healthy"]` and enemy distance at cuts `[10, 30]` with label `near`, which are the exact thresholds and words the ground-truth `policy()` and the instructions use. The projection computes the predicates the rules test. (inference from scenarios.ts)
- The "about $0.0171" is not a billing receipt. run.ts computes it as `totalTokens / 1e6 * 0.042` with a hard-coded price; 406,326 x 0.042 / 1e6 = 0.01707.
- Heal accuracy raw 60.0% is 18 of 30 calls (10 scenarios x 3 reruns); n is small and reruns are not independent.
- Calibration bins pool all 210 calls per arm (reruns of the same 70 scenarios). Computed from results.json, the weighted gap between average confidence and accuracy is about 0.04 for both arms (raw: 8.48/210; projected: 8.37/210). Raw is close to calibrated in the 0.7 to 0.9 bin (81.7% conf, 81.4% acc); projected is under-confident (0.7 to 0.9 bin: 81.3% conf, 100% acc).

## What it claims / describes
`bench/run.ts` calls `client.systemOne({ state, questions: { action: choice(INSTRUCTIONS, CRITERIA) } })` from `@typesafe-ai/sdk` for each of 70 seeded scenarios (`makeScenarios(10, 42)`, mulberry32 PRNG), two variants (raw state; `projectState(raw)`), 3 reruns, concurrency 5. Labels come from `policy(raw)`, a seven-rule first-match function that "Mirrors INSTRUCTIONS exactly". Scenarios are rejection-sampled until each action has 10, so the class balance (10 per action) is not the natural distribution.

The raw state carries distractor fields (mesh id, LOD level, fps, draw calls, navmesh version, velocities, up to 8 enemies with positions). The projection drops unknown fields (`unknown: "drop"`), keeps at most 5 enemies sorted by distance with only `type` and banded `distance`, bands hp relative to `maxHp`, and converts `lastNoiseAt` with `time({ now })` (src/time.ts not read; output format not stated).

## Numbers

| metric | raw | projected | setup | caveat |
|---|---|---|---|---|
| accuracy | 74.3% (0.742857) | 100.0% | 210 calls each, jev-1.13.0 | labels and projection share thresholds |
| scenarios whose answer changed across reruns | 6/70 | 0/70 | 3 reruns | |
| avg input tokens | 1236 (1235.84) | 699 (699.04) | | |
| p50 latency | 336 ms | 335 ms | client-side wall clock, concurrency 5 | |
| p95 latency | 422 ms | 390 ms | | |
| heal accuracy | 60.0% | 100.0% | 30 calls per arm | n=10 scenarios |
| patrol accuracy | 43.3% | 100.0% | 30 calls | |
| retreat accuracy | 50.0% | 100.0% | 30 calls | |
| total input tokens | 406,326 | | both arms | |
| cost | "about $0.0171" | | `(totalTokens / 1e6) * 0.042` in run.ts | hard-coded price, no receipt |
| raw calibration bins (n / avg conf / acc) | 0 to 0.5: 38 / 41.2% / 28.9%; 0.5 to 0.7: 32 / 58.3% / 56.3%; 0.7 to 0.9: 70 / 81.7% / 81.4%; 0.9 to 1: 70 / 95.8% / 100% | | last bin is [0.9, 1.01) | pooled reruns |
| projected calibration bins | 0 to 0.5: 0; 0.5 to 0.7: 3 / 66.0% / 100%; 0.7 to 0.9: 29 / 81.3% / 100%; 0.9 to 1: 178 / 98.9% / 100% | | | |

Text and table agree; results.md is generated from the same arrays as results.json.

## Mechanism details you could implement
- Schema-driven projection: `band({ max, cuts, labels })`, `count({ few, many })`, `prune({ keep, sortBy, max })`, `each(...)`, `pipe(...)`, `time({ now })`, applied with `project(raw, SCHEMA, { unknown: "drop" })`.
- The pattern for a memory stack: before a typed decision, turn numeric or verbose state into the vocabulary the decision instructions use, drop fields the decision does not need, cap list lengths.

## Limitations, caveats, counter-evidence
- Label leakage by design: the projection encodes the rule thresholds, so the projected arm tests rule lookup on pre-computed predicates, not reasoning over state. The lift therefore measures "doing the arithmetic for the model", not projection in general. (inference)
- One synthetic domain, balanced classes, one model version, no seed variation (seed 42 only).
- Judge: none (exact match against a deterministic policy), so no shared-model judge issue.
- Cost is estimated, not billed.

## Takeaways for tuning a memory stack
- For B14: this file shows Jev confidence tracking accuracy reasonably on raw state in a toy task (gap about 0.04 pooled); it does not show calibration on our data, and pooled reruns inflate n. It narrows rather than supports a contradiction of B14.
- The projection lift should be expected only when we know the decision thresholds in advance. For memory stages (write gate, staleness) we usually do not, so test projection with thresholds that are not copied from the labels.

## Open questions
- Does the lift survive if projection cut points differ from the label rules (e.g. cuts at 0.25/0.45)?
- What does `time()` emit, and would "recent" be pre-computed too?
