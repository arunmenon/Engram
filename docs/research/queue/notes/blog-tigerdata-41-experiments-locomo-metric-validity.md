---
schema_version: 1
artifact_id: N-20260929-12
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104607854443499540", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:tigerdata.com/blog/41-experiments-6-days-what-human-was-for
claim_cluster: url:tigerdata.com/blog/41-experiments-6-days-what-human-was-for
feeds: ["memory"]
primary_source: https://www.tigerdata.com/blog/41-experiments-6-days-what-human-was-for
source_commit: n/a
strength: builder-report
pillar_primary: R6
pillar_secondary: ["R5", "R3"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["agent-driven-experiment-loop", "grep-plus-ranked-search", "fact-extraction-ablation", "postgres-memory-store", "mcp-tools"], "workload": ["chat-memory-qa"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["label-leakage", "run-to-run-noise", "cost"]}
evidence_grade: {"directness": "medium: F1 trajectory and phase deltas are reported, but per-change F1 for each human intervention is not isolated", "control": "low: single conversation sample of about 200 questions, run-to-run spread about 0.04, and a declared measurement break inside the headline trajectory", "independence": "low: vendor (Tiger Data) blog about its own Postgres-based harness", "reproducibility": "low: harness of about 1,400 lines of TypeScript, no repository link given", "applicability": "medium: the metric-validity failure modes (label leak in prompt, metric counting the wrong unit) apply directly to our PDLC benchmark harness"}
beliefs_affected: {"supports": ["B19", "B20", "B5"], "contradicts": [], "would_create": ["On LoCoMo, a single-conversation quick eval of about 200 questions has about 0.04 F1 run-to-run spread, larger than most single-change gains in an agent-driven experiment loop, so per-change decisions need repeats or a larger sample"]}
claim_correction: The 0.392 to 0.666 headline crosses a declared measurement break (the article says numbers after it are not comparable to numbers before it); the honest-eval step moved F1 by -0.017, the largest gain (+0.131) came from plumbing (MCP tools made non-deferred), only 2 of the 4 human interventions were scoring fixes, and all figures come from a single-conversation sample of about 200 questions with about 0.04 run-to-run spread (raw F1 0.638).
---

# Tiger Data: 41 experiments in 6 days on LoCoMo, and what the human was for

- **URL:** https://www.tigerdata.com/blog/41-experiments-6-days-what-human-was-for
- **Type:** vendor blog (builder writeup)
- **Author / org:** Matvey Arye, Tiger Data (TimescaleDB)
- **Date:** 2026-09-28
- **Retrieved:** 2026-09-29, commit n/a (web page; read through 4 WebFetch passes, which returned short quotes and summaries, not full text; quotes below are as returned)
- **Cited by evidence:** https://x.com/TimescaleDB/status/2104607854443499540 (@TimescaleDB, 2026-09-28)
- **Relevance to a memory stack:** medium-high for R6 and priority 4. A concrete account of how an agent-driven eval loop on LoCoMo adopted measurement artifacts, with a noise floor figure; weak as evidence about memory mechanisms.

## TL;DR
- Claude (via Claude Code CLI, MCP tools, Postgres store) ran 41 experiments in 6 days: "17 adopted and 24 reverted, 108 eval runs", about 85 commits, about 1,400 lines of TypeScript. LoCoMo F1 went 0.392 to 0.666; "Raw F1 landed at 0.638, against a previous published best of 0.598".
- The four human interventions: (1) prompt leaked the question category (answer key), removing it cost temporal accuracy (scoring fix, -0.017 phase); (2) the recall metric counted dialogue turn ids, which facts lack, so an apparent gain was an artifact (scoring fix, prevented a false adoption, 0 F1 change); (3) ablating Haiku fact extraction showed zero F1 contribution, and removing it sped ingestion 50% (system change); (4) a human reordered four hypotheses and the new top pick, grep combined with ranked search, was "the largest win of that round" (system change, prioritisation).
- Noise floor: "three runs on unchanged code producing a range of 0.606 to 0.645"; quick evals use "~200 questions, single conversation sample".
- Claim correction: measurement fixes did not raise the score; they lowered it (-0.017) or blocked a fake gain. The rise is mostly plumbing (+0.131) and prompting (+0.097). The headline spans a declared comparability break.

## What it claims / describes
- **Setup.** A memory harness on Postgres exposed as MCP tools; Claude Code wrote nearly all code and ran every experiment; each eval run took 5 to 7 minutes. The thesis: fast loops make bad objectives dangerous; the human's role is to ask whether the metric measures what it claims ("The agent rows. You steer.", post).
- **Trajectory by phase** (section "What the trajectory actually shows", as returned by the fetch tool):
  1. Removing friction, +0.131 (0.392 to 0.523): "unglamorous plumbing: making the MCP tools non-deferred".
  2. Structuring ingestion, +0.039 (0.523 to 0.562): "Fact extraction, speaker trees, prev/next linking".
  3. Prompting, +0.097 (0.562 to 0.659): "Speaker attribution checks, grep regex, unlimited tool calls".
  4. Making eval honest, -0.017 (0.659 to 0.642): "Removing the category hint from the prompt cost us temporal accuracy".
  5. Changing what the agent sees, +0.024 (0.642 to 0.666): "Drop facts, index image captions, speaker-first tree filtering".
  The deltas sum exactly to 0.392 to 0.666. The article marks a break: "Numbers after this line are not comparable to numbers before it."
- **The four interventions, labelled:**

| # | Intervention (article heading or quote) | Type | Effect on F1 |
|---|---|---|---|
| 1 | "The prompt was reading the answer key." Category hint removed | scoring / eval validity | part of the -0.017 phase |
| 2 | "The recall metric could not measure the thing it reported." Metric counted dialogue turn ids | scoring / eval validity | blocked adoption of an artifactual gain; F1 delta not stated |
| 3 | "Expensive did not mean valuable." Haiku fact extraction ablated: zero F1, added search noise, 50% slower ingestion | memory system | part of the +0.024 phase ("Drop facts") |
| 4 | "A human reordered them, and the reordered top pick, forcing grep to combine with ranked search, turned out to be the largest win of that round." | memory system (prioritisation) | round gain not isolated in what I read |

- So, of 0.392 to 0.666 (+0.274), measurement changes account for -0.017 (plus an avoided false gain of unknown size), and system changes for the rest. The biggest single phase was not one of the four human interventions (inference from the phase list).

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| LoCoMo F1 (headline) | 0.666 | 0.392 at start | "~200 questions, single conversation sample" | crosses a declared measurement break |
| Raw F1 | 0.638 | "previous published best of 0.598" | same | whose 0.598 is not named; relation of 0.638 to 0.666 not explained in what I read |
| Run-to-run spread, unchanged code | "0.606 to 0.645", "0.04 between identical runs" | | three runs | larger than 3 of the 5 phase deltas |
| Experiments | 41 in 6 days; "17 adopted and 24 reverted, 108 eval runs" | | | about 85 commits, about 1,400 lines TypeScript |
| Phase deltas | +0.131, +0.039, +0.097, -0.017, +0.024 | | see phases above | each phase bundles several changes |
| Fact extraction ablation | zero F1; ingestion 50% faster without it | with Haiku extraction | | F1 numbers of the ablation not stated |
| Eval time | 5 to 7 minutes per run | | | |

- F1 computation (token F1 vs LLM judge), the answering model and any judge model: not stated in what I read. LoCoMo categories used: not stated; the category-hint fix implies categories were visible to the prompt before the fix.

## Mechanism details you could implement
- Eval hygiene checks that caught real problems: strip benchmark metadata (category labels) from anything the system under test can read; check that a retrieval metric's unit (turn ids) exists in the thing being retrieved (facts).
- Ablate expensive ingestion steps (LLM fact extraction) before keeping them: here zero F1 and 50% slower ingestion.
- Retrieval: combine grep (regex/exact) with ranked search in one tool path; speaker-first tree filtering; index image captions (details not given).
- Noise floor: three repeats of unchanged code gave a 0.039 range, so require gains above that or run more repeats (matches synthesis section 6 "Noise floor").

## Limitations, caveats, counter-evidence
- Single conversation, about 200 questions, as stated; not the full LoCoMo. Not comparable with published LoCoMo numbers computed on the full set (inference).
- No repository link; harness not public in what I read.
- Answering and grading models not named; F1 definition not stated.
- Vendor blog promoting Postgres as a memory store.
- Phase deltas bundle several changes; the four interventions are not individually quantified except as noted.
- Several phase gains (+0.039, +0.024, -0.017) are within the stated 0.04 run-to-run spread.

## Takeaways for tuning a memory stack
- Before trusting any gain on our PDLC benchmark, run a label-leak audit of prompts and a unit audit of each metric (both happened here and match our own V1 to V8 leak catalogue, B19).
- Set a noise floor per benchmark slice with at least three repeats; on about 200 questions expect about 0.04 F1 spread.
- LLM fact extraction at ingestion earned nothing here; keep raw text plus good retrieval as the baseline arm (consistent with B5 and B16's direction).
- Tool plumbing (non-deferred tools, unlimited tool calls) moved F1 more than memory design did; hold harness plumbing fixed when comparing memory arms.

## Open questions
- How is F1 computed and which models answer and grade?
- What is 0.666 versus raw 0.638?
- Full-LoCoMo result for the final configuration?
- Size of the artifactual recall gain that was blocked.

## Grading and labels
- Directness: medium, phase deltas reported, interventions not isolated.
- Control: low, one conversation, about 200 questions, 0.04 spread, measurement break mid-trajectory.
- Independence: low, vendor self-report.
- Reproducibility: low, no repo link.
- Applicability: medium, the eval failure modes transfer to our harness.
- Strength: builder-report.
- Pillars: R6 primary; R5, R3 secondary.
- Memory stage: evaluation.
- Tags: agent-driven-experiment-loop, fact-extraction-ablation, grep-plus-ranked-search; label-leakage, run-to-run-noise.
- Beliefs: supports B19 (label leakage in prompts is a real, recurring eval failure), supports B20 (the headline narrows on a primary read), supports B5 in direction (an LLM summarising/extraction step gave zero F1; ingestion-time, not scheduled consolidation); would create a noise-floor belief for small LoCoMo samples.

## Origin chain
- post https://x.com/TimescaleDB/status/2104607854443499540 -> https://www.tigerdata.com/blog/41-experiments-6-days-what-human-was-for -> sections "Fast loops make bad objectives dangerous", "The division of labor that emerged", "What the trajectory actually shows", "Why the store was Postgres", "Run this yourself".
- Independence: post and blog are by the same vendor; no third-party replication; LoCoMo cited as arXiv 2402.17753.
