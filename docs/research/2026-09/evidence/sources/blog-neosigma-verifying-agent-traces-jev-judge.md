---
schema_version: 1
artifact_id: N-20260927-05
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103915871051903064", "file_id": null, "sha256": null}, {"artifact_id": "post:2103911558124634468", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:neosigma.ai/blog/verifying-agent-traces-at-scale-with-jev
claim_cluster: url:neosigma.ai/blog/verifying-agent-traces-at-scale-with-jev
feeds: ["decision", "memory"]
primary_source: https://neosigma.ai/blog/verifying-agent-traces-at-scale-with-jev
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision-model judge", "binary pass/fail rubric", "repeatability test", "blinded human audit", "preregistered thresholds"], "workload": ["tau2-bench agent traces"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: same 834 frozen traces, same rubric, two judges, human audit", "control": "medium: preregistered thresholds and a blinded 100-trace human audit, but human n is small (CI inconclusive) and GPT-5 Mini is a single comparator", "independence": "medium: neosigma is a Jev user, not TypeSafe; traces from the public tau2 benchmark", "reproducibility": "medium: frozen public traces and rubric described; code and raw verdicts not seen", "applicability": "high: pass/fail judging of agent traces is exactly our eval-harness judge question"}
beliefs_affected: {"supports": ["B21"], "contradicts": [], "would_create": ["A decision-model pass/fail judge matched GPT-5 Mini on human agreement (88 vs 85 of 100), caught more labelled failures (25 vs 17 of 29) and flipped verdicts less on repeats (3 vs 19 of 100 traces) at 6.2x lower cost"]}
claim_correction: none (6.2x cheaper and 34x faster match; the post omits that human agreement was within noise, 95% CI [-10.9, +5.1])
---

# Cheaper Judges, Denser Feedback: verifying agent traces at scale with Jev (neosigma blog)

- **URL:** https://neosigma.ai/blog/verifying-agent-traces-at-scale-with-jev
- **Type:** vendor blog (Jev user, not the model vendor)
- **Author / org:** Kartikeya Gupta, Gauri Gupta, Ritvik Kapila; neosigma
- **Date:** 2026-09-26
- **Retrieved:** 2026-09-27 (web page; no version id)
- **Cited by evidence:** @neosigma_ai https://x.com/neosigma_ai/status/2103915871051903064 and https://x.com/neosigma_ai/status/2103911558124634468
- **Relevance to a memory stack:** high for evaluation. It is the second field measurement (after Sentry in the synthesis section 6) of a decision model as a pass/fail judge, and the first with a blinded human audit, repeatability and preregistered thresholds.

## TL;DR
- 834 frozen tau2 traces (agent GPT-5.6 Terra, three seeds), binary rubric "Did the agent successfully complete the user's task?", judged by Jev and by GPT-5 Mini (structured verdict + confidence + rationale); 10,000 decisions per judge.
- Blinded human audit of 100 traces: Jev agreed 88/100, GPT-5 Mini 85/100 (difference inconclusive, 95% CI [-10.9, +5.1]).
- Failure recall on 29 human-labelled failures: Jev 25, GPT-5 Mini 17 (95% CI [-44.4, -12.9], passed the preregistered gate).
- Repeatability (100 traces x 20 repeats): Jev 98.99% pairwise agreement, 3 traces flipped; GPT-5 Mini 93.7%, 19 flipped.
- Cost for 10,000 decisions: $3.23 vs $19.98 (6.2x); median latency 231 ms vs 7.8 s (34x); p95 311 ms vs 15,443 ms.

