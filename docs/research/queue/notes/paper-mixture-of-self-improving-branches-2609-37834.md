---
schema_version: 1
artifact_id: N-20261001-07
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105214701626122496", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.37834
claim_cluster: arxiv:2609.37834
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.37834
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6"]
tags: {"mechanism": ["harness search", "branch-local development subsets", "proposal policy as SKILL.md", "per-input router"], "workload": ["coding agent", "terminal tasks", "olympiad math"], "lifecycle_stage": ["none"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: held-out results table and full-run token table", "control": "low: total token budgets unequal (1.55x to 2.16x Meta-Harness), single runs", "independence": "medium: one group; Meta-Harness baseline reimplemented settings", "reproducibility": "low: single runs, proposer and solver are proprietary models", "applicability": "medium: harness self-improvement for coding agents"}
beliefs_affected: {"supports": ["B15"], "contradicts": [], "would_create": ["Splitting harness search into branches with their own evolving development subsets and routing per input beats a single-development-set search on held-out tasks, but at 1.55x to 2.16x the tokens, so the gain is not shown at matched budget"]}
claim_correction: The post reports gains "relative to Meta-Harness" without the budget: the method used 1.55x (SWE-bench Lite) to 2.16x (math) the total tokens of Meta-Harness, and the paper says unequal token usage and limited repeated evaluations "constrain conclusions about efficiency and reliability".
memory_stage: none
---

# Mixture of Self-Improving Branches for Agent Harness Optimization (MoSIB, arXiv 2609.37834)

- **URL:** https://arxiv.org/abs/2609.37834 (HTML: https://arxiv.org/html/2609.37834)
- **Type:** paper
- **Author / org:** Haoyu Dong, Yuhang Zhou, Zihao Lin, Yifan Wu, Bo Peng, Mingyi Wang, Xiangjun Fan, Lizhu Zhang, Zhuokai Zhao (affiliations not shown on abstract page)
- **Date:** submitted 2026-09-29
- **Retrieved:** 2026-10-01 (abstract and HTML: method, Table 1, Table 5, limitations)
- **Cited by evidence:** @runbywren, 2026-09-30, https://x.com/runbywren/status/2105214701626122496
- **Relevance to a memory stack:** medium. The branch-local "development subset" and "proposal guidance" are memories of what each search line has learned; the result speaks to how a self-improving loop should partition its evidence to avoid overfitting one development set.

## TL;DR
- Harness search with B=2 branches; each keeps its own development subset (cases reassigned by "frontier coverage voting": a branch owns a case when its leading harnesses solve it with margin >= 2; cases solved by all branch frontiers are pruned), its own candidate history on disk, and its own proposal guidance (a SKILL.md revised every 5 iterations by Claude Opus 4.6 from recent traces).
- At the end, one development-best harness per branch; a router (optimised with GEPA on head-exclusive development cases) picks which harness to run for each new input.
- Held-out (Table 1) vs Meta-Harness: math with Gemini Flash 62.0 vs 46.0 (+34.8% relative), math with Sonnet 4.5 30.5 vs 29.0 (+5.2%), Terminal-Bench 2.0 50.0 vs 44.8 (+11.6%), SWE-bench Lite 66.0 vs 63.6 (+3.8%).
- Token cost (Table 5): 2.16x (math), 1.69x (Terminal-Bench 2.0), 1.55x (SWE-bench Lite) of Meta-Harness. Single runs.
- Router falls slightly below the stronger individual branch head in 2 of 4 settings.

## What it claims / describes
"Harness optimization provides a practical setting for recursive self-improvement (RSI), where agent-generated modifications inform subsequent changes through execution feedback." Meta-Harness uses one fixed development set and one proposal policy; MoSIB lets branches specialise. Setup: N=20 search iterations, B=2 branches, frontier size q=5, ownership margin 2, subset updates every iteration once the frontier holds 5, proposal-policy updates every 5 iterations. Task solving uses Claude Sonnet 4.5; the proposer uses Claude Opus 4.6. Splits: math 250 dev / 200 held-out IMO-level; Terminal-Bench 2.0 30 dev / 58 test; SWE-bench Lite 50 dev / 250 test. "All harness selection and router configuration rely solely on development data."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| math, Gemini Flash solver | 62.0 | Meta-Harness 46.0 | 200 held-out, Table 1 | single run |
| math, Sonnet 4.5 solver | 30.5 | 29.0 | same | |
| Terminal-Bench 2.0 | 50.0 | 44.8 | 58 test tasks | 1 task = 1.7 points |
| SWE-bench Lite | 66.0 | 63.6 | 250 test tasks | |
| total tokens, math | 172.90M | 79.92M (2.16x) | Table 5 | |
| total tokens, Terminal-Bench 2.0 | 4,001.39M | 2,366.80M (1.69x) | Table 5 | |
| total tokens, SWE-bench Lite | 2,951.48M | 1,907.17M (1.55x) | Table 5 | |

Other fixed baselines in the paper (no-memory prompting, few-shot, BM25 retrieval for math; Terminus 2 and Terminus-KIRA; mini-swe-agent) were not extracted.

## Mechanism details you could implement
- Partition the development set by which search line solves what; drop cases every line solves (no signal) and give contested cases to the line that solves them by a margin.
- Keep proposal guidance as a per-branch document updated from repeated evidence, distinguishing "repeated evidence across implementations from isolated successes/failures".
- Route per input among specialised heads instead of picking one global winner; train the router only on development cases.

## Limitations, caveats, counter-evidence
- Paper: "unequal total token usage and limited repeated evaluations constrain conclusions about efficiency and reliability"; ablations "do not establish that each observed trajectory change caused its subsequent test gain".
- Gains are small on SWE-bench Lite (+2.4 points absolute) and Sonnet math (+1.5), within likely run-to-run noise (inference).
- Proposer is a stronger model than the solver; benefits may depend on proposer strength.

## Takeaways for tuning a memory stack
- When a self-improvement loop's memory is "what worked on the dev set", one dev set overfits; branch-local subsets are a concrete alternative, but compare at matched tokens before adopting.
- Our hypothesis cards on self-improvement should require matched-budget arms; this paper is the counter-example of an unmatched one.

## Open questions
- What is MoSIB vs Meta-Harness at equal total tokens (for example Meta-Harness with 2x iterations)?
- How stable are the branch assignments across seeds?

## Grading and labels
- **Directness: high.** **Control: low** (unmatched budget, single runs). **Independence: medium.** **Reproducibility: low.** **Applicability: medium.**
- **Pillars:** R5 primary (self-improvement loop design); R6 secondary (budget accounting). **Memory stage:** none.
- **Beliefs:** supports B15 in direction (multiple lineages with comparative evidence beat one), with the budget caveat. **Contradictions:** none.

## Origin chain
Post @runbywren 2105214701626122496 (2026-09-30) -> arXiv 2609.37834 -> method section, Table 1 (held-out), Table 5 (tokens), limitations text -> this note. Independence: Meta-Harness is the comparison system from other authors; related bus notes N-20260930-16 (MetaSkills, arXiv 2609.38143) and N-20260927-19 (SoL-Pi) are separate groups as far as shown.
