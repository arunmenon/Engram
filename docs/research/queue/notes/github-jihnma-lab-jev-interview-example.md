---
schema_version: 1
artifact_id: N-20260930-18
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105133011360711036", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:jihnma/lab-jev-interview-example
claim_cluster: github:jihnma/lab-jev-interview-example
feeds: ["decision"]
primary_source: https://github.com/jihnma/lab-jev-interview-example
source_commit: 9d88b0ec3f199c3f39c873e4ec54164776d6b23b
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R6", "R4"]
memory_stage: evaluation
priority: 1
tags: {"mechanism": ["System One model as judge", "same request to both judges", "fitted decision bar", "samples=1 vs samples=3"], "workload": ["adaptive interview scoring", "Japanese and English", "synthetic applicants"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "low", "reproducibility": "high", "applicability": "low"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Asking Jev three times per judgement (samples=3) changed no decision in 100 cases while doubling calls and tokens"]}
claim_correction: The post reports Jev's speed and ranking quality (4.9 s median, AUC 0.993 vs 0.969). The repository's own analysis shows that at the predeclared bar Jev was less accurate than Claude Haiku 4.5 (62 of 90 correct, 69%, against 68 of 90, 76%), with 28 false hires against 22; Jev is ahead only after the bar is fitted or a second gate is added after the fact.
---

# lab-jev-interview-example (jihnma): Jev (TypeSafe) against Claude Haiku 4.5 as the judge in 100 adaptive interviews

- **URL:** https://github.com/jihnma/lab-jev-interview-example
- **Type:** repo (experiment record)
- **Author / org:** jihnma (individual). No licence file seen at HEAD.
- **Date:** commit read `9d88b0ec3f199c3f39c873e4ec54164776d6b23b` (2026-09-30 12:03:55 +0900, "The judge test: 100 adaptive interviews, Jev against a generative model")
- **Retrieved:** 2026-09-30, shallow clone at repos/lab-jev-interview-example. Read: experiment/logs/analysis.md (every table), experiment/run.py (arms, baseline judge prompt, metering), experiment/answer-guide.md, experiment/analyse.py (header, BAR), brief.md. Not read: the interview program itself (a sibling repository `lab-jev-interview`, not in this clone), spec.json rows, the 100 answer files, per-call logs. Nothing was executed. There is no README at HEAD; analyse.py refers to one.
- **Cited by evidence:** https://x.com/jihnma/status/2105133011360711036 (@jihnma, author). Decision digest of 2026-09-30.
- **Relevance to a memory stack:** medium. It is not a memory workload, but it is a clean same-input judge swap with every call metered, and it shows two things we need for any System One gate: the default threshold was wrong for both judges, and repeated sampling bought nothing.

## TL;DR
- 100 invented job applicants (60 Japanese, 40 English), answers written in advance by a language model from a specification row. An adaptive interview program asks up to 12 of 16 questions; at each turn a judge picks the next question and at the end scores the applicant. Three arms: `baseline` (Claude Haiku via `claude -p`, given the identical JSON request), `jev1` (one Jev call per judgement), `jev` (the same with samples=3).
- Speed: judge seconds per interview, median 4.9 (jev1), 10.13 (jev), 40.38 (baseline). Tokens per interview are about equal for jev1 and baseline (145,075 vs 154,040 median).
- Ranking: AUC over the 90 labelled applicants 0.993 (jev1), 0.992 (jev), 0.969 (baseline).
- Decisions at the predeclared bar of 1.5: baseline 68/90 correct (76%), jev and jev1 62/90 (69%). All errors are false hires; none are false rejects.
- Claim correction: the post quotes the speed and AUC and omits the accuracy at the bar, where Jev is worse.

## What it claims / describes

**Setup (experiment/run.py docstring).** "Nothing in the loop is reimplemented here. The program is imported ... the only thing an arm changes is `app.ask_jev`." Every judge call is metered into experiment/logs/<arm>.jsonl.

**Baseline judge.** `claude -p` with `--model haiku` (BASELINE_MODEL default "haiku"; the post names it Claude Haiku 4.5), no tools, no MCP, one turn, extended thinking off ("with it on, one judgement took 47-103 s and 5,000-9,000 output tokens on the pilot", source uses dashes). System prompt, verbatim start: "You are the judge inside an adaptive interview program. You receive one JSON request with `state` (the job brief as `job_context`, and `answers_so_far`) and `questions`. Answer every question in `questions`, keyed by its name, using only the criteria given." It asks for probabilities for `choice`, `noul` and `score` questions in JSON. Structured output mode failed: "with eleven required objects Haiku never satisfied the schema in five attempts", so the reply is parsed as plain JSON with up to 3 attempts.

**Applicants (experiment/answer-guide.md).** "Every applicant in `spec.json` is invented. Their answers were written by a language model (Claude Sonnet 4.5, via subagents) from the row in `spec.json` ... before any interview ran." Rows vary Java depth, Rust readiness, money-handling experience, alignment with working principles (`aligned`, `mixed`, `conflict`), and answer style (`concrete`, `terse`, `verbose`, `vague`, `persuasive_unsupported`, `irrelevant_drift`). Labels come from a rule over the specification row (hire, reject, borderline, mixed); 90 of 100 carry a hire or reject label.

**Decision rule.** Pass if the weighted total is at least 1.5 (`BAR = 1.5`, commented "interface.json's untuned measurement_boundary"). A second score, `fit`, is reported but not part of the rule.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Judge seconds per interview, median | jev1 4.9; jev (samples=3) 10.13 | Haiku 40.38 | analysis.md, "Resources per interview", n=100 per arm | baseline goes through a CLI process per call |
| Seconds per call (turn / widget / score) | jev1 0.22 / 0.21 / 0.32 | Haiku 2.03 / 1.17 / 5.68 | "Calls by kind" | |
| Total tokens per interview, median | jev1 145,075; jev 322,110 | Haiku 154,040.5 | same | samples=3 more than doubles tokens (+116.9% total) |
| Calls, total over 100 interviews | jev1 2,138; jev 4,460 | Haiku 2,150 | same | |
| Baseline cost | $30.86 for 100 interviews | Jev cost not computed ("-") | same | no dollar comparison in the repository |
| Accuracy at bar 1.5 | jev1 62/90 (69%); jev 62/90 (69%) | Haiku 68/90 (76%) | "Decisions against the labels" | false hires 28 / 28 / 22; false rejects 0 in all arms |
| Accuracy with a post hoc fit gate (total >= 1.5 AND fit >= 1.5) | jev1 80/90 (89%); jev 80/90 (89%) | Haiku 73/90 (81%) | "With a fit gate" | labelled post hoc by the author |
| AUC, total score | jev1 0.993; jev 0.992 | Haiku 0.969 | "Ranking quality", 90 labelled | the figures quoted in the post |
| Fitted bar, leave-one-out accuracy | jev1 84/90 (0.933) at bar 2.49; jev 85/90 (0.944) at 2.48 | Haiku 80/90 (0.889) at 2.685; chance 0.633 | "The bar fitted to the filed decisions" | the fitted bar is about 1.0 above the default for every judge |
| Strong tech, weak culture applicants (label reject) | jev1 0/14 correct; jev 0/14 | Haiku 0/14 | "By applicant type" | every judge passes all 14 at the default bar; Jev's median `fit` for them is 0.03 to 0.04, Haiku's 1.88 |
| Persuasive but unsupported applicants (label reject) | jev1 3/6; jev 3/6 | Haiku 6/6 | same | Jev is more often taken in by fluent answers with no specifics |
| By language | ja: jev1 39/53 (74%), Haiku 42/53 (79%); en: jev1 23/37 (62%), Haiku 26/37 (70%) | | "By language" | |
| Agreement jev vs jev1 | same decision on 100/100; r = 0.999 | | "Agreement between arms" | samples=3 changed nothing |
| Agreement Haiku vs jev1 | same decision on 94/100; r = 0.969 | | same | all 6 disagreements are rejects that Jev passed |
| Repeat stability | 0 decision flips in 12 applicants x 2 runs for both judges; total sd/mean 0.01 (jev), 0.03 (baseline) | | "Repeated interviews" | |
| Haiku with thinking on, 3 applicants | 397.91 to 537.42 judge seconds each against 28.56 to 39.82 | | "baseline-thinking" | |
| Answer length vs level | r = 0.38 for every arm | | "Answer length versus level" | both judges reward length equally |

## Mechanism details you could implement
- Judge swap harness: keep the loop fixed and replace only the judge function; give the generative judge the identical JSON request and ask for a probability per option so both judges return the same shape.
- Meter every call: kind, seconds, bytes, input and output tokens, options offered.
- Fit the decision bar per judge on labelled outcomes and report leave-one-out accuracy; do not carry a threshold from one judge to another.
- Report AUC (threshold-free) and accuracy at the operating threshold side by side; they disagreed here.
- A second dimension as a veto (`fit >= 1.5`) separated the culture-conflict rejects for Jev (fit near 0) far better than for Haiku (fit 1.88).

## Limitations, caveats, counter-evidence
- Synthetic applicants written by one language model from a specification; labels derived from the same specification by rule. The test measures whether a judge recovers the specification, not real hiring validity.
- One job brief, one question plan, 90 labelled cases; a 6-case difference separates the arms at the bar.
- The fit gate and the fitted bar are post hoc on the same 90 cases (the fitted bar has leave-one-out, the gate does not).
- The baseline is one small generative model with thinking off; a stronger model is not tested.
- Jev's dollar cost is not recorded.
- The interview program is in another repository and was not read; how the questions to the judge are worded is unknown here.
- Author-run, single source.

## Takeaways for tuning a memory stack
- A fast typed judge can rank well and still decide worse at a fixed threshold. Any gate we build on a System One score needs its threshold fitted on our labels, per model.
- Do not pay for repeated samples by default: samples=3 cost 2.1x the calls for identical decisions.
- Separate "quality" from "disqualifying" signals into different questions; one weighted total hid a near-zero score on the disqualifier.
- Fluent but unsupported text fooled Jev more than the generative judge in this set (3 of 6 vs 0 of 6 errors); a write gate or evidence grader that reads confident prose should be tested on that failure specifically.

## Open questions
- Does the persuasive-unsupported weakness appear on real text, or is it an artefact of answers written by a model? Unknown.
- What is Jev's cost per interview? Not recorded.
- Would the fitted bars hold on a fresh set of applicants? Not tested beyond leave-one-out.

## Grading and labels
- **Directness: high.** Full analysis tables, run script and per-call logs in a pinned repository.
- **Control: medium.** Same inputs and loop for both judges, a repeat run and a samples ablation; one baseline model, synthetic labels.
- **Independence: low.** One author wrote the task, the applicants' specification, the labels and the analysis.
- **Reproducibility: high.** Pinned commit with answers, logs and scripts; needs the sibling program and API access to re-run.
- **Applicability: low.** Interview scoring, not memory or engineering artifacts; the method transfers, the numbers do not.
- **Strength:** repo-pinned.
- **Pillars:** R9 primary (System One model as the judge at the evaluation stage). Secondary R6 (judge comparison method), R4 (threshold choice). Memory stage: evaluation. Priority 1.
- **Beliefs:**
  - B14 supports: the shipped default threshold (1.5) was far from the fitted one (about 2.5) for Jev; thresholds had to be fitted locally.
  - B13 adjacent: more sampling (samples=3) did not improve decisions.
  - Would create: samples=3 changes no decisions at 2.1x the calls.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/jihnma/status/2105133011360711036 ("Jev: 4.9s median / AUC 0.993; Claude Haiku 4.5: 40.4s / AUC 0.969") -> https://github.com/jihnma/lab-jev-interview-example at 9d88b0e -> experiment/logs/analysis.md sections "Resources per interview", "Decisions against the labels", "Ranking quality" -> this note.
- Independence: single author. Same vendor model (Jev) as the other judge notes on the bus (JEV-as-a-Judge 2609.26550, neosigma, LangChain, Typed Evals); no shared dataset or harness with them.
