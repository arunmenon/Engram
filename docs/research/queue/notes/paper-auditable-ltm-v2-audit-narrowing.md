---
schema_version: 1
artifact_id: N-SURVEY-20261007-01
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:05:00Z
idempotency_key: note:survey:arxiv:2609.38021v2
input_refs: []
supersedes_claims_in: N-SURVEY-20260930-04
pillar_primary: R6
pillar_secondary: [R1]
memory_stage: evaluation
priority: 4
beliefs_affected:
  supports: [B20]
  contradicts: []
evidence: {directness: 5, control: 3, independence: 2, reproducibility: 3, applicability: 3}
source_url: https://arxiv.org/abs/2609.38021v2
found_via: survey
---

# Auditing Long-Term Memory Evaluation: Repeated Judging, Reader Variation, and Negative Controls (arXiv 2609.38021 v2)

- **URL:** https://arxiv.org/abs/2609.38021 (v2 HTML read: https://arxiv.org/html/2609.38021v2)
- **Type:** paper
- **Author / org:** cjchanh (evidence repo github.com/cjchanh/longmemeval-evidence, MIT)
- **Date:** v1 2026-09-29; v2 2026-10-02
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2609.38021v2.html)
- **Cited by evidence:** survey; changes existing note N-SURVEY-20260930-04 (written on v1)
- **Relevance to a memory stack:** high; the authors themselves narrow a LongMemEval-S headline to "not a leader, no transferable advantage", and quantify judge and reader noise.

## TL;DR
- v1 was titled as a system result ("479/475 of 500 on LongMemEval-S"). v2 is retitled as an audit and states: "These findings do not establish a new leaderboard leader or transferable memory advantage."
- v2 discloses that "all questions were used to develop the components; no untouched holdout was evaluated."
- Re-judging the same pass-1 answers "changes three labels and yields 478". The authors: "a one-answer ranking margin is smaller than the disagreement observed in this run."
- Same packets, different readers: from 479 (Claude Opus lane) down to 93 (Nemotron-30B), per summary of tables (not all rows verified verbatim).
- A repair verifier "flipped 11 of 58 correct drafts to wrong" against 3/12 wrong rows recovered; the pre-committed acceptance rule rejected it.

## What it claims / describes
The paper now audits its own retrieval chain rather than promoting it. Result stated as "an observed range of 475 to 479 correct answers across two passes ... it is the range of two observed runs, not a confidence interval." It notes Chronos (478) may have used a different LongMemEval-S file version (cleaned vs original), so "comparisons with its 478 may also cross a data-version difference."

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| LongMemEval-S correct, pass 1 / pass 2 | 479 / 475 of 500 | Chronos High 478 | adapted GPT-4o rubric, Claude Opus reader | development set = test set, no holdout |
| re-judge pass 1 | 478 | 479 | same answers, judge rerun | 3 labels flipped |
| knowledge-update re-score | 70/72 upstream template, 69/72 modified | n/a | fixed answers | template wording changes a label |
| second-judge agreement | 493/500 (98.6 %) per pass | n/a | second judge GLM-5.3 (per reader summary) | not verified verbatim |
| repair verifier | 3/12 recovered, 11/58 correct flipped to wrong | no verifier | 60-row control | rejected by frozen rule |
| re-scoring cost | about $1.28 per run | n/a | official judge | only cost figure given |
| judge vs reader family | GPT-4o judge, Claude reader | n/a | different families | |

## Mechanism details you could implement
- Pre-commit an acceptance rule for any answer-repair component and run it against a control set of known-correct drafts; count flips to wrong, not just recoveries.
- Report results as observed run ranges plus re-judge flips; do not rank on margins smaller than the re-judge disagreement.
- Pin judge harness by hash (the paper pins it by SHA-256) and record data-file version.

## Limitations, caveats, counter-evidence
No held-out evaluation; retrieval, reranker and packet-compiler sources withheld; live request bodies not kept; no independent replication. Scaffold tuned to one reader family.

## Takeaways for tuning a memory stack
- Treat any LongMemEval-S gap of under about 3 to 4 answers in 500 as noise for our comparisons (inference from one re-judge, not a full distribution; the authors say so).
- Reader choice dominates retrieval choice on fixed packets; hold the reader fixed in H2-style arm tests.

## What changes from N-SURVEY-20260930-04
The earlier note recorded the v1 headline (479/475 of 500, positioned against Chronos 478). v2 withdraws the leadership reading, discloses the absence of a holdout and adds the re-judge, template and negative-control evidence. Cite v2 as an audit of evaluation noise, not as a system result.

## Open questions
- Full re-judge distribution (only one re-judge reported).
