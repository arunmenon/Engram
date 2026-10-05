---
schema_version: 1
artifact_id: N-20260929-14
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104637466904818104", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2603.04257
claim_cluster: arxiv:2603.04257
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2603.04257
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R3
pillar_secondary: ["R5", "R2"]
memory_stage: assembly
tags: {"mechanism": ["indexed-summary-plus-archive", "learned-compress-and-read", "grpo", "context-budget-penalty", "segmented-trajectories"], "workload": ["modified-alfworld", "long-horizon-agent"], "lifecycle_stage": ["write", "read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: the headline numbers are in Figure 4 and its caption, but test-set size and seeds are not stated", "control": "low: the only comparison is the same model before RL training; no summarisation-only, similarity-retrieval or full-context baseline", "independence": "low: one lab (Accenture Center for Advanced AI), one environment built by the authors", "reproducibility": "low: no code link found, test split, seeds and episode counts not stated", "applicability": "medium: the archive-plus-index design matches our keep-the-source preference, but the task is a modified household text game in which retrieval is made mandatory"}
beliefs_affected: {"supports": ["B16"], "contradicts": [], "would_create": ["An RL-trained agent can learn to archive full-fidelity blocks behind a short index and read them back on demand, reducing peak working context about 43% on an in-distribution long-horizon task; whether it beats a hand-written archive policy is untested"]}
claim_correction: The post presents 24.2% to 85.6% as Memex beating standard agents at the same context budget; the paper's 24.2% is the same Qwen3 model with the same Memex tools before RL training, on a modified ALFWorld used for both training and evaluation, with no summarisation or retrieval baseline and no stated test-set size.
---

# Memex(RL): Scaling Long-Horizon LLM Agents via Indexed Experience Memory (arXiv 2603.04257)

- **URL:** https://arxiv.org/abs/2603.04257 (full text read at https://arxiv.org/html/2603.04257v1)
- **Type:** paper
- **Author / org:** Zhenting Wang, Huancheng Chen, Jiayun Wang, Wei Wei; Center for Advanced AI, Accenture
- **Date:** 2026-03-04 (v1)
- **Retrieved:** 2026-09-29 (v1, HTML). Found through the arXiv API because the post gives no link.
- **Cited by evidence:** @AviPilcer, https://x.com/AviPilcer/status/2104637466904818104 ("24.2% task success jumped to 85.6%. Using 43% less context"; no paper link). Also summarised second-hand in the memory digest brief of 2026-09-29.
- **Relevance to a memory stack:** medium. The design (short index in context, full-fidelity archive outside, explicit read-back) is the "keep the source, retrieve on demand" pattern; the evidence for learning it with RL is weak.

## TL;DR
- Memex keeps an "Indexed Summary" in context (progress plus index-to-description pairs) and moves full content blocks to an external key-value store; the agent calls `CompressExperience` to archive and rewrite its context and `ReadExperience(index)` to pull a block back.
- MemexRL trains the agent (Qwen3-30B-A3B-Thinking-2507) with GRPO on a reward of task success minus penalties for context over 8,000 tokens, redundant tool calls and format errors.
- **Claim correction.** "MemexRL increases the task success rate from 24.22% to 85.61%, while reducing the peak working context length from 16934.46 to 9634.47 tokens" (Figure 4). The comparison is the same model before RL training, in the same modified ALFWorld used for training, where "look" is limited to once per episode so location ids "can only be recovered through ReadExperience". There is no summarisation-only, similarity-retrieval or full-context baseline, and the test-set size and seeds are not stated.
- Learned behaviour: `CompressExperience` calls fall from 6.5 to 3 per episode and `ReadExperience` calls rise from 1 to 6 to 7 (Figure 5): archive less often, read back more.
- The theoretical result is conditional: if the summary is decision-sufficient with at most B dereferences, the policy matches full-context optimality; the paper does not show MemexRL finds such summaries.

## What it claims / describes
**Context layout.** `M = [m0, u, M_work]`: system prompt, task instruction (never compressed), and a dynamic working context. The Indexed Summary sigma holds "actionable progress" and index-description pairs pointing into the experience store D (index to full-fidelity content block).

**Operations.**
- `CompressExperience(IndexedSummary, MemoryBlocks)`: writes blocks to D and replaces the working context with the indexed summary. In experiments "The summary produced by CompressExperience is truncated to 300 tokens."
- `ReadExperience(index)`: dereferences archived blocks into context.
- `ContextStatus(M, tau)`: reports working-context tokens against the threshold.

**Training (MemexRL).** GRPO-style group-relative advantages (Equation 2). Reward (Equation 1): `R = R_task - P_context - P_redundancy - P_format` with
- `P_context = min(1, sum max(0, C_t - tau) / (tau * T))`, tau = 8,000 tokens, context window 32K;
- `P_redundancy = N_redundant / N_tool_call` (identical tool name and arguments with no state change);
- `P_format = N_malformed / N_tool_call`.
Episodes with k compressions are split into k+1 segments sharing the terminal reward. Model: Qwen3-30B-A3B-Thinking-2507 (MoE, about 3B active). Training set: "3553 tasks" from modified ALFWorld; batch 32 prompts, group size 8; Adam, lr 5e-6, weight decay 0.1, KL 0.001.

**Environment modifications.** Hidden admissible commands, hidden initial observation, "the look action is restricted to once per episode. After the first use, the location IDs can only be recovered through ReadExperience, creating an explicit dependency on the memory retrieval mechanism", and the 300-token summary cap. Success is environment-verified goal state.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| task success | 85.61% | 24.22% (same model before RL) | modified ALFWorld, Figure 4; test size not stated | in-distribution; no other baselines |
| peak working context | 9,634.47 tokens | 16,934.46 tokens | Figure 4(b), "approaching the penalty threshold of 8,000 tokens" | same |
| rollout success during training | "from approximately 20% to over 90%" | | training curves, Figures 2 to 3 | training rollouts, not held-out |
| total penalty during training | -0.4 to -0.1 | | Figures 2 to 3 | |
| CompressExperience calls per episode | 6.5 to 3 | | Figure 5 | |
| ReadExperience calls per episode | 1 to 6-7 | | Figure 5 | |
| training tasks | 3,553 | | modified ALFWorld | |

## Mechanism details you could implement
- A two-tier working context: a capped index (300 tokens in the paper) of "what was done, where the evidence is" plus an external store of verbatim blocks addressed by stable ids. Never compress the task instruction.
- Expose three tools to the agent: archive (write blocks, rewrite context), read(id), and a context-status probe with the budget.
- If training or tuning a policy, penalise overflow above a soft budget proportionally, penalise identical repeated tool calls, and share the terminal reward across compression segments.
- For a hand-written policy (inference): archive tool outputs verbatim, keep only ids and one-line descriptions in context, and read back by id before acting on a detail (error codes, file paths).

## Limitations, caveats, counter-evidence
- One environment, trained and tested in-distribution; the modifications make retrieval mandatory, which favours a memory-read policy by construction.
- No comparison with summarisation-only compaction, retrieval by similarity, or a full-context run under the same 32K window; the gain cannot be attributed to Memex versus RL on the task itself (inference).
- Test-set size, seeds, runs and variance not stated; no confidence intervals.
- No explicit limitations section. No code link found in the text read.
- The propositions assume decision-sufficient summaries; they are not evidence that the learned summaries are sufficient.
- Consistent with, but not evidence for, the synthesis view that summaries lose evidence: the paper does not measure information loss from summarisation.

## Takeaways for tuning a memory stack
- Treat the archive-and-index pattern as a candidate arm for long engineering sessions (incident agents, multi-hour coding), compared against summarisation compaction and truncation, not as a proven win.
- Measure read-backs per episode and peak working context alongside success; the learned policy's shift toward fewer archives and more reads is the behaviour to look for.
- Keep the task instruction and stable evidence ids outside any compression step.

## Open questions
- What does a hand-written archive-plus-index policy score on the same modified ALFWorld without RL?
- How does it compare to summarisation-only and to verbatim truncation (see bus card PC-20260928-01 on truncate-not-rewrite)?
- Does it transfer to tasks where re-observation is cheap (the unmodified environment), or to coding tasks?

## Grading and labels
- Directness: medium; headline numbers in a figure caption, evaluation size not stated.
- Control: low; only the pre-RL model as a baseline.
- Independence: low; one lab, one self-modified environment.
- Reproducibility: low; no code link, no seeds, no test split stated.
- Applicability: medium; the design fits our keep-the-source principle, the task does not resemble engineering work.
- Strength: paper-single-benchmark.
- Pillars: R3 primary (context assembly under a budget); R5 (learned memory operations), R2 (archive as a state change) secondary. Memory stage: assembly.
- B16 supports (weakly): verbatim archived blocks read back on demand outperform relying on the summary alone in this setup; not a controlled comparison.
- Would create: an RL-trained agent can learn archive-and-read-back, cutting peak context about 43% in-distribution; untested against a hand-written policy.
- Contradiction rows: none.

## Origin chain
- Post @AviPilcer 2104637466904818104 (no link) -> arXiv API search "MemexRL" -> arXiv 2603.04257v1 HTML, Equations 1 to 2, Figures 2 to 5, experimental setup -> this note.
- Independence: no shared authors with other bus notes known; the digest's summary of the same result is second-hand from the same post.
