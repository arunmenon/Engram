---
schema_version: 1
artifact_id: N-SURVEY-20261006-03
artifact_type: note
producer: triage
run_id: survey-20261006T054504Z-b489
created_at: 2026-10-06T06:40:00Z
idempotency_key: note:survey:aclanthology:2026.kallm-1.21
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R6]
memory_stage: linking
priority: 3
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: medium, control: low, independence: high, reproducibility: high, applicability: low}
source_url: https://aclanthology.org/2026.kallm-1.21/
found_via: survey
---

# Large Language Models for Knowledge Graph Extraction: A Schema-Constrained Evaluation Framework

- **URL:** https://aclanthology.org/2026.kallm-1.21/ (PDF read, pp. 224 to 227); code: https://github.com/SukSev/kg_benchmarking
- **Type:** paper (workshop, KG-LLM @ LREC 2026)
- **Author / org:** Markus Ilves, Eduard Barbu, Jaan Übi
- **Date:** May 2026
- **Retrieved:** 2026-10-06
- **Cited by evidence:** survey run, R10 questions 3 and 4
- **Relevance to a memory stack:** medium; tiny sample, but two signals we need: relations (links) are where models fail, and gold sets undercount correct links.

## TL;DR
- Closed schema of 6 entity types and 96 relation types injected in the prompt, DocRED, 10 documents.
- Entities are easy (F1 74.1 to 84.0); relations are not: triple F1 Claude Opus 4.5 39.9, Gemini 3 Pro 39.3, GPT-5.1 21.7, Mistral 7B 4.2.
- Mistral 7B: 266 hallucinated triples and 41 schema violations vs 0 to 6 for frontier models.
- Manual check of Gemini 3 Pro: of 156 extracted triples, 96 (61.5%) were not in gold, and reviewers found many of those textually supported. Strict triple F1 is a lower bound.

## Numbers
| Model | Entity F1 | Triple F1 | Halluc. triples | Missed triples | Schema violations | Relation mismatches |
|---|---|---|---|---|---|---|
| Gemini 3 Pro | 77.2 | 39.3 | 96 | 89 | 0 (not shown) | 3 |
| GPT-5.1 | 84.0 | 21.7 | 73 | 122 | 6 | 23 |
| Claude Opus 4.5 | 79.5 | 39.9 | 60 | 97 | 0 (not shown) | 3 |
| Mistral 7B | 74.1 | 4.2 | 266 | 140 | 41 | 13 |

Manual evaluation (Gemini 3 Pro, two-step, temperature 0, 3 evaluators): gold 186 entities, 149 triples; model 205 entities (151 matched, 54 additional), 156 triples (60 matched, 96 additional). Cost, latency: not stated. n = 10 documents (authors flag low statistical robustness).

## Limitations, caveats, counter-evidence
- 10 documents; Mistral 7B is a 2023 general model, not a System One decision model; one prompt design.
- Manual review covered one model only.

## Takeaways for tuning a memory stack
- Do not ask a small generative model to emit typed links free-form against a schema. If a small model is used at the linking stage, constrain it to a decision over candidate pairs (yes/no per link type), which is the System One shape (inference).
- For our PDLC benchmark: link gold sets will be incomplete; budget a manual adjudication pass of "false positive" links, or precision will be understated.
