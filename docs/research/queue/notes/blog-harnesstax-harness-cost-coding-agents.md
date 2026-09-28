---
schema_version: 1
artifact_id: N-20260928-02
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104172198537855432", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:harnesstax.github.io
claim_cluster: url:harnesstax.github.io
feeds: ["decision", "memory"]
primary_source: https://harnesstax.github.io/
source_commit: f8a8281c41bb97d34efee83e58be522ef1bb78cd
strength: paper-single-benchmark
pillar_primary: R6
pillar_secondary: ["R3"]
tags: {"mechanism": ["agent harness", "tool schema size", "initial context"], "workload": ["coding agents", "SWE-bench Lite", "Terminal-Bench 2.0"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: measures success and token cost for each model-harness pair with official evaluators", "control": "medium: same 30 tasks, same prices, 3 attempts per task, bootstrap CIs; harnesses run at native high-effort configs so the harness is the whole bundle, no component ablation", "independence": "medium: UC Berkeley Sky Lab and Arena authors; API access sponsored by Arena and Anthropic credits from Laude; no harness vendor authored it", "reproducibility": "medium: dashboard data pinned in site repo f8a8281; traces promised but not yet released; a third party (plurnk/harnesstax-evidence) publishes runs on the task set", "applicability": "high: coding agents on software tasks; our experiments run inside such harnesses"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Harness choice changes coding-agent cost by up to about 2x (up to 5x in the extreme) at success within about 2 to 5 points; cost must be reported per harness and the harness frozen in any memory experiment"]}
claim_correction: The post's "Claude Code costs ~2x a minimal 4-tool harness at near-identical success rates" matches the SWE-bench Lite geometric mean (2.0x vs Pi); on Terminal-Bench 2.0 the ratio is 1.5x, the sample is 30 tasks per benchmark, and it is a blog/dashboard, not a peer-reviewed paper.
---

# HarnessTax: How Much Does the Harness Matter for Coding Agents? (UC Berkeley Sky Lab)

- **URL:** https://harnesstax.github.io/ (source repo https://github.com/HarnessTax/HarnessTax.github.io)
- **Type:** research blog with interactive dashboard (no arXiv paper found; arXiv title search for "HarnessTax" returned 0 results on 2026-09-28)
- **Author / org:** Melissa Z. Pan, Shuo Yang, Negar Arabzadeh, Ion Stoica, Matei Zaharia (UC Berkeley); Wei-Lin Chiang (Arena Intelligence Inc.)
- **Date:** dashboard build published 2026-09-22 (repo commit date); references accessed 2026-09-16
- **Retrieved:** 2026-09-28. The page is JavaScript-rendered (WebFetch saw only a loading indicator), so the text was read from the site repo shallow clone at `f8a8281c41bb97d34efee83e58be522ef1bb78cd` (2026-09-22 00:52:08 +0000, "Publish dashboard build from AgentBRANE a812aeb1"), file `data/blog/harness-x-model.0af74054a7.json`; local copy `repos/harnesstax-site`
- **Cited by evidence:** @rajeevchhajer, https://x.com/rajeevchhajer/status/2104172198537855432 ("HarnessTax: Claude Code costs ~2x a minimal 4-tool harness at near-identical success rates")
- **Relevance to a memory stack:** medium-high. Not a memory result, but it says the harness is a first-order cost variable: any memory experiment that compares arms across harnesses, or reports cost without naming the harness, is confounded.

## TL;DR
- 21 model-harness pairs (7 models x Claude Code, Codex CLI, Pi) on the same 30 randomly sampled tasks from SWE-bench Lite and from Terminal-Bench 2.0, 3 attempts per task, 100-turn cap, native high-effort settings, official evaluators, 10,000-resample bootstrap CIs, one fixed price list dated 2026-09-01.
- "Harness choice has little effect on task success rate, but can significantly affect the cost": average harness effect on success within +/-2% (SWE-bench Lite) and about +/-5% (Terminal-Bench 2.0); Claude Code costs "2.0x as much as Pi and 1.6x as much as Codex on SWE-bench Lite, and 1.5x as much as Pi on Terminal-Bench 2.0" (geometric means). Extreme: "similar success rates at up to 5x costs".
- Example: Claude Fable 5 solves 97.8% in Claude Code, 96.7% in Codex, 96.7% in Pi; Claude Code $1.33 vs Pi $0.67 per attempt, with 15.3 vs 15.4 turns.
- Mechanism offered: Claude Code's mean initial context is over 10x Pi's (longer instructions, larger tool schemas). Pi exposes four tools: read, write, edit, bash.
- "An alternative harness achieves the highest observed success rate in nine of twelve comparisons" (six Anthropic and OpenAI models x two benchmarks).

