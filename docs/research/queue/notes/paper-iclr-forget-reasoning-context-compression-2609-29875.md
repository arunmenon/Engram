---
schema_version: 1
artifact_id: N-20260928-29
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:08:43Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.29875
claim_cluster: arxiv:2609.29875
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.29875
source_commit: v1
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R2"]
memory_stage: assembly
tags: {"mechanism": ["context compression", "reasoning-block deletion", "proxy entropy ranking", "[SKIP] placeholder"], "workload": ["long-horizon agent", "code", "office", "security", "web"], "lifecycle_stage": ["assembly", "working memory"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: measures reward and token use of an in-context compression policy on long-horizon agent tasks including 80 code tasks", "control": "medium: baselines (8 context-management methods on Pilot40) and ablations incl. delete-all-thinking and random deletion; but no seeds, runs per task or CI stated for the 260-task headline", "independence": "low: TierFlow team authors; WorkBuddyBench authorship and public availability not stated; reward computation not stated as read", "reproducibility": "low: no code URL found; agent DeepSeek-V4-Flash and scorer Qwen3.5 9B named", "applicability": "medium: coding is one domain and ICLR lost reward there (-0.064) while raising tokens"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["Dropping an agent's past reasoning blocks while keeping actions, tool calls and observations cuts tokens without average reward loss; on code tasks the one measurement shows a reward loss"]}
claim_correction: Numbers match (0.699 -> 0.718; -25.5% / -14.4% / -33.3%), but the +0.019 average is carried by the Security domain (+0.229) while Code (-0.064, with +6.35% input and +16.21% output tokens), Office (-0.042) and Web (-0.022) all lost reward, and no seeds or interval are reported for the headline.
---

# When Can Agents Forget Their Reasoning? ICLR for Long-Horizon Agent Context Compression (arXiv 2609.29875)

- **URL:** https://arxiv.org/abs/2609.29875 (full text read at https://arxiv.org/html/2609.29875)
- **Type:** paper
- **Author / org:** Mingxuan Wang, Fei Luo, Bo Wang, Guorun Yao, Yinglong Guo, Chao Ning, Hongyue Chen (TierFlow Team); Yanbiao Ma (Gaoling School of AI, Renmin University of China); Jungong Han (Tsinghua University)
- **Date:** v1 submitted 2026-09-24; 30 pages
- **Retrieved:** 2026-09-28, arXiv v1 (abstract and HTML full text). No code URL found.
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI, roundup item 3, feed memory)
- **Relevance to a memory stack:** medium. Working-memory (in-context) policy for long agent runs: which parts of history can be dropped. Directly relevant to our coding agents' context budget, but the coding-domain result is negative.

## TL;DR
- ICLR splits the agent's past reasoning text into blocks on `\n\n`, scores each block by mean token entropy under a frozen proxy (Qwen3.5 9B), removes the lowest floor(0.8N) blocks, replaces them with a literal `[SKIP]`, and never touches actions, tool calls or observations. Runs before every request after the first; skipped when scorer input exceeds 42K tokens.
- 260 WorkBuddyBench tasks (Code 80, Office 50, Security 60, Web 70), agent DeepSeek-V4-Flash: reward 0.699 -> 0.718; input -25.48%, output -14.41%, cache read -33.28%; W/T/L 102/76/82.
- **Claim correction:** per domain (Table 2), Code 0.770 -> 0.706 (-0.064) with input +6.35% and output +16.21%; Office 0.818 -> 0.776 (-0.042); Web 0.721 -> 0.699 (-0.022); Security 0.478 -> 0.707 (+0.229). The average gain is one domain; on code it cost reward and tokens.
- Ablation (80-task set): deleting all thinking already gets 71.78 vs ICLR 73.76 vs base 62.67; most of the gain comes from dropping reasoning at all, the entropy ranking adds about 2 points (single numbers, no intervals as read).
- Compared with bus note `paper-cliffcompaction-truncate-not-rewrite-2609-26779.md` (CliffCompaction, coding agents, "truncate, not rewrite", by title): same direction (delete stale history instead of summarising it; ICLR beat summarising compactors such as SelfCompact 65.9 and ACON-Core 63.3 on Pilot40). But ICLR's own code domain lost 0.064 reward, so for coding agents this paper is a caution, not support (inference; we cannot read the CliffCompaction note).

## What it claims / describes
**Question.** When is accumulated reasoning safe to drop? Thesis: reasoning is "dynamic working state, not permanent history"; it becomes replaceable once derived state is externalised into code, files or tool outputs.

**Method (Appendix C.2 and method section).**
1. Segment each past assistant reasoning trace into blocks: "double newline boundaries as a deterministic segmentation rule".
2. Score each token with a frozen proxy: H(t) = -sum_v p(v | c_t) log2 p(v | c_t); block score = mean over the block's tokens.
3. Remove the lowest floor(0.8N) nonempty blocks (no removal when N = 1). Fixed 80% ratio over blocks, not tokens.
4. Replace removed blocks with `[SKIP]`. Actions, tool calls, observations unchanged.
5. Apply before each request after the first; skip when the scorer input exceeds 42K tokens.

**Evidence for the externalisation thesis.** Linear probe on the frozen 9B model's hidden states predicting compression boundaries: AUROC 0.844, AP 0.811, balanced accuracy 0.760 (265 samples, 31 tasks, task-level nested splits; Table 12). Activation patching KL repair rises from 0.047 (layer 4) to 0.978 (layer 31) (Table 13). Future behavioural risk 67.31% without externalised derived state vs 36.2% with it (Tables 14 and 15). Controlled interventions (Tables 16 and 17): keeping only the latest reasoning preserves the rule score (0.872); deleting only the latest drops it to 0.760; clearing reasoning after code is written to disk leaves the score unchanged (0.759); hiding stderr makes the agent re-issue the same Bash call.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Reward, all | 0.718 | base 0.699 | Table 2, 260 tasks | no seeds/CI stated; W/T/L 102/76/82 |
| Input / output / cache-read tokens | -25.48% / -14.41% / -33.28% | base | Table 2 | total 2.69M -> 2.19M (-18.5%) as read |
| Code reward | 0.706 (-0.064); input +6.35%, output +16.21% | 0.770 | Table 2, 80 tasks | compression cost reward and tokens |
| Office reward | 0.776 (-0.042); input -2.50%, output -2.55% | 0.818 | 50 tasks | |
| Security reward | 0.707 (+0.229); input -35.23%, output -31.02% | 0.478 | 60 tasks | carries the average |
| Web reward | 0.699 (-0.022); input -37.16%, output -19.04% | 0.721 | 70 tasks | |
| Pilot40 comparison | ICLR 70.3 | base 67.5; SelfCompact 65.9; SAM 65.9; ACON-Core 63.3; LLMLingua-2 62.0; SWE-Pruner 60.5; Sculptor 59.3; PACE 58.4; ACM 33.7 | Table 1, 40 tasks | different task set and scale from Table 2 |
| Ablation, 80-task set | ICLR 73.76 (+11.09) | base 62.67; delete all thinking 71.78; step-only entropy 71.14; random 10% 67.56 | Table 3 | delete-all cuts input 62.9% |
| Random token deletion | 10% deletion -> input -60.53%; 20% -> -44.01% | | ablation | non-monotonic, "trajectory amplification" |
| Probe for compression boundary | AUROC 0.844 | | Table 12, 265 samples, 31 tasks | |

Text vs table: the summary says ICLR "improved reward"; Table 2 shows it improved in 1 of 4 domains.

## Mechanism details you could implement
- Keep every action, tool call and observation verbatim; delete the agent's own past reasoning text; leave a `[SKIP]` marker so the transcript structure stays intact.
- Simplest arm first: delete all prior reasoning (71.78 vs ICLR 73.76 on the ablation set, larger token cut). Entropy ranking needs a second model on the path.
- Keep the latest reasoning block: deleting only the latest dropped the rule score 0.872 -> 0.760.
- Make sure derived state is externalised (files written, stderr visible) before dropping reasoning; hidden stderr caused repeated tool calls.
- Deletion (truncation) rather than rewriting preserves cache prefixes better (inference: cache-read tokens -33%).

## Limitations, caveats, counter-evidence
- No explicit limitations section in the main text as read; Appendix L (broader impact) not returned by the fetch.
- No runs per task, seeds, or interval for the 0.699 -> 0.718 difference as read; Appendix D.3 describes a task-level bootstrap but we did not find it applied to the headline.
- Reward computation for WorkBuddyBench and its authorship and availability are not stated as read. The same "Wang et al." group's PaMER paper (arXiv 2609.27286, in the same post) also reports on WorkBuddyBench (inference: possibly an in-house benchmark).
- Fixed 80% ratio; 42K-token scorer limit with no reported skip rate; only one proxy model.
- Coding domain: reward -0.064 with more tokens. For our coding agents this is the relevant row.
- Appendix A AI-use statement: generative AI used for "language editing, drafting assistance, and literature discovery". No instruction-bearing content found in the paper or post.

## Takeaways for tuning a memory stack
- For long engineering-agent runs, test "drop old reasoning, keep tool I/O" as a cheap context policy, but measure per task type; coding lost reward here.
- Prefer deletion to rewriting when cache reuse matters (cache-read -33%).
- Externalise state (notes files, test output) so reasoning can be dropped safely; this is a design rule for agent scratchpads.
- Do not trust an average across domains; report per domain.

## Open questions
- Why did code tasks lose reward and gain tokens? Not analysed as read.
- Headline variance across runs? Not stated.
- Does the gain survive a different agent model (Claude, GPT)? Not tested.

## Grading and labels
- **Directness: medium.** Agent reward and tokens on long tasks; includes a code domain.
- **Control: medium.** Many baselines and a delete-all ablation, but no variance on the headline.
- **Independence: low.** Company team on a benchmark of unstated origin.
- **Reproducibility: low.** No code URL.
- **Applicability: medium.** Relevant policy; negative on code.
- **Pillars:** R3 primary (what to keep in context); R2 secondary (retirement of working-state history).
- **Stage:** assembly.
- **Priority:** none matched.
- **Beliefs affected:**
  - Supports B20: the post's "improved reward" needed narrowing per domain.
  - B5 (scheduled summarising consolidation, nearest measurements negative): not about long-term consolidation; weakly consistent in that summarising compactors (SelfCompact, ACON-Core) scored below the uncompressed base on Pilot40; no belief change.
  - Would create: dropping past reasoning while keeping tool I/O cuts tokens without average reward loss, but lost reward on code.
- **Against the synthesis and bus notes:** consistent in direction with CliffCompaction (truncate, not rewrite) by title; the code-domain loss is a caution for that note's coding-agent setting. No contradiction row against a belief.
- **Arm-vs-arm test this quarter (frozen harness):** arm A no compression vs arm B delete all prior reasoning blocks (keep actions, tool calls, observations and the latest block, `[SKIP]` marker) vs arm C CliffCompaction-style truncation; metric: coding task pass rate, input and cache-read tokens, 3+ seeds.

## Origin chain
- Post 2104583094078525629 (@RubberDucky_AI, roundup item 3) -> arXiv 2609.29875 v1 -> Table 2 (full 260, per domain), Table 1 (Pilot40), Table 3 (ablations), Tables 12 to 17 (externalisation analysis), Appendix C.2 (segmentation).
- Independence: one post (a roundup, likely machine-generated, inference); authors TierFlow team plus Renmin and Tsinghua; benchmark possibly shared with the same group's PaMER paper (2609.27286). No shared authors with CliffCompaction as far as the titles show (unknown).
