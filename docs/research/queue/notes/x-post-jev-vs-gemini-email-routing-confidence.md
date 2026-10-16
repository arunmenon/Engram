---
schema_version: 1
artifact_id: N-20261010-06
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2100655158992719907", "file_id": null, "sha256": null}, {"artifact_id": "post:2100606119504712138", "file_id": null, "sha256": null}, {"artifact_id": "post:2100604560335139083", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2100604560335139083
claim_cluster: x:2100604560335139083
feeds: ["decision"]
primary_source: https://x.com/nikhilmudholkar/status/2100604560335139083
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["confidence-threshold-automation", "selective-prediction"], "workload": ["email-routing", "german-business-email"], "lifecycle_stage": ["act"], "cross_cutting": []}
evidence_grade: {"directness": "medium: first-hand thread with counts, no write-up or data", "control": "medium: same emails and instructions for 3 models", "independence": "high: independent builder on private real data", "reproducibility": "low: private dataset, thread only", "applicability": "medium: selective automation by confidence maps to our gates"}
beliefs_affected: {"supports": [], "contradicts": ["B14"], "would_create": []}
claim_correction: The quoted post says "Jev's most confident 85.5% had zero errors"; the thread's root shows Jev lost on overall accuracy (96.4% vs 97.5% and 98.5% for two Gemini models) and the zero-error slice is against reference labels on this one dataset.
---

# Jev (TypeSafe) lost to Gemini on 1,565 business emails, but its top-confidence 85.5% had zero errors (@nikhilmudholkar thread)

- **URL:** https://x.com/nikhilmudholkar/status/2100604560335139083 (thread 1/8 to 5/8 read)
- **Type:** X thread (first-hand)
- **Author / org:** @nikhilmudholkar; emails from industrial suppliers (company not named)
- **Date:** 2026-09-17
- **Retrieved:** 2026-10-10 via the fxtwitter mirror API, posts 1/8 to 5/8 (6/8 to 8/8 not retrieved)
- **Cited by evidence:** https://x.com/completeskeptic/status/2100655158992719907 (@completeskeptic), https://x.com/nikhilmudholkar/status/2100606119504712138
- **Relevance to a memory stack:** medium. Independent evidence that Jev confidence separates safe-to-automate from needs-review on real data, which bears on our "vendor calibration claimed, not shown" belief.

## TL;DR
- 1,565 emails (1,201 real + 364 AI-written for rare categories), 10 categories, mostly German; same text and instructions for 3 models.
- Overall accuracy: Jev 96.4%, Gemini 3.5 Flash-Lite 97.5%, Gemini 3.8 Flash 98.5%; class-balanced 92.0 / 94.6 / 96.9%.
- "737 predictions had >=99% confidence. Every one matched the reference label. Below 70% confidence, nearly half were wrong." "Jev's most confident 85.5% had zero errors against the reference labels."

## What it claims / describes
Thread argues the value is in where errors fall: mistakes cluster where Jev signals uncertainty, so a confidence cutoff decides what to route automatically.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| overall accuracy | Jev 96.4% | Gemini 3.5 Flash-Lite 97.5%; Gemini 3.8 Flash 98.5% | 1,565 emails, 10 classes (2/8, 3/8) | 364 synthetic rows included |
| class-balanced accuracy | 92.0% | 94.6%; 96.9% | same | |
| errors in >=99% confidence | 0 of 737 | | same (4/8) | by rule of three, rate below about 0.4% (B21, inference) |
| errors in top 85.5% by confidence | 0 | | same (5/8) | "That's on this dataset." |
| error rate below 0.7 confidence | "nearly half" | | same | count not stated |

## Mechanism details you could implement
- Rank by Jev confidence; automate the top slice that has zero errors on a held-out labelled set; send the rest to people.

## Limitations, caveats, counter-evidence
- Reference labels' origin not stated; Gemini confidences not compared (would they separate as well?).
- Threshold chosen on the same data it is reported on (inference: optimistic).

## Takeaways for tuning a memory stack
- Compare decision models on coverage at zero (or target) error, not on overall accuracy; the less accurate model may automate more safely.

## Open questions
- Coverage at zero error for the Gemini models; posts 6/8 to 8/8.

## Grading and labels
- Directness medium, control medium, independence high, reproducibility low, applicability medium.
- Pillar R9, secondary R4. Stage: routing. Priority 1.
- Contradiction: B14 ("Vendor calibration is claimed, not shown"; Against column "none"). This is an independent measurement where Jev's confidence ranking was useful (0 of 737 errors at >=0.99). It shows ranking quality, not calibration in the ECE sense, so the belief's statement may need narrowing rather than reversal.

## Origin chain
post 2100655158992719907 (@completeskeptic) quotes 2100606119504712138 (5/8) -> thread root 2100604560335139083 and 2/8 to 4/8 -> this note. No external source; independent of TypeSafe.