## What it claims / describes
Three findings on two open benchmarks: (1) harness affects cost more than correctness; (2) a minimal open-source harness (Pi) sits on the cost-success Pareto frontier on both benchmarks; (3) models can do as well or better outside their provider's harness (e.g. GPT-5.6 Sol on Terminal-Bench 2.0: 83.3% in Pi vs 78.9% in Codex, $0.42 vs $0.76; Sonnet 4.6 on SWE-bench Lite: 68.9% in Codex vs 66.7% in Claude Code at similar cost).

Setup details (Experiment Setup section, verbatim fragments): "We run each pair three times per task"; "cap each attempt at 100 agent turns"; "We estimate 95% confidence intervals using 10,000 bootstrap resamples, each drawing 30 task averages with replacement"; "For SWE-bench Lite, we block external network access from all task containers, disable the default web tools in Claude Code and Codex, and reject hosted tool declarations at the API request level." Kimi K3 via Fireworks AI. Pi got two packages for subscription keys and turn control.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| cost ratio Claude Code / Pi | 2.0x | Pi | SWE-bench Lite, geometric mean over shared models | 30 tasks x 3 attempts |
| cost ratio Claude Code / Codex | 1.6x | Codex CLI | SWE-bench Lite | |
| cost ratio Claude Code / Pi | 1.5x | Pi | Terminal-Bench 2.0 | |
| harness effect on success | within +/-2% | | SWE-bench Lite average | |
| harness effect on success | about +/-5% | | Terminal-Bench 2.0 average | |
| Fable 5 success | 97.8% CC / 96.7% Codex / 96.7% Pi | | SWE-bench Lite | ceiling effect likely (inference) |
| Fable 5 cost per attempt | $1.33 CC vs $0.67 Pi | | SWE-bench Lite | 15.3 vs 15.4 turns |
| initial context | Claude Code over 10x Pi | Pi | first main model call, SWE-bench Lite, all 7 models | Figure 3 |
| GPT-5.6 Sol | 83.3% Pi vs 78.9% Codex; $0.42 vs $0.76 | own harness | Terminal-Bench 2.0 | |
| Sonnet 4.6 | 68.9% Codex vs 66.7% Claude Code | own harness | SWE-bench Lite | similar cost |
| alternative harness best | 9 of 12 comparisons | provider harness | 6 models x 2 benchmarks | highest observed, not significance-tested |
| max cost spread at similar success | up to 5x | | | per-pair figure not in text |

## Mechanism details you could implement
- Freeze the harness as an explicit experimental factor: record harness name, version, tool set and initial-context size with every run; report cost per attempt from provider token counts at a fixed price list.
- Measure first-call context (instructions + tool schemas) as a cheap predictor of harness cost.
- A four-tool harness (read, write, edit, bash) is a credible minimal baseline arm for memory experiments; memory tools add to schema size, which this study shows is itself a cost driver (inference).

## Limitations, caveats, counter-evidence
- Authors: "These findings can be limited to the two open-source benchmarks we test, which the models may have encountered during training. Results may differ on other benchmarks and workloads."
- 30 tasks per benchmark; success rates near ceiling for strong models on SWE-bench Lite compress any harness effect on success (inference).
- Harnesses run in native configurations, so "harness" bundles prompts, tools, caching behaviour and effort mapping; "Turn counts and effort settings follow each harness's own definitions."
- Profiling traces "will" be released; not yet available, so per-task numbers cannot be checked. Dashboard chart JSON is in the site repo.
- API access sponsored by Arena Intelligence (a co-author's company) and Anthropic credits via Laude; no evident stake in Pi (inference).
- Not peer reviewed.

## Takeaways for tuning a memory stack
- In any arm-versus-arm memory test, hold the harness fixed and report cost; a memory arm that shrinks context may look good or bad depending on the harness overhead it rides on.
- Cost claims from vendors ("X% cheaper with our memory") should be asked "in which harness, at what baseline context".
- Consider a minimal-harness arm when measuring whether memory reduces tokens.

## Open questions
- Per-task traces and the 5x case.
- Does the harness gap persist on long multi-session tasks where memory matters?
- How much of Claude Code's overhead is cached (cheap) vs uncached input?

## Grading and labels
- Directness high; control medium (matched tasks and prices, but harness is a bundle); independence medium (academic, sponsor ties noted); reproducibility medium (dashboard data pinned, traces pending); applicability high.
- Pillars: R6 primary (whether a model evaluation supports its conclusion when the harness is unreported, cost accounting), R3 secondary (initial-context size as the cost driver). Tags: cost.
- Beliefs: would create a belief on harness as a cost confounder. No held belief contradicted; nothing in the synthesis addresses harness cost.

## Origin chain
post 2104172198537855432 (@rajeevchhajer) -> harnesstax.github.io (JS app) -> site repo HarnessTax/HarnessTax.github.io at f8a8281, blog JSON -> Experiment Setup and Findings 1 to 3 -> this note. Independence: related third-party record plurnk/harnesstax-evidence ("Raw record of plurnk benchmark campaigns on the HarnessTax SWE-bench Lite task set", not read). No shared authors with CliffCompaction (N-20260928-01).
