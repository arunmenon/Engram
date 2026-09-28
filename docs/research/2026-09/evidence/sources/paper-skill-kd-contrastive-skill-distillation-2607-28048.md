---
artifact_id: N-SURVEY-20260927-08
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2607.28048
input_refs: []
pillar_primary: R5
pillar_secondary: []
beliefs_affected:
  supports: []
  contradicts: [B15]
  note: weak contradiction; a single contrastive success/failure update did not beat single-source induction, and the gain came from validation and consolidation, not from richer evidence
evidence:
  directness: 3
  control: 3
  independence: 4
  reproducibility: 1
  applicability: 2
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2607.28048
found_via: survey
---

# SKILL-KD: Contrastive Skill Distillation for LLM Agents

- **URL:** https://arxiv.org/abs/2607.28048 (HTML v2 read)
- **Type:** paper
- **Author / org:** Qiming Shi, Yibo Dou, Jiawen Zhu, Yulong Tao, Linbo Jin, Zhaolu Kang, Yunfan Zhou, Di Weng
- **Date:** v2, 4 Aug 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R5 question on B15 (comparative evidence) and H6
- **Relevance to a memory stack:** medium. The one ablation found that separates "richer, contrastive evidence" from "validated, consolidated updates" in skill induction.

## TL;DR
- Skills distilled for a student model from teacher and student trajectories, with adaptive validation and drift-aware consolidation.
- Ablation (Group 1, Qwen3.5-4B student, Qwen3.7-plus teacher): Pairwise contrastive update 59.0, Batch of four trajectories 59.4, Student-only 60.1, Teacher-only 58.3, full SKILL-KD 66.8, no skill 43.5.
- Authors, verbatim: "richer behavioral evidence alone is insufficient, while adaptive validation and drift-aware consolidation are critical for producing effective and compact skills."
- Full method also produced the most compact skills: 38 rules / 3,010 words vs 85 / 6,966 for Pairwise.
- Single run per benchmark, no variance, no code link.

## What it claims / describes
Contrastive skill distillation across teacher and student trajectories on five benchmarks: SearchQA, SpreadsheetBench, DocVQA, LiveMath, ALFWorld. Group 2 uses Qwen3.6-35B-A3B student with ChatGPT-5.5 teacher.

## Numbers

Table 2, skill-acquisition variants, Group 1 (verbatim):

| Method | Avg. score | Avg. gain | Total rules | Total words |
|---|---|---|---|---|
| No Skill | 43.5 | +0.0 | 0 | 0 |
| Student-only | 60.1 | +16.6 | 96 | 6,821 |
| Teacher-only | 58.3 | +14.8 | 80 | 5,683 |
| Batch | 59.4 | +15.9 | 46 | 3,849 |
| Pairwise | 59.0 | +15.5 | 85 | 6,966 |
| SKILL-KD | 66.8 | +23.4 | 38 | 3,010 |

Splits (train/val/test): ALFWorld 39/18/134; SpreadsheetBench 80/40/280; SearchQA 400/200/1400; LiveMath 35/18/124; DocVQA 107/53/374. Runs: one per benchmark. Cost, latency: not stated.

## Mechanism details you could implement
- Separate the evidence operator (single, pairwise, batch) from the acceptance operator (validate on a held-out split, consolidate against drift). Only the second moved the score by more than about 1 point here.

## Limitations, caveats, counter-evidence
- Single run; the 1.1-point gap between Student-only and Pairwise is inside any plausible noise floor (inference), so this shows "no measurable benefit", not harm.
- Not coding agents and not cross-lineage comparison in MGM's sense (MGM compares agents from different lineages on the same task; here teacher vs student trajectories). Applicability to B15 is partial.
- No code.

## Takeaways for tuning a memory stack
- B15 remains a lead: MGM's ablation is still the only support, and this independent ablation found no gain from contrastive evidence alone once validation was held out of the comparison.
- H6 should be run as a 2x2: evidence (single vs comparative) x acceptance (ungated vs validation-gated). Otherwise a comparative-arm win cannot be told apart from a validation effect.

## Open questions
- Does MGM's Phi_CH gain survive when both arms get the same validation gate?
