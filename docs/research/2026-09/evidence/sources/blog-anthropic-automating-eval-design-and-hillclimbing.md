---
schema_version: 1
artifact_id: N-20261001-10
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105190807397445746", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:claude.dev/blog/automating-eval-design-and-hillclimbing
claim_cluster: url:claude.dev/blog/automating-eval-design-and-hillclimbing
feeds: ["decision"]
primary_source: https://claude.dev/blog/automating-eval-design-and-hillclimbing/
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R5"]
tags: {"mechanism": ["random train/test split for hillclimbing", "grader consistency check", "code graders vs LLM judge with checkable claims", "task sampling from production"], "workload": ["customer support tickets", "API skill evaluation"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: describes the tooling and reports outcome numbers, without per-case data", "control": "medium: held-out test split reported for one example (90.5 vs 78.6), baseline stated", "independence": "low: vendor describing its own tooling and models", "reproducibility": "low: datasets not released", "applicability": "high: our harness hillclimbs prompts and policies against our own eval set"}
beliefs_affected: {"supports": ["B19", "B20"], "contradicts": [], "would_create": ["An automated hillclimber must split train and test at random, never see test failures, and report the train-test gap; on one support benchmark the train score reached 98.9% while held-out test was 90.5%"]}
claim_correction: none (the post's six practices are a fair summary; it omits the reported numbers)
memory_stage: evaluation
---

# Automating eval design and hillclimbing (Anthropic, claude.dev blog, Lance Martin, 2026-09-28)

- **URL:** https://claude.dev/blog/automating-eval-design-and-hillclimbing/
- **Type:** vendor blog
- **Author / org:** Lance Martin, Anthropic
- **Date:** 2026-09-28
- **Retrieved:** 2026-10-01 (blog page via WebFetch)
- **Cited by evidence:** @tutao0123, 2026-09-30, https://x.com/tutao0123/status/2105190807397445746 ("6 practices before you trust a hillclimb on your agent eval")
- **Relevance to a memory stack:** high for evaluation discipline. We tune memory policies and prompts against our own eval set; this is a vendor's checklist for doing that without fooling ourselves, with one held-out number showing the train-test gap.

## TL;DR
- Build eval tasks that "mirror production": sample from production traffic, bug reports or tickets, and from cases humans judged hard; do not sample only today's model failures (that "can measure a model's failure fingerprint rather than intrinsic difficulty").
- Graders: programmatic checks for constrained outputs (exact match, fixed labels, schema, passing tests); LLM-as-judge only for open-ended outputs, with "a rubric written as checkable claims"; read a sample of scored transcripts "before believing your evaluator".
- Diagnostics: run the grader twice on the same output and report verdict changes; flag when baseline exceeds about 95%.
- Hillclimbing: random train/test split; "if the train set scores improve while the test set scores stay flat, then that is a common overfitting warning sign"; "Never paste failures into the prompt"; "Keep the answers structurally out of the model's reach".
- Example: support benchmark from 74.4% at 4.6 cents per ticket (Opus 4.8, high effort) to 88.9% at 1 cent (Sonnet 5, low effort), then 98.9% with prompt improvements; held-out test 90.5% vs baseline 78.6% at one-fifth the cost.

## What it claims / describes
Two commands in the claude-api tooling: `build-eval` (proposes tasks and graders) and a hillclimber (iterates prompts or configurations against the eval). The post describes the checks the tooling runs automatically: grader repeatability, infrastructure reliability, ceiling warnings, and the automatic random split into train (visible to the hillclimber) and test (never seen).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| support accuracy after model/effort change | 88.9% at 1 cent/ticket | 74.4% at 4.6 cents (Opus 4.8, high effort) | customer support benchmark | n not stated |
| support accuracy after prompt hillclimb | 98.9% | 88.9% | same, train side (inference: the 98.9% is not labelled held-out) | |
| held-out test | 90.5% | 78.6% | same, test split | about one-fifth the cost |
| claude-api skill eval | 87.9% after 24 rounds | 66% | adding docs sections, fixing type tables, correcting task specs | some gains came from fixing task specifications, i.e. the eval itself |

## Mechanism details you could implement
- Split once at random before any tuning; the tuner reads train only; report train and test after every round and stop on a widening gap.
- Grader repeatability check: grade each output twice; report the flip rate.
- Ceiling check: if the baseline is above about 95%, the eval cannot show improvement.
- Prefer code graders whenever the output is constrained; for LLM judges, write rubrics as checkable claims and never let the system under test grade itself.

## Limitations, caveats, counter-evidence
- Vendor post about its own tooling and models; datasets, n and per-case results are not published.
- The 98.9% vs 90.5% gap (inference: train vs held-out) is itself the overfitting warning the post describes.
- Part of the claude-api skill gain came from "correcting task specifications", which changes the eval and the score together.

## Takeaways for tuning a memory stack
- Our harness (B19: labels leaked before) should enforce the random train/test split and the "never paste failures into the prompt" rule mechanically, not by convention.
- Add grader flip rate and a ceiling check to every eval report.
- When a tuning round edits the eval's task specs, re-baseline before comparing.

## Open questions
- What is the size of the support benchmark and its split?
- How often did the hillclimber's train-test gap trigger a stop in practice?

## Grading and labels
- **Directness: medium.** **Control: medium.** **Independence: low.** **Reproducibility: low.** **Applicability: high.**
- **Pillars:** R6 primary (whether a tuning result supports its conclusion); R5 secondary (automated improvement loop). **Memory stage:** evaluation.
- **Beliefs:** supports B19 (leakage through the tuner is a known failure; the tool keeps answers out of reach); supports B20 (headline numbers narrow on the held-out split: 98.9 vs 90.5). **Contradictions:** none.

## Origin chain
Post @tutao0123 2105190807397445746 (2026-09-30) -> claude.dev blog post (2026-09-28) -> sections on task sampling, graders, diagnostics, hillclimbing safeguards, documented results -> this note. Independence: vendor's own report; no external replication.
