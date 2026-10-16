---
schema_version: 1
artifact_id: N-20260926-06
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103302125593702883", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.29429
claim_cluster: arxiv:2609.29429
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.29429
source_commit: 473b72f290234a49484c4d89c03aababcd74f758
strength: paper-single-benchmark
pillar_primary: R4
pillar_secondary: ["R6", "R8"]
tags: {"mechanism": ["decision model as detector", "noul / choice / score questions", "calibration audit"], "workload": ["alignment-failure detection: injection, deception, hallucination, sycophancy"], "lifecycle_stage": ["read", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: AUROC and ECE per benchmark against scorer labels", "control": "medium: trivial baselines (length, TF-IDF, all-positive) and reference judges, split-half for targeted questions; one decision model only", "independence": "medium: academic authors not affiliated with TypeSafe (as far as stated); labels mostly from scorer LLM judges", "reproducibility": "high: benchmark and code released at a pinned commit", "applicability": "medium: prompt-injection (1,036 items) and concealing-uncertainty categories map to our memory injection gate; targets are 2-7B models, English only"}
beliefs_affected: {"supports": ["B14", "B24"], "contradicts": [], "would_create": ["Decision-model probabilities rank alignment failures well (median AUROC 0.886) but are poorly calibrated per benchmark (median ECE 0.168, worse than the paper's null 0.074); use them for ranking and fit thresholds per source"]}
claim_correction: none
---

# Just Ask Jev: Reinforcement Learning for Calibrated Decisions as a Zero-Shot Detector of AI Alignment Failures (arXiv 2609.29429)

- **URL:** https://arxiv.org/abs/2609.29429 (HTML read); code https://github.com/sumleo/RLCDAlignBench
- **Type:** paper + benchmark (RLCDAlignBench)
- **Author / org:** Ruoqi Guo, Yi Liu, Gelei Deng, Yuekang Li, Lida Zhao, Yutao Wu, Simin Chen, Ying Zhang, Leo Yu Zhang (affiliations not captured)
- **Date:** 2026-09-24
- **Retrieved:** 2026-09-26; repo HEAD `473b72f290234a49484c4d89c03aababcd74f758` (2026-09-25) via GitHub API; not cloned
- **Cited by evidence:** https://x.com/gastronomy/status/2103302125593702883 (@gastronomy, arXiv title bot; exploration sample E34)
- **Relevance to a memory stack:** high for R4/R8. The largest independent test we have of Jev (jev-1.13.0) as a detector, including 1,036 prompt-injection items, with explicit calibration numbers, which our belief B14 says nobody publishes.

## TL;DR
- RLCDAlignBench: 10 failure categories, 44 source benchmarks, 7,193 detection instances; one call to jev-1.13.0 answers typed questions about one input.
- Zero-shot generic noul: **median AUROC 0.886 [0.821, 0.952] over 31 benchmarks**; targeted questions (split-half) 0.911 [0.860, 0.944]; targeted gain "+0.006 [-0.004, +0.015]" (interval includes zero).
- Calibration: **per-benchmark ECE median 0.168 versus null 0.074**; pooled ECE 0.047. Pooled calibration looks fine; per-source calibration is worse than the paper's null reference.
- Cost "$0.30" per pass vs "$18.96" for reference judges (63x cheaper); median latency 0.31 s.
- Weak where the failure needs unobservable references (MACHIAVELLI reward annotations, deceptive goals); on GPT-3.5 outputs kappa 0.668 vs the judge's 0.790.

## What it claims / describes
- **Categories (items):** sycophancy 639, jailbreaks 414, deception 540, prompt injection 1,036, hallucination 1,164, privacy violation 808, social bias 199, reward hacking 714, concealing uncertainty 748, power seeking 931.
- **Questions:** generic templates with per-benchmark behaviour phrases; three answer types (noul, choice, score); targeted families (direct, rubric, decomposition).
- **Baselines:** response length, TF-IDF logistic regression, all-positive; reference scorers are LLM judges (GPT-4o-mini mentioned) and rule-based systems, which also supply most labels.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| generic noul AUROC, median | 0.886 [0.821, 0.952] | length / TF-IDF / all-positive (values not captured) | 31 benchmarks, zero-shot | labels mostly from scorer judges |
| targeted AUROC (split-half) | 0.911 [0.860, 0.944] | generic | | gain +0.006 [-0.004, +0.015] |
| per-benchmark ECE, median | 0.168 | null 0.074 | | the null's construction not captured (inference: base-rate predictor) |
| pooled ECE | 0.047 | | all instances | pooling hides per-source miscalibration |
| cost per pass | $0.30 | $18.96 reference judges | 7,193 instances | 63x |
| latency | median 0.31 s | | | |
| agreement on GPT-3.5 outputs | kappa 0.668 | judge 0.790 | | |

## Mechanism details you could implement
- Use the decision model's probability as a **ranking score** (AUROC is high) and set thresholds **per source or benchmark** on local labels; do not trust one global threshold (per-benchmark ECE 0.168).
- Report both pooled and per-source ECE; pooled ECE can look good (0.047) while each source is off.
- Generic questions are nearly as good as hand-targeted ones here (+0.006), so start generic and spend effort on thresholds, not phrasing (inference from the reported gain).

## Limitations, caveats, counter-evidence
- Verbatim: "RLCDAlignBench covers one RLCD model (jev-1.13.0), English benchmarks, 2-7B targets, and mostly scorer labels."
- Labels come mostly from LLM judges, so AUROC measures agreement with those judges, not ground truth.
- Whether judge and target model families overlap is not stated.
- Failures that need hidden context (reward annotations, the agent's actual goal) are not detectable from the transcript alone.

## Takeaways for tuning a memory stack
- For our served-memory injection gate (B24, jevmem pattern), expect good ranking but local threshold fitting per source (repo docs vs chat vs tool output). Calibrate before gating.
- Measure ECE per source in our P0 fixtures, not only pooled.

## Open questions
- Per-category AUROC for prompt injection specifically? Not captured in the fetched text.
- Does recalibration (isotonic/Platt) close the per-benchmark ECE gap? Not tested here (see N-20260926-07 for a 3.3x reduction on crash narratives).

## Grading and labels
- Directness high; control medium; independence medium; reproducibility high (commit 473b72f2); applicability medium.
- Pillar R4 (a decision model as a classifier; calibration). Secondary R6 (judge-label evaluation) and R8 (prompt-injection and deception detection).
- Beliefs: supports B14 (vendor calibration is claimed, not shown: per-benchmark ECE 0.168 vs null 0.074; fit thresholds locally). Supports B24 (injection gates on served memory are feasible, AUROC-level evidence, not a planted-line test). Would create the belief in frontmatter.
- Contradiction rows: none. (Pooled ECE 0.047 could be read as supporting the vendor calibration claim; per-benchmark numbers do not.)

## Origin chain
post 2103302125593702883 (@gastronomy, title only, no link) -> arXiv API title search -> arXiv 2609.29429 (HTML) -> composition, results and calibration sections, limitations -> repo sumleo/RLCDAlignBench @ 473b72f2. Independence: no shared authors with TypeSafe or our local sources (as stated); shares the model under test (jev-1.13.0) with N-20260926-07 and N-20260926-08.
