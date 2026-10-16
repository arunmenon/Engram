---
schema_version: 1
artifact_id: N-20260928-11
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104218875810185287", "file_id": null, "sha256": null}, {"artifact_id": "post:2104315197942812696", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:vectorize-io/agent-memory-benchmark
claim_cluster: github:vectorize-io/agent-memory-benchmark
feeds: ["memory"]
primary_source: https://github.com/vectorize-io/agent-memory-benchmark
source_commit: 03c1d0f1d27da63034f0931121c858faba512383
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R5", "R3"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["coding-agent memory plugin", "past-decision recall", "corrections loop"], "workload": ["engineering agents", "bug fixing", "Claude Code", "Codex", "opencode"], "lifecycle_stage": ["read", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-task result files for 22 runs are committed in outputs/sdebench", "control": "medium: memory vs no-memory arms on the same 61 tasks, same agents and models, 2 to 3 repeats per arm, but the tasks are planted by the vendor and no intervals are reported", "independence": "low: Vectorize builds both Hindsight and the benchmark, and designed the planted tasks", "reproducibility": "medium: harness and outputs pinned at a commit; task sources under sdebench/datasets are not in the clone (empty directory)", "applicability": "high: coding agents fixing regressions where the needed knowledge is a past developer decision is our PDLC case"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["On coding tasks whose obvious fix fails a hidden test, a recall-on-prompt memory plugin roughly halves the human corrections needed and cuts agent cost by about a quarter to a half (vendor-planted tasks)"]}
claim_correction: The posts list agent-memory-benchmark as one of ten memory repos with no claim; the repo itself carries an unadvertised coding-memory result (sdebench): solve rates are saturated near 100% in every arm, and the measured effect is in corrections needed and cost, not in solve rate.
---

# Agent Memory Benchmark (AMB, Vectorize): sdebench, does memory help a coding agent? Hindsight vs no memory

- **URL:** https://github.com/vectorize-io/agent-memory-benchmark
- **Type:** repo (vendor benchmark harness with committed outputs)
- **Author / org:** Vectorize (makers of Hindsight); licence not visible in the files read
- **Date:** HEAD commit `03c1d0f1d27da63034f0931121c858faba512383` (2026-09-22 14:23:44 +0200, "fix(sdebench): stop redaction crashing runs, read the plugin's diagnostics again (#47)")
- **Retrieved:** 2026-09-28, shallow clone at `repos/agent-memory-benchmark`. Read: README.md, catalog.json, external_results.json (head), sdebench/harness/run.py (header, arms, feedback loop), all 22 `outputs/sdebench/*/coding/boltons.json` headers and per-task `meta` (vanilla-claude-1 is only present gzipped and was not read).
- **Cited by evidence:** @Lummox_eth 2026-09-27 https://x.com/Lummox_eth/status/2104218875810185287 (item "10 Agent Memory Benchmark"); @damkina7 2026-09-27 https://x.com/damkina7/status/2104315197942812696 (same list)
- **Relevance to a memory stack:** high. It is the first committed, repeated memory-vs-no-memory measurement on coding-agent bug fixes we have seen, and its task design ("the obvious fix fails a hidden test; the reason is a past decision") is one of the five tasks we want in our own PDLC memory benchmark.

## TL;DR
- AMB wraps seven datasets behind one ingest/retrieve/generate/judge pipeline (catalog.json): BEAM, LifeBench, LoCoMo, LongMemEval, PersonaMem, PrecisionMemBench and sdebench.
- sdebench (catalog: "Does memory help a coding agent? Bug-fix tasks whose obvious fix fails a hidden test.") runs a real coding agent (Claude Code with Sonnet 5, Codex with gpt-5.4-mini, opencode with Gemini 3.5 Flash) on 61 regression tasks in a Docker sandbox, grades against FAIL_TO_PASS + PASS_TO_PASS + HIDDEN_TO_PASS tests, and on failure feeds the pytest tail back (up to 5 "interventions").
- Solve rate is saturated: 60 or 61 of 61 in every run, memory or not. The difference is in interventions: summed over 61 tasks, no-memory arms needed 49 to 54 (Claude Code), 80 to 83 (Codex), 69 to 76 (opencode); Hindsight arms needed 17 to 25, 25 to 31 and 46 to 50.
- Tasks solved with zero interventions: Codex 3 to 5 without memory vs 35 to 42 with Hindsight; Claude Code 21 to 25 vs 40 to 46.
- Agent cost over the 61 tasks fell from about $33 to $38 to $16 to $18 (Codex) and about $27 to $28 to $19 to $22 (Claude Code); opencode moved less ($35 to $42 vs $32 to $37).
- PrecisionMemBench (77 cases) scores whether the returned belief-id set satisfies every "must" and "must not" assertion, "noise is a hard failure, not an invisible cost" (README).

