---
schema_version: 1
artifact_id: N-20261004-04
artifact_type: note
producer: triage
run_id: triage-20261004T014502Z-25fb
created_at: 2026-10-04T01:52:17Z
input_refs: [{"artifact_id": "post:2104071417612607877", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x-article:2104056839075934208
claim_cluster: x-article:2104056839075934208
feeds: ["decision"]
primary_source: https://x.com/i/article/2104056839075934208
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R6", "R4"]
memory_stage: routing
priority: 2
tags: {"mechanism": ["self-hosted-decision-model", "fine-tuning-on-own-decisions", "teacher-self-agreement-label-filter", "fact-not-opinion-questions"], "workload": ["agent-task-gating"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: first-hand account with numbers, no data or code released", "control": "low: before/after on the same model, test set size and split not stated", "independence": "high: independent hobbyist builder", "reproducibility": "low: repo not published (author offers to publish on demand)", "applicability": "high: fine-tuning a small open decision model on our own agent decisions is exactly priority 2"}
beliefs_affected: {"supports": ["B14", "B20"], "contradicts": [], "would_create": ["Label reliability bounds a fine-tuned decision model: questions whose teacher labels disagree with themselves cannot be learned; filter labels by teacher self-agreement (author uses about 85%) before training"]}
claim_correction: The post says one question "scored worse than a coin flip"; the article shows it was a three-way question at 31% (chance 33.3%), and a second question (model choice) at 29%; the majority-class baseline is not stated
---

# "I Trained a Tiny AI to Judge Everything": a self-hosted decision model fine-tuned on 1,500 own tasks, and why two questions failed (X article, @thatguyinjapan)

- **URL:** https://x.com/i/article/2104056839075934208 (announcing post https://x.com/thatguyinjapan/status/2104071417612607877)
- **Type:** X article (builder writeup)
- **Author / org:** @thatguyinjapan ("American Expat in Japan"), independent builder
- **Date:** 2026-09-27
- **Retrieved:** 2026-10-04 via the fxtwitter mirror API, which returns the full article blocks; version n/a
- **Cited by evidence:** @thatguyinjapan 2104071417612607877
- **Relevance to a memory stack:** high, a first-hand report of fine-tuning an open, local decision model on one's own agent decisions, with the failure mode that matters most for us: noisy teacher labels

## TL;DR
- A small open-source classifier "in that same family" as Jev, fine-tuned on "about 1,500 real tasks from my own sessions, labeled by my own bigger local model", all on one Mac, 40 ms per decision.
- Fact-type questions (needs files? terminal? web? double-check?) reached "78 to 87% accurate" at once.
- Opinion-type questions failed: "How hard is this task?" 31% (three-way), "Which model should handle this?" 29%.
- Fix: decompose difficulty into yes/no fact questions, keep only those where the teacher agreed with itself on 100 tasks (92 to 96% on four; one at 79% was cut). The difficulty flag became "right 81% of the time, on a base rate of 22%".
- The model-choice question was dropped for rules: default local, escalate on the difficulty flag or an actual failure.

## What it claims / describes
Pipeline: a big local model labels each of about 1,500 tasks once; a small open decision model is fine-tuned on those labels; at run time the small model is a "judgment gate" in front of the author's agent (Hermes), served locally, reached by a POST request, described as "harness agnostic". Diagnosis verbatim: "I'd frozen one coin-flip per task and told the small model 'learn this.' It learned the noise perfectly. Noise doesn't generalize." Reformulation: four chat models were asked independently to turn "is this task difficult" into five yes/no questions; three axes converged: "does it need sequential dependent steps? Does it require diagnosis instead of a known procedure? Is 'done' ambiguous?" Then: "before trusting any labels, ask the teacher twice and measure agreement." Rules: "Teacher self-agreement above ~85% or don't bother"; "Beat the dumb strategy or don't ship"; "a mixed-corpus training run made everything worse."

Not stated: the base model's name, test-set size and split, per-question class balance, the fine-tuning recipe, the teacher model.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Fact questions accuracy | "78 to 87% accurate" | not stated | 4 questions, own tasks | test n not stated |
| "How hard is this task?" | "31%" | chance 33.3% (three-way) | single-pass teacher labels | |
| "Which model should handle this?" | "29%" | not stated | | dropped |
| Teacher self-agreement | "92 to 96% agreement on four"; one "79%" | | 100 tasks, asked twice | |
| Difficulty flag after retraining | "right 81% of the time" | "base rate of 22%" | precision of the hard flag | recall not stated |
| Training set | "about 1,500 real tasks" | | own sessions | |
| Latency | "40 milliseconds" | | one Mac | |

## Mechanism details you could implement
- Before fine-tuning on our own decisions, run the teacher twice per item and keep only question types with self-agreement at or above about 85%.
- Rephrase opinion questions as several text-answerable fact questions; combine them with rules.
- Always compare with the majority-class baseline and with a simple rule.
- Route by rules over reliable flags rather than a learned "which model" question; consistent with the bus note blog-jays-local-llm-routers-lost-to-always-medium.md.

## Limitations, caveats, counter-evidence
- No released data, model name or test protocol; numbers are the author's.
- Precision 81% at 22% base rate without recall can hide a flag that rarely fires (inference).
- The "research team" benchmark the author cites is not named in the article.

## Takeaways for tuning a memory stack
- For priority 2 (our own open decision model), label quality is the first risk: measure teacher self-agreement per question before any training.
- Linking and staleness decisions phrased as opinions ("is this relevant?") will likely fail the same way; phrase them as facts ("does B cite A's id?") where possible (inference).

## Open questions
- What base model and how many test items?
- Does the self-agreement filter help Jev zero-shot as well, or only fine-tunes?

## Grading and labels
- Directness: medium. Control: low. Independence: high. Reproducibility: low. Applicability: high.
- Pillars: R9 primary, R6 and R4 secondary. Stage: routing. Priority 2 (open-weight, self-hosted, tuned on own decisions).
- Beliefs: supports B14 (fit locally, do not trust out of the box); supports B20 (headline claims narrow on a primary read, here "worse than a coin flip" is 31% on a three-way); would create a label-reliability belief.
- Contradiction rows: none.

## Origin chain
Post 2104071417612607877, then X article 2104056839075934208 (full text through the mirror API), then the sections "So I asked four AI models the same question" and "The result", then this note. Independence: one builder, own data, own teacher model.
