---
schema_version: 1
artifact_id: N-SURVEY-20260927-11
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2605.24117
input_refs: []
pillar_primary: R5
pillar_secondary: []
beliefs_affected: {supports: [B16], contradicts: []}
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 2, applicability: 3}
source_url: https://arxiv.org/abs/2605.24117
found_via: survey
strength: paper-ablated
---

# SkillEvolBench: Benchmarking the Evolution from Episodic Experience to Procedural Skills

- **URL:** https://arxiv.org/abs/2605.24117 (read via https://arxiv.org/html/2605.24117v1)
- **Type:** paper
- **Author / org:** Yingtie Lei, Zhongwei Wan, Jiankun Zhang, Samiul Alam, Zixuan Zhong, Peizhou Huang, Xin Wang, Jingxuan Zhang, Donghao Zhou, Yunta Hsieh, Zhihao Dou, Hui Shen, Yan Xu, Dimitrios Dimitriadis, Tuo Zhang, Mi Zhang (The Ohio State University, University of Chicago, UCL, University of Michigan, CUHK, Case Western Reserve University, Amazon)
- **Date:** 2026-05-22 (arXiv v1)
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R5, beliefs B16
- **Relevance to a memory stack:** high, it is a matched comparison of "store raw episodes" vs "distill episodes into procedural skills" across 10 models and 3 real coding-agent harnesses, which is exactly Engram's episode vs Workflow node choice.

Retrieval note: the HTML was read through a fetch tool that returns a model-extracted rendering, not raw HTML. Tables 1 and 2 below were cross-checked by recomputing the paper's own reported per-arm means from the per-model deltas (they match to within 0.02 pp), so they are trustworthy. Figure-derived numbers (per-environment, Raw-Trajectory means) were not in tables and are lower confidence.

## TL;DR
- 180 tasks (6 environments x 5 task families x 6 role-conditioned tasks), 10 models across Claude Code, Codex CLI and Gemini CLI; arms: No-Skill, Raw-Trajectory, three self-generated skill variants, three curated-start variants, plus forced "Tier3" resource bundling.
- Authors' headline: "Raw trajectories reveal a lossy abstraction bottleneck ... agents often use episodic traces more effectively than the distilled skills derived from them." The skills-minus-Raw-Trajectory heatmap is described as "predominantly negative across models, variants, and metrics."
- Against No-Skill on frozen deployment (ESR), most skill arms lose on average: Curated-Static -2.44 pp, SelfGen-Revision -2.56 pp (1 win / 1 tie / 8 losses over 10 models), SelfGen-ZeroShot -2.56 pp; only the "update after every attempt" arms are slightly positive (Curated-Always +0.78 pp, SelfGen-Always +0.44 pp).
- Forcing richer skill libraries (scripts/, references/, assets/) costs more (+$0.119 per attempted task for Curated-Tier3) and does not reliably help (Curated-Tier3 mean ESR change 0.0 pp, 3W/2T/5L); authors attribute this to "episode-specific assumptions, over-specific validators, stale context, or weakly triggered files."
- One of six environments (E1 Code Debugging and Modification) is software engineering; the result is cross-domain, not coding-specific.

## What it claims / describes
Setup. Each task family has three acquisition roles (canonical, enriched, variant) on which a skill library may be learned, and three deployment roles on which the library is frozen: context-shift, adversarial/shortcut-resistance, and composition. Metrics: LSR (learning/acquisition success), RSR (replay success on original acquisition tasks with the frozen library), ESR (frozen evaluation/deployment success), CSSR (context shift), ARSR (adversarial/shortcut resistance), CompSR (composition).

Environments (5 families each):
- E1 Code Debugging and Modification: systematic-error-diagnosis, dependency-conflict-resolution, safe-refactoring, multi-file-bug-fix, merge-conflict-resolution.
- E2 Tool and API Orchestration: pre-call-parameter-validation, retry-and-backoff, pagination-complete-retrieval, multi-step-orchestration, response-validation-fallback.
- E3 Data Processing and Structured Query: schema-inspection-before-query, type-normalization-before-sort, key-alignment-before-merge, null-safe-filtering-aggregation, result-sanity-reconciliation.
- E4 Document Parsing and Transformation; E5 Research and Information Synthesis; E6 Communication and Scheduling Operations.