## What it claims / describes
**Pipeline (README).** Ingest -> Retrieve -> Generate (Gemini) -> Judge (a second Gemini call). "Retrieval time is tracked separately from generation; ingestion time is also recorded." An oracle mode ingests only gold documents. PrecisionMemBench runs `--mode retrieval`: "no answer LLM, no judge, and the score is the fraction of cases whose returned belief-ID set satisfies every assertion."

**sdebench harness (sdebench/harness/run.py docstring):** "Flow: build the repo -> ship the agent the bug report + failing regression test -> run the agent (--agent opencode|claude-code|codex) -> on a failing grade, feed the pytest tail back and resume (the corrections loop, cap --max-interventions) -> capture the SOURCE diff (tests excluded) -> grade in Docker against FAIL_TO_PASS + PASS_TO_PASS + HIDDEN_TO_PASS from pristine copies." "Metrics reported: solved (binary), interventions, turns, wall, tokens, cost". `--max-interventions` default 5 (line 737).

**Arms (run.py `--history` choices).** `full` (vanilla: full repo with git history), `hscoding` (full repo plus memory "via the ACTUAL product integration", the hindsight-coding-agents plugin hooks: Claude Code `UserPromptSubmit` hook, Codex hook, opencode plugin), plus `squashed`, `hindsight`, `memtool`, `inject`, `oracle`, `hybrid`, `index`, `provided`, `conversations`, `skill` (not in the committed outputs read). Vanilla fairness rule (lines 842 to 852): past developer conversations are made reachable to the plain agent (native sessions for opencode, markdown transcripts under `/root/project-history` for the others) but "the prompt does NOT point at them. Whether the agent thinks to look for prior context is exactly the behavior under test [dash] a pointer in the prompt made a strong agent read them every time and collapsed the vanilla/memory gap by design rather than by ability."

**Tasks (per-task `meta` in outputs).** 61 tasks on "boltons" codebases; tiers `planted=52`, `real-function=9`; categories collection-merge 8, filter-rule 9, invariant 9, mapping 9, numeric-policy 9, ordering 8, set-membership 9. Example (boltons-budget-001): bug report "our Retrier retries well past where it should stop ... Restore the intended attempt budget"; the fix is `MAX_ATTEMPTS = 10` -> `7`, a value only a past decision explains.

## Numbers

Per run, summed over 61 tasks (outputs/sdebench/<run>/coding/boltons.json; interventions and cost from `results[].meta`):

| run | memory | agent:model | solved | interventions | zero-intervention tasks | agent cost USD |
|---|---|---|---|---|---|---|
| vanilla-claude-2 | none | claude-code:claude-sonnet-5 | 60/61 | 50 | 24 | 26.33 |
| vanilla-claude-3 | none | same | 61/61 | 49 | 25 | 27.75 |
| full61-cc-none-1 | none | same | 61/61 | 49 | 24 | 27.45 |
| full61-cc-none-2 | none | same | 61/61 | 54 | 21 | 26.90 |
| hindsight-claude-1 | hindsight-coding | same | 61/61 | 24 | 41 | 21.50 |
| hindsight-claude-2 | hindsight-coding | same | 61/61 | 17 | 46 | 19.53 |
| hindsight-claude-3 | hindsight-coding | same | 61/61 | 25 | 40 | 20.78 |
| full61-cc-hs-1 | hscoding | same | 61/61 | 23 | 43 | 20.54 |
| full61-cc-hs-2 | hscoding | same | 61/61 | 17 | 45 | 19.37 |
| vanilla-codex-1/2/3 | none | codex:gpt-5.4-mini | 61, 60, 61 | 80, 83, 83 | 5, 3, 4 | 32.86, 37.65, 35.12 |
| hindsight-codex-1/2/3 | hindsight-coding | same | 61/61 each | 25, 30, 31 | 42, 38, 35 | 15.98, 16.78, 17.67 |
| vanilla-opencode-1/2/3 | none | opencode:google/gemini-3.5-flash | 61/61 each | 74, 76, 69 | 5, 3, 5 | 41.66, 39.52, 34.90 |
| hindsight-opencode-1/2/3 | hindsight-coding | same | 60, 61, 61 | 50, 46, 50 | 19, 20, 19 | 31.77, 32.30, 37.14 |

