---
schema_version: 1
artifact_id: N-SURVEY-20261006-02
artifact_type: note
producer: triage
run_id: survey-20261006T054504Z-b489
created_at: 2026-10-06T06:35:00Z
idempotency_key: note:survey:arxiv:2605.29168
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R3]
memory_stage: ingestion
priority: 3
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: medium, control: medium, independence: high, reproducibility: medium, applicability: medium}
source_url: https://arxiv.org/abs/2605.29168
found_via: survey
---

# Better Later Than Sooner: Neuro-Symbolic KG Construction via Ontology-grounded Post-extraction Correction (OAK+MEND)

- **URL:** https://arxiv.org/abs/2605.29168 (read: https://arxiv.org/html/2605.29168v2)
- **Type:** paper
- **Author / org:** Lorenzo Loconte, Timothy Hospedales, Cristina Cornelio
- **Date:** v1 2026-05-27, v2 2026-09-06
- **Retrieved:** 2026-10-06
- **Cited by evidence:** survey run, R10 question 2
- **Relevance to a memory stack:** high; it answers "put the ontology in the prompt, or extract freely and fix afterwards?" with token cost.

## TL;DR
- Extract open-domain first, map types and predicates to the ontology by embedding similarity, then call the LLM only on facts that violate ontology constraints.
- Valid triples 96.8% (Qwen3-30B-A3B) vs 79.4% for putting the constraints in the prompt, at 0.59x the token cost of the Wikontic baseline (in-context is 0.79x).
- Downstream QA is unchanged (HotpotQA F1 56.4 vs 55.6 in-context, 57.7 Wikontic).

## What it claims / describes
Three stages: (1) open extraction with no ontology in the prompt; (2) canonicalization: cosine similarity between extracted type/predicate and ontology candidates (Qwen3-Embedding-0.6B); if several candidates are within beta=0.05 of the best, the LLM picks, given entities previously typed with that label; (3) MEND: targeted LLM correction only of facts violating constraints.

## Numbers
| Method | Triples valid | Qualifiers valid | Weighted token cost |
|---|---|---|---|
| OAK+MEND (Qwen3-30B-A3B) | 96.8% | 91.5% | 0.59x |
| OAK+MEND (GPT-OSS-120B) | 98.4% | 96.8% | 0.79x |
| Wikontic (Qwen) | 77.4% | not stated | 1.00x |
| In-context constraints (Qwen) | 79.4% | 82.6% | 0.79x |

| HotpotQA | EM | F1 |
|---|---|---|
| OAK+MEND (Qwen) | 45.6 | 56.4 |
| OAK+MEND (GPT) | 46.1 | 56.8 |
| Wikontic (Qwen) | 46.4 | 57.7 |
| In-context (Qwen) | 45.0 | 55.6 |

n = 1000 entries each from HotpotQA and MuSiQue. Validity is measured against the ontology's own constraints, not against a gold KG (no ontology-aligned gold exists, the authors say). Latency: not stated. Judge: none.

## Mechanism details you could implement
- Ambiguity band: only send canonicalization to the LLM when the top candidates are within 0.05 cosine. This is a natural slot for a System One model (inference).
- Constraint check is symbolic (domain/range type rules); repair is only paid for on violations.

## Limitations, caveats, counter-evidence
- Open-weight LLMs only; general Wikidata-style ontology, not software artifacts.
- "Valid" means schema-consistent, not correct: a well-typed wrong link counts as valid.
- QA did not improve; the benefit is consistency and cost, not answer quality.

## Takeaways for tuning a memory stack
- For PDLC ingestion, do not paste the full node and edge schema into every extraction prompt. Extract, canonicalize by embedding, and repair only violations (for example an `implements` edge from a test to a requirement).
- Measure link correctness separately from schema validity.

## Open questions
- Does the gap hold with a small schema (our ~7 node types, 7 link types) where in-prompt constraints are cheap?
