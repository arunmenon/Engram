---
schema_version: 1
artifact_id: N-20260927-16
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103848533908390330", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:shanghua-gao/rsi-jev
claim_cluster: github:shanghua-gao/rsi-jev
feeds: ["decision", "memory"]
primary_source: https://github.com/Shanghua-Gao/RSI-Jev
source_commit: bbcd82bcdcc1781db01f4e6b17edd4d29a914fa8
strength: repo-pinned
pillar_primary: R5
pillar_secondary: ["R6", "R4"]
tags: {"mechanism": ["agent-driven-research-loop", "registered-predictions", "held-out-read-once", "per-question-confidence-head", "general-knowledge-replay"], "workload": ["typed-decisions", "decision-model-training"], "lifecycle_stage": ["train", "evaluate", "promote"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: release record with per-benchmark tables, seeds, held-out table and a list of ~50 arms", "control": "high: four confirmation seeds, a noise bar, and three benchmarks frozen before the search and read once", "independence": "low: one author's loop grading its own releases; two held-out upstreams now private", "reproducibility": "medium: pinned commit, checkpoints with sha256 manifest, loaders pinned to upstream commits; v2.0 replay data not downloadable", "applicability": "medium: the loop's promotion discipline transfers to any self-improving component; the model itself is a Jev-style decision model"}
beliefs_affected: {"supports": ["B15", "B14", "B20"], "contradicts": [], "would_create": ["In an agent-run self-improvement loop, in-domain suite gains can be entirely non-transferable; only a benchmark frozen before the search and read once separates real from selected gains"]}
claim_correction: The post says v2.0 reaches "0.849 vs Qwen3.5-4B's 0.813 on an unseen benchmark" and that "uncertainty calibration did" transfer; the release record shows v2.0 at 0.8492 on that held-out set (SemIf external) is identical to v1.0 (change 0.0000), is flat or worse on all three held-out sets (scienthoon -0.0241), and calibration only "travels, partly" (ECE worse on tasksource, 0.0460 to 0.0888); the "0.79 vs Jev 1.13's 0.73" compares a model trained on typed-decisions' train split with a zero-shot Jev, and the 0.73 is not in the repo at this commit.
---

# RSI-Jev: an agent-run research loop that trains Jev-style decision models (v2.0 release record)

- **URL:** https://github.com/Shanghua-Gao/RSI-Jev (weights: https://huggingface.co/shgao/rsi-jev-v2.0-qwen3.5-2b)
- **Type:** repo
- **Author / org:** Shanghua Gao; loop described as "the next version of AutoScientists" (mims-harvard/AutoScientists). Code MIT, checkpoints Apache-2.0. "Not affiliated with TypeSafe AI."
- **Date:** commit bbcd82bcdcc1781db01f4e6b17edd4d29a914fa8, 2026-09-26 06:57:11 -0400, "BENCHMARKS: seeds scale with the effect, and say which rule v2.0 was judged under (#2)"
- **Retrieved:** 2026-09-27 (shallow clone at repos/rsi-jev). Read: README.md, BENCHMARKS.md, versions/v2.0.md sections 3 to 9, rsijev/targets_suite.py lines 722 to 735.
- **Cited by evidence:** @GaoShanghua 2026-09-26 https://x.com/GaoShanghua/status/2103848533908390330 (backlog, deferred by budget)
- **Relevance to a memory stack:** medium-high for R5/R6. The clearest public example this month of a self-improvement loop that reports its own non-transfer: in-suite +0.096, held-out flat to negative. The promotion discipline (registered predictions, confirmation seeds, a noise bar, a held-out set read once) is the template our H6 and outcome-loop experiments need.

## TL;DR
- The loop: agents "propose the hypotheses, register their predictions before spending GPU time, run the experiments, and retire their own champions when the evidence says to." About 50 arms between v1.0 and v2.0; nine reached a release.
- v2.0 (2B, Qwen3.5 Base tower) trains on the train splits of ten of its twelve suite benchmarks and adds a per-question confidence head. Suite mean 0.7056 vs v1.0 0.609; suite ECE 0.0546 vs 0.0921.
- Held-out benchmarks frozen before the search, read once: tasksource 0.5771 to 0.5761, SemIf external 0.8492 to 0.8492, scienthoon OOD 0.7148 to 0.6907. The record says: "v2.0 is not a better decision model than v1.0."
- Calibration on typed-decisions: confidence >= 0.9 on 539 of 2,000 decisions, 98.3% right; v1.0 reached 0.9 on only 29. Out of distribution, v2.0 is "more confident without being more accurate".
- Claim correction: the post's "unseen benchmark" win and "calibration transferred" are both narrowed by the repo's own held-out table.

## What it claims / describes
**Loop.** Propose, register a prediction, experiment, learn, retire champions. Rules in BENCHMARKS.md: an arm starts at one seed; a gap of about +0.015 or more is confirmed by one fresh seed; smaller gaps get up to three seeds plus a fresh confirmation seed. "The bar is the suite's own noise: +0.006 on the suite mean, no benchmark down by more than its own seed noise, MMLU-Pro within 0.030. Per-seed sd is 0.011 to 0.016 on a single benchmark." The released checkpoint is seed 17, "fixed in advance as primary, not the best of the four". A checkpoint is re-scored from disk and must reproduce per-question predictions exactly. "An arm that clears the bar but fails exactly one guard is not discarded. It gets a diagnosis of the failing metric and a targeted repair."

**Held-out rule.** "Three benchmarks, tasksource, SemIf external and scienthoon OOD, were frozen before this work began and are scored once, after a release model has been chosen, never during the search."

**What the arms established** (README table, verbatim values): v1.0 typed-decisions 0.662; train on the benchmark's train split 0.7794 ("rejected": costs general knowledge); plus 15% general-knowledge replay 0.796 ("the first keeper"); other benchmarks' train splits 1k per source suite 0.6932; 3k per source 0.7049; four fresh seeds 0.7029 (+0.069 confirmed); one global temperature suite ECE 0.1073 ("under-confident on typed-decisions and over-confident out of distribution, so one number cancels out"); per-question confidence head ECE 0.0639; the same forbidden to sharpen score questions ECE 0.0736 (shipped); v2.0 suite 0.7056, ECE 0.0546.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| suite mean (12 benchmarks, weighted) | 0.7056 (seed 17) | v1.0 0.609 | four-seed recipe mean 0.705 | 10 of 12 benchmarks contributed train splits |
| suite ECE | 0.0546 | v1.0 0.0921 | calibrated checkpoint | 0.0893 without the calibration files |
| confirmation | 0.7029 vs 0.6337 (+0.069) | previous champion on same 4 new seeds | "higher on all four" | over 8 seeds +0.0708, MMLU-Pro -0.0272 |
| typed-decisions | 0.7925 | v1.0 0.659 | LocalLLaMA/typed-decisions test, 400 docs, 2,000 decisions | in-domain (train split used) |
| MMLU-Pro 1k | 0.305 | v1.0 0.351 | guard benchmark | fell |
| procedural | 0.6223 | v1.0 0.647 | no train split | fell |
| held-out tasksource | 0.5761 | v1.0 0.5771 | 979 questions, read once | -0.0010 |
| held-out SemIf external | 0.8492 | v1.0 0.8492 | 252 questions | 0.0000; loader lists `qwen3.5_4b_direct: 0.813` as external reference |
| held-out scienthoon OOD | 0.6907 | v1.0 0.7148 | 873 questions | -0.0241 |
| ECE held-out | scienthoon 0.0824 to 0.0599; MMLU-Pro 0.1009 to 0.0399; tasksource 0.0460 to 0.0888 | v1.0 to v2.0 | | worse on tasksource |
| calibration bins (typed-decisions) | >=0.9: 539 at 0.983; 0.7-0.9: 509 at 0.833; 0.5-0.7: 707 at 0.713; <0.5: 245 at 0.518 | v1.0 had 29 decisions >= 0.9 | 2,000 decisions | in-domain |
| act-on-top-x% | 100%: 0.792; 80%: 0.851; 60%: 0.892; 40%: 0.945; 20%: 0.995 | | typed-decisions | |
| speed | ~10 ms per decision; 52 ms to read a document + 11.5 ms per decision on NVIDIA GB10 bf16 | | | |
| training cost | one H100, about 50 min per seed at 2B | | | |

Judge: benchmark labels (teacher modal label for pooled top-1), no LLM judge. Seeds stated.

## Mechanism details you could implement
- Promotion gate for any self-modifying component: registered prediction, a bar equal to measured seed noise (+0.006 suite, per-benchmark sd 0.011 to 0.016), one fresh confirmation seed the arm was never selected on, and guards (a general-ability benchmark within 0.030).
- Keep a held-out set frozen before the search and read it exactly once per release; report it next to the in-suite gain.
- Calibration as a free post-hoc lever: a per-question confidence head that "rescales every answer without changing which option wins"; a single global temperature failed because miscalibration had opposite signs in and out of domain.
- Replay 15% general data when training on in-domain splits to hold back forgetting (30% did not help further).
- Ship a negative-results ledger (EXPLORE.md, ~50 arms and why each failed).

## Limitations, caveats, counter-evidence
- Record's own limitations: "The headline does not generalise." "Its benchmark scores are not zero-shot." "General knowledge got worse." "Procedural decisions got worse." "More confident on unfamiliar documents. Mean confidence rose on every held-out benchmark while accuracy did not, so the calibration gain is a property of the domains the head was fitted on." "Two of the three held-out benchmarks come from upstreams that have since gone private." "One model, one size. 2B only, and one seed's checkpoint."
- The Jev 1.13 typed-decisions figure the post cites (0.73) is not in the repo at this commit; InternLM's Intern-Decision README reports Jev at 73.35% on "Typed Decision" (same 400/2,000 split), which is zero-shot (see `github-internlm-intern-decision.md`).
- The loop is judged by the same author and suite it optimises (inference: selection pressure on the suite is exactly what the held-out table exposes).

## Takeaways for tuning a memory stack
- For any memory component that improves itself from outcomes, report in-distribution gain and a frozen held-out read side by side; expect the first to overstate.
- Calibrate per question type, not globally; check calibration on out-of-distribution data before trusting thresholds there.
- Use a fixed primary seed chosen in advance, and a confirmation seed, before promoting a change.

## Open questions
- Would the loop find transferable gains if the held-out set were used as a stopping signal (and then a new held-out set)?
- How do v2.0's confidence thresholds behave on engineering-agent decisions?

## Grading and labels
- Directness: high. Control: high. Independence: low. Reproducibility: medium. Applicability: medium.
- Strength: repo-pinned. Pillar R5 (self-improvement loop and transfer); secondary R6 (held-out read-once, seed rules), R4 (calibration of a decision model).
- Beliefs: supports B15 weakly (an agent loop with comparative evidence across arms produced promotions, but none transferred); supports B14 (calibration must be fitted and checked locally; it did not fully travel); supports B20 (the post's two headline claims narrow on a primary read). Would create: "in-domain gains from an agent-run loop can be entirely non-transferable; only a frozen, read-once held-out set shows it".
- Contradiction rows: none.

## Origin chain
@GaoShanghua post 2103848533908390330 (quotes 2103572751466312150, v1.0 announcement) -> github.com/Shanghua-Gao/RSI-Jev at bbcd82b -> README arms table, versions/v2.0.md sections 4.1 to 4.3 and 9, BENCHMARKS.md seed rules -> this note. Independence: single author; benchmarks include Jev-style panels and Kev/Nimble sets shared with other open decision-model projects (Kev and SemIf also appear in Intern-Decision's baselines).
