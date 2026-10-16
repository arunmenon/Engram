---
schema_version: 1
artifact_id: N-20260928-01
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104172198537855432", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26779
claim_cluster: arxiv:2609.26779
feeds: ["memory", "decision"]
primary_source: https://arxiv.org/abs/2609.26779
source_commit: b48d660ae3c1f6037094d6cfc6b5d9f5938a7957
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R2", "R1"]
tags: {"mechanism": ["context compaction", "truncation", "summarisation", "sliding window"], "workload": ["coding agents", "long-horizon tasks", "Terminal-Bench 2.0", "SWE-bench Verified", "KernelBench"], "lifecycle_stage": ["in-session context management", "read-time assembly"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: measures resolve rate and cost of each compaction method directly on agent benchmarks", "control": "medium: compaction methods compared at a matched 16K threshold with one model (Table 6), error bars over runs, but no component ablation of the truncation rules", "independence": "medium: CMU and Bosch authors with no stake in the compared scaffolds; one group, one method family", "reproducibility": "high: open-source proxy pinned at commit b48d660; public benchmarks; run count per cell not stated in the extract", "applicability": "high: coding agents on long sessions, exactly our build-time engineering workload"}
beliefs_affected: {"supports": ["B5"], "contradicts": [], "would_create": ["Verbatim truncation of old tool output (drop results over 500 chars, keep signatures) matches or beats LLM summarisation for in-session compaction of coding agents at about the same cost"]}
claim_correction: The post says "truncate, never rewrite, up to 50% cheaper + SOTA on KernelBench"; on SWE-bench Verified at 16K the plain sliding window scored highest (72.80 vs CliffCompaction 71.33 vs summarisation 70.27, Table 6), and summarisation was slightly cheaper (-23% vs -21%), so the win over summarisation is small on SWE-bench and the 50% saving is on Terminal-Bench full-context comparisons.
---

# CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding Agents (arXiv 2609.26779)

- **URL:** https://arxiv.org/abs/2609.26779 (HTML full text https://arxiv.org/html/2609.26779); code https://github.com/nguyenvuthientrang/cliffcompaction
- **Type:** paper + repo
- **Author / org:** Trang Nguyen, Eulrang Cho, Tim Dettmers (Carnegie Mellon University); Bingqing Chen (Bosch Center for AI)
- **Date:** submitted 2026-09-22
- **Retrieved:** 2026-09-28; arXiv abstract and HTML; repo shallow clone at `b48d660ae3c1f6037094d6cfc6b5d9f5938a7957` (2026-09-22 23:33:39 -0400, "Banner: absolute URL for PyPI"), local copy `repos/cliffcompaction` (README read; code not executed)
- **Cited by evidence:** @rajeevchhajer weekly reading list, https://x.com/rajeevchhajer/status/2104172198537855432 ("CliffCompaction: truncate, never rewrite. Up to 50% cheaper + SOTA on KernelBench")
- **Relevance to a memory stack:** high. It is a controlled comparison of summarising vs verbatim-truncating vs sliding-window compaction for coding agents, the closest published measurement to our B5 question (does rewriting history into summaries help), and it touches replay: a summary is a new, unreproducible artifact, a truncation is a deterministic function of the log.

## TL;DR
- CliffCompaction compacts a coding agent's context by **truncating, not rephrasing**: tool results over 500 characters are dropped, results up to 500 characters kept verbatim, tool calls reduced to signatures, agent thoughts cut to 300 characters, system prompt and task kept, the K most recent turn pairs kept unchanged. Previous compactions are discarded entirely, so each "cliff" compresses only the latest live session.
- On Terminal-Bench 2.0 it resolves as many or more tasks than full context at roughly half the cost (Kimi K2.6: 61.42 +/- 1.30 vs 59.16 +/- 3.41, $0.19 vs $0.40; GLM 5.1 16K: 54.33 +/- 2.35 vs 49.83 +/- 3.42, $0.27 vs $0.54).
- Head-to-head at a 16K threshold on SWE-bench Verified (Kimi K2.7, Table 6): sliding window 72.80 +/- 2.43 (cost +9%), CliffCompaction 71.33 +/- 0.50 (-21%), summarisation + microcompaction 71.00 +/- 0.69 (-17%), LLM summarisation 70.27 +/- 0.95 (-23%). Differences are within about one to two standard deviations (inference).
- On KernelBench Level 3 with Kimi K2.7 at 200 steps, CliffCompaction (128K) reached 2.23x speedup vs 1.30x without compaction (256K); at 400 steps 3.58x.
- **Claim correction:** "truncate, never rewrite" is supported against summarisation, but on SWE-bench the simplest sliding window was most accurate, and the 50% saving is against full context on Terminal-Bench, not against summarisation.

## What it claims / describes
Agents on long tasks exceed their context window and must compact. Summarising compaction (the Claude Code default) rewrites older turns into an LLM summary; repeated summarisation of summaries can drift ("context drift through iterative compaction"). CliffCompaction instead lets context grow until a token threshold (tested at 8K, 16K, 32K, 45K, 128K, 200K), then applies deterministic truncation rules to the current live session only, discarding previous compacted history. The name refers to the sawtooth "cliff" in context length. The paper frames this as "maximizing compaction precision at the expense of recall": what survives is verbatim, but more is dropped.

It is shipped as a transparent API proxy: point an agent's base URL at it (`cliff enable`, defaults to Claude Code; Codex via a provider block in `~/.codex/config.toml`), and "the agent is unchanged and unaware" (README).

Harnesses: mini-swe-agent (SWE-bench Verified), OpenHands (SWE-bench Verified, KernelBench), Terminus-2 (Terminal-Bench 2.0), Claude Code (Terminal-Bench 2.1). Models: Kimi K2.5/K2.6/K2.7, GLM 4.7 Flash to 5.3 Flash, GPT-5-mini, GPT 5.3 Codex, Opus 4.6/4.7.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| % resolved, Kimi K2.6 | 61.42 +/- 1.30 (32K and 16K) | full context 59.16 +/- 3.41 | Terminal-Bench 2.0, Terminus-2, Table 2 | n tasks and runs per cell not in extract |
| cost per task, Kimi K2.6 | $0.19 | $0.40 full context | same | |
| % resolved, GLM 5.1 | 53.20 +/- 5.31 (32K), 54.33 +/- 2.35 (16K) | 49.83 +/- 3.42 | same | |
| cost, GLM 5.1 | $0.34 (32K), $0.27 (16K) | $0.54 | same | |
| % resolved, GLM 5.3 Flash in Claude Code | 76.69 +/- 1.41 (45K) | 73.03 +/- 3.04 (200K full) | Terminal-Bench, Claude Code harness | cost $0.16 vs $0.21 |
| SWE-bench Verified, Kimi K2.6 | 73.27 +/- 0.12 (32K), 71.87 +/- 1.31 (16K), 67.60 +/- 1.06 (8K) | 73.87 +/- 0.31 full | mini-swe-agent, Table 3 | accuracy falls at 8K |
| SWE-bench Verified, GLM 5.1 | 68.80 +/- 1.59 (32K), 69.33 +/- 1.10 (16K), 65.13 +/- 0.76 (8K) | 71.40 +/- 0.72 full | same | compaction costs 2 to 6 points here |
| cost SWE-bench, 32K/16K | Kimi $0.18/$0.17, GLM $0.20/$0.15 | Kimi $0.19, GLM $0.25 | same | small savings on short-horizon SWE tasks |
| method comparison, SWE-bench 16K Kimi K2.7 | CliffCompaction 71.33 +/- 0.50, cost -21% | sliding window 72.80 +/- 2.43 (+9%); summarisation 70.27 +/- 0.95 (-23%); summ + microcompaction 71.00 +/- 0.69 (-17%) | Table 6 | only matched-threshold head-to-head |
| method comparison, KernelBench L3 | CliffCompaction 3.58x speedup, $8.32 | sliding window 2.86x $21.52; summarisation 3.47x $8.10; summ + micro 3.33x $12.84 | Table 6 | |
| KernelBench L3, Kimi K2.7, 200 steps | 2.23x speedup, 94% accuracy | no compaction 256K: 1.30x, 86% | Table 5 | |
| test-time scaling, Kimi K2.6 16K + SGV, k=3 | practical 69.7% at $58.01 | Opus 4.7 single 69.4%; GPT 5.3 Codex 64.7% at $64.63 | Terminal-Bench 2.0, Table 4 | "+10.5pts @ 1.9x" |

## Mechanism details you could implement
Truncation rules as reported (Section on method):
```text
tool result > 500 chars   -> dropped
tool result <= 500 chars  -> kept verbatim
tool call                 -> signature: tool name, target file, essential args (embedded content removed)
agent thought             -> truncated to 300 chars
system prompt, task text  -> kept in full
last K turn pairs         -> kept unchanged
trigger                   -> context crosses threshold T (8K..200K); previous compacted history discarded
```
Deployment shape: a stateless proxy between the harness and the model API that rewrites the request body. For a memory stack this is the "summary as cache, log as source of truth" pattern: the full log stays in the ledger; the served context is a deterministic projection of it (inference).

## Limitations, caveats, counter-evidence
- Authors: "The benefits CliffCompaction brings depend on the scaffold and on the task ... cost savings grow with the complexity of the scaffold itself ... the benefit is meaningful only for medium-to-long-horizon tasks."
- Authors: "Our comparison is limited to methods that act on the conversation history itself at inference time. We do not compare against approaches that train the model to manage its own context, or that maintain an external memory store." So it says nothing about retrieval-based memory as the alternative.
- No systematic component ablation (which rule matters: the 500-char cut, the 300-char thought cut, discarding old compactions).
- On SWE-bench Verified the sliding window was the most accurate method at 16K; CliffCompaction's advantage over summarisation there is about one point with overlapping spread (inference).
- Standard deviations are shown but the number of runs and tasks per cell were not in the extract (unknown).
- The proxy rewrites requests invisibly to the agent (README: "the agent is unchanged and unaware"). For governance this means what the model saw differs from what the harness logged unless the proxy logs its output (inference, R1/R8).

## Takeaways for tuning a memory stack
- Treat in-session compaction as a deterministic projection of the log, not a rewrite: verbatim fragments plus signatures are at least as good as summaries here, and they are replayable.
- Always include a sliding-window arm: it was the strongest accuracy baseline on SWE-bench at 16K.
- Keep the full log (ledger) regardless; truncation drops large tool outputs, so a retrieval path back to them is the natural complement (inference).
- The result supports keeping summarising consolidation off by default (B5), though it is in-session compaction, not scheduled memory consolidation.

## Open questions
- Runs and tasks per cell, and per-task variance, for Tables 2, 3, 6.
- Does truncation plus a retrieval tool over the dropped outputs beat both?
- How do the rules behave on long structured artifacts (specs, diffs) where a single tool result is legitimately large?

## Grading and labels
- Directness high: resolve rate and dollar cost per method on agent benchmarks.
- Control medium: matched-threshold head-to-head exists (Table 6) for one model; the rest compare to full context.
- Independence medium: academic authors, no vendor stake; single group.
- Reproducibility high: pinned open-source proxy, public benchmarks.
- Applicability high: coding agents, long sessions.
- Pillars: R3 primary (bounded context assembly), R2 secondary (rewrite vs preserve semantics), R1 secondary (a truncation is reproducible from the log, a summary is not).
- Beliefs: supports B5 (summarising compaction is not better than a verbatim alternative; nearest measurements negative or null); would create a belief on truncation vs summarisation for in-session compaction. No contradiction with a held belief or the synthesis.

## Origin chain
post 2104172198537855432 (@rajeevchhajer, reading list) -> arXiv 2609.26779 abstract and HTML -> Tables 2 to 6 and limitations section -> repo README at b48d660 -> this note. Independence: shares no authors with HarnessTax (UC Berkeley) or the other items in the same reading-list post; Tim Dettmers is also the author of the dLab post in the same list.
