---
schema_version: 1
artifact_id: N-SURVEY-20260928-16
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:38:00Z
idempotency_key: note:survey:arxiv:2609.21616
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R6]
memory_stage: ingestion
priority: 4
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 4
  independence: 5
  reproducibility: 5
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.21616
found_via: survey
claim_cluster: local-open-weight-labelling-of-engineering-artifacts
---

# Labelling Bug-Fixing Commits with Local Open-Weight Language Models

- **URL:** https://arxiv.org/abs/2609.21616 (HTML read). Pipeline and corpus: https://github.com/Raubkatz/BugFixCommitLabelling (CC BY 4.0)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** 2026-09
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R10 question 4 (typing engineering artifacts at ingestion) and R6 benchmark design
- **Relevance to a memory stack:** medium. Typing a commit (bug fix or not) from message plus diff with a local model is an ingestion-stage decision for our PDLC graph, and the paper's benchmark-design finding applies directly to our PDLC memory benchmark.

## TL;DR
- Seven local open-weight models (7B to 122B) label commits from message plus diff; on the manually validated SmartSHARK Java corpus the best, mistral-small3.2:24b, reaches F1 0.645 +/- 0.093 (P 0.572, R 0.751), against a keyword baseline at F1 0.399 +/- 0.114.
- "Larger models do not consistently outperform smaller ones": qwen3.5:122b F1 0.620, below the 24B and 35B models.
- Corpora without negative examples cannot rank classifiers by precision; the model ranking on positive-only corpora "inverts" on the negative-inclusive corpus.
- Released: 389,567 labelled commits (79,696 fixes) from 33 projects in Java, Python, JavaScript, as a silver standard.

## What it claims / describes
Prompt each model with the commit message and the code diff (at most ten changed files and fifty lines per file), deterministic decoding (temperature 0, top-p 0, top-k 1), on two rented L40 GPUs. Compare with a stemming keyword baseline ("fix", "bug", "fixup", "fail", "correct").

## Numbers
| Model | F1 | Precision | Recall |
|---|---|---|---|
| mistral-small3.2:24b | 0.645 +/- 0.093 | 0.572 +/- 0.107 | 0.751 +/- 0.099 |
| qwen3.6:35b | 0.633 +/- 0.094 | 0.545 +/- 0.117 | 0.773 +/- 0.088 |
| qwen3.5:122b | 0.620 +/- 0.093 | 0.517 +/- 0.117 | 0.799 +/- 0.074 |
| Keyword baseline | 0.399 +/- 0.114 | 0.436 +/- 0.137 | 0.394 +/- 0.143 |

Other models tested: codegemma:7b, gemma4:12b, codestral:22b, qwen3-coder:30b (per-model numbers not extracted). Time per commit: not stated.

## Mechanism details you could implement
- Input budget that worked: message plus at most 10 files x 50 lines of diff.
- Deterministic decoding for reproducible labels (relevant to R1 replay).

## Limitations, caveats, counter-evidence
- Precision around 0.52 to 0.57: roughly four in ten predicted fixes are wrong; not good enough to write edges without a gate.
- Generative prompting only; no typed decision model or fine-tuned encoder arm.

## Takeaways for tuning a memory stack
- For ingestion typing on private code, a local 24B to 35B model is enough; scaling to 122B did not help. This supports keeping memory text in-house at ingestion (priority 2) without frontier models.
- PDLC memory benchmark rule: every link or type question set must include negatives (non-links, non-fixes, unchanged requirements) or precision cannot be measured and rankings can invert.

## Open questions
- Would a System One model (Jev or open-weight) with a Noul "does this diff fix a defect described in the message?" match the 24B model at lower cost?
