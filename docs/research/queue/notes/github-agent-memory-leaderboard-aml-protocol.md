---
schema_version: 1
artifact_id: N-20261008-03
artifact_type: note
producer: triage
run_id: triage-20261008T014615Z-49b5
created_at: 2026-10-08T02:01:00Z
input_refs: [{"artifact_id": "post:2105271190143340848", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:AML-memory/agent-memory-leaderboard
claim_cluster: github:AML-memory/agent-memory-leaderboard
feeds: ["memory"]
primary_source: https://github.com/AML-memory/agent-memory-leaderboard
source_commit: 1b8142bfe0f20f1c5218d6b554aa0012de34e504
strength: repo-pinned
pillar_primary: R6
pillar_secondary: ["R10"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["add/search contract", "fixed answer model and judge", "capability taxonomy"], "workload": ["chat memory", "coding memory"], "lifecycle_stage": ["evaluation"], "cross_cutting": []}
evidence_grade: {"directness": "medium: the repo shows the protocol and scoring code; no scores were reachable", "control": "medium: answer and judge pipeline held fixed by design, models are env variables not named in the repo", "independence": "medium: organisers from 20+ institutions, upstream datasets reused", "reproducibility": "low: benchmark data, gold answers and the coding track are private", "applicability": "high: has a coding-memory track (reuse of engineering experience in the same repository)"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A public memory leaderboard pins the reader and judge for all systems, removing the configuration drift that makes vendor LongMemEval and LoCoMo numbers incomparable"]}
claim_correction: none (post describes the categories and the separate open-source and commercial boards accurately; it gives no scores, and none were reachable)
---

# Agent Memory Leaderboard (AML): fixed reader and judge for memory systems, with a private coding-memory track

- **URL:** https://github.com/AML-memory/agent-memory-leaderboard (site: https://agentmemoryleaderboard.ai/)
- **Type:** repo (public evaluation release)
- **Author / org:** "Agent Memory Leaderboard Organizers", "researchers from more than twenty universities and research organizations" (README)
- **Date:** commit 1b8142bfe0f20f1c5218d6b554aa0012de34e504, 2026-08-27 12:15:53 +0800, "Publish public evaluation pipelines"; launched July 29, 2026; first board August 12, 2026
- **Retrieved:** 2026-10-08 (shallow clone at repos/agent-memory-leaderboard; README.md, api_config.py, data/longmemeval-s/pipeline.py read; leaderboard page fetched, no score table in the returned content)
- **Cited by evidence:** @EveryDevAi, https://x.com/EveryDevAi/status/2105271190143340848 (2026-09-30, no link; matched by name and description, inference)
- **Relevance to a memory stack:** high for priority 4. It is the reader-pinned leaderboard the memory trends file predicted, and its coding-memory track is the closest public analogue to a PDLC memory benchmark.

## TL;DR
- Systems expose only Add and Search; AML runs answer generation, judging and aggregation, under "a versioned evaluation contract" (benchmark bundle, pipeline revision, model configuration, scoring rules).
- Textual track: "More than 10 benchmark datasets, over 1,500 histories and tasks, and nearly 5,000 evaluation questions" (PersonaMem, LoCoMo-Refined, CLBench, BEAM, LongMemEval, ScriptMem), mapped to seven capabilities (explicit fact recall; relational and multi-hop; temporal and event understanding; memory governance; personalization; rules and process execution; epistemic safety and privacy).
- Coding track: "12 repositories, 150 base software-engineering tasks, and 1,290 time-constrained historical tasks with fine-grained relevance annotations"; capabilities Debug Memory and Development Memory ("historical architectural decisions"). Unreleased.
- Open-source and commercial products ranked separately. No scores reached this run; whether Mem0, Letta, Zep, supermemory or Hindsight are listed is unknown.

## What it claims / describes
Flow: apply for an AML key, provide Add and Search APIs, pass a compatibility smoke test, run the full suite, review and publish. "All formal results remain private until the evaluation completes and the submission passes leaderboard review." Scores are on a 0-100 scale after normalisation. Comparisons are valid "only when the complete evaluation contract matches". Answer and judge models are supplied as environment variables (`ANSWER_MODEL`, `JUDGE_MODEL`, `JUDGE_VERSION` in api_config.py); which models the public board uses is not stated in the repo. The LongMemEval-S judge returns JSON with label CORRECT or WRONG (data/longmemeval-s/pipeline.py lines 140 to 148). Second cycle "expected to open on September 20, 2026".

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Textual coverage | >10 datasets, >1,500 histories and tasks, ~5,000 questions | | README "Evaluation at a glance" | |
| Coding coverage | 12 repos, 150 base tasks, 1,290 historical tasks | | README | private track |
| System scores | unknown | | leaderboard page returned no table | re-fetch next run |

## Mechanism details you could implement
- Narrow the system under test to Add(history) and Search(query, scope); hold reader and judge fixed; record a contract version with every score. This is directly reusable for our PDLC memory benchmark harness.
- Report a capability profile, not one number; map questions from mixed datasets into a common taxonomy.
- Coding memory framed as time-constrained history: tasks only see engineering history before their timestamp (inference from "time-constrained historical tasks").

## Limitations, caveats, counter-evidence
- No benchmark data, gold answers or model outputs are public; the reader and judge identities are not in the repo, so judge-reader overlap is unknown.
- Search-only interface excludes systems whose value is in assembly or in-loop tool use (inference).
- Scores not obtained this run.

## Takeaways for tuning a memory stack
- Model our PDLC benchmark harness on the Add/Search plus fixed-reader contract; borrow the coding-memory framing (debug memory, development memory) for "warn before repeating a failed fix" and "recall the decision behind a design".
- Consider submitting our stack to AML's coding track as an external check (inference).

## Open questions
- Which answer and judge models are pinned? Who is on the board, and with what capability profiles?
- Will the coding track's tasks or annotation schema be released?

## Grading and labels
- Directness medium; control medium; independence medium; reproducibility low; applicability high.
- R6 primary (memory benchmarks), R10 secondary. Memory stage: evaluation. Priority 4.
- Would create: reader-pinned leaderboard belief in frontmatter. Bears on the memory trends prediction "A reader-pinned memory leaderboard appears" (appears to be met, pending scores).
- No contradiction rows.

## Origin chain
post x:2105271190143340848 (@EveryDevAi, no link) -> GitHub search "agent memory leaderboard" -> github.com/AML-memory/agent-memory-leaderboard at 1b8142b -> README sections "Evaluation at a glance", "A controlled evaluation protocol", api_config.py -> this note. Independence: reuses public datasets (LongMemEval, LoCoMo, BEAM, CLBench, PersonaMem); several third-party baseline repos exist (for example richrichgo/aml-memory-baseline), not read.
