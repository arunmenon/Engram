---
schema_version: 1
artifact_id: N-20260927-18
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103749643385631010", "file_id": null, "sha256": null}, {"artifact_id": "post:2103749860705054861", "file_id": null, "sha256": null}, {"artifact_id": "post:2104075442487697647", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:kyu1204/jgrep
claim_cluster: github:kyu1204/jgrep
feeds: ["decision"]
primary_source: https://github.com/kyu1204/jgrep
source_commit: 89026fbe3c42f170b86c21bf40ce67cbc7041e40
strength: repo-pinned
pillar_primary: R3
pillar_secondary: ["R4"]
tags: {"mechanism": ["code-first-cascade", "per-file-noul", "diff-compaction", "predictive-test-selection"], "workload": ["coding-agent", "CI", "diff-review"], "lifecycle_stage": ["read", "select"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-commit rows for 60 commits with recall, code-only recall, selection size, tokens, cost and time", "control": "medium: code-only layer is a real ablation baseline; no random-at-same-budget or embedding baseline; ground truth is a proxy (tests the author edited)", "independence": "low: author-run on author-chosen repos", "reproducibility": "high: pinned commit, script bench/tests/run.ts, raw JSONL rows per repo, commit filter described", "applicability": "high: selecting which artifacts a code diff affects is a build-time read over engineering artifacts"}
beliefs_affected: {"supports": ["B9"], "contradicts": [], "would_create": ["For diff-conditioned selection over engineering artifacts, a cheap code layer (name and import match) plus one yes/no decision per remaining candidate roughly doubles recall over the code layer alone at about 12% selection"]}
claim_correction: Posts say "92% recall"; the ground truth is the test files each commit's author edited (a proxy for affected tests), recall is 0.919 over 60 commits with per-repo means from 0.861 to 1.000, and the "extra" selected tests are not scored as false positives.
---

# jgrep --tests: predictive test selection with code rules first and one Jev Noul per remaining test file

- **URL:** https://github.com/kyu1204/jgrep
- **Type:** repo
- **Author / org:** kyu1204 (posting as @MINTr5dw). Powered by TypeSafe Jev (`jev-latest`).
- **Date:** commit 89026fbe3c42f170b86c21bf40ce67cbc7041e40, 2026-09-25 01:37:06 +0900, "tests: type-test file suffixes (.tst.ts, .test-d.ts) and benchmark link (#9)"; benchmark run dated 2026-09-23, jgrep 0.4.0
- **Retrieved:** 2026-09-27 (shallow clone at repos/jgrep). Read: README.md (test-selection section), bench/tests/README.md (method, all 60 rows, summary, misses).
- **Cited by evidence:** @MINTr5dw https://x.com/MINTr5dw/status/2103749643385631010 and https://x.com/MINTr5dw/status/2103749860705054861 ; +1 thread post 2104075442487697647. Backlog cluster (deferred by budget). The @FederCr jevos post in the same pre-cluster is a separate claim (see triage log).
- **Relevance to a memory stack:** high on applicability. The same shape as our build-time read: given a diff, which stored artifacts (tests, specs, ADRs) are affected? A code layer first, a typed yes/no per candidate second.

## TL;DR
- Three layers, cheapest first: tests named after a changed file, tests importing a changed module (both in code), then "one Noul per file" asked of Jev with "the compacted diff (source files only, changed lines only) and each test file's imports and test names". Threshold 0.5 "because a missed test costs more than an extra one".
- 60 commits across hono, zod, fastify, flask, requests: mean recall 0.919 vs 0.432 for the code layer alone; mean selection ratio 0.116; total cost $0.1115; mean 1.08 s per commit.
- Local 142-file TypeScript suite, 3 commits: 47 files selected (12 by name, 27 by import, 8 by Jev), 536 of 1,420 test cases, 12.6 s vs 18.9 s full suite; selection itself 7 requests, 56k tokens, $0.0024, 1.0 s.
- Misses are broad, whole-library test files that match no single source file by name, which Jev scored below 0.5.

## What it claims / describes
Benchmark method (bench/tests/README.md): for each repo, the 12 most recent non-merge commits that touch at least one non-test source file and one test file, diff under 60 KB. Ground truth G = test files the commit modified or added (still existing). Those test files are reverted to their parent state before scoring, "This stops a commit's own test-file edits from trivially self-selecting". Run `jgrep --tests C~1 --all --json --no-cache`; selected S = entries with p >= 0.5. recall = |G and S| / |G|; code-only recall uses only `direct` and `import` reasons; "extra" = selected tests not in G, "not necessarily wrong". Runs happen in a scratch git worktree; invalid runs are retried once then skipped.

## Numbers

| repo | n commits | mean recall | mean code-only recall | mean selection ratio | total cost | mean seconds |
|---|---|---|---|---|---|---|
| hono | 12 | 1.000 | 0.917 | 0.098 | $0.0296 | 1.14 |
| zod | 12 | 0.899 | 0.269 | 0.190 | $0.0368 | 1.13 |
| fastify | 12 | 0.958 | 0.208 | 0.122 | $0.0341 | 1.15 |
| flask | 12 | 0.875 | 0.350 | 0.109 | $0.0074 | 1.03 |
| requests | 12 | 0.861 | 0.417 | 0.060 | $0.0036 | 0.92 |
| all | 60 | 0.919 | 0.432 | 0.116 | $0.1115 | 1.08 |

Max tokens per commit about 97k (zod), under a 300k cap. Model: `jev-latest` (CLI does not echo the served version). Uncertainty: none reported; single run per commit. Judge: none (set overlap).

## Mechanism details you could implement
- Cascade: deterministic matches first (name stem, import graph), model only for the remainder.
- Compact the state: changed lines of source files only; for each candidate, only its imports and test names.
- One Noul per candidate in a batched request; threshold set by the cost asymmetry (0.5 here because misses cost more).
- Evaluate against a proxy ground truth with self-selection removed (revert the commit's own edits to the candidate set before scoring).

## Limitations, caveats, counter-evidence
- Ground truth is "tests the author touched", which undercounts affected tests; precision is not measured ("extra" not scored).
- No baseline at the same selection budget (random 12%, embedding similarity, or an LLM).
- Misses cluster on broad test files (zod assignability, JSON schema, bundle size; flask test_basic; requests test_requests), i.e. candidates whose relevance is global rather than local.
- Author-chosen repos; recency filter; single run.

## Takeaways for tuning a memory stack
- For "which stored artifacts does this change touch?", run cheap structural links first and ask a typed yes/no only for the rest; here that took recall from 0.43 to 0.92 at about 12% selection and cents per 60 commits.
- Expect the model to under-select global artifacts (architecture docs, cross-cutting ADRs are the analogue, inference); pin those with rules.
- Measure with self-selection removed.

## Open questions
- Recall at matched selection budget against embeddings or BM25 over test names?
- Precision of "extra" selections against actually failing tests?

## Grading and labels
- Directness: high. Control: medium. Independence: low. Reproducibility: high. Applicability: high.
- Strength: repo-pinned. Pillar R3 (diff-conditioned evidence selection within a budget); secondary R4 (decision-model gate and threshold by error cost).
- Beliefs: supports B9 loosely (a cheap, bounded selection rule keeps recall high at a small fraction of candidates; not a sufficiency stop rule as such). Would create: code layer plus per-candidate yes/no roughly doubles recall over code alone for diff-conditioned artifact selection.
- Contradiction rows: none.

## Origin chain
@MINTr5dw replies to @typesafeai (2103749643385631010, 2103749860705054861) -> github.com/kyu1204/jgrep at 89026fb -> README "--tests" section and bench/tests/README.md summary table -> this note. Independence: single author, single run; Jev is the only model tested.