## What it claims / describes
- Goal: evaluation cheap and fast enough to learn from most production traces.
- Traces: 834 frozen tau2 traces across three seeds from 278 public tasks (the blog lists 342 retail, 150 airline, 342 telecom trace counts).
- Judges: Jev (TypeSafe System One, RLCD-trained) with the binary rubric; GPT-5 Mini with a structured schema returning verdict, confidence and rationale.
- Checks: agreement with the tau2 reward (treated as supporting evidence, not ground truth), a 100-trace blinded human audit, failure recall on 29 labelled failures, repeatability over 20 runs of 100 traces, validity (100% completion for both).
- Preregistered thresholds: within 5 points of GPT-5 Mini on human agreement; within 10 points on failure recall; >= 99.5% valid completions; >= 99% repeatability (descriptive).
- Disagreement example (airline task 32): GPT-5 Mini and tau2 marked it failed (no nonstop booked, database unchanged); Jev and the human marked it passed because the customer declined the $396 upgrade and asked for no changes.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| human agreement | Jev 88/100 | GPT-5 Mini 85/100 | blinded reviewer, 100 traces | 95% CI [-10.9, +5.1]: inconclusive |
| failure recall | Jev 25/29 | GPT-5 Mini 17/29 | 29 human-labelled failures | 95% CI [-44.4, -12.9]; passed gate |
| agreement with tau2 reward | Jev 83.5% (696/834) | GPT-5 Mini 84.4% (704/834) | 834 traces | tau2 reward not ground truth |
| repeatability | Jev 98.99%, 3 traces flipped | GPT-5 Mini 93.7%, 19 flipped | 100 traces x 20 repeats | Jev below the 99% target (descriptive) |
| cost per 10,000 decisions | $3.23 | $19.98 | measured | 6.2x; "9.6x on first-seen traces projected" |
| median latency | 231 ms | 7.8 s | | 34x |
| p95 latency | 311 ms | 15,443 ms | | |
| valid completions | 100% | 100% | 10,000 each | |

## Mechanism details you could implement
- Rubric as one binary proposition per trace ("Did the agent successfully complete the user's task?").
- Evaluate a judge on four axes before adopting it: human agreement, failure recall on labelled failures, repeatability over repeated calls, and validity rate; write the thresholds down before running.
- Report failure recall separately: a judge that is lenient on failures is the dangerous one for gating.
- Repeatability protocol: 100 traces x 20 calls, count traces whose verdict flips.

## Limitations, caveats, counter-evidence
- Blog: the 100-trace human audit was "not large enough to make the preregistered agreement test conclusive"; tau2 reward is "supporting evidence rather than ground truth"; figures beyond 10,000 decisions are projections.
- One comparator (GPT-5 Mini); no frontier LLM judge; no calibration measure (ECE) reported, so B14 is untouched.
- Judge thresholds for Jev (probability cut-off) not captured in the text read.
- Failure recall rests on 29 failures (B21: small n bounds).

## Takeaways for tuning a memory stack
- A decision-model judge is a credible default for high-volume pass/fail checks on agent traces; route only the failures or low-confidence cases to an LLM for explanation (consistent with the Sentry setup in the synthesis).
- Adopt the four-axis judge acceptance test and preregistered thresholds for our P3 harness.
- Size the human audit for the effect you care about: 100 traces could not resolve a 3-point agreement difference.

## Open questions
- Jev's decision threshold and whether it was tuned on these traces.
- Calibration of Jev's pass probability on this rubric.
- Behaviour on long engineering traces rather than customer-service dialogues.

## Grading and labels
- Directness high; control medium; independence medium; reproducibility medium; applicability high.
- Pillars: R6 primary (judge design and evaluation integrity); R4 secondary (decision model as automated decision).
- B21 supports: the small-sample caution shows up directly (29 failures, 100 audit traces).
- Would create: decision-model judge matched an LLM judge on human agreement and beat it on failure recall and repeatability at 6.2x lower cost (one study).
- No contradiction rows. Consistent with synthesis section 6 (Sentry).

## Origin chain
posts 2103915871051903064 and 2103911558124634468 (@neosigma_ai) -> neosigma blog (2026-09-26) -> core table, preregistered thresholds, disagreement example, limitations -> this note. Independence: authors are a Jev customer; traces from public tau2; not linked to Sentry or LangChain sources in the catalogue.
