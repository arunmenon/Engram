---
schema_version: 1
artifact_id: N-20260929-04
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104635559163613631", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:harrisonsec.com/blog/jev-calibration-two-confidence-numbers
claim_cluster: url:harrisonsec.com/blog/jev-calibration-two-confidence-numbers
feeds: ["memory", "decision"]
primary_source: https://harrisonsec.com/blog/jev-calibration-two-confidence-numbers/
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["calibration-ece", "equal-mass-bins", "max-class-probability-gate", "confidence-field", "three-way-routing"], "workload": ["agent-tool-call-gating", "coding-agent"], "lifecycle_stage": ["read"], "cross_cutting": ["calibration", "abstention", "escalation", "synthetic-rule-generated-labels"]}
evidence_grade: {"directness": "high: measures calibration of both Jev signals on the same decisions, the exact claim", "control": "low: one task, one run, one model version (not stated), bin count not stated, split sizes stated only for ambiguous (80)", "independence": "medium: independent builder, not TypeSafe; no replication; no code or data released", "reproducibility": "low: no code, dataset, question text or Jev version published; labels generated from undisclosed rules", "applicability": "medium: coding-agent tool-call routing (allow, human, block) is close to our gating and routing stages, but a 3-class choice, not memory relevance"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Jev's `confidence` field is worse calibrated than the top-class probability in the same response (calibration error 0.19 vs 0.12 on one 1,200-case task); threshold on the top-class probability, not on `confidence`"]}
claim_correction: Matches the source with two qualifications: the source calls the metric "overall calibration error" with equal-mass bins (the post says ECE; bin count not stated), and it is one task, one day, one unstated Jev version with no code or data released.
---

# Jev ships two confidence numbers; the API hands you the worse one (Harrison Guo)

- **URL:** https://harrisonsec.com/blog/jev-calibration-two-confidence-numbers/
- **Type:** builder writeup (blog)
- **Author / org:** Harrison Guo (harrisonsec.com)
- **Date:** September 28, 2026 (page date)
- **Retrieved:** 2026-09-29 via WebFetch (4 fetches of the page; the fetch tool returns model-extracted text, so quotes below are what the tool returned as verbatim). Jev version: not stated. No local copy.
- **Cited by evidence:** @gzxharrison2079 post https://x.com/i/status/2104635559163613631 ("Its `confidence` field is worse calibrated than the raw probabilities right next to it. ECE 0.19 vs 0.12.")
- **Relevance to a memory stack:** high for any stage that thresholds a Jev `choice` answer (routing, recall gate, write gate): it says which of the two returned numbers to read, and shows overconfidence concentrated on underspecified inputs.

## TL;DR
- 1,200 synthetic coding-agent tool-call decisions, three-way (allow unattended, send to human, block), labels "generated from rules, not hand-written and not scraped".
- Overall calibration error: top-class probability 0.12, the `confidence` field 0.19. "It is worse on every split." Per-split values for the `confidence` field are not given.
- Failure is concentrated on ambiguous inputs (n = 80): accuracy 0.75 at mean confidence 0.89, calibration error 0.28, against 0.09 on clear and 0.17 on trap cases. "Jev handles inputs that are hard because they are adversarial, and stumbles on inputs that are hard because they are incomplete."
- Operating point: "Gating on the max class probability at a threshold of 0.8, Jev handles 65% of the decisions automatically", with "zero blocked commands leaking through".
- Claim correction: the post's "ECE 0.19 vs 0.12" matches the source's "overall calibration error" table; the source gives no bin count, no Jev version, no code.

## What it claims / describes
**Task** (section "What I tested"). "I built 1,200 agent tool-call decisions." "Each one is a tool an autonomous coding agent wants to run, and the job is to classify it." Classes: allow unattended, send to human, block. Three splits: clear (surface reading matches the correct answer), trap (surface reading contradicts the correct answer, adversarial), ambiguous (input genuinely underspecified). "The tasks are generated from rules, not hand-written and not scraped ... It makes the set reproducible. And it makes it provably unseen, so a good calibration score cannot be memorization." Split sizes: ambiguous "the smallest, at 80 cases"; clear and trap sizes not stated.

**What was recorded.** "For each decision I recorded the predicted class, the full probability distribution, and Jev's own `confidence` scalar." The Jev question type, option text, instructions and state are not stated (a 3-option `choice` question is the likely shape, inference).

**Calibration method.** "I used equal-mass bins, because these models pile their confidence up near the top and equal-width bins hide the error there." Number of bins: not stated. "I also computed a noise floor, the calibration error a perfect model would post at this sample size from chance alone." How the floor was computed (simulation or formula): not stated. Whether the metric is ECE with L1 weighting or another variant: not stated beyond "calibration error".

**Main finding** (section "The finding that changes how you use it"). "Jev gives you two numbers you could route on. The `confidence` scalar in its own field. And the probability it assigned to the class it picked. They are not the same number, and they are not equally good." "The field named `confidence`, the one you would reach for first, is the worse signal." "You want the max class probability." What the `confidence` field is computed from (margin, entropy, other): not stated.

**Recommendations** (section "The part that transfers", as extracted): gate on max class probability, generate test sets deterministically, split evaluation by failure type, measure the actual routing signal, report operating points rather than averages.

## Numbers

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| overall calibration error, top-class probability | 0.12 | `confidence` field 0.19 | 1,200 decisions, equal-mass bins | bin count not stated; "ECE" is the post's label |
| overall calibration error, `confidence` field | 0.19 | top-class probability 0.12 | same | "worse on every split"; per-split values not given |
| clear split: accuracy / mean confidence / calibration error / noise floor | 0.96 / 0.88 / 0.09 / 0.02 | | n not stated | which signal the per-split table uses is not stated |
| trap split | 0.91 / 0.77 / 0.17 / 0.04 | | n not stated | underconfident on average (0.77 vs 0.91) |
| ambiguous split | 0.75 / 0.89 / 0.28 / 0.08 | | n = 80 | overconfident; author: "a strong signal to test on your own ambiguous inputs, not as a settled number" |
| automation coverage at max-prob >= 0.8 | 65% of decisions | not stated | 1,200 decisions | "zero blocked commands leaking through"; error rate of automated decisions on allow vs human not stated |

## Mechanism details you could implement
- Read the probability of the chosen option from the `choice` answer's distribution, not the `confidence` scalar, when thresholding.
- Report calibration with equal-mass bins plus a noise floor at your sample size; with n = 80, a calibration error below about 0.08 is indistinguishable from chance on that split (source's floor value).
- Report operating points (coverage at a threshold, leaks of the dangerous class) rather than a single average.
- Split evaluation sets by failure cause (clear, adversarial trap, underspecified); underspecified inputs need separate thresholds or a route-to-human default (inference).
- Generate labelled sets from rules so they are reproducible and unseen (the author's rationale).

## Limitations, caveats, counter-evidence
- Author: "Jev will change. The numbers here are from one model version on one day, on one task." The ambiguous split "is also the smallest, at 80 cases."
- No code, dataset, question text or Jev version released ("None provided in article" per extraction), so the result cannot be rerun.
- Bin count and the exact calibration-error formula are not stated; with equal-mass bins, ECE depends on bin count (inference).
- Rule-generated labels define "correct" by the author's rules; on ambiguous cases the label itself is a convention (inference).
- Per-split table does not say whether it uses top-class probability or `confidence`.
- 0.12 is still a sizable calibration error; neither signal is shown to be calibrated, which reinforces fitting thresholds locally.
- Extraction caveat: my reads went through a fetch tool that paraphrases; numbers were consistent across three fetches.

## Takeaways for tuning a memory stack
- Any code that thresholds a Jev `choice` (routing, recall gate, kind selection) should log and gate on the chosen option's probability and log `confidence` alongside, not instead (consistent with Datadog advice in synthesis section 5 to log raw probabilities).
- Expect overconfidence where the state is underspecified; in memory terms, short or context-free queries at the recall gate and terse turns at the write gate (inference). Evaluate those separately.
- Fit thresholds on our own labelled decisions with equal-mass bins and a noise floor; do not trust vendor calibration claims (B14).
- Related prior notes on Jev calibration exist in the archive (bus-notes: `github-trustifai-typed-evals-jev-calibration.md`, `github-pavelravvich-jev-bench-calibration.md`, `blog-jev-vs-llms-banking77-calibration-cascade.md`); not re-read for this note.

## Open questions
- What is `confidence` computed from, and does the gap hold for `score` answers (e.g. GPT Researcher's usefulness score) and for many-option choices (60 memory ids)?
- Clear and trap split sizes, bin count, Jev version: not stated.
- Leak and error rates per class at 0.8 for the `confidence` field (would it automate less or leak more?): not stated.

## Grading and labels
- Directness: high. Compares the two signals directly on the same decisions.
- Control: low. One task, one run, unstated version and bin count, partial split sizes.
- Independence: medium. Independent builder; no replication; no released artefacts.
- Reproducibility: low. Nothing released.
- Applicability: medium. Coding-agent tool-call gating is close to our routing and gate stages; not a memory relevance task.
- Strength: builder-report.
- Pillars: R9 primary; R4 secondary.
- Memory stage: routing (three-way route: automate, human, block).
- Tags: mechanism calibration-ece, equal-mass-bins, max-class-probability-gate, confidence-field, three-way-routing; workload agent-tool-call-gating, coding-agent; lifecycle read; cross-cutting calibration, abstention, escalation, synthetic-rule-generated-labels.
- Beliefs supports: B14 (vendor calibration claimed not shown; here both signals are miscalibrated, the named `confidence` more so).
- Beliefs contradicts: none.
- Beliefs would_create: gate on the top-class probability, not the `confidence` field (0.12 vs 0.19 on one task).
- Contradiction: none with held beliefs. It narrows synthesis section 5 ("choice and score answers add probabilities and confidence"): the two are not interchangeable, and the named `confidence` is the worse routing signal on this task.

## Origin chain
- @gzxharrison2079 post 2104635559163613631 -> harrisonsec.com blog post (same author, Harrison Guo, inference from handle and byline) -> section "The finding that changes how you use it" (two-row calibration table) and the per-split table.
- Independence: single author, own synthetic dataset, no shared harness or dataset with other Jev notes; not affiliated with TypeSafe as far as stated (affiliation not stated).
- Instruction-bearing content: none found on the page (per fetch extraction).
