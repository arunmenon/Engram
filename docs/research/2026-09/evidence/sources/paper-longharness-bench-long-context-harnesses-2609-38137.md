---
schema_version: 1
artifact_id: N-20260930-17
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105180911218405713", "file_id": null, "sha256": null}, {"artifact_id": "post:2105181653631205716", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.38137
claim_cluster: arxiv:2609.38137
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.38137
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R6
pillar_secondary: ["R3"]
memory_stage: evaluation
tags: {"mechanism": ["file-and-shell agents", "recursive decomposition", "embedding retrieval tools", "cost per instance accounting"], "workload": ["long-context reasoning at 90K to 160K tokens", "scattered evidence", "contradiction detection across 700 memos"], "lifecycle_stage": ["evaluation", "assembly"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "medium", "reproducibility": "medium", "applicability": "medium"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["On long-context tasks no harness dominates: the same harness that lifts one task by 50 points drops another to zero, and cost per instance varies by more than 10x at similar or worse accuracy"]}
claim_correction: none
---

# LongHarness Bench: Stress-Testing Language Model Harnesses for Long-Context Reasoning (arXiv 2609.38137)

- **URL:** https://arxiv.org/abs/2609.38137 (full text read at https://arxiv.org/html/2609.38137). Project page: https://stringnlplab.github.io/longharness/
- **Type:** paper (benchmark)
- **Author / org:** Quang Hieu Pham, Thuy Duong Nguyen, Jocelyn Qiaochu Chen, Xi Ye. University of Alberta; Alberta Machine Intelligence Institute (Amii).
- **Date:** 2026-09-29 (v1)
- **Retrieved:** 2026-09-30, arXiv HTML v1. No dataset or code download link was found in the text read beyond the project page.
- **Cited by evidence:** https://x.com/runbywren/status/2105180911218405713 and https://x.com/runbywren/status/2105181653631205716 (@runbywren, watchlist timeline and a reply repeating the same numbers). Memory digest of 2026-09-30.
- **Relevance to a memory stack:** medium. It measures how much the read harness changes accuracy and cost when the evidence is long and scattered, with cost per instance in every cell. One suite (find 15 contradictory memos among 700) is close to a contradiction-linking workload.

## TL;DR
- Four suites of long-context tasks (about 100K to 160K tokens each) run with five harnesses (direct inference, RLM, OpenCode, mini-swe-agent, ReAct) and five models. Every cell reports accuracy and dollars per instance.
- Best configuration: GPT-5.6-sol with mini-swe-agent, 68.0% macro-average at $0.816 per instance. Direct inference with the same model: 60.0% at $0.822.
- No harness wins everywhere. With GPT-5.6-sol, OpenCode takes Program Execution Tracing from 94% to 96% but Outlier Memo Detection from 44% to 10% and Equivalent Program Pair Search from 44% to 0%.
- More spend does not buy accuracy: on Outlier Memo Detection RLM scores 92% at $7.23 per instance and mini-swe-agent 100% at $0.583.
- The post's numbers match Table 2. Its headline says "Same accuracy"; its body and the table show RLM is lower (92% vs 100%). Not counted as a claim correction because the post states the correct figures.

## What it claims / describes

**Suites.**
1. Constraint Solving Search: find all people satisfying conditions scattered across about 120K tokens.
2. Equivalent Program Pair Search: find matching program pairs among 200 implementations (about 100K tokens).
3. Program Execution Tracing: recover a computation result from 320 shuffled prior execution records (about 160K tokens).
4. Outlier Memo Detection: locate 15 contradictory memos in a collection of 700 memos (about 2,500 statements).
Instance counts per suite are not stated in the text read (accuracies move in steps of 2 points, which is consistent with 50 instances per suite; inference). Instances are generated from private specifications with fixed seeds; answer keys come from task-specific solvers; distractors are near-twin claims, syntax mutations and boundary changes.

**Harness categories.** File-and-shell agents (OpenCode, mini-swe-agent): the context is stored in files, the agent greps, reads and writes small programs. Programmatic decomposition (RLM, Recursive Language Models): recursive filtering with sub-model calls. Embedding retrieval (ReAct with retrieval tools).

**Cost accounting.** API list prices per model (Table 6), including cache read and write rates for GPT-5.6-sol ($4.00/M input, $0.40/M cache read, $5.00/M cache write, $20.00/M output; higher above 272K input). Evaluation protocol uses a 3M-token budget.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Macro-average, GPT-5.6-sol + mini-swe-agent | 68.0% ($0.816) | Direct 60.0% ($0.822); RLM 53.5% ($4.30); OpenCode 40.5% ($2.90); ReAct 43.0% ($1.93) | Table 2, four suites | no variance reported |
| Outlier Memo Detection, GPT-5.6-sol | mini-swe-agent 100% ($0.583); RLM 92% ($7.23) | Direct 44% ($1.17); OpenCode 10% ($3.11); ReAct 6% ($2.77) | Table 2 | RLM costs about 12.4x mini-swe-agent (7.23 / 0.583) |
| Equivalent Program Pair Search, GPT-5.6-sol | ReAct 52% ($2.68); Direct 44% ($0.780); mini-swe-agent 42% ($1.34) | RLM 2% ($7.86); OpenCode 0% ($5.41) | Table 2 | |
| Program Execution Tracing, GPT-5.6-sol | OpenCode 96% ($1.37); Direct 94% ($0.648) | RLM 76% ($1.47); mini-swe-agent 88% ($1.02); ReAct 82% ($0.866) | Table 2 | |
| Constraint Solving Search, GPT-5.6-sol | Direct 58% ($0.690); OpenCode 56% ($1.72) | RLM 44%; mini-swe-agent 42% ($0.320); ReAct 32% | Table 2 | direct inference is best here |
| GLM-5.3 macro-average | Direct 9.5%; mini-swe-agent 42.5% ($3.00); OpenCode 38.0% ($3.33) | | Table 2 | |
| Qwen3.8-27B macro-average | Direct 0.0%; OpenCode 38.5% ($7.06); mini-swe-agent 33.0% ($5.32) | | Table 2 | weaker models gain most from a harness |
| Gemini 3.8 Flash macro-average | Direct 10.0% ($0.162); mini-swe-agent 25.0% ($0.550) | | Table 2 | |
| Kimi-K2.6 macro-average | 0.0% to 1.5% in every harness | | Table 2 | |
| Existing benchmarks, GPT-5.6-sol | OOLONG-Synth: Direct 64%, mini-swe-agent 86% ($0.217); LongBench-v2: 60% to 68% across harnesses | | Table 3 | LongBench-v2 subset is 42 hard of 50 examples |

Verbatim excerpt: "For GPT-5.6-sol, OpenCode slightly improves Program Execution Tracing accuracy from 94% to 96%, but reduces accuracy from 44% to 10% on Outlier Memo Detection and from 44% to 0% on Equivalent Program Pair Search."

## Mechanism details you could implement
- Report accuracy and cost per instance together for every read-path variant, with cache read and write prices included.
- For "find the contradictory items in a large set", the winning pattern was an agent that writes small scripts and keeps a fact table on disk, then verifies candidates with code (mini-swe-agent on Outlier Memo Detection). Recursive LLM decomposition reached similar accuracy at 12x the cost.
- For "find matching pairs among many items", embedding neighbourhood search (ReAct) was best and file agents were poor.
- Keep direct full-context inference as a baseline arm: it was best on one of four suites with the strongest model.

## Limitations, caveats, counter-evidence
- The paper has no limitations section. Exact-match scoring; one evaluation protocol; five models; no repeated runs or intervals.
- Synthetic tasks built from private specifications; how closely they reflect real engineering artifacts is not shown.
- Instance counts per suite are not stated in the text read.
- Harness versions and configurations matter and are not pinned in the text read (inference).
- Consistent with HarnessTax (note blog-harnesstax-harness-cost-coding-agents.md), which reports harness-dependent cost on coding tasks; this adds long-context reasoning tasks and per-task reversals.

## Takeaways for tuning a memory stack
- A read path should be chosen per question type. A single "best" context-assembly harness does not exist in this data.
- Contradiction detection over hundreds of items favours scripted verification over recursive summarise-and-filter.
- Cost per instance varied from $0.32 to $7.86 for one model; any internal comparison that reports accuracy alone will mislead.
- For our PDLC memory benchmark scope, the memo suite is a template for "spot the stale or contradictory memory" probes with a deterministic answer key.

## Open questions
- How many instances per suite, and what is the run-to-run variance? Not stated.
- Would a memory system (index plus retrieval) beat the file agent on the memo suite at lower cost? Not tested.
- Are the generators released so the suites can be regenerated at other lengths? The text says frozen instances "regenerate byte for byte"; a download link was not found.

## Grading and labels
- **Directness: high.** Full accuracy and cost table read.
- **Control: medium.** Same tasks across five harnesses and five models with cost; no budget matching, no repeats.
- **Independence: medium.** Academic group with no product in the comparison; harnesses are third-party.
- **Reproducibility: medium.** Deterministic generators and fixed seeds described; artifact link not confirmed.
- **Applicability: medium.** Long scattered evidence and contradiction finding are close to build-time reads; content is synthetic.
- **Strength:** paper-single-benchmark.
- **Pillars:** R6 primary (whether an evaluation supports a harness claim; cost accounting). Secondary R3 (context assembly method). Memory stage: evaluation.
- **Beliefs:**
  - B9 adjacent: cheaper reads at equal or better accuracy exist (mini-swe-agent vs RLM), but through a different mechanism than a sufficiency stop.
  - Would create: no harness dominates on long-context tasks; cost spreads exceed 10x.
- **Contradiction rows:** none.

## Origin chain
- Posts https://x.com/runbywren/status/2105180911218405713 and https://x.com/runbywren/status/2105181653631205716 -> arXiv 2609.38137 v1 -> Table 2 (accuracy and cost per cell), Table 3, Table 6 (prices) -> this note.
- Independence: single source; both posts are by the same account. Shares no authors with HarnessTax (inference from author lists).
