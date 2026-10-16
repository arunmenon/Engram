---
schema_version: 1
artifact_id: N-SURVEY-20260928-25
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:arxiv:2404.03868
claim_cluster: learned-types-and-canonicalisation (arxiv:2404.03868, arxiv:2505.23628)
found_via: survey
source_url: https://arxiv.org/abs/2404.03868
strength: paper-ablated
pillar_primary: R10
pillar_secondary: ["R9", "R2"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["extract then define then canonicalise", "schema retriever", "merging new relation types into existing ones", "schema induction at scale with an 8B model"], "workload": ["open knowledge-graph construction"], "lifecycle_stage": ["ingestion", "schema evolution"], "cross_cutting": ["type admission"]}
evidence: {"directness": "medium: relation-type canonicalisation on WebNLG, REBEL, Wiki-NRE; no engineering artifacts", "control": "medium: EDC ablates the schema retriever and compares with CESI, REGEN, GenIE; AutoSchemaKG has no admission gate to ablate", "independence": "medium: academic groups", "reproducibility": "medium: public benchmarks", "applicability": "medium: canonicalising a proposed new type into an existing one is the admission decision the EvoOntology gate makes by task score"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Canonicalising proposed types into existing ones yields fewer types at higher precision (WebNLG 200 relations at 0.956 vs CESI 280 at 0.724); no paper ablates a type-admission gate directly"]}
answers_watch_request: null
---

# Extract, Define, Canonicalize (EDC, arXiv 2404.03868) and AutoSchemaKG (arXiv 2505.23628): how learned types are kept from multiplying

- **URL:** https://arxiv.org/abs/2404.03868 ; https://arxiv.org/abs/2505.23628
- **Type:** paper (two, one cluster)
- **Author / org:** not captured in the extract
- **Date:** v2 2024-10-02 (EDC); v3 2025-08-01 (AutoSchemaKG)
- **Retrieved:** 2026-09-28, arxiv HTML through a summarising fetch
- **Cited by evidence:** CTO focus questions 2 and 4 (learned ontologies; admitting a new type)
- **Relevance to a memory stack:** medium. These are the measured alternatives to hand-modelled types, and a check on EvoOntology (N-20260928-07).

## TL;DR
- **EDC** has an LLM extract triples, define each relation in words, then canonicalise it: a fine-tuned E5-Mistral-7B schema retriever proposes existing relations and the LLM verifies whether the new one is the same.
  - Self-canonicalisation, precision with the number of relation types kept:
    - WebNLG: 0.956 with 200 relations, against CESI 0.724 with 280
    - REBEL: 0.867 with 225, against 0.504 with 307
    - Wiki-NRE: 0.898 with 106, against 0.753 with 114
  - Removing the schema retriever lowers F1 on WebNLG from 0.794 to 0.752 and on REBEL from 0.559 to 0.517.
  - A Mistral-7B extractor trails GPT-4 by about 5 to 7 F1 points (WebNLG EDC+R 0.762 against 0.820).
- **AutoSchemaKG**: Llama-3-8B extracts and induces a schema over 900M+ nodes and 5.9B edges, at about 78,400 GPU-hours.
  - Triple precision about 99 to 100%, judged by DeepSeek-V3 (Table 2).
  - The induced schema reaches "over 80% and often 90% recall" against human types, by semantic similarity (Table 4).
  - 12 to 18% gains over dense retrieval on multi-hop QA (Table 5).
  - It has no admission filter.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| canonicalisation precision / #relations, WebNLG | 0.956 / 200 | CESI 0.724 / 280 | EDC, human evaluation | |
| same, REBEL | 0.867 / 225 | 0.504 / 307 | EDC | |
| same, Wiki-NRE | 0.898 / 106 | 0.753 / 114 | EDC | |
| F1 without schema retriever, WebNLG | 0.752 | 0.794 with | EDC ablation | |
| extractor size gap, WebNLG EDC+R | Mistral-7B 0.762 | GPT-4 0.820 | EDC | table number not captured |
| triple precision | 99.13 to 100.0 | none | AutoSchemaKG Table 2 | LLM judge (a different model) |
| schema recall vs human types | >80%, often 90% | | AutoSchemaKG Table 4 | similarity-based |

## Mechanism details you could implement
- Admission of a new link or node type in three steps: define it in words, retrieve the nearest existing types, then decide `same_as_existing(k)` or `new`. This is a closed Choice over k+1 options, a natural typed-decision shape.
- Count types. A rising type count without a precision gain is the failure EDC avoids and AutoSchemaKG does not guard against (inference).

## Limitations, caveats, counter-evidence
- Nobody ablates the admission gate as a separate component. EvoOntology's gate admits by downstream task score, EDC's by semantic sameness, so they are different gates.
- These are open-domain relation types. PDLC types are few and known in advance, so learned types matter mostly for team-specific artifacts (runbook, feature flag, incident).

## Takeaways for tuning a memory stack
- Keep a prescribed PDLC core. Admit new types only through canonicalise-first then gate-by-task, combining EDC with the EvoOntology gate.

## Open questions
- Which gate matters for us: sameness or task score? Test both on proposed types from our own traffic.