Arms:
1. No-Skill: no persistent memory.
2. Raw-Trajectory: retrieves compacted same-family acquisition trajectories, no skill induction.
3. SelfGen-Zero-Shot: model writes fixed skills from task metadata only, before the canonical task.
4. SelfGen-Revision (labelled "Experience" in Table 2): induces skills from canonical trajectories, revises after failed attempts.
5. SelfGen-Always: updates after every acquisition attempt.
6. Curated-Static: fixed curated skills.
7. Curated-Revision: starts from curated skills, revises after failures.
8. Curated-Always: curated start, revises after every attempt.
9. Always+Tier3 (curated and selfgen): mandatory resource bundling into scripts/, references/, assets/.

Harnesses and models: Claude Code (Opus 4.6, Opus 4.5, Sonnet 4.6, Sonnet 4.5); Codex CLI (GPT-5.4, GPT-5.3-Codex, GPT-5.2-Codex); Gemini CLI (Gemini 3.1 Pro, Gemini 3 Flash, Gemini 2.5 Pro). 10 configurations (4 + 3 + 3).

Trajectory compaction: "Each acquisition attempt yields a compacted trajectory summary ... from harness-recorded artifacts such as instructions, file accesses, tool calls, commands, edits, generated outputs, tests, and final responses." Details are in an appendix I did not retrieve; the number of trajectories retrieved per task and the token budget were not stated in what I read.

Grading: no LLM judge was mentioned in what I retrieved; verification is described as deterministic outcome checks plus process-level evidence. Not independently confirmed from the appendix.

## Numbers
Per-cell n: each metric cell for one model is over 30 families' worth of tasks for deployment roles (e.g. CSSR, ARSR, CompSR are each 30 tasks: 6 envs x 5 families x 1 role), so one task = 3.3 pp. ESR appears to be over the 90 deployment tasks (one task = 1.1 pp) (inference from the value granularity). No confidence intervals, no seeds, no significance tests reported.

Table 1 (No-Skill vs curated-start), success %, delta vs No-Skill in parentheses. "n/a" = not applicable (the source shows a dash).

