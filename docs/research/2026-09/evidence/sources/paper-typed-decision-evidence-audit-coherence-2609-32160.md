---
schema_version: 1
artifact_id: N-SURVEY-20260929-05
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2609.32160
input_refs: []
pillar_primary: R9
pillar_secondary: [R6, R4]
memory_stage: evaluation
priority: 1
beliefs_affected:
  supports: [B14, B20]
  contradicts: []
evidence:
  directness: 4
  control: 3
  independence: 5
  reproducibility: 3
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.32160
secondary_sources:
  - https://arxiv.org/abs/2609.33209
  - https://arxiv.org/abs/2609.33971
found_via: survey
claim_cluster: typed-decision-evidence-standard-and-probability-coherence
---

# Typed Decision Models: An Early Evidence Audit and Evaluation Checklist (arXiv 2609.32160), with the probability-coherence papers (arXiv 2609.33209, 2609.33971)

- **URL:** https://arxiv.org/abs/2609.32160 (no code). Companions: https://arxiv.org/abs/2609.33209 (code https://github.com/bro789/typed-decision-coherence, read in full), https://arxiv.org/abs/2609.33971 (code https://github.com/samanjoy2/system-one-coherence, abstract only)
- **Type:** paper (an audit of 28 papers, plus two measurement papers)
- **Author / org:** Lijuan Tang, Yuemeng Zheng (Northeastern University); Keyi Li, Yihao He, Quanyi Li (Northeastern University, Shenyang); Saman Sarker Joy
- **Date:** 2026-09 (audit snapshot as of 2026-09-25); 2026-09-27 (both coherence papers)
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 question 1; shapes how every R9 card should be designed
- **Relevance to a memory stack:** high for our experiment design. It says which baselines a System One claim needs before it counts, and it shows that Jev's yes/no probabilities for related questions do not fit together, which matters for any gate that combines several Noul answers.

## TL;DR
- Audit of 28 arXiv papers written within nine days of Jev's 15 Sep 2026 release: "The typed readout has not yet shown an independent accuracy advantage." Only 5 of 26 compare against a label log-probability baseline on the same backbone; 1 of 27 tests option-name invariance; 12 of 27 report no confidence intervals or significance tests; 3 of 20 report latency with and without caching.
- Where the typed head was compared against the same backbone reading label tokens, it tied: AUROC .974 vs .950 (not significant); macro accuracy .761 vs .761.
- "Repeated-request caching shrinks the median paired latency difference to under a millisecond"; Jev's two-decimal output grid limits resolution for labels rarer than 1%.
- Coherence (2609.33209, 160 items, 480 negation pairs): Jev's P(yes) for a statement and for its negation deviate from summing to 1 by a mean 0.064 (Qwen3.8-27B first-token 0.293, verbalised 0.122); Jev's three separate single-label yes/no probabilities sum to 1.14 on average although its multiple-choice probabilities always sum to 1.
- 2609.33971 (abstract): rebuilding a probability through intermediate categories disagrees with the direct answer by total variation 0.219 to 0.689; accuracy changes ranged from +21.3 to -22.9 points.

## The 14-item checklist (2609.32160), with compliance in the audited papers
- Baselines: B1 label log-prob baseline on the same backbone (5/26); B2 cheap generative cascade baseline (1/5); B3 task-specific trained model (7/13).
- Test design: T1 spread between models, avoid saturated tests (parity claims were made on 100/100, 63/63, 212 to 216 of 216); T2 consistency across repeated, reordered, reworded requests (17/26); T3 option-name invariance (1/27); T4 data provenance.
- Reporting: R1 exact version and run date; R2 CIs or significance tests (15/27); R3 disclose choices made after seeing test data.
- Calibration: C1 calibration measured (13/17); C2 accuracy on the highest-confidence examples; C3 thresholds fitted on held-out data (7/7); C4 latency with and without caching (3/20).

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Typed head vs label tokens, same backbone | AUROC .974 | .950 | Ren et al. as audited | not significant |
| Typed head vs typed-head control | macro acc .761 | .761 | Yu and Yao as audited | 8.9x faster |
| Jev vs best of 19 LLMs | median macro-F1 -11.6 | | Ibrahim and Zaki as audited | 44x cheaper |
| Jev escalation example | 92.5 | GPT-6 93.1 | as audited | at 57% of the fee |
| Negation complementarity MAD | Jev 0.064 [0.055, 0.072], same-side rate 0.067 | Qwen3.8-27B first-token 0.293 (same-side 0.417); verbalised 0.122 | 480 pairs, ChaosNLI and PubMedQA | temperature 0 |
| Jev repeat-noise floor | 0.013 | | same | violations about 5x noise |
| Partition additivity abs(sum - 1) | Jev 0.141 | Qwen 0.319 | Table 3 | single-label yes/no sum 1.14 |
| Cross-format gap | Jev 0.091 | Qwen 0.131 | Table 3 | |
| 10 questions batched vs separate | difference +0.0004 [-0.0021, 0.0029] | | 2609.33209 | batching is safe |
| Cost | 3,360 Jev calls for $0.0757; median 0.64 s | Qwen on 2x RTX A6000, vLLM 0.19.1, 0.44 s | 2609.33209 | |
| Direct vs rebuilt probability | TV 0.219 to 0.689; accuracy +21.3 to -22.9 | | 2609.33971, Jev and Laya, 72,000 questions | abstract only |

## Limitations, caveats, counter-evidence
- The audit covers papers written within nine days of release, mostly on one hosted version; it flags internal numerical inconsistencies in several audited papers and opposite cost directions between two sibling papers.
- Coherence: 160 items, two English domains, one comparison LLM, one Jev version through one gateway, no paraphrase controls.

## Takeaways for tuning a memory stack
- Every R9 card should carry a label log-probability arm on an open backbone (B1) and a cheap generative cascade arm (B2), and report latency with caching off.
- Do not combine several separate Noul probabilities as if they were a distribution (for example "P(supersedes) + P(contradicts) + P(unrelated)"): ask one multiple-choice question instead, which Jev normalises. Batching up to 10 questions in one request did not change answers.
- Treat probabilities near a 1% base rate as coarse: the output grid is two decimals.

## Open questions
- Do our memory gates currently add or compare separate yes/no probabilities? If so, the incoherence applies directly (see PC-20260929-01 on which confidence number the code reads).
