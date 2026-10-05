---
schema_version: 1
artifact_id: N-SURVEY-20260928-22
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:arxiv:2409.04073
claim_cluster: small-model-entity-matching (arxiv:2409.04073, arxiv:2607.24688)
found_via: survey
source_url: https://arxiv.org/abs/2409.04073
strength: paper-single-benchmark
pillar_primary: R9
pillar_secondary: ["R10", "R7"]
memory_stage: linking
priority: 1
tags: {"mechanism": ["zero-shot entity matching with a 124M model", "leave-one-dataset-out", "cross-encoder vs bi-encoder vs generative matchers"], "workload": ["record matching across heterogeneous tables"], "lifecycle_stage": ["linking"], "cross_cutting": ["cross-hub identity", "G13"]}
evidence: {"directness": "medium: entity matching on product and bibliographic tables, not engineering artifacts", "control": "medium-high: 9 datasets, leave-one-dataset-out, several baselines including GPT-4 MatchGPT; the companion paper runs 1,215 fine-tuning runs across architectures and sizes", "independence": "medium: academic groups, public benchmarks", "reproducibility": "medium: public datasets; commit not recorded", "applicability": "medium: cross-hub duplicate detection (G13) is the same task; losses concentrate on heterogeneous product-style records, which cross-tool records resemble (inference)"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["For cross-hub 'same thing' decisions, a small matcher gives up about 4 F1 points against GPT-4 at about 1/3,900 of the per-token cost; a generative model earns its cost mainly under distribution shift"]}
answers_watch_request: null
---

# AnyMatch: Efficient Zero-Shot Entity Matching with a Small Language Model (arXiv 2409.04073), with the companion factorial study arXiv 2607.24688

- **URL:** https://arxiv.org/abs/2409.04073 ; companion https://arxiv.org/abs/2607.24688 (abstract only; no HTML version)
- **Type:** paper
- **Author / org:** not captured in the extract
- **Date:** 2024-09 (AnyMatch); 2026-07-27 (companion)
- **Retrieved:** 2026-09-28, arxiv HTML through a summarising fetch; numbers are what the tool extracted from the tables
- **Cited by evidence:** CTO focus question 4 (G13, resolving the same entity across hubs)
- **Relevance to a memory stack:** medium-high. This is the quantified cost and accuracy trade for G13.

## TL;DR
- A GPT-2 (124M) matcher, evaluated zero-shot leave-one-dataset-out on 9 datasets, averages **81.96 F1 against 86.36 for MatchGPT on GPT-4** (Table 2).
- The cost per 1K tokens is "$0.0000038" against GPT-4's "$0.015", which the paper calls "3,899 times lower" (Table 4). Throughput is 693,999 tokens/s, against 26,721 for Jellyfish-13B and 2,108 for MatchGPT on Mixtral-8x7B (Table 3).
- Its losses are on heterogeneous product-style data: AMGO 55.08 vs 74.91, WAAM 61.51 vs 89.67, WDC 63.31 vs 85.83. It wins on BEER (96.55 vs 69.57).
- The companion study (Qwen3 family: 3 architectures by 3 variants by 3 sizes, 9 datasets, 1,215 runs) finds, in its abstract:
  - "Cross-encoders retain a consistent advantage over bi-encoders"
  - "Generative matchers do not universally outperform cross-encoders. Instead, their advantages concentrate under distribution shift"
  - "larger models rely more heavily on shortcut learning and therefore do not necessarily perform better"

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| mean F1 | 81.96 | MatchGPT GPT-4 86.36 | 9 datasets, zero-shot, Table 2 | gold labels, no LLM judge |
| AMGO F1 | 55.08 | 74.91 | Table 2 | largest loss |
| WAAM F1 | 61.51 | 89.67 | Table 2 | |
| WDC F1 | 63.31 | 85.83 | Table 2 | |
| BEER F1 | 96.55 | 69.57 | Table 2 | small model wins |
| cost per 1K tokens | $0.0000038 | $0.015 (GPT-4) | Table 4 | 2024 prices |
| throughput | 693,999 tok/s | Jellyfish 26,721; MatchGPT-Mixtral 2,108 | Table 3 | hardware not captured |
| companion tables | not read | | | abstract only |

## Mechanism details you could implement
- For G13: a small cross-encoder as the first pass over candidate pairs that share an identifier or title, with escalation to a larger model only when the pair comes from a source pairing never seen before (distribution shift).
- This extends G13's Noul `same_claim` with a pair-architecture choice: a cross-encoder rather than two embeddings compared.

## Limitations, caveats, counter-evidence
- None of the datasets contain engineering artifacts. Matching "Jira PAY-1423" against "GitHub issue #812" is untested.
- Jev or other typed decision models are not in the comparison.

## Takeaways for tuning a memory stack
- G13 is the gateway decision where the published evidence most favours a small model, provided the labelled set includes new source pairings.

## Open questions
- Does a typed decision model (Jev, Intern-Decision) land nearer the GPT-4 or the GPT-2 row on cross-tool pairs?