| Model | Condition | LSR | RSR | ESR | CSSR | ARSR | CompSR |
|---|---|---|---|---|---|---|---|
| Opus 4.6 | No-Skill | 38.9 | n/a | 37.8 | 46.7 | 36.7 | 30.0 |
| | Curated-Static | 40.0 (+1.1) | n/a | 34.4 (-3.4) | 46.7 (0.0) | 36.7 (0.0) | 20.0 (-10.0) |
| | Revision | 44.4 (+5.5) | 56.7 (+17.8) | 38.9 (+1.1) | 40.0 (-6.7) | 43.3 (+6.6) | 33.3 (+3.3) |
| | Always | 42.2 (+3.3) | 46.7 (+7.8) | 37.8 (0.0) | 40.0 (-6.7) | 46.7 (+10.0) | 26.7 (-3.3) |
| Opus 4.5 | No-Skill | 42.2 | n/a | 32.2 | 40.0 | 40.0 | 16.7 |
| | Curated-Static | 45.6 (+3.4) | n/a | 34.4 (+2.2) | 43.3 (+3.3) | 40.0 (0.0) | 20.0 (+3.3) |
| | Revision | 38.9 (-3.3) | 42.2 (0.0) | 34.4 (+2.2) | 43.3 (+3.3) | 36.7 (-3.3) | 23.3 (+6.6) |
| | Always | 42.2 (0.0) | 44.4 (+2.2) | 36.7 (+4.5) | 43.3 (+3.3) | 43.3 (+3.3) | 23.3 (+6.6) |
| Sonnet 4.6 | No-Skill | 37.8 | n/a | 38.9 | 40.0 | 50.0 | 26.7 |
| | Curated-Static | 41.1 (+3.3) | n/a | 35.6 (-3.3) | 36.7 (-3.3) | 46.7 (-3.3) | 23.3 (-3.4) |
| | Revision | 41.1 (+3.3) | 51.1 (+13.3) | 38.9 (0.0) | 46.7 (+6.7) | 43.3 (-6.7) | 26.7 (0.0) |
| | Always | 40.0 (+2.2) | 44.4 (+6.6) | 38.9 (0.0) | 46.7 (+6.7) | 43.3 (-6.7) | 26.7 (0.0) |
| Sonnet 4.5 | No-Skill | 41.1 | n/a | 35.6 | 40.0 | 46.7 | 20.0 |
| | Curated-Static | 35.6 (-5.5) | n/a | 36.7 (+1.1) | 43.3 (+3.3) | 43.3 (-3.4) | 23.3 (+3.3) |
| | Revision | 40.0 (-1.1) | 42.2 (+1.1) | 28.9 (-6.7) | 36.7 (-3.3) | 33.3 (-13.4) | 16.7 (-3.3) |
| | Always | 37.8 (-3.3) | 38.9 (-2.2) | 33.3 (-2.3) | 40.0 (0.0) | 40.0 (-6.7) | 20.0 (0.0) |
| GPT-5.4 | No-Skill | 43.3 | n/a | 33.3 | 43.3 | 33.3 | 23.3 |
| | Curated-Static | 43.3 (0.0) | n/a | 32.2 (-1.1) | 40.0 (-3.3) | 40.0 (+6.7) | 16.7 (-6.6) |
| | Revision | 45.6 (+2.3) | 45.6 (+2.3) | 38.9 (+5.6) | 50.0 (+6.7) | 43.3 (+10.0) | 23.3 (0.0) |
| | Always | 43.3 (0.0) | 42.2 (-1.1) | 40.0 (+6.7) | 40.0 (-3.3) | 50.0 (+16.7) | 30.0 (+6.7) |
| GPT-5.3-Codex | No-Skill | 44.4 | n/a | 34.4 | 36.7 | 46.7 | 20.0 |
| | Curated-Static | 45.6 (+1.2) | n/a | 32.2 (-2.2) | 36.7 (0.0) | 43.3 (-3.4) | 16.7 (-3.3) |
| | Revision | 42.2 (-2.2) | 48.9 (+4.5) | 34.4 (0.0) | 36.7 (0.0) | 46.7 (0.0) | 20.0 (0.0) |
| | Always | 42.2 (-2.2) | 45.6 (+1.2) | 32.2 (-2.2) | 40.0 (+3.3) | 40.0 (-6.7) | 16.7 (-3.3) |
| GPT-5.2-Codex | No-Skill | 43.3 | n/a | 36.7 | 40.0 | 53.3 | 16.7 |
| | Curated-Static | 51.1 (+7.8) | n/a | 30.0 (-6.7) | 40.0 (0.0) | 36.7 (-16.6) | 13.3 (-3.4) |
| | Revision | 45.6 (+2.3) | 43.3 (0.0) | 36.7 (0.0) | 43.3 (+3.3) | 46.7 (-6.6) | 20.0 (+3.3) |
| | Always | 44.4 (+1.1) | 45.6 (+2.3) | 37.8 (+1.1) | 46.7 (+6.7) | 43.3 (-10.0) | 23.3 (+6.6) |
| Gemini 3.1 Pro | No-Skill | 40.0 | n/a | 35.6 | 40.0 | 46.7 | 20.0 |
| | Curated-Static | 44.4 (+4.4) | n/a | 35.6 (0.0) | 36.7 (-3.3) | 43.3 (-3.4) | 26.7 (+6.7) |
| | Revision | 43.3 (+3.3) | 55.6 (+15.6) | 35.6 (0.0) | 36.7 (-3.3) | 43.3 (-3.4) | 26.7 (+6.7) |
| | Always | 40.0 (0.0) | 45.6 (+5.6) | 35.6 (0.0) | 40.0 (0.0) | 40.0 (-6.7) | 26.7 (+6.7) |
| Gemini 3 Flash | No-Skill | 40.0 | n/a | 35.6 | 30.0 | 53.3 | 23.3 |
| | Curated-Static | 41.1 (+1.1) | n/a | 32.2 (-3.4) | 36.7 (+6.7) | 43.3 (-10.0) | 16.7 (-6.6) |
| | Revision | 42.2 (+2.2) | 42.2 (+2.2) | 32.2 (-3.4) | 30.0 (0.0) | 46.7 (-6.6) | 20.0 (-3.3) |
| | Always | 43.3 (+3.3) | 37.8 (-2.2) | 37.8 (+2.2) | 46.7 (+16.7) | 36.7 (-16.6) | 30.0 (+6.7) |
| Gemini 2.5 Pro | No-Skill | 30.0 | n/a | 26.7 | 26.7 | 30.0 | 23.3 |
| | Curated-Static | 30.0 (0.0) | n/a | 18.9 (-7.8) | 20.0 (-6.7) | 23.3 (-6.7) | 13.3 (-10.0) |
| | Revision | 28.9 (-1.1) | 32.2 (+2.2) | 21.1 (-5.6) | 16.7 (-10.0) | 30.0 (0.0) | 16.7 (-6.6) |
| | Always | 31.1 (+1.1) | 26.7 (-3.3) | 24.4 (-2.3) | 26.7 (0.0) | 23.3 (-6.7) | 23.3 (0.0) |

