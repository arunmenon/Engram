---
schema_version: 1
artifact_id: N-SURVEY-20261007-03
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:11:00Z
idempotency_key: note:survey:arxiv:2610.04838
input_refs: []
pillar_primary: R2
pillar_secondary: [R6, R10]
memory_stage: staleness
priority: 4
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: 4, control: 3, independence: 2, reproducibility: 3, applicability: 5}
source_url: https://arxiv.org/abs/2610.04838
found_via: survey
---

# MemTrace: State-Consistent Memory for Long-Horizon Coding Agents (arXiv 2610.04838)

- **URL:** https://arxiv.org/abs/2610.04838 (HTML v1 read); code github.com/Homy-Xu/MemTrace (pinning not stated)
- **Type:** paper
- **Author / org:** not stated in extract
- **Date:** 2026-10-04
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2610.04838v1.html)
- **Cited by evidence:** survey
- **Relevance to a memory stack:** high; test-scored, real-repository, multi-step coding tasks where memory must survive context refreshes. Also three benchmarks for our map.

## TL;DR
- Abstract: "improving DeepSWE pass@1 by 21.2 points, SWE-EVO Resolved Rate by 4.4 points, and SWE-Milestone Score by 17.8 points under Codex CLI."
- Table 2: MemTrace 56.6 (67.6) DeepSWE; 69.6 SWE-EVO resolved; native SWE-EVO 47.8.
- Text vs table: the SWE-EVO "+4.4" is against the strongest baseline (text: "65.2% vs. 69.6%"), while the gain over the native agent is 21.8 points. Text and table are consistent once read this way; quote the +4.4 as the fair margin.
- A repository state graph (files, symbols, tests) adds lift: "Adding the RSG further raises performance to 56.6%".

## What it claims / describes
State-consistent memory for coding agents whose context is refreshed: tracked relations among files, symbols and tests (RSG) plus bound-file survival over long runs. Codex CLI v0.144.4 and mini-swe-agent harnesses; model deepseek-v4-flash, 200K context.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| DeepSWE pass@1 | 56.6 | native 35.4 | 113 tasks, 91 repos, 5 languages | single model |
| SWE-EVO resolved | 69.6 | native 47.8; best baseline 65.2 | 46 Python tasks, 7 projects | 2 of 48 excluded |
| SWE-Milestone score | 46.4 | native 28.6 | 98 milestones, 7 itineraries | |
| bound-file survival at 1,001 steps | 0.495 [0.456, 0.530] | n/a | task-cluster bootstrap | |
| wall clock per task | DeepSWE 54.17 min (Codex CLI), 75.30 (mini-swe-agent); SWE-EVO 82.05, 114.03 | n/a | | token cost not stated |
| judge | test execution, no LLM judge | | | |
| seeds, leakage | not stated | | | |

## Mechanism details you could implement
- Keep a typed repository state graph (file, symbol, test nodes with relations) as memory alongside episodic notes; refresh on context reset.

## Limitations, caveats, counter-evidence
Authors' own system; one model; RepoGraph baseline Python-only; leakage of SWE task repos into model training not discussed.

## Takeaways for tuning a memory stack
- Benchmark map: SWE-EVO and SWE-Milestone measure release-level and milestone evolution, the closest public analogue to "notice a changed requirement over weeks" for our PDLC benchmark; DeepSWE is long-horizon single task.
- Candidate second benchmark for H1 next to DreamBench-SWE; executable oracles avoid judge bias.

## Open questions
- Seeds and variance on pass@1; token cost.
