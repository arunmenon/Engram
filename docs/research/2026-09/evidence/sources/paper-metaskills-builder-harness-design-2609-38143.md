---
schema_version: 1
artifact_id: N-20260930-16
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105180478026482058", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.38143
claim_cluster: arxiv:2609.38143
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.38143
source_commit: unknown
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6"]
memory_stage: consolidation
tags: {"mechanism": ["meta-skills for the harness builder", "skill bank learned from execution feedback", "frozen weights", "full bank vs retrieved skills"], "workload": ["agent harness construction", "scientific law discovery tasks"], "lifecycle_stage": ["consolidation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "high", "independence": "low", "reproducibility": "medium", "applicability": "medium"}
beliefs_affected: {"supports": ["B16"], "contradicts": [], "would_create": ["Where an induced procedure is delivered matters more than whether one exists: the same learned bank helps when given to the component that builds the environment and hurts when handed to the component that does the task"]}
claim_correction: none
---

# Learning Meta-Skills for Agent Harness Design in Test-Time AI4AI (MetaSkills, arXiv 2609.38143)

- **URL:** https://arxiv.org/abs/2609.38143 (full text read at https://arxiv.org/html/2609.38143)
- **Type:** paper
- **Author / org:** Cheng Qian, Kunlun Zhu, Beibin Li, Zhenhailong Wang, Heng Ji. Apodex; University of Illinois Urbana-Champaign.
- **Date:** 2026-09-29 (v1)
- **Retrieved:** 2026-09-30, arXiv HTML v1. Code link in the paper: https://github.com/qiancheng-apodex/MetaSkill-AI4AI (not cloned this run; commit unknown).
- **Cited by evidence:** https://x.com/runbywren/status/2105180478026482058 (@runbywren, watchlist timeline). Memory digest of 2026-09-30.
- **Relevance to a memory stack:** medium. A controlled test of procedural memory: the same skill bank is delivered to two different consumers and the sign of the effect flips.

## TL;DR
- Two frozen models: a Builder designs the execution environment (tools, controller, memory and context handling) for a task; a Target solves the task inside it. The Builder keeps a bank of "meta-skills" learned from the Target's execution records.
- A meta-skill is three short fields: "when identifies observable conditions that call for support; provide specifies the capability or resource the environment should supply; and use explains how the Target should employ that support." At most 192 tokens each.
- Full-bank Builder meta-skills reach 65.31% macro-average over six model-benchmark pairs: +8.95 points over a Builder with no skills (56.36) and +12.02 over giving skills directly to the Target (53.29). Table 3.
- Skills handed straight to the Target are below the no-skill Builder in every variant tested (51.23 to 54.38 against 56.36).
- The post's numbers match the paper. No claim correction.

## What it claims / describes

**Loop.** For each development task the Builder constructs a harness, the Target runs, the Builder reviews the execution record and score, and then makes "Maximum one evidence-grounded update (keep/revise/add) per development task" to the bank. Two passes over the development tasks. The bank is frozen before test.

**Budgets.** Skill-update calls up to 8K output tokens; harness construction up to 16K. Target limits on Harness-Bench: 30 model turns, 30 tool calls, 96K cumulative tokens, 1,200 s. On NewtonBench: 12 turns, 10 tool calls, 192K tokens, 3,600 s. Builder learning and construction happen outside the Target's budget.

**Benchmarks.** Harness-Bench: 106 tasks (11 development, 95 test), deterministic completion-oracle score. NewtonBench: 324 tasks (32 development, 292 test), symbolic-structure accuracy.

**Models.** Builder GPT-5.6-Sol. Targets Gemini-3.6-Flash, Qwen3.8-Flash, GPT-OSS-120B. Self-improvement runs use the same model as Builder and Target (Gemini-3.6-Flash, Gemini-3.1-Pro). Temperature zero.

**Conditions compared (Table 3).** Native environment; Builder with no skills; skills written by the Builder but given directly to the Target (retrieved or all); independent structured Target skills; mined free-form Target skills; Builder meta-skills (retrieved or all).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Macro-average, Builder meta-skills, all | 65.31 | Native 51.40; Builder no skills 56.36; Direct Builder skills all 53.29; Independent structured Target skills all 54.38; Mined free-form Target skills all 51.23 | Table 3, 95 + 292 test tasks, 3 Targets | one run per condition |
| Macro-average, Builder meta-skills, retrieved | 60.45 | full bank 65.31 | Table 3 | retrieval of skills loses 4.86 points against using the whole bank |
| Harness-Bench (Gemini / Qwen / GPT-OSS), meta-skills all | 67.81 / 72.64 / 68.22 | no skills 53.29 / 71.51 / 63.02 | Table 3 | Qwen gain is 1.13 points |
| NewtonBench (Gemini / Qwen / GPT-OSS), meta-skills all | 68.84 / 63.70 / 50.68 | no skills 56.16 / 50.34 / 43.84 | Table 3 | |
| Same model as Builder and Target | +18.71 points average over no-skill construction; +14.14 over direct delivery | | Figure 3(a) | figure values, not a table |
| Ablation on NewtonBench, without controller | Gemini 55.48 (-13.36, 95% CI [-18.49, -8.22]); Qwen 58.90 (-4.79, [-10.27, 0.68]); GPT-OSS 49.66 (-1.03, [-6.51, 4.11]) | Full 68.84 / 63.70 / 50.68 | Table 4 | only the Gemini interval excludes zero |
| Ablation on NewtonBench, without memory + context | Gemini 66.78 (-2.05, [-7.53, 3.08]); Qwen 59.59 (-4.11, [-9.25, 1.03]); GPT-OSS 54.11 (+3.42, [-2.05, 8.90]) | Full | Table 4 | all intervals span zero |
| Transfer of a bank to another Builder | Harness-Bench +2.72 (interval spans zero) vs own bank +3.69; NewtonBench -4.45 vs own bank +9.93 | no-skill control | Figure 3(b) | transferred banks are weaker than locally learned ones |
| Outcome transitions on NewtonBench | "No valid submission" 394 to 254; correct discoveries 439 to 535; 145 recoveries, 46 regressions | | Figure 4(a), three Targets pooled | |
| Uncertainty method | paired task bootstrap, 20K resamples, unadjusted 95% intervals | | | no seed variation; single execution per condition |

## Mechanism details you could implement
- Meta-skill schema: `{when, provide, use}`, at most 192 tokens in total.
- Update rule: after each task, at most one of keep, revise, add, and the change must cite the execution record that motivates it.
- Deliver the bank to the component that prepares the working environment, not to the component that acts.
- Use the whole bank when it is small; retrieving a subset lost about 5 points here.
- Score with all declared test tasks in the denominator; failures count as zero.

## Limitations, caveats, counter-evidence
- The paper's own limits (appendix): "The reported improvements therefore concern the resulting Builder-Target system"; reuse "across datasets, unseen task families, and different tool interfaces is a promising next step"; Builder cost is outside the Target's budget and is not reported as a number.
- The memory and context component of the generated harness shows no reliable effect (Table 4, intervals span zero); the controller does, for one Target.
- Bank transfer across Builders is weak or negative on NewtonBench (-4.45).
- 46 regressions on NewtonBench: the bank also breaks tasks that worked before.
- One run per condition; two benchmarks; development and test tasks come from the same benchmarks.
- Authors are affiliated with Apodex, which sells agent tooling (inference about interest; the paper does not discuss it).

## Takeaways for tuning a memory stack
- Evidence for keeping procedural memory away from the acting agent's prompt: distilled skills given directly to the task model did not beat a no-skill environment builder in any variant.
- If procedures are induced at all, test them as inputs to context assembly (what to provide and when) rather than as instructions to the executor.
- A small bank used whole beat retrieval over the bank; retrieval of procedures is an extra failure point.
- Track regressions as well as gains when a learned bank is switched on.

## Open questions
- How large is the bank after two passes, and does it plateau? Not reported as a curve.
- What is the Builder's token cost per task? Not reported.
- Does the effect hold when the Builder is not a stronger model than the Target? Only the same-model figure addresses this.

## Grading and labels
- **Directness: high.** Main table and ablation with bootstrap intervals.
- **Control: high.** Eight delivery conditions on the same tasks and Targets, component ablation, transfer study.
- **Independence: low.** One group; one benchmark of the two (Harness-Bench) is closely tied to the method's setting.
- **Reproducibility: medium.** Code link given; not inspected; commercial API models.
- **Applicability: medium.** Harness construction for task agents; not memory over engineering artifacts.
- **Strength:** paper-ablated.
- **Pillars:** R5 primary (procedure induction and transfer). Secondary R6 (paired bootstrap, full denominators). Memory stage: consolidation (turning execution records into reusable procedures).
- **Beliefs:**
  - B16 supports: skills delivered to the executor (direct, independent, or mined) score 51.23 to 54.38 against 56.36 with none.
  - B15 adjacent: updates are grounded in single-task execution records, not cross-lineage comparison; not a test of B15.
  - Would create: the consumer of the induced procedure decides the sign of the effect.
- **Contradiction rows:** none. Open row, tension with a broad reading of B16: induced procedures did help (+8.95 points) when given to the Builder, so "induced procedures are a hypothesis" now has one positive controlled result, limited to harness construction.

## Origin chain
- Post https://x.com/runbywren/status/2105180478026482058 -> arXiv 2609.38143 v1 -> Table 3 (65.31, 56.36, 53.29), Figure 3(a) (+18.71), Table 4 -> this note.
- Independence: single source. Shared authors with the other skill notes on the bus (SkillOpt, SkillLift, EvoSkill, SkillsBench) were not checked; treat independence from them as unknown.
