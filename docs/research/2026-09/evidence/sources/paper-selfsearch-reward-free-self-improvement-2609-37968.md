---
schema_version: 1
artifact_id: N-20261001-06
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105251976963383530", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.37968
claim_cluster: arxiv:2609.37968
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.37968
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6"]
tags: {"mechanism": ["self-improvement from episode records", "reward-free search", "lineages", "population-mean evaluation"], "workload": ["coding agent", "terminal tasks"], "lifecycle_stage": ["consolidation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-model, per-benchmark success and cost table plus an ablation table", "control": "medium: initial agent and two evaluation-guided search baselines, two ablations, but one search per setting and small task sets (60 to 120)", "independence": "medium: academic authors; initial agent from DGM's implementation; benchmark graders", "reproducibility": "low: no seeds or repeated searches stated; code release not checked", "applicability": "medium: coding agents improving their own instructions and tools from records, close to our outcome loop"}
beliefs_affected: {"supports": ["B15"], "contradicts": [], "would_create": ["Records of earlier self-improvement episodes (trajectories, code changes, check results) can replace per-candidate benchmark scoring as the search signal, at about 3x lower search cost, with 2 to 3 point ablation losses when the records are removed"]}
claim_correction: The post's "+5.0 pp with -38.5% cost" combines two different measures: +5.0 pp is overall success of the DeepSeek adaptive agent on SWE-bench Multilingual (68.3 to 73.3), while -38.5% cost is computed only on tasks both the initial and evolved agents solve; the capability-lineage DeepSeek agent fell on the same benchmark (68.3 to 66.7). The abstract's "up to 11.2" is 11.3 by Table 1 (43.8 to 55.1).
memory_stage: consolidation
---

# SelfSearch: Reward-Free Search for Self-Improving Agents (arXiv 2609.37968)

- **URL:** https://arxiv.org/abs/2609.37968 (HTML full text: https://arxiv.org/html/2609.37968)
- **Type:** paper
- **Author / org:** Jungwoo Yang, Injin Kong, Yohan Jo (affiliations not shown on the abstract page)
- **Date:** submitted 2026-09-29, revised 2026-09-30
- **Retrieved:** 2026-10-01 (abstract and HTML full text: Table 1, Table 4, method and cost sections)
- **Cited by evidence:** @runbywren, 2026-09-30, https://x.com/runbywren/status/2105251976963383530
- **Relevance to a memory stack:** medium to high. It treats the record of past self-improvement episodes as the memory that drives the next revision, which is our outcome-loop question (R5): can stored receipts of what was tried and what happened replace expensive re-evaluation?

## TL;DR
- An agent revises its own instructions, tools and procedures; each successor reads the "records of previous self-improvement episodes" ("interaction trajectories, code changes, and check results") instead of downstream benchmark scores, and becomes the next actor.
- Two lineages (capability and adaptive), ten generations, two agents per generation; initial agent B0 from DGM's implementation. Search models gpt-5.6-sol and deepseek-v4-pro-0813; downstream models gpt-5.6-luna and deepseek-v4-flash-0731 (medium reasoning).
- Table 1 after ten generations: Terminal-Bench 2.1 GPT 43.8 -> 55.1 (capability) / 44.9 (adaptive); DeepSeek 65.2 -> 73.0 / 71.9. SWE-bench Multilingual GPT 53.3 -> 60.0 / 58.3; DeepSeek 68.3 -> 66.7 / 73.3. SWE-bench Verified GPT 75.0 -> 77.5 / 75.0; DeepSeek 81.7 -> 86.7 / 86.7.
- Ablation (Table 4): removing episode records costs 2.0 pp (GPT, 76.2 -> 74.2) and 2.9 pp (DeepSeek, 86.7 -> 83.8); a fixed improver costs 1.6 and 2.9 pp.
- Search cost: DeepSeek V4 Flash capability agent solves 73 of 89 Terminal-Bench 2.1 tasks (82.0%), "tying Codex", for $4.03 of search; evaluation-guided linear and archive search cost $12.35 and $7.53 (GPT).

## What it claims / describes
Self-improvement episodes: an agent inspects and edits its own instructions, tools and procedures, runs, and leaves a record (trajectory, code diff, check results). SelfSearch drops the per-candidate evaluation on the target benchmark ("reward-free"): "Each successor becomes the next actor, while its episode record informs subsequent revisions." Two lineages run in parallel (capability and adaptive directions) for ten generations with two agents per generation; success is reported per final agent and as a population mean. Baselines: the initial agent B0, evaluation-guided linear search, evaluation-guided archive search; ablations without episode records and with a fixed improver. Cost is "total model execution cost divided by the number of attempted tasks, including unsuccessful attempts."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Terminal-Bench 2.1, GPT, capability agent | 55.1% ($0.0219/task) | B0 43.8% ($0.0212) | 89 tasks, Table 1 | single search |
| Terminal-Bench 2.1, GPT, adaptive | 44.9% ($0.0199) | 43.8% | same | |
| Terminal-Bench 2.1, DeepSeek, capability / adaptive | 73.0% ($0.0264) / 71.9% ($0.0250) | 65.2% ($0.0301) | same | |
| SWE-bench Multilingual, GPT, capability / adaptive | 60.0% / 58.3% | 53.3% | 60 tasks, 8 languages | |
| SWE-bench Multilingual, DeepSeek, capability / adaptive | 66.7% ($0.0321) / 73.3% ($0.0332) | 68.3% ($0.0521) | same | capability agent declined |
| SWE-bench Verified, GPT, capability / adaptive | 77.5% / 75.0% | 75.0% | 120 tasks | |
| SWE-bench Verified, DeepSeek, capability / adaptive | 86.7% / 86.7% | 81.7% | same | |
| cost on tasks both agents solve | -38.5% | B0 | DeepSeek adaptive, SWE-bench Multilingual | subset measure |
| ablation, no episode records | GPT 74.2 (-2.0); DeepSeek 83.8 (-2.9) | full 76.2 / 86.7 (means) | Table 4 | |
| ablation, fixed improver | GPT 74.6 (-1.6); DeepSeek 83.8 (-2.9) | same | Table 4 | |
| search cost to 82.0% on TB2.1 | $4.03 | linear search $12.35, archive search $7.53 (GPT) | Section 3.3 | different models across rows |

## Mechanism details you could implement
- Store each improvement episode as a record: the trajectory, the code or prompt diff, and the check results (tests, linters). Feed the last records to the improver as context for the next revision.
- Run at least two lineages with different objectives (capability vs adaptive) and keep a population; report the population mean, not the best agent.
- Account cost per attempted task, including failures.
- Keep the evaluation set out of the improver's loop (reward-free); use it only to report (inference: this also reduces leakage risk, see B19).

## Limitations, caveats, counter-evidence
- One search per setting; the paper notes "Further work should examine how consistently these gains arise across independent searches". No seeds or intervals.
- Small task sets (60, 89, 120): one task is 1.1 to 1.7 points.
- Not uniformly positive per agent: DeepSeek capability agent on SWE-bench Multilingual fell 1.6 points; GPT adaptive on SWE-bench Verified unchanged.
- Ablation gaps (2 to 3 points) are within a few tasks on these set sizes (inference).
- No dedicated limitations section.

## Takeaways for tuning a memory stack
- The memory that matters for self-improvement is the episode record with its check results, not just the final lesson; keep diffs and test outcomes linked to each revision (fits our receipt and replay design).
- Reward-free search is cheaper but needs a separate held-out evaluation before promotion; SelfSearch reports evaluation but does not gate on it.
- Report population means and per-lineage results; single best-agent numbers overstate.

## Open questions
- How variable are the gains across independent searches?
- Does reading records of failed episodes help more than successful ones?
- Would the same signal work for memory-policy revisions (write gate thresholds) rather than agent code?

## Grading and labels
- **Directness: high.** **Control: medium.** **Independence: medium.** **Reproducibility: low.** **Applicability: medium.**
- **Pillars:** R5 primary (learning from experience records); R6 secondary (single-search evaluation). **Memory stage:** consolidation (turning episode records into revisions).
- **Beliefs:** supports B15 (comparative evidence across lineages produces better refinements; here two lineages and records of earlier episodes beat the fixed improver and the no-records ablation). Bears on B16 without settling it (records are used raw, not distilled; no distilled-skill arm). **Contradictions:** none.

## Origin chain
Post @runbywren 2105251976963383530 (2026-09-30) -> arXiv 2609.37968 v2 -> Table 1 (success and cost), Table 4 (ablations), Section 3.3 (search cost), method section -> this note. Independence: B0 from DGM's implementation; benchmarks are public; no shared authors with MGM (B15's source) as far as shown.
