---
schema_version: 1
artifact_id: N-20260927-09
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103920741481848861", "file_id": null, "sha256": null}, {"artifact_id": "post:2103924691220181385", "file_id": null, "sha256": null}, {"artifact_id": "post:2103923124219810106", "file_id": null, "sha256": null}, {"artifact_id": "post:2103927694295769184", "file_id": null, "sha256": null}, {"artifact_id": "post:2103922958922359267", "file_id": null, "sha256": null}, {"artifact_id": "post:2103926030545441182", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:dzhng/jevgrep
claim_cluster: github:dzhng/jevgrep
feeds: ["decision", "memory"]
primary_source: https://github.com/dzhng/jevgrep
source_commit: 762028fa076d2d823235d74e5687bea5d070e4c5
strength: repo-pinned
pillar_primary: R3
pillar_secondary: ["R6"]
tags: {"mechanism": ["hierarchical directory traversal", "decision-model file and declaration selection", "reading leads without excerpts", "no fixed top-k"], "workload": ["SWE-bench (10-task tuned Python subset)", "coding agent context collection"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: paired per-task cost and solve outcomes with receipts", "control": "medium: frozen runtime, byte-identical repeat, independent audit of 273 checks; but baseline run once, n=10, and Jev cost excluded from scored cost", "independence": "low: author-run evaluation on an author-tuned subset", "reproducibility": "high for records: pinned commit, plan hash and aggregate SHA-256 recorded; many evidence files point to /tmp paths not in the repo", "applicability": "high: context collection for a coding agent over a repository, our core read workload"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["Decision-model context selection for a coding agent cut model spend 27 to 41% on a 10-task subset but lost 1 of 8 baseline solves in both cohorts"]}
claim_correction: post says jevgrep "reduces your coding agent cost by 40% (verified on SWE-bench)"; the repo says one ten-task tuned SWE-bench subset repeat, Sol cost $7.62 to $4.52 (40.7%) with Jev cost excluded, solve rate 7/10 vs 8/10 baseline, and both cohorts failed the original quality gate; the first cohort saved 27.3% at 6/10
---

# jevgrep: a Jev-driven research CLI for coding-agent context collection (dzhng/jevgrep)

- **URL:** https://github.com/dzhng/jevgrep
- **Type:** repo
- **Author / org:** David Zhang (@dzhng); npm `@dzhng/jevgrep`, CLI `jg`
- **Date:** release 0.3.0
- **Retrieved:** 2026-09-27, commit `762028fa076d2d823235d74e5687bea5d070e4c5` (2026-09-26 14:45:10 -0700, "chore: release 0.3.0"); local copy repos/jevgrep. Read: README.md, docs/architecture.md, docs/exploration.md, specs/done/jevgrep/assets/variance-repeat.md.
- **Cited by evidence:** @dzhng https://x.com/dzhng/status/2103920741481848861 and https://x.com/dzhng/status/2103923124219810106 ; @transitive_bs https://x.com/transitive_bs/status/2103924691220181385 ; replies 2103927694295769184, 2103922958922359267, 2103926030545441182
- **Relevance to a memory stack:** high as a worked example of decision-model-driven context selection over a code repository, and as an unusually honest evaluation record that narrows its own headline.

## TL;DR
- `jg "<question>" <root>` walks the directory tree; Jev classifies directories (names, metadata), files (content fragments) and declarations; returns a summary, file locations, reading leads and selected source with line references. No fixed top-k: "Keep every file that passes relevance criteria".
- Measured: one ten-task tuned Python SWE-bench subset with the Sol model. Repeat cohort: full Sol cost $7.6220690 -> $4.5195532 (40.70%), solves 7/10 vs 8/10 saved baseline. First cohort: $5.5410776 (27.30%), 6/10.
- "This is a cost reduction with a quality tradeoff, not evidence of equal or better solve quality." Both cohorts failed the original gate (preserve every baseline solve).
- Jev charges are excluded from scored cost; the repeat's known Jev subtotal is $1.021334412 (full total unknown). Adding it gives about $5.54, i.e. about 27% savings (inference).

## What it claims / describes
- Hierarchical discovery: traverse a directory frontier instead of uploading the whole root; local lookahead crosses intermediate directories; files classified from content fragments; one extra discovery pass anchored on a class-bearing candidate to find omitted backends or subclasses.
- Three separate decisions: is the file useful; which declaration locations are useful leads; which source to include now. "A useful path need not have a confident excerpt."
- Declaration units (Python, TS/JS parsers) with surrounding context; fallback to chunks for other text.
- Incompleteness is reported: "A rejected directory means its descendants were not inspected, not that each descendant was found irrelevant... Report incomplete discovery rather than manufacture negative evidence."
- Data handling: eligible source content is sent to Jev through the chosen provider; default filters skip hidden, dependency/build, binary and obvious credential files, "not a guarantee".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| official solves | 7/10 (repeat); 6/10 (first) | 8/10 saved baseline | 10-task tuned Python SWE-bench subset, Sol | baseline run once and reused |
| baseline solves preserved | 7/8 (repeat); 6/8 (first) | | | gate required 8/8 |
| full Sol cost incl. failures | $4.5195532 (repeat); $5.5410776 (first) | $7.6220690 | | Jev excluded |
| Sol savings | 40.70% (repeat); 27.30% (first) | | | |
| solved tasks cheaper than baseline | 4 of 10 in each cohort | | | |
| Jev subtotal (repeat, known) | $1.021334412 | | provider metadata | full total unknown |
| audit | 273 checks, no discrepancies | | 10 receipts, 158 Sol generation charges | audit file in /tmp, not in repo |
| per-task example: pytest | $0.6108848 (repeat) | $2.3444580 | | cost win |
| per-task example: xarray | $0.5114540 (repeat) | $0.4937066 | | lost earlier cost win |

## Mechanism details you could implement
- Ask the decision model about directories first, then files, then declarations; never impose a fixed number of returned files.
- Return "reading leads" (paths + declaration ranges) separately from included excerpts, so the caller can read more without the tool forcing it.
- Mark uninspected regions explicitly as unknown in the output (a receipt-friendly property for R1).
- Evaluation discipline worth copying: freeze the runtime (byte-identical install, plan hash), never pool cohorts, never rerun baselines to pick the better attempt, and keep a gate ("preserve every baseline solve") that the headline must pass.

## Limitations, caveats, counter-evidence
- README: "The sample is a tuned Python subset evaluated with Sol, so it does not establish general savings, faster execution, or results for other coding agents."
- n=10; one saved baseline run; decision-model cost excluded from the headline.
- Django lost a baseline solve in both cohorts; the repeat's retrieval ranked the critical SQLite file 24th instead of 9th ("observed differences, not proof that ranking caused the miss").
- Many evidence files referenced live under /tmp on the author's machine, not in the repository.

## Takeaways for tuning a memory stack
- Decision-model context selection can cut coding-agent spend, but here it traded away one solve in ten; count the selector's own cost.
- A recall miss on one critical file is enough to lose a task; for build-time reads, measure per-task critical-evidence recall, not only average cost.
- Copy the honest-reporting pattern: report the gate that failed next to the saving.

## Open questions
- Result with Jev cost included and with a baseline rerun (variance of the baseline itself)?
- Performance on non-Python repositories and other agents?
- Would a stop rule (B9) or a sufficiency check prevent the Django-style miss?

## Grading and labels
- Directness high; control medium; independence low; reproducibility high for the record, weaker for rerunning; applicability high.
- Pillars: R3 primary (request-time evidence selection within a budget); R6 secondary (claim narrowing, cost accounting).
- B9 (stop rule cuts tokens at equal accuracy): not supported here; tokens and cost fell but solves dropped 8/10 to 7/10, and there is no stop rule.
- B20 supports: the headline claim narrowed on primary read (40% "verified" -> one 10-task repeat, quality gate failed, selector cost excluded).
- No contradiction rows.

## Origin chain
post 2103920741481848861 (@dzhng) -> github.com/dzhng/jevgrep at 762028fa -> README "What we measured"; specs/done/jevgrep/assets/variance-repeat.md table; docs/architecture.md -> this note. Independence: author-run; SWE-bench tasks public but subset tuned by the author.
