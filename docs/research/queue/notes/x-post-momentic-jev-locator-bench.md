---
schema_version: 1
artifact_id: N-20261010-05
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2103188520156229672", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2103188520156229672
claim_cluster: x:2103188520156229672
feeds: ["decision"]
primary_source: https://x.com/wuweiweiwu/status/2103188520156229672
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["jev-with-llm-fallback", "hybrid-subagent"], "workload": ["ui-test-automation", "element-locating"], "lifecycle_stage": ["act"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: first-hand numbers from the company's own evals, no write-up", "control": "medium: same benchmark across Jev, Jev plus fallback and their v5-auto, but n not stated", "independence": "high: Momentic is a Jev evaluator, not TypeSafe", "reproducibility": "low: private evals, no n, no data", "applicability": "medium: fallback design transfers; visual locating does not"}
beliefs_affected: {"supports": ["B12", "B13"], "contradicts": [], "would_create": []}
claim_correction: none
---

# Momentic tests Jev (TypeSafe) on Locator Bench: 51.8% alone, 78.0% with fallback, vs 84.6% for its own v5-auto

- **URL:** https://x.com/wuweiweiwu/status/2103188520156229672
- **Type:** X post (first-hand report from a named company; long-form post text)
- **Author / org:** @wuweiweiwu (Momentic), reporting tests by Momentic CTO @itsjeffan
- **Date:** 2026-09-24
- **Retrieved:** 2026-10-10 via the fxtwitter mirror API (full post text; earlier runs only saw the truncated text and the image)
- **Cited by evidence:** https://x.com/wuweiweiwu/status/2103188520156229672 (@wuweiweiwu)
- **Relevance to a memory stack:** medium. A named team's negative-leaning production evaluation of Jev with an LLM fallback, the same escalation pattern we design for decision stages.

## TL;DR
- Locator Bench (visual, spatial and logical reasoning to find a described element): Jev 51.8% at 0.35 s median; Jev + v5 fallback 78.0% at 1.5 s; Momentic v5-auto 84.6% at 2.5 s.
- Broader AI-action eval: Jev-only prototype completed about 8% of tasks (4x faster per step than Luna); Luna for general tasks plus Jev locating reached about 24%, 2.8x faster per step than baseline.
- Verdict: "we'd still need it to meet our accuracy requirements for each task before using it in customer tests".

## What it claims / describes
Momentic (AI UI testing) ran Jev on its hardest locator eval and on locator + assertion evals ("Jev was 8x faster than Luna, our fast config, at 1/4 the cost; accuracy was lower there too"). The Jev-only agent could click and type but could not run JavaScript, do AI checks or extract data. Jev takes no images, and "even checking whether a page is ready can need visual context".

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| Locator Bench accuracy, Jev | 51.8% at 0.35 s median | Momentic v5-auto 84.6% at 2.5 s | Locator Bench, n not stated | text-only model on a visual task |
| Jev + v5 fallback | 78.0% at 1.5 s | same | same | fallback rule not stated |
| locator + assertion evals | 8x faster than Luna at 1/4 cost, lower accuracy | Luna | n and accuracy not stated | |
| AI-action task completion | Jev only about 8%; Luna + Jev about 24% | baseline completion not stated | n not stated | |

## Mechanism details you could implement
- Jev as a fast first pass with fallback to a stronger model; measure the accuracy-latency frontier of the combination, not Jev alone.

## Limitations, caveats, counter-evidence
- n, fallback trigger and baseline completion rate unknown; no write-up.
- Task needs vision; Jev is text-only, so this bounds Jev on visual tasks, not on text decisions.

## Takeaways for tuning a memory stack
- A decision model plus fallback recovers most but not all of the gap (78.0 vs 84.6); budget for the residual when a stage has strict accuracy needs.
- "If a test keeps failing for the wrong reasons, engineers learn to ignore it": false-positive cost matters more than latency for gates people read.

## Open questions
- Fallback trigger (confidence threshold?) and its rate.

## Grading and labels
- Directness medium, control medium, independence high, reproducibility low, applicability medium.
- Pillar R9, secondary R4. Stage: routing. Priority 1.
- B12 supports: Jev-only agent completes about 8%; with an LLM handling general tasks, about 24%.
- B13 supports in spirit: escalation to a larger model helps but does not reach the larger model alone (inference).

## Origin chain
post 2103188520156229672 (@wuweiweiwu) -> full post text (no external source) -> this note. Already in decision-trends (2026-09-25 line) as a capability-limit bullet; this note adds the fallback and hybrid numbers.
