---
schema_version: 1
artifact_id: N-SURVEY-20260928-14
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:31:00Z
idempotency_key: note:survey:arxiv:2607.28587
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R6]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 4
  control: 3
  independence: 5
  reproducibility: 4
  applicability: 5
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2607.28587
secondary_sources:
  - https://arxiv.org/abs/2609.01087
  - https://arxiv.org/abs/2602.01253
found_via: survey
claim_cluster: automatic-implements-trace-link-accuracy
---

# How well can a model decide an IMPLEMENTS trace link? PAIChecker, fine-tuned PR-issue alignment, and TraceLLM

- **URL:** https://arxiv.org/abs/2607.28587 (PAIChecker, ASE 2026; code https://github.com/manyiResearch/PAIChecker). Cluster companions read: https://arxiv.org/abs/2609.01087 (fine-tuning LLMs to classify PR-issue alignment, submitted to EMSE), https://arxiv.org/abs/2602.01253 (TraceLLM, requirements traceability by prompting)
- **Type:** paper (three independent papers, one claim cluster)
- **Author / org:** not stated in the extracted text
- **Date:** 2026-07 (PAIChecker v2), 2026-09-01 (PR-issue fine-tuning), 2026-02-01 (TraceLLM)
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R10 questions 1 and 2 (trace link recovery accuracy; can a small model decide links)
- **Relevance to a memory stack:** high. The PDLC graph's IMPLEMENTS and REFINES edges will be decided by a model. These papers give the current accuracy for exactly that decision, the human agreement ceiling, and show that the "free" gold links (a PR that references an issue) are wrong often enough to matter.

## TL;DR
- Explicit PR-issue pairs are not ground truth: in SWE-bench Verified, 68 of 500 (13.6%) pairs are misaligned (two annotators, kappa 0.91 binary, 0.86 fine-grained). Patterns: defective PR 30, scope creep 22, incomplete specification 18, follow-up PR 3, unspecified literal 1.
- A three-phase multi-agent checker detects misalignment at 88.11% to 92.12% binary accuracy with frontier backbones (Gemini-3.1-Pro best: 92.12% accuracy, 91.10% F1; Qwen-3.5-Plus 80.56%, 74.07% F1), at 42K to 59K tokens and $0.08 to $0.23 per instance.
- Fine-grained alignment (exact / missing / tangling / both) is hard even for humans: kappa 0.575 on 400 Transformers PR-issue pairs. Fine-tuned 3B to 7B code models reach 62.75% average accuracy but only 34.44% average macro-F1 (best macro-F1 35.80%, Deepseek-Coder); StableCode-3B (1.6 GB) at 65% accuracy matches Llama-3.1-70B prompting at 64.06%.
- Classic requirement -> design trace recovery by prompting (TraceLLM, CM1): best GPT-4o-Mini prompt reaches precision 0.52, recall 0.59, F2 0.57 zero-shot, against a prior LLM result of P 0.38, R 0.85, F2 0.43. True links are 1% to 4% of candidate pairs in these datasets.

## What it claims / describes
PAIChecker: Phase I, three sub-agents analyse the issue, the PR scope and the PR's connections; Phase II synthesises a preliminary label set; Phase III validates at code level with repository file retrieval. Evaluated on SWE-Gym and SWE-bench Multilingual.

PR-issue fine-tuning: 400 pairs from huggingface/transformers, labelled in two stages by raters with 3, 7 and 20+ years of experience. Classes: Exact 267 (66.75%), Missing 59 (14.75%), Tangling 56 (14%), Missing and Tangling 18 (4.50%). 50/50 split stratified by merge status; training set augmented to 800 (200 per class). Parameter-efficient fine-tuning of CodeLlama-7B, CodeQwen1.5-7B, StableCode-3B, CodeGemma-7B, Deepseek-Coder-6.7B; GPT-4o instruction-tuned via API. A100 40 GB, 10 epochs, batch 16, lr 3e-5, AdamW, 8-bit backbone.

TraceLLM: prompt engineering and demonstration selection across eight LLMs on CM1 (22 requirements, 53 design elements, 45 true links), EasyClinic UC-TC (63 links), EasyClinic UC-ID (26 links), CCHIT (1,064 requirements, 10 regulations, 78 links). Label-aware, diversity-based demonstration sampling worked best.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Misaligned PR-issue pairs, SWE-bench Verified | 13.6% (68/500) | | manual, kappa 0.91 | curated benchmark; raw repos likely worse (inference) |
| PAIChecker binary accuracy / F1, SWE-Gym | Gemini-3.1-Pro 92.12% / 91.10%; GPT-5.3-Codex 88.11% / 87.17%; Claude-Sonnet-4.6 87.49% / 86.52%; Qwen-3.5-Plus 80.56% / 74.07% | single-LLM prompting (numbers not extracted) | | |
| PAIChecker cost | 42K to 59K tokens; $0.08 to $0.23 per instance | | | |
| Human agreement, 4-class PR-issue alignment | kappa 0.575 | | 400 pairs | ceiling for any model |
| Fine-tuned 3B to 7B, 4-class | accuracy 62.75% avg (best 66.00%, CodeLlama-7B); macro-F1 34.44% avg (best 35.80%) | base models 59.11% acc, 30.07% macro-F1 | single repo | no cross-project test |
| StableCode-3B vs Llama-3.1-70B prompting | 65% vs 64.06% accuracy | | | |
| TraceLLM CM1, GPT-4o-Mini zero-shot | P 0.52, R 0.59, F2 0.57 | prior LLM P 0.38, R 0.85, F2 0.43 | | full comparison table truncated in the read; cost not extracted |

## Mechanism details you could implement
- Separate "is there a link" from "is the link exact": PAIChecker's taxonomy (scope creep, defective PR, incomplete spec, follow-up PR) is a ready label set for an IMPLEMENTS edge's `status` or `confidence` reason.
- Do not take explicit references (PR body says "fixes #123") as confidence 1.0; start them high but let a checker downgrade them.
- Candidate links are sparse (1% to 4% positives in classic datasets): report precision at fixed recall, not accuracy.

## Limitations, caveats, counter-evidence
- PAIChecker's backbones are frontier LLMs; no System One or small model arm.
- The fine-tuning study uses one repository and augmentation; its macro-F1 is low partly because minority classes are tiny.
- TraceLLM datasets are small, old, and not agent-era artifacts.
- None of the three reports calibration of link confidence.

## Takeaways for tuning a memory stack
- An IMPLEMENTS decision is not a solved classification: frontier multi-agent checkers reach about 88% to 92% binary accuracy at several cents per link; small fine-tuned models match large prompted models on accuracy but are weak on the minority "partly implements" classes.
- The human ceiling for fine-grained link typing is modest (kappa 0.575); keep our link taxonomy coarse at first (implements yes / no / partial) and carry a confidence.
- No source tests a System One model on this decision. That gap is exactly the CTO's priority 3 slice.

## Open questions
- Does a typed decision model (Jev or an open-weight one) reach PAIChecker's binary accuracy at a small fraction of its $0.08 to $0.23 per link?
- Is its confidence calibrated enough to gate which links are written without review?
