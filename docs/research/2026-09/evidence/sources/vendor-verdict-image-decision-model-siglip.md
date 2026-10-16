---
schema_version: 1
artifact_id: N-20261001-05
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105231812524171610", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:shubhambaid/verdict
claim_cluster: hf:shubhambaid/verdict
feeds: ["memory"]
primary_source: https://huggingface.co/shubhambaid/verdict
source_commit: e6c08fc0b84a2f8c13ec12720946f88cb229fec6
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision head on frozen encoder", "other / none option", "per-question-type temperature", "order-free option tokens"], "workload": ["image classification"], "lifecycle_stage": ["none"], "cross_cutting": []}
evidence_grade: {"directness": "high: results table against the encoder's own zero-shot baseline on held-out classes", "control": "high: same frozen encoder as baseline, held-out classes and a held-out domain, checkpoint chosen on validation classes", "independence": "low: single builder, own split", "reproducibility": "medium: weights and package at a pinned revision; training code and seeds not read", "applicability": "low: images, not text memory; the abstention-transfer finding carries over"}
beliefs_affected: {"supports": ["B11"], "contradicts": [], "would_create": ["A trained 'none of these' option in a small decision head abstains well in-domain (0.623 on unseen classes) but transfers poorly to a new domain (6% on EuroSAT), so admission gates need per-domain abstention measurement"]}
claim_correction: The post reports only the yes/no win (0.94 vs 0.75); the card also shows Verdict 1 to 4 points below plain SigLIP 2 zero-shot on multiple choice and 7.8 points below on the new domain (0.346 vs 0.424).
memory_stage: none
priority: 2
---

# Verdict v1: a 6.2M-parameter typed-decision head on a frozen SigLIP 2 encoder (images, Jev/Laya-style)

- **URL:** https://huggingface.co/shubhambaid/verdict
- **Type:** repo (Hugging Face model)
- **Author / org:** shubhambaid (Shubham Baid); licence not set in card metadata; training data licences vary (DTD research-only)
- **Date:** created 2026-09-30T08:12:46Z; revision e6c08fc0b84a2f8c13ec12720946f88cb229fec6
- **Retrieved:** 2026-10-01 (README.md at the pinned revision). results.md not read; weights not downloaded.
- **Cited by evidence:** @shubhamkahanhai, 2026-09-30, https://x.com/shubhamkahanhai/status/2105231812524171610
- **Relevance to a memory stack:** low to medium. Images are not our workload, but it is a clean, honestly reported small decision model with a trained "other" option, measured on held-out classes and a held-out domain.

## TL;DR
- Head: "a 3-layer transformer over `[question] [pooled image] [7x7 patch tokens] [option_1 ... option_k] [OTHER]`, with one token per option and no positional encoding, so option order doesn't matter." Each option logit is SigLIP's own zero-shot score (`scale*cos + bias`) plus a learned correction; one temperature per question type fitted on validation classes.
- Wins big on yes/no (`noul`): unseen classes 0.941 vs 0.751 zero-shot; new domain (EuroSAT) 0.689 vs 0.495.
- Loses on multiple choice: unseen k=10 0.910 vs 0.938; all-classes 0.767 vs 0.805; EuroSAT k=10 0.346 vs 0.424.
- Abstention: with the correct answer removed, says `other` 0.623 on unseen classes, but only 6% on EuroSAT.
- Option phrasing swings accuracy: default label template 0.970 on a 200-image probe; "{label}, {description}" 0.420.

## What it claims / describes
Question types: `choice` (pick one option or `other`) and `noul` (is this statement about the image true?); `score` not supported. Training: about 23k images from CIFAR-100, Oxford-IIIT Pets, Flowers-102, DTD, Food-101; 20% of each dataset's classes held out for test, 10% for validation; EuroSAT held out entirely. Choice questions use k = 2 to 100 options; 15% have the correct answer removed (target `other`); 20% of questions are noul. "For noul questions the options are two learned YES/NO tokens, so label wording can't sway the answer." With the correction at zero the head reproduces SigLIP's own decision. Same request/response shape as Jev (`type`, `instructions`, `criteria`; `probabilities`, `choice`, `confidence`).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| seen classes, choice k=10 | 0.932 | SigLIP 2 zero-shot 0.935 | macro-avg over datasets (card "Results") | |
| unseen classes, choice k=10 | 0.910 | 0.938 | held-out classes | below baseline |
| unseen classes, choice over all classes | 0.767 | 0.805 | | below baseline |
| EuroSAT, choice k=10 | 0.346 | 0.424 | new domain | below baseline |
| seen classes, noul | 0.955 | 0.753 | | |
| unseen classes, noul | 0.941 | 0.751 | | the post's headline |
| EuroSAT, noul | 0.689 | 0.495 | | |
| unseen, correct answer removed -> `other` | 0.623 | n/a (zero-shot cannot abstain) | | |
| EuroSAT, correct answer removed -> `other` | 6% | n/a | card "Limitations" | abstention does not transfer |
| option phrasing probe | 0.970 default; 0.420 "{label}, {description}"; 0.810 custom template | | 200 Pets images, cat/dog/bird | |
| head size | 6.2M parameters | | frozen siglip2-base-patch16-224 | |

## Mechanism details you could implement
- Residual decision head: start from the base encoder's zero-shot score and learn a correction, so an untrained head equals the baseline (safe default).
- Order-free option tokens (no positional encoding) remove option-order bias by construction; compare with the permutation averaging other builders need for Jev (see N-20261001-02).
- Train the none/other option explicitly by removing the gold answer from 15% of questions; fit one temperature per question type on held-out classes.
- For text memory (inference): the same recipe on a frozen text embedder could give a tiny in-house admission or rerank head, but measure abstention per domain.

## Limitations, caveats, counter-evidence
- Card: trained only on class-membership questions; counting, spatial, quality and free-form statements untested; free-form noul answers "unvalidated"; abstention transfers poorly; 224 px frozen encoder; data licences vary.
- Single builder, no seeds or intervals stated in the card; results.md (ECE, AUROC) not read this run.

## Takeaways for tuning a memory stack
- A trained "none" option can look good in-domain and collapse out of domain (0.623 to 6%). Any admission or recall gate we train must report abstention on a held-out domain (for us: a held-out project or repository).
- A small head on a frozen encoder can beat the encoder's zero-shot on yes/no but lose on multi-way choice; test each question type separately.

## Open questions
- What are the ECE and AUROC values in results.md?
- Would the same residual-head recipe on a text embedder match Laya-class models on our yes/no memory questions?

## Grading and labels
- **Directness: high.** **Control: high** (same encoder baseline, held-out classes and domain, validation-only selection). **Independence: low.** **Reproducibility: medium.** **Applicability: low.**
- **Pillars:** R9 primary (small open decision models); R4 secondary (abstention). **Memory stage:** none. **Priority:** 2.
- **Beliefs:** supports B11 (admission must allow empty, and the none option is a separate design problem: here it works in-domain and fails out of domain). **Contradictions:** none.

## Origin chain
Post @shubhamkahanhai 2105231812524171610 (2026-09-30) -> hf:shubhambaid/verdict at e6c08fc -> README.md sections "Architecture", "Training", "Results", "Limitations" -> this note. Independence: builds on Google's SigLIP 2; no shared authors with other bus notes.