- Turns summed: Codex 1,781 to 1,869 (none) vs 1,392 to 1,461 (Hindsight); Claude Code 971 to 999 vs 832 to 896; opencode 2,325 to 2,427 vs 2,115 to 2,298.
- Judge: none for sdebench (`judge_llm: null`); grading is the hidden and regression tests.
- Uncertainty: 2 to 4 repeats per arm; no intervals computed in the repo (the spread between repeats is shown above).

## Mechanism details you could implement
- Task design for a PDLC memory benchmark: plant a past decision (a limit, an invariant, an ordering rule) in developer conversations or history, then file a bug whose obvious fix contradicts it; grade with a hidden test that encodes the decision. Seven decision categories above are a ready taxonomy.
- Metric: interventions to a passing hidden test (cap 5), plus tokens and cost across all rounds; solve rate alone saturates.
- Fair baseline: make the history reachable to the no-memory agent but do not point at it, because a pointer "collapsed the vanilla/memory gap by design rather than by ability" (run.py comment).
- Deliver memory through the product's real hook (prompt-submit hook), not a system-prompt append.
- Precision-style retrieval test: per case, assert which belief ids must and must not appear; any extra id fails the case (PrecisionMemBench).

## Limitations, caveats, counter-evidence
- The vendor built the system, the benchmark and the planted tasks (independence low). 52 of 61 tasks are "planted".
- Task definitions (`sdebench/datasets/`) are empty in the clone; only outputs and the harness are present, so task quality could not be read.
- Few repeats and no intervals; opencode shows a smaller and noisier gain (cost overlap between arms).
- vanilla-claude-1 exists only as `.gz` and was not read.
- The benchmark tests recall of a planted decision; it does not test staleness (a decision that was later reversed), which is where memory can hurt (inference).
- No scores for the other AMB datasets were read in this pass beyond PersonaMem external references (arXiv 2504.14225).

## Takeaways for tuning a memory stack
- For engineering agents, measure memory by corrections avoided and cost, not solve rate.
- Include "warn before repeating a failed fix / honour a past decision" tasks with hidden tests in our PDLC benchmark; this harness is a template.
- Add reversed-decision variants so a memory that surfaces stale decisions is penalised (inference).

## Open questions
- Do the gains hold on tasks the vendor did not plant, e.g. the 9 real-function tasks alone?
- How many interventions come from the memory surfacing a wrong or stale decision?
- What does the `memtool`, `inject` and `oracle` arm data look like, if run?

## Grading and labels
- Directness: high, committed per-task outputs. Control: medium, same tasks and agents, repeats, no intervals. Independence: low, vendor-built. Reproducibility: medium, harness pinned, tasks absent. Applicability: high, coding agents and past decisions.
- Pillars: R6 primary (a benchmark and its protocol), R5 and R3 secondary. Memory stage: evaluation. Priority 4 (benchmarks; directly informs the PDLC benchmark scope). Product named: Hindsight.
- Beliefs: would create the belief stated in the frontmatter; nothing in B1 to B25 covers memory's effect on coding-agent corrections.
- Contradiction rows: none.

## Origin chain
- Posts 2104218875810185287 and 2104315197942812696 (listicles naming the repo) -> repo vectorize-io/agent-memory-benchmark@03c1d0f -> `catalog.json`, `README.md`, `sdebench/harness/run.py` lines 1 to 14, 737, 842 to 875, `outputs/sdebench/*/coding/boltons.json` -> this note.
- Independence: Vectorize also produces Hindsight (N-CAT-14, N-20260927-13); shares LongMemEval and LoCoMo with most memory notes; the coding track is new.