Table 2 (No-Skill vs self-generated), ESR only plus the axis where effects are largest (full table has the same columns as Table 1; No-Skill rows identical to Table 1):

| Model | ZeroShot ESR | Experience (Revision) ESR | Always ESR | ZeroShot ARSR | Experience ARSR | Always ARSR |
|---|---|---|---|---|---|---|
| Opus 4.6 | 32.2 (-5.6) | 32.2 (-5.6) | 37.8 (0.0) | 33.3 (-3.4) | 36.7 (0.0) | 46.7 (+10.0) |
| Opus 4.5 | 34.4 (+2.2) | 31.1 (-1.1) | 35.6 (+3.4) | 40.0 (0.0) | 40.0 (0.0) | 40.0 (0.0) |
| Sonnet 4.6 | 36.7 (-2.2) | 40.0 (+1.1) | 40.0 (+1.1) | 43.3 (-6.7) | 40.0 (-10.0) | 50.0 (0.0) |
| Sonnet 4.5 | 27.8 (-7.8) | 35.6 (0.0) | 33.3 (-2.3) | 30.0 (-16.7) | 40.0 (-6.7) | 40.0 (-6.7) |
| GPT-5.4 | 33.3 (0.0) | 31.1 (-2.2) | 35.6 (+2.3) | 40.0 (+6.7) | 36.7 (+3.4) | 40.0 (+6.7) |
| GPT-5.3-Codex | 34.4 (0.0) | 31.1 (-3.3) | 34.4 (0.0) | 40.0 (-6.7) | 40.0 (-6.7) | 43.3 (-3.4) |
| GPT-5.2-Codex | 30.0 (-6.7) | 34.4 (-2.3) | 38.9 (+2.2) | 36.7 (-16.6) | 43.3 (-10.0) | 43.3 (-10.0) |
| Gemini 3.1 Pro | 36.7 (+1.1) | 32.2 (-3.4) | 33.3 (-2.3) | 46.7 (0.0) | 36.7 (-10.0) | 43.3 (-3.4) |
| Gemini 3 Flash | 40.0 (+4.4) | 33.3 (-2.3) | 36.7 (+1.1) | 53.3 (0.0) | 40.0 (-13.3) | 43.3 (-10.0) |
| Gemini 2.5 Pro | 15.6 (-11.1) | 20.0 (-6.7) | 25.6 (-1.1) | 13.3 (-16.7) | 30.0 (0.0) | 20.0 (-10.0) |

