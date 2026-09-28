---
schema_version: 1
artifact_id: N-SURVEY-20260927-07
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2602.12670
input_refs: []
pillar_primary: R5
pillar_secondary: [R3]
beliefs_affected:
  supports: [B16]
  contradicts: []
  note: self-generated skills score below no skills; curated skills help least in software engineering; a companion study (arXiv 2608.11888) catalogues 307 skill-induced failures
evidence:
  directness: 3
  control: 4
  independence: 4
  reproducibility: 4
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2602.12670
found_via: survey
---

# SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks (with companion: Agent Skills Can Be Harmful, arXiv 2608.11888)

- **URL:** https://arxiv.org/abs/2602.12670 (current HTML read); companion https://arxiv.org/abs/2608.11888 (HTML read)
- **Type:** benchmark paper (plus companion empirical study)
- **Author / org:** SkillsBench: 142 contributors, authorship list not captured. Companion: Gen Dong, Yanjie Gao, Liqun Li, Tianyin Xu, Yu Hua, Fan Yang.
- **Date:** SkillsBench v1 Feb 2026, later revised; companion 12 Aug 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R5 question on B16 (induced procedures are a hypothesis)
- **Relevance to a memory stack:** medium-high. Skills are the product form of procedural memory. This is a paired, verifier-scored test of curated vs self-generated procedures, with a software-engineering slice.

## TL;DR
- Current version: 87 tasks, 8 domains, 18 model-harness configurations, deterministic verifiers, three trials per cell, paired deltas with 95 % CIs.
- Curated skills: 33.9 % to 50.5 % pass rate (+16.6 pp); configuration range +4.1 to +25.7 pp.
- Self-generated skills (agent authors packs with Anthropic's skill-creator before solving): -8.1 to -11.5 pp vs no skills on the three configurations tested.
- Software Engineering gains least among the listed domains: 37.6 % to 49.2 % (+11.6 pp).
- 2 to 3 compact skills beat many or long ones: "comprehensive" documentation +0.7 pp.

## Version disagreement (flag)
The v1 abstract and secondary summaries report 84 or 86 tasks, 11 domains, 7 configurations, 7,308 trajectories, +16.2 pp curated (24.3 % to 40.6 %), Software Engineering +4.5 pp, self-generated -1.3 pp, and 16 of 84 tasks negative. The current HTML reports 87 tasks, 8 domains, 18 configurations, +16.6 pp, SE +11.6 pp, self-generated -8.1 to -11.5 pp, 13 of 87 tasks negative. The direction holds across versions; the magnitudes do not. Cite the version.

## Numbers (current HTML)

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Pass rate, curated skills | 50.5 % | 33.9 % no skills | 18 configs, task-macro | +16.6 pp; normalised gain 25.5 % |
| Self-generated skills | -8.1 to -11.5 pp | no skills | 3 configs | skill-creator authoring before the task, no trajectory feedback |
| Software Engineering | 49.2 % | 37.6 % | per-domain | +11.6 pp, smallest listed |
| Mathematics & OR | 55.4 % | 45.7 % | per-domain | +9.7 pp |
| 1 skill / 2-3 / >=4 | +18.0 / +19.0 / +10.1 pp | no skills | Appendix F | |
| Compact / standard / detailed / comprehensive | +19.0 / +21.5 / +14.5 / +0.7 pp | no skills | Appendix F | |
| Tasks with negative delta | 13 of 87 | | | worst -7.4 pp |

Audit of self-generated failures (verbatim): "generated packs the solver never discovers, creator-side authoring that displaces solver work, and confidently wrong pack content".

Companion, Agent Skills Can Be Harmful (2608.11888): Claude Opus 4.6 in OpenCode 1.15.1 on SkillsBench (84 tasks) and SWE-Skills-Bench (490 SE tasks); 307 confirmed skill-induced failures from 20,664 potential paired comparisons. Functional failures 125: Task-Implementation Fault 86 (68.8 %), Artifact Misplacement 24, Environment Mismatch 13, Applicability Mismatch 2 (1.6 %). Efficiency regressions 182: Excessive Procedure 114 (62.6 %, of which Excessive Verification 67), Context Bloat 46 (Skill-Body 43), Dependency Resolution 22. The companion reports SWE-Skills-Bench shows "limited average improvement, many skills with no pass-rate gain". Automated attribution (SkillTriage, GPT-5.5 2-of-3 vote) matched manual labels 88.8 % (functional) and 72.5 % (efficiency).

## Mechanism details you could implement
- If Engram induces Workflows, keep them short and few per task: more than three or comprehensive procedures erased most of the gain.
- Most harm came from on-topic procedures (only 2 of 125 functional failures were off-topic), so a relevance gate does not protect; a verifier-facing check does.

## Limitations, caveats, counter-evidence
- Self-generated skills here are written before the task with no trajectory feedback; induction from observed trajectories (AWM, EvoSkill) is a different, untested condition in this benchmark.
- Versions disagree (see flag).
- Skills are human-curated by benchmark contributors, some likely close to task authors (inference).

## Takeaways for tuning a memory stack
- Supports B16 in the weak form: model-authored procedures without outcome evidence hurt. It does not settle trajectory-induced procedures.
- For build-time SE work the upside of even curated procedures is modest (+4.5 to +11.6 pp depending on version), so procedural memory is not where the first gains are for Engram's use case.

## Open questions
- A SkillsBench-style paired test of trajectory-induced procedures vs raw trajectory exemplars on SE tasks does not appear to exist.
