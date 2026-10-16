---
schema_version: 1
artifact_id: N-20260928-20
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:08:43Z
input_refs: [{"artifact_id": "post:2104488796209508678", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.23570
claim_cluster: arxiv:2609.23570
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.23570
source_commit: v1
strength: paper-ablated
pillar_primary: R6
pillar_secondary: ["R5", "R3"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["experience injection", "top-1 retrieval", "structured experience record", "failure attribution"], "workload": ["coding agent", "SWE-style repository tasks"], "lifecycle_stage": ["write", "retrieval", "assembly"], "cross_cutting": ["cost", "memory benchmark", "shared_state"]}
evidence_grade: {"directness": "high: resolve rate measured by executable tests on real repository tasks for coding agents, memory-off matched", "control": "medium: matched memory-off, irrelevant-memory control, 4 seeds per target, target-level bootstrap CIs, strip ablation; but the injection arm is target-aware and targets were selected for positive injection uplift on the reference solver, retrieval is top-1 only, memory-side tokens not recorded", "independence": "medium: SIAT/SUAT and Alibaba authors, no stake in Mem0, SimpleMem, MemoryOS or A-MEM stated; histories and memory extraction both use deepseek-v4-flash, the reference solver", "reproducibility": "medium: code URL stated (AlibabaResearch/DAMO-ConvAI/VibeMemBench), open-weight solvers, 4 seeds; repo not cloned or read here", "applicability": "high: coding agents on repository tasks is our workload; no Claude or GPT solvers, SWE-rebench V2 repos only"}
beliefs_affected: {"supports": ["B7", "B20"], "contradicts": ["B16"], "would_create": ["Off-the-shelf memory systems (Mem0, SimpleMem, MemoryOS, A-MEM) retrieving top-1 from raw coding-agent histories do not beat memory-off on executable repository tasks; the form of the served record, not its ranking, is the dominant failure"]}
claim_correction: Post numbers match, but the +1.1 to +4.5 pp injection lift has every 95% CI crossing zero (authors call it directional), the injected experience is target-aware and targets were pre-selected for injection uplift so it is an upper bound not a deployable memory, and "69% of failing pairings" is 160 of 231 target x solver x system triplets on two solvers, not 69% of the 11 failing solver x system pairings.
---

# VibeMemBench: Evaluating Memory Systems for Coding Agents on Real Repository Coding Tasks (arXiv 2609.23570)

- **URL:** https://arxiv.org/abs/2609.23570 (full text read at https://arxiv.org/html/2609.23570)
- **Type:** paper
- **Author / org:** Liyang Fan, Yingcheng Shi, Yongbin Li, Chenghao Sun, Xin Chen, Xander Xu, Hu Wei, Shiwen Ni, Min Yang, Jieping Ye. Shenzhen Institutes of Advanced Technology (CAS), SUAT, Alibaba Group / Alibaba Token Hub. Corresponding: Yongbin Li (Alibaba), Min Yang (SIAT). Code stated at https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/VibeMemBench
- **Date:** v1 submitted 2026-09-20
- **Retrieved:** 2026-09-28, arXiv v1 (abstract page and HTML full text; repo not cloned, it is a subtree of the large DAMO-ConvAI monorepo)
- **Cited by evidence:** https://x.com/runbywren/status/2104488796209508678 (@runbywren, 2026-09-28, feed memory, 3 views)
- **Relevance to a memory stack:** high. The first benchmark we have seen that measures whether memory systems (including Mem0) raise executable resolve rate for coding agents against a matched memory-off baseline, with a failure taxonomy that points at the record format rather than the retriever.

## TL;DR
- 111 targets from 90 SWE-rebench V2 repositories, 3,634 completed history trajectories (MiniSWEAgent, deepseek-v4-flash, one seed, temperature 0.5, 250-step limit). Resolution is decided by executable tests, 4 seeds per target and condition, 95% CIs by target-level percentile bootstrap (10,000 resamples).
- Injecting a "frozen verified experience" (one short structured record: bug class, root cause, fix pattern, reusable lesson) raised resolve on 4 of 5 held-out solvers by +1.1 to +4.5 pp (deepseek-v4-pro +0.0) and cut steps on all five. **Claim correction:** every one of these CIs crosses zero (e.g. kimi-k2.7-code +4.5, CI [-0.23, +9.46]); the record is built target-aware and targets were kept only if injection lifted the reference solver, so this arm is an oracle-assisted upper bound, not a memory system.
- When Mem0, SimpleMem, MemoryOS or A-MEM retrieve top-1 from the same history, 11 of 12 solver x system pairings do not beat memory-off (only glm-5 + MemoryOS, +2.0, CI [-3.38, +7.43]). Only one pairing is significantly worse (glm-5 + Mem0, -5.5, CI [-10.59, -0.45]).
- Failure attribution: "form degradation" (relevant history reached, fix pattern dropped or buried in raw transcript) is 69.3% (160 of 231) of failing target x solver x system triplets on the deepseek-v4-pro and kimi-k2.7-code rosters; ranking miss only 1.3% (3). **Claim correction:** the post's "69% of failing pairings" reads as 69% of the 11 failing system pairings; it is a triplet-level count on 2 solvers, and the attribution script agrees only weakly with two LLM judges (Cohen's kappa 0.32 and 0.24).
- Compared with the bus note `github-vectorize-agent-memory-benchmark-sdebench.md` (Hindsight vs no memory on sdebench): same question (does memory help a coding agent against memory-off), different systems (Hindsight is not among VibeMemBench's four) and different harness. From the title alone we cannot tell sdebench's direction, so agreement is undetermined; if sdebench shows Hindsight beating no memory, it would be the only system in our catalogue to do so on coding work, and the VibeMemBench "form" finding gives a testable reason why (Hindsight serves merged observations rather than raw transcript chunks, inference from the synthesis section 3).

## What it claims / describes
**Question.** Existing memory evaluations "do not show whether those systems improve executable repository work" (abstract). VibeMemBench measures persistent memory for coding agents under "a declared agent configuration and accounting rule" (Limitations).

**Construction (SIEVE, four stages, section 3).**
1. History trajectories: 3,634 completed trajectories in the target repositories, produced by MiniSWEAgent with deepseek-v4-flash, one seed, temperature 0.5, 250-step limit.
2. Verification: "Inject the source gold patch and execute the declared validation. Discard an instance when the gold patch does not pass."
3. Offline patch-pattern screen using LLM judgment (oracle-assisted): the target gold patch "enters only the offline patch-pattern screen. Test patch remains evaluator-only. Neither artifact may reach target-aware experience construction, runtime memory retrieval, or the target solver context."
4. Target-aware experience construction (Appendix B.2): for each retained history/target pair one record, which "receives the target problem statement, the history problem statement, a compressed history trajectory, and the history final patch" and "contains a bug class, root cause, fix pattern, and reusable lesson"; extracted by deepseek-v4-flash. "The target statement only selects which historical lesson to emphasize." Selection rule (section 3.3, Eq. 1): retain a target only when the reference memory-off rate is below 1 and the reference uplift is positive ("positive deepseek-v4-flash reference uplift by design", section 5).

**Arms.** Memory off; frozen verified experience (direct injection of the record); irrelevant-memory control; each memory system (Mem0, SimpleMem, MemoryOS, A-MEM) ingesting the same histories and retrieving top-1 into a fixed context budget (numeric budget not stated as read). Memory records for the systems are extracted from trajectories by deepseek-v4-flash; embeddings Qwen3-Embedding-4B. A dose curve (1 to 5 records) is run for Mem0 on deepseek-v4-pro.

**Solvers.** Reference: deepseek-v4-flash (used for selection, so excluded from transfer claims). Held-out transfer: deepseek-v4-pro, glm-5, glm-5.2, kimi-k2.7-code, qwen3.8-max. Memory systems were run on three of them (deepseek-v4-pro, glm-5, kimi-k2.7-code).

**Metrics.** Resolved = "the share of target-seed runs whose declared test predicate passes"; 111 targets x 4 seeds = 444 target-seed runs per condition; 4/4 = targets passing in every seed; solver input/output tokens; steps. Memory-side token consumption is not recorded ("The protocol does not record memory-side token consumption ... so they do not enter the comparison across systems", section 4.1). No dollar cost.

**Failure attribution (section 4.4, Tables 4 and 5).** A failing pairing "is a target, solver, and system whose four-seed resolved count falls below the matched memory-off count": 231 over 85 targets. Categories: form degradation, coverage miss, ranking miss, use failure. Form degradation splits into instruction pollution, overgeneralized fix pattern, tool/shell noise, schema omits fix field, fix replaced by symptom, other.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Resolved, deepseek-v4-pro, frozen verified exp. | 67.1% (+0.0), CI [-5.63, +5.86] | memory off 67.1% | Table 1, 111 targets x 4 seeds | steps 47.6 vs 50.3 |
| Resolved, glm-5, frozen exp. | 57.4% (+2.4), CI [-2.25, +7.21] | 55.0% | Table 1 | steps 66.2 vs 77.1 (-10.9); input 1.93M vs 2.45M per run |
| Resolved, glm-5.2, frozen exp. | 80.4% (+3.6), CI [-0.90, +8.11] | 76.8% | Table 1 | no irrelevant-memory control row for glm-5.2 in Table 1 as read |
| Resolved, kimi-k2.7-code, frozen exp. | 74.3% (+4.5), CI [-0.23, +9.46] | 69.8% | Table 1 | 4/4 targets 62 vs 56 |
| Resolved, qwen3.8-max, frozen exp. | 80.2% (+1.1), CI [-2.93, +5.41] | 79.1% | Table 1 | output tokens +5.1k per run |
| Irrelevant-memory control | deepseek-v4-pro 63.7% (-3.4); glm-5 54.3% (-0.7); kimi 69.1% (-0.7) | memory off | Table 1 | also cuts steps (e.g. glm-5 -7.8), so part of the step reduction is not content-specific (inference) |
| Reference solver deepseek-v4-flash | memory off 43.2%, frozen 78.6% | | Table 10 | targets selected on this uplift; not a transfer result |
| Mem0 | deepseek-v4-pro 62.8% (-4.3) [-9.68, +1.35]; glm-5 49.5% (-5.5) [-10.59, -0.45]; kimi 68.0% (-1.8) [-6.53, +2.70] | memory off | Table 2 | only significant negative pairing is glm-5 |
| SimpleMem | 66.9% (-0.2); 53.2% (-1.8); 69.6% (-0.2) | memory off | Table 2 | |
| MemoryOS | 64.6% (-2.5); 57.0% (+2.0) [-3.38, +7.43]; 66.0% (-3.8) | memory off | Table 2 | the single pairing above memory-off |
| A-MEM | 63.1% (-4.0); 52.5% (-2.5); 65.8% (-4.0) | memory off | Table 2 | |
| Pairings not beating memory-off | 11 of 12 | | Table 2, 3 solvers x 4 systems | top-1 retrieval |
| Mem0 dose curve | "stays below the memory-off baseline at every budget from one to five records" | memory off | deepseek-v4-pro, Appendix O | exact values not extracted |
| Form degradation | 69.3% (160 of 231) | | failing target x solver x system triplets, 2 solvers, 85 targets (Table 4) | kappa script vs judges 0.32 / 0.24 |
| Coverage miss / ranking miss / use failure | 16.0% (37) / 1.3% (3) / 13.4% (31) | | Table 4 | |
| Form subtypes | instruction pollution 40.0% (64); overgeneralized fix pattern 18.1% (29); tool/shell noise 10.0% (16); schema omits fix field 8.8% (14); fix replaced by symptom 3.8% (6); other 19.4% (31) | | Table 5, n=160 | percentages are of the 160 |
| Strip ablation | recover 0.60 seeds per pairing (flagged lines removed) vs 0.48 (equal number of random lines removed) | untouched record | 62 of the 64 instruction-pollution pairings, section 4.4 | "the harm operates through transcript volume rather than instruction semantics" |
| Counterfactual replacement | "Replacing each failing record with the frozen verified experience for the same target recovers 196 seeds over the 160 form degradation pairings" | | section 4.4 | target-aware record again |
| Dollar cost | not stated | | | memory-side tokens not recorded |

## Mechanism details you could implement
- **Experience record schema** (Appendix B.2): four fields, `bug class`, `root cause`, `fix pattern`, `reusable lesson`; Appendix K describes the good form as "short and unpolluted with all four fields". Write this at trajectory close, not a raw transcript chunk.
- **Verification before storing**: only keep history whose final patch passes the declared validation (gold patch injected and executed). For our agents (inference): only promote a fix lesson once its patch passed CI.
- **What breaks retrieved records** (Table 5), usable as a write-time lint: instructions copied from the transcript into the record (40%), a fix pattern generalised beyond the case (18%), tool or shell noise (10%), a schema without a fix field (8.8%), the symptom stored instead of the fix (3.8%).
- **Volume matters more than wording** (strip ablation): deleting random lines recovered 0.48 seeds per pairing vs 0.60 for deleting the flagged instruction lines, so shorter records help even before targeted cleaning.
- **Evaluation protocol worth copying for our PDLC benchmark**: matched memory-off per solver, an irrelevant-memory control, 4 seeds per target, target-level bootstrap with seeds kept together, "4/4" counts, steps and tokens per run, and a failure taxonomy (coverage, ranking, form, use).

## Limitations, caveats, counter-evidence
- Limitations section (verbatim): "VibeMemBench measures persistent memory under a declared agent configuration and accounting rule, over 111 targets from an oracle-assisted patch-pattern screen and a positive reference uplift rule that supply no gold retrieval label. The solver pool omits proprietary frontier models such as the Claude and GPT families for reasons of inference budget, so the solver-agnostic protocol stays untested for them."
- The frozen verified experience is target-aware and the target set is filtered for positive injection uplift on the reference solver. The comparison "injection helps, systems do not" is therefore oracle arm vs deployable arm (inference); the transfer solvers are held out from selection but the targets are not.
- All five injection lifts have 95% CIs crossing zero; the authors treat intervals crossing zero as "directional evidence". No multiple-comparison correction.
- Memory systems only at top-1 in the main table (dose curve only for Mem0 on one solver); fixed budget value not given as read; memory systems' extraction model is deepseek-v4-flash, not each product's default (inference: a product-default configuration might differ).
- Failure attribution relies on a script with weak agreement with two LLM judges (kappa 0.32 and 0.24), and covers only 2 of the 3 memory-system solvers.
- Memory-side tokens and cost are not recorded, so no cost/benefit comparison across systems.
- The post text is duplicated in items.jsonl (the post repeats itself, with a malformed link "2609.23570Memory"); no instruction-bearing content found in the post or paper.

## Takeaways for tuning a memory stack
- Do not assume a generic memory layer (Mem0-style extraction plus top-1 retrieval) helps engineering agents; in 11 of 12 pairings it did not beat memory-off, and it can hurt (glm-5 + Mem0, -5.5 pp significant).
- Invest in the form of the served record (short, typed fields with an explicit fix field, no copied instructions or tool noise) before investing in the ranker: ranking misses were 1.3% of failures.
- Store verified outcomes only (patch passed tests), and serve a compact lesson, not transcript.
- Always run an irrelevant-memory control: here it also cut steps, so step reduction alone is not evidence that memory content helped.
- For our PDLC benchmark (priority 4): copy the matched memory-off, 4-seed, bootstrap-by-target design and the coverage/ranking/form/use taxonomy.

## Open questions
- Would a non-target-aware version of the four-field record (written at trajectory close, retrieved by the system) keep the lift? Not tested.
- How do Hindsight, Zep, Letta, supermemory or a Jev-reranked store do on the same targets? Not tested.
- Does top-k above 1 help systems other than Mem0? Not reported.
- Memory-side token cost per system: not recorded.
- Results on Claude or GPT solvers: not tested.

## Grading and labels
- **Directness: high.** Executable resolve rate for coding agents with a matched memory-off baseline.
- **Control: medium.** Good controls (irrelevant memory, seeds, bootstrap, strip ablation) but the positive arm is oracle-assisted and selection-biased; top-1 only.
- **Independence: medium.** Academic plus Alibaba; no stated stake in the evaluated systems; the same deepseek-v4-flash builds histories, extracts memories and is the reference solver.
- **Reproducibility: medium.** Code URL stated, open-weight models, seeds; not verified by us.
- **Applicability: high.** Coding agents on real repositories; missing frontier proprietary solvers.
- **Pillars:** R6 primary (a memory benchmark and whether its evaluation supports conclusions); R5 (learning from verified experience), R3 (form of what is served).
- **Stage:** evaluation.
- **Tags:** see frontmatter.
- **Priority:** 4 (memory benchmarks; directly relevant to scoping our PDLC memory benchmark).
- **Beliefs affected:**
  - Supports B7: a task-conditioned (target-aware) record outperformed generic systems that distil at write time and retrieve; lead-grade, and the positive arm is oracle-assisted.
  - Supports B20: the post's headline needed narrowing on primary read (CIs, selection, 69% denominator).
  - Contradicts B16 (qualified): in this coding setting a short distilled record beat raw-transcript records, and form degradation of raw transcript was the main failure; weakened because the distilled record is target-aware.
  - Would create: generic memory systems at top-1 do not beat memory-off on executable coding tasks; record form, not ranking, dominates failures.
- **Contradiction: B16** "Raw trajectories often beat distilled skills": VibeMemBench Tables 1, 2 and 5 show raw transcript records failing mainly through form degradation while a four-field distilled record lifts resolve (directionally). Open row; resolution needs a non-target-aware distilled arm.
- **Against the synthesis:** the synthesis section 1 cites EvoSkill's "raw trajectories often beat distilled skills"; this paper points the other way for coding agents. Relation to bus note sdebench (Hindsight vs no memory): undetermined from its title; same question, disjoint systems.
- **Arm-vs-arm test this quarter (frozen harness):** arm A memory-off vs arm B top-1 raw transcript chunk from past runs vs arm C the same history written at trajectory close as a four-field record (bug class, root cause, fix pattern, lesson), non-target-aware; metric: task pass rate with 4 seeds and target-level bootstrap, plus steps and injected tokens.

## Origin chain
- Post 2104488796209508678 (@runbywren, 0 likes, 3 views) -> arXiv 2609.23570 v1 -> Table 1 (injection transfer), Table 2 (memory systems), Tables 4 and 5 and section 4.4 (failure attribution), Table 10 (reference solver), section 3.3 Eq. 1 (selection), Appendix B.2 (record construction), Limitations.
- Independence: single post, single paper. Authors from SIAT, SUAT and Alibaba; the evaluated systems (Mem0, SimpleMem, MemoryOS, A-MEM) are third-party. Dataset derived from SWE-rebench V2. Harness MiniSWEAgent. No shared authors with the sdebench bus note (Vectorize) or with any note in our catalogue that we can see.