Summary metrics:

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Mean ESR change, Curated-Static | -2.44 pp; "increases cost $0.077 per attempted task" | No-Skill | 10 models, frozen deployment | my count from Table 1: 2 wins / 1 tie / 7 losses |
| Mean ESR change, Curated-Revision | -0.67 pp, 3W/4T/3L | No-Skill | same | matches Table 1 recomputation |
| Mean ESR change, Curated-Always | +0.78 pp, 4W/3T/3L | No-Skill | same | strongest curated variant per authors |
| Mean ESR change, SelfGen-Revision | -2.56 pp, 1W/1T/8L | No-Skill | same | skills induced from the same trajectories Raw-Trajectory uses |
| Mean ESR change, SelfGen-Always | +0.44 pp, 5W/2T/3L | No-Skill | same | differences of 1 to 3 tasks |
| Mean ESR change, SelfGen-ZeroShot | -2.56 pp; range +4.4 (Gemini 3 Flash) to -11.1 (Gemini 2.5 Pro) | No-Skill | same | metadata-only skills |
| Mean ESR change, Curated-Tier3 | 0.0 pp, 3W/2T/5L, "+$0.119 per attempted task on average" | No-Skill | forced scripts/references/assets bundling | cost unit is USD per attempted task |
| Mean ESR change, SelfGen-Tier3 | -1.11 pp, 4W/1T/5L | No-Skill | same | Gemini 3 Flash ESR 35.6 to 27.8; Sonnet 4.5 35.6 to 30.0 |
| Raw-Trajectory means (all models) | RSR 48.2%, ESR 37.6%, ARSR 44.7%, CompSR 25.7% | n/a | Figure 6 aggregate, "strongest baseline" | from a figure, not a table; one extraction pass labelled 48.2 as LSR, another as RSR, so treat that one value as ambiguous |
| No-Skill means (my computation from Table 1) | ESR 34.7%, ARSR 43.7%, CompSR 22.0% | n/a | 10 models | (inference) Raw-Trajectory ESR 37.6 is about +2.9 pp over No-Skill and above every skill arm's mean ESR (best: Curated-Always about 35.5) |
| Count of cells where Raw-Trajectory beats a skill arm | not countable from retrieved tables | n/a | paper gives only a heatmap (skill minus Raw) | authors: "predominantly negative across models, variants, and metrics"; no per-model Raw-Trajectory table found in main text |
| Environment spread | "67.3 pp for LSR, 42.1 pp for ESR" between easiest and hardest environments; across baselines only "1.9 pp (LSR), 5.4 pp (ESR)" | n/a | Figure 6 | environment matters far more than memory arm; per-environment means reported by extraction (E1 Code ESR about 37%) look inconsistent with a 42 pp spread, so per-environment values are low confidence |
| E6 CompSR | 0.0% for all baselines | n/a | Communication composition | floor effect |
| Model heterogeneity | Opus 4.5 benefits from 7 of 9 variants (avg +2.72 pp); GPT-5.4 from 5 (+2.22 pp); Gemini 2.5 Pro harmed by 7 (-3.70 pp) | No-Skill | ESR | weaker models hurt most by skills |
| Tier3 examples | Opus 4.6 37.8 to 40.0 ESR (SelfGen-Always+Tier3); Gemini 3.1 Pro 35.6 to 40.0 (Curated-Always+Tier3) | No-Skill | Figure 5 | "larger libraries do not reliably improve frozen deployment" |
| Latency | not stated | | | |
| Judge shares model with system | no LLM judge mentioned (deterministic checks) | | | appendix not read |

