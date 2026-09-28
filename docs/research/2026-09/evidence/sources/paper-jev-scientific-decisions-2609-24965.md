---
schema_version: 1
artifact_id: N-20260927-14
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103817017442607193", "file_id": null, "sha256": null}, {"artifact_id": "post:2103851450719687056", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.24965
claim_cluster: arxiv:2609.24965
feeds: ["memory", "decision"]
primary_source: https://arxiv.org/abs/2609.24965
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["typed-choice-then-code", "three-level-scoring"], "workload": ["scientific-decisions"], "lifecycle_stage": ["decide"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-configuration table of returned, semantic, downstream and label correctness", "control": "medium: twelve configurations on identical packets and code, but a 20-choice development set with a ceiling (six configs at 100%)", "independence": "medium: academic authors (JHU, Columbia, PolyU, Penn State), no vendor affiliation stated", "reproducibility": "low: no code or data link found on the abstract page", "applicability": "medium: the three-level scoring (choice, derived value, final label) maps onto build-time decisions whose intermediate values get reused"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["Final-label accuracy can hide wrong intermediate selections that later steps reuse; evaluate the reused relation, not only the verdict"]}
claim_correction: The post frames the paper as proof that Jev prevents "silent memory poisoning" in "persistent memory buffers" over "multi-day production runs", with a "14% latent divergence rate" and Jev "guaranteeing" joint exactness; the paper never mentions memory, reports 7 wrong selections out of 588 received results on one Choice, and shows Jev tied at 100% with five other configurations; it also names GPT-5.6 Sol and Claude Opus 5, not "GPT-6 Sol" and "Claude Opus 5.5".
---

# Jev for Scientific Decisions: Evaluating Semantic Choices and Their Consequences (arXiv 2609.24965)

- **URL:** https://arxiv.org/abs/2609.24965 (HTML v2: https://arxiv.org/html/2609.24965v2)
- **Type:** paper
- **Author / org:** Boyuan Deng (Johns Hopkins University, corresponding), Shuyi Fan (Columbia University), Hongyang Zhang (The Hong Kong Polytechnic University), Xinhong Xie (The Pennsylvania State University)
- **Date:** v1 2026-09-21, v2 2026-09-23
- **Retrieved:** 2026-09-27 (abstract page and HTML v2)
- **Cited by evidence:** @marfinxx 2026-09-26 https://x.com/marfinxx/status/2103817017442607193 ; reply @EternitiesAI https://x.com/EternitiesAI/status/2103851450719687056 . Backlog cluster (deferred by budget, attempt 1).
- **Relevance to a memory stack:** medium. Not a memory paper. Useful for the evaluation pattern: score the model's semantic choice, the value code derives from it, and the final label separately, because a correct label can ride on a wrong reusable intermediate.

## TL;DR
- Harness: models receive prepared evidence passages, structured records, instructions and candidate meanings; Jev answers via its native Choice interface, other models return candidate ids through a constrained JSON schema; "The shared deterministic program applies the case's computation and claim-assessment rules to produce scientific outputs and a final label."
- 12 configurations x 20 source-grounded Choices in 10 cases x 5 repetitions. Jev 1.13: 50/50 returned, 100/100 semantic, 50/50 downstream, 50/50 label, median 0.335 s, p95 0.442 s, $0.0595 per 1,000. Five other configurations (GPT-5.6 Sol, GPT-6 Astra, Claude Sonnet 5, Claude Opus 5, Kimi K3) are also 100/100 semantic.
- The only semantic errors: 7 wrong selections on one culture-history Choice (Luria and Delbruck 1943), which "changed downstream counts while preserving the correct final label". "Across the 588 received results, all final labels were correct, while 581 downstream outputs were exact."
- **Claim correction (large):** the viral post adds memory poisoning, persistent memory buffers, multi-day runs, a "Deceptive Safety Mask", a "14% latent divergence rate" and a Jev "guarantee"; none of these is in the paper (checked against the HTML). Model names in the post are also wrong.

## What it claims / describes
Scientific workflows often need a semantic choice among known relations (for example, whether observations share a culture) before deterministic arithmetic. The paper evaluates Jev as that semantic component inside a harness that follows TypeSafe's documented guidance: the model only chooses; code does arithmetic and applies claim rules. Three levels are scored separately: semantic selection, downstream output, final claim label.

Culture-history case (verbatim summary from the paper): column 11a contains ten samples from one culture; column 11 contains ten separately grown cultures; reference growth-history counts are (1, 10). The seven wrong selections produced (10, 1) four times, (1, 1) twice and (10, 10) once. All kept the correct final label.

## Numbers

Table 1 (verbatim values):

| model | returned /50 | semantic /100 | downstream /50 | label /50 | median s | p95 s | $ per 1,000 |
|---|---|---|---|---|---|---|---|
| Jev 1.13 | 50 | 100 | 50 | 50 | 0.335 | 0.442 | 0.0595r |
| GPT-5.6 Luna | 50 | 99 | 49 | 50 | 1.509 | 2.753 | 0.2025e |
| GPT-5.6 Terra | 49 | 98 | 49 | 49 | 1.166 | 2.147 | 1.5391e |
| GPT-5.6 Sol | 50 | 100 | 50 | 50 | 1.385 | 2.370 | 3.0470e |
| GPT-6 Astra | 50 | 100 | 50 | 50 | 2.384 | 4.418 | 7.6174e |
| Claude Sonnet 5 | 50 | 100 | 50 | 50 | 2.162 | 5.422 | 4.2502e |
| Claude Opus 5 | 50 | 100 | 50 | 50 | 3.237 | 3.967 | 10.6965e |
| Qwen3.8 Flash | 42 | 83 | 41 | 42 | 14.182 | 34.320 | 0.4013r |
| Qwen3.8 Max 0902 | 50 | 95 | 45 | 50 | 14.236 | 21.393 | 4.8302r |
| DeepSeek V4.1 Flash | 48 | 96 | 48 | 48 | 5.449 | 8.821 | 0.3508r |
| DeepSeek V4 Pro 0813 | 49 | 98 | 49 | 49 | 7.569 | 10.086 | 3.4299r |
| Kimi K3 | 50 | 100 | 50 | 50 | 11.116 | 25.744 | 5.4663r |

The "r" and "e" suffixes on cost are not explained in the fetched text (inference: reported vs estimated cost). n: 20 Choices x 5 repetitions = 100 semantic answers, 50 requests per configuration. Uncertainty: none reported. Judge: deterministic reference labels, no LLM judge.

## Mechanism details you could implement
- Split every decision into (1) a typed semantic choice by a model, (2) deterministic code that derives values, (3) a rule that assigns the final label. Log and evaluate all three.
- Give the model candidate meanings as explicit options, with evidence packets prepared in advance.
- For the evaluation harness: a correct final verdict is not evidence that the intermediate relation (which later steps may reuse or store) was right. Score the reused relation directly.

## Limitations, caveats, counter-evidence
- Paper's own limitations (verbatim): "The comparison uses a development collection of twenty model-routed Choices in ten cases. The same curated English packets recur across repetitions, and six configurations achieve complete correctness. All observed semantic errors concern one Choice. This design characterizes the supplied decisions; evaluating transfer requires new, source-separated cases and broader relation coverage."
- Ceiling effect: six configurations are perfect, so the benchmark cannot rank the top.
- No code or data link found on the abstract page.
- The post's "51x cheaper than GPT-6 Sol and 180x cheaper than Claude Opus 5.5" is arithmetic on Table 1 costs (3.0470/0.0595 = 51.2; 10.6965/0.0595 = 179.8) but with wrong model names.

## Takeaways for tuning a memory stack
- When a decision result is written to memory or reused downstream, evaluate the stored intermediate (the relation, the count), not only the verdict that passed review.
- A decision model can tie frontier LLMs on prepared, closed-option semantic choices at a fraction of the latency; that says nothing about open-ended or memory tasks.

## Open questions
- Which three comparison models made the seven wrong selections? Not stated in the fetched text.
- Would the pattern hold on source-separated cases?

## Grading and labels
- Directness: high, full per-configuration table.
- Control: medium, identical packets and code; tiny ceiling-limited set.
- Independence: medium, academic authors, no vendor tie stated.
- Reproducibility: low, no released code or data found.
- Applicability: medium, the three-level evaluation pattern transfers.
- Strength: paper-single-benchmark. Pillar R4 (typed decision component); secondary R6 (evaluation must check reused intermediates).
- Beliefs: supports B20 (the viral post's headline is almost entirely narrowed or unsupported on a primary read). Would create: "final-label accuracy can hide wrong reusable intermediates; evaluate the reused relation".
- Contradiction rows: none.
- Instruction-bearing: none.

## Origin chain
@marfinxx post 2103817017442607193 (quotes an image link) -> arXiv 2609.24965 abstract -> HTML v2 Table 1, culture-history case, limitations -> this note. Independence: single study; Jev guidance followed by the authors, no TypeSafe affiliation stated.
