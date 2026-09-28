---
schema_version: 1
artifact_id: N-20260926-05
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103739425058598941", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.24971
claim_cluster: arxiv:2609.24971
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.24971
source_commit: 81cb6f8405b40a9e76089cef650806a80af06ea2
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R7", "R3"]
tags: {"mechanism": ["action-graded memory benchmark", "with/without-history validation", "cost and latency reporting"], "workload": ["knowledge-work agent with email, Slack, calendar, CRM tools via MCP"], "lifecycle_stage": ["write", "read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-system accuracy, cost and latency on 600 tasks", "control": "medium: same harness and model per comparison and tasks validated with and without history, but single run per configuration and no intervals", "independence": "low: benchmark built by Mem0 authors and Mem0 is a compared system (and wins on one of three model rows)", "reproducibility": "medium: dataset and code released (CC BY 4.0) at a pinned commit; synthetic personas", "applicability": "medium: grades actions from long-term memory with real tool calls, closer to agents than QA benchmarks; not engineering work"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["On an action-graded memory benchmark the memory layer changes accuracy by up to about 21 points and total cost by up to about 5x at fixed harness and model, and the ordering of vendors flips across agent models"]}
claim_correction: none
---

# DolphinBench: Mapping the Pareto Frontier of Agent Memory (arXiv 2609.24971)

- **URL:** https://arxiv.org/abs/2609.24971 (HTML v2 read); site https://dolphinbench.ai/ ; code https://github.com/mem0ai/dolphinbench
- **Type:** paper + benchmark (vendor-authored)
- **Author / org:** Soumil Rathi, Deshraj Yadav, Taranjeet Singh (Mem0)
- **Date:** v1 2026-09-21, v2 2026-09-22
- **Retrieved:** 2026-09-26; repo HEAD `81cb6f8405b40a9e76089cef650806a80af06ea2` (2026-09-23) via GitHub API; leaderboard page loads dynamically and returned no rows
- **Cited by evidence:** https://x.com/himanshutwtxs/status/2103739425058598941 (@himanshutwtxs, links dolphinbench.ai and quotes @deshrajdry's announcement x:2102435297887911969)
- **Relevance to a memory stack:** high for R6. First benchmark in our catalogue that grades **actions** taken from years-old history and requires cost and latency next to accuracy; it also gives new numbers for Hindsight and Supermemory, both in our local sources.

## TL;DR
- 3 synthetic knowledge-work personas, about 500k tokens of user messages each (tiktoken o200k_base), spanning Jan 2023 to Dec 2027, up to 5,128 messages per persona with 2,963+ unrelated messages between a rule and the task that needs it; 200 tasks per persona, 600 total.
- Each task was **validated by running an agent with and without the relevant history**: "Both runs with history must pass every grading check, and both runs without history must fail."
- Tools are stateful MCP simulations of email, Slack, Discord, calendar and CRM; memory is read-only at task time; history is ingested from scratch per system.
- Grading: deterministic checks for factual requirements plus an LLM judge (GPT-5.6-Sol) for semantic interpretation. One run per configuration, no intervals.
- Hermes + GPT-5.6-Luna: Mem0 70.67%, Hindsight 69.50%, Honcho 68.50%, built-in 65.67%, Supermemory 59.17%. With MiniMax M3, built-in memory is 26.50% and Mem0 47.83%. With Claude Code + Claude Sonnet 5, Honcho 35.83% > Mem0 32.33% > built-in 26.33%.
- Authors are Mem0; Mem0 tops one model row, not all.

## What it claims / describes
- **Design goal:** "agents today often take real-world actions that depend on long-term memory and context recall over time"; recall-only benchmarks miss whether the agent applies the memory correctly in a tool action.
- **Protocol:** each memory system ingests the persona's history sequentially from scratch; then isolated tasks run with fresh app state and read-only memory; the request never reminds the agent of the rule.
- **Reporting rule:** accuracy, total cost (agent + memory system) and median latency together, to map a Pareto frontier. Key finding (verbatim): "A more accurate agent need not be slower, and a more expensive agent need not be more accurate."

## Numbers
Table 2, verbatim as extracted (accuracy over 600 tasks; costs in USD for the full run; median latency per task in seconds):

| harness | model | memory | accuracy % | agent $ | memory $ | total $ | median latency s |
|---|---|---|---|---|---|---|---|
| Hermes | GPT-5.6-Luna | built-in | 65.67 | 61.48 | 0.00 | 61.48 | 44.35 |
| Hermes | GPT-5.6-Luna | Mem0 | 70.67 | 61.54 | 34.68 | 96.21 | 37.69 |
| Hermes | GPT-5.6-Luna | Honcho | 68.50 | 96.56 | 46.30 | 142.85 | 44.66 |
| Hermes | GPT-5.6-Luna | Hindsight | 69.50 | 57.99 | 26.66 | 84.65 | 55.31 |
| Hermes | GPT-5.6-Luna | Supermemory | 59.17 | 63.86 | 281.79 | 345.64 | 52.68 |
| Hermes | MiniMax M3 | built-in | 26.50 | 107.03 | 0.00 | 107.03 | 51.40 |
| Hermes | MiniMax M3 | Mem0 | 47.83 | 111.71 | 36.31 | 148.02 | 46.95 |
| Hermes | MiniMax M3 | Honcho | 47.33 | 168.39 | 43.46 | 211.85 | 80.33 |
| Hermes | MiniMax M3 | Hindsight | 41.00 | 119.51 | 38.82 | 158.33 | 144.28 |
| Hermes | MiniMax M3 | Supermemory | 20.00 | 111.68 | 386.02 | 497.70 | 137.52 |
| Claude Code | Claude Sonnet 5 | built-in | 26.33 | 1,132.75 | 0.00 | 1,132.75 | 32.19 |
| Claude Code | Claude Sonnet 5 | Mem0 | 32.33 | 1,803.63 | 26.94 | 1,830.57 | 42.30 |
| Claude Code | Claude Sonnet 5 | Honcho | 35.83 | 1,556.02 | 9.79 | 1,565.82 | 37.92 |

Caveat: Hindsight and Supermemory rows under Claude Code were not present in the extracted table (not run, or not extracted; not stated). Per-persona breakdown not provided. Single run per cell; with n = 600, a 95% interval on a 70% accuracy is roughly +/- 3.7 points (inference, binomial approximation), so gaps under about 5 points between neighbours are not separable.

## Mechanism details you could implement
- **Task validity filter:** keep a memory task only if an agent with the relevant history passes and without it fails, run twice each. This removes tasks answerable from priors, a leakage class our own harness had (B19). Directly reusable for our held-out set.
- **Distractor spacing:** thousands of unrelated messages between the rule and the task.
- **Action grading:** check tool calls and final state deterministically where possible; LLM judge only for semantic parts.
- **Report cost split:** agent tokens vs memory-system cost, plus median latency, for every configuration.

## Limitations, caveats, counter-evidence
- Authors' list: synthetic data, three personas only, simulated environments, short task workflows, ingestion separated from testing.
- Conflict of interest: Mem0 authors benchmarking Mem0 against competitors; configuration effort per competitor not stated (inference: vendor defaults likely).
- LLM judge (GPT-5.6-Sol) is from the same family as one agent model (GPT-5.6-Luna) (inference: potential shared bias).
- Claude Code rows cost 10 to 20x more than Hermes rows at lower accuracy; the reason (harness token use) is not analysed in the extracted text.
- Supermemory's memory cost ($281.79 to $386.02) dominates its total; whether this reflects its consolidation ("dreams") pipeline is not stated.

## Takeaways for tuning a memory stack
- The memory layer matters most with weaker agent models (MiniMax M3: +21.3 points Mem0 vs built-in) and less with stronger ones (Luna: +5.0).
- Vendor ranking is not stable across agent models and harnesses; evaluate on our own harness and model.
- Adopt the with/without-history validation filter and the cost-plus-latency reporting rule in our P3 harness.

## Open questions
- Per-persona and per-task-type variance? Not reported.
- Do the vendors' own tuned configurations change the order? Not tested.
- How much of Supermemory's cost is consolidation, and does it pay off on longer horizons?

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium (commit 81cb6f84, CC BY 4.0); applicability medium.
- Pillar R6 (a new memory benchmark and its reporting protocol). Secondary R7 (what Mem0, Honcho, Hindsight, Supermemory ship and how they compare) and R3.
- Beliefs: supports B20 in spirit (headline "Mem0 best" narrows on a primary read: true for one of three model rows, single runs, vendor-authored). New relative to local sources: first third-party-style accuracy/cost numbers for Hindsight (`github-vectorize-io-hindsight.md`) and Supermemory (`x-article-supermemory-jev-memory-context.md`) on an action benchmark. Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103739425058598941 (@himanshutwtxs; quotes @deshrajdry x:2102435297887911969, not in items) -> dolphinbench.ai -> arXiv 2609.24971 v2 -> Table 2, Figure 2 (validation), limitations section -> repo mem0ai/dolphinbench @ 81cb6f84. Independence: benchmark authors = Mem0 team; Hindsight is vectorize-io, Supermemory is Dhravya Shah's company (both in local sources, no shared authors).