## Mechanism details you could implement
- Deployment-axis stratification: evaluate stored procedures not just on replay but on three held-out variants of each family: context-shift (same procedure, different surrounding context), adversarial shortcut (a tempting shortcut that violates the procedure), composition (procedure must combine with another family's procedure). RSR (replay) is systematically inflated vs ESR (e.g. Opus 4.6 Curated-Revision RSR 56.7 vs ESR 38.9), so replay success is a poor proxy for transfer.
- Update policy as an explicit arm: "Revision" (edit skill only after a failed attempt) vs "Always" (edit after every attempt). In this benchmark Always was the only policy with non-negative mean ESR for both curated and self-generated starts.
- Compacted trajectory record fields to keep for raw-episode retrieval: instructions, file accesses, tool calls, commands, edits, generated outputs, tests, final responses.
- Tier structure for skills: Tier3 = a skill with attached scripts/, references/, assets/. Treat bundled artifacts as opt-in, since forced bundling added cost and carried episode-specific validators.

## Limitations, caveats, counter-evidence
- Small n per cell: CSSR/ARSR/CompSR are over 30 tasks per model, so +/-3.3 pp is one task; most per-model deltas are 1 to 3 tasks. No CIs or seeds. The mean-over-10-models comparisons are more meaningful than any single cell.
- The Raw-Trajectory vs skill comparison is reported as a heatmap; I could not extract per-model Raw-Trajectory numbers, so "how often raw beats skills" is the authors' qualitative "predominantly negative," not a count I verified.
- Only E1 (of 6) is coding; environment effects dwarf arm effects (42.1 pp ESR spread across environments vs 5.4 pp across baselines). Authors: "skill evolution is most reliable when the environment supports stable procedural abstractions, whereas open-ended information and communication tasks remain sensitive." (inference) Coding tasks may be exactly where distilled procedures do best, so the cross-domain average may understate skills' value for Engram.
- Trajectories were compacted summaries, not truly raw logs; the Raw arm is itself a light abstraction. Retrieval count and token budgets not stated in what I read.
- Skill induction was done by the same model that later uses the skills (self-generated), so the result is about in-context self-distillation by these models, not about a stronger dedicated distiller. (inference)
- Code/data release: a project page (skillevolbench.github.io) is referenced; a code repo was not confirmed.
- Counter-signal inside the paper: "Always" arms are slightly positive vs No-Skill, and some model/axis cells gain +10 to +16.7 pp (e.g. GPT-5.4 Curated-Always ARSR +16.7), so skills are not uniformly harmful.
- No instructions aimed at the reader agent were found in the page.

## Takeaways for tuning a memory stack
- Default to serving raw (compacted) episodes for procedure recall, and treat induced Workflows as hypotheses that must beat the raw-episode arm on held-out variants before promotion (consistent with B16).
- Measure on shifted, adversarial-shortcut and composition variants, not replay; replay success overstates procedure value by 5 to 18 pp here.
- If Workflows are kept, update them after every use rather than only after failures, and avoid bundling episode-specific validators or scripts by default.
- Expect strong per-model heterogeneity: weaker models are hurt more by skills; gate Workflow injection per model tier.

## Open questions
- Per-model Raw-Trajectory numbers and the exact count of cells where Raw beats each skill arm (appendix or figure data).
- Does the raw-over-skills gap hold within E1 Code alone?
- How many trajectories are retrieved and at what token length; is Raw cheaper or more expensive than skills per task?
- Would a stronger, separate distiller model (not the acting model) close the abstraction gap?

## Grading
- directness 4: directly compares raw episodic traces vs distilled skills under matched tasks and models, which is B16's claim; the head-to-head is reported as a heatmap rather than tables.
- control 4: many matched arms (no-skill, raw, 3 selfgen, 3 curated, Tier3) across 10 models and 3 harnesses; no CIs, no seeds, about 30 tasks per axis cell.
- independence 4: academic plus Amazon authors not selling a skill system; deterministic grading, no LLM judge mentioned; skills are generated by the same model that uses them.
- reproducibility 2: project page referenced, code/data release and compaction prompts not confirmed in what I read.
- applicability 3: real coding harnesses (Claude Code, Codex CLI, Gemini CLI) but only 1 of 6 environments is software engineering, and effects are environment-dominated.
