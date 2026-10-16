---
schema_version: 1
artifact_id: N-SURVEY-20260930-01
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:55:00Z
idempotency_key: note:survey:arxiv:2609.05339
input_refs: []
pillar_primary: R7
pillar_secondary: [R1, R2, R6]
memory_stage: none
beliefs_affected:
  supports: [B22, B1, B5]
  contradicts: []
evidence: {directness: high, control: high, independence: medium, reproducibility: low, applicability: medium}
strength: paper-ablated
source_url: https://arxiv.org/abs/2609.05339
found_via: survey
---

# Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability

- **URL:** https://arxiv.org/abs/2609.05339 (HTML v1 read: https://arxiv.org/html/2609.05339v1)
- **Type:** paper
- **Author / org:** Ankit Goyal, Jaideep Ray (LinkedIn)
- **Date:** 2026-09-04 (v1)
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2609.05339.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R7 question 1 (swap test evidence)
- **Relevance to a memory stack:** high. It is the only source found that runs a swap test on the memory store itself (writer model, reader model, embedder) with the history held fixed, and reports what survives.

## TL;DR
- Four store formats over the same 48 synthetic histories: raw long context (LC-RAW), chunked retrieval (RAG), model-written notes (NOTES), fixed-schema knowledge graph (KG-fixed). Two open-weight models under 10B parameters act as writer and reader. Scoring is exact match, no LLM judge.
- Swapping the writer model barely moves a fixed-schema graph ("+0.0004 ± 0.0020") but moves model-written notes by "+9.91 or −13.28 percentage points depending on the specific migration direction".
- A half-migrated embedding index (50/50 old and new vectors) captures "only a 4.96-point accuracy improvement" of the "11.90-point gain achieved through full re-embedding".
- Repairing notes from the store alone fails in all 48 histories; keeping the raw history allows repair in 34 of 48 for one direction and 0 of 48 for the other.
- The authors' conclusion: "direction-specific migration testing, strict embedding space isolation, and the retention of source histories for memory repair".

## What it claims / describes
The same interaction history is preserved in four forms and then the model behind the store is changed.

1. LC-RAW: the history is kept verbatim and read in context.
2. RAG: the history is chunked and retrieved with a single-stage dense retriever (BAAI/bge-large-en, v1.0 then v1.5).
3. NOTES: a model compresses the history into natural-language notes.
4. KG-fixed: the history is normalised into a knowledge graph with a fixed schema.

Models: Llama-3.1-8B-Instruct and Qwen2.5-7B-Instruct-1M, served locally, deterministic reads, fixed seeds ("repeated live reads vary by only 0.0016").

Data: 48 synthetic evaluation histories (12 further calibration histories excluded), 160 questions per history (7,680 question-answer pairs). Question classes: direct facts, temporal changes, contradictions, multi-step relations, aliases. Entity and value codes are randomised so pretraining knowledge cannot answer.

Swaps tested: writer model (A to B and B to A), reader inheriting the other model's store, embedding model version, and repair with or without the raw history. Metrics: accuracy, RPAS (retained performance after swap), CTR (cost to recover).

Planned tests: four one-sided tests with a 5-point practical margin, Holm-adjusted. Two passed (H2 +6.95 pp, p 1.3e-6; H7a +8.90 pp, p 3.9e-7), two did not (H1 −1.47 pp, H4a −1.51 pp).

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| NOTES, Llama reader, inherited store | 0.4753 ± 0.0214 | own store 0.3762 ± 0.0164 (swap +9.91 pp) | 48 histories | notes written by the stronger model help the weaker reader |
| NOTES, Qwen reader, inherited store | 0.3391 ± 0.0164 | own store 0.4719 ± 0.0187 (swap −13.28 pp) | 48 histories | asymmetric |
| KG-fixed, Llama reader | 0.8445 ± 0.0075 inherited | 0.8456 ± 0.0072 own (−0.11 pp) | 48 histories | |
| KG-fixed, Qwen reader | 0.9880 ± 0.0024 inherited | 0.9878 ± 0.0036 own (+0.02 pp) | 48 histories | |
| LC-RAW | Llama 0.7121 ± 0.0084; Qwen 0.9109 ± 0.0071 | n/a | histories fit in context | no swap column |
| RAG | Llama 0.5346 ± 0.0116; Qwen 0.5647 ± 0.0125 | n/a | single-stage dense | |
| Old embedding index | 0.4257 ± 0.0099 accuracy; recall@k 0.4846; MRR 0.3237 | n/a | bge-large-en v1.0 | two readers pooled |
| Full re-embed | 0.5447 ± 0.0093 (+11.90 pp) | old index | v1.5 | |
| 50/50 mixed index | 0.4753 ± 0.0088 (+4.96 pp) | old index | half the vectors migrated | about 58 % of the upgrade gain lost (inference from the two rows) |
| Ideal routing upper bound | 0.5960 ± 0.0086 (+17.03 pp) | old index | knows which index holds the answer | not achievable, bound only |
| NOTES loss decomposition | total 0.584; store construction 0.467 ± 0.014 (80 %); retrieval 0.036 (6 %); reader residual 0.081 (14 %) | n/a | pooled | |
| RAG loss decomposition | total 0.450; retrieval 0.364 ± 0.012 (81 %); store construction 0.005 (1 %); reader residual 0.081 (18 %) | n/a | pooled | |
| Repair, NOTES with raw history, Llama to Qwen | 34/48 reach 90 % target, median $0.76; 28/48 at 95 %; 22/48 at 99 % | store-only 0/48 at every target | per history | |
| Repair, NOTES with raw history, Qwen to Llama | 0/48 at every target | store-only 0/48 | per history | raw history was not enough when the repair model was the weaker one |
| Repair, RAG re-embed | 48/48 at every target, median $0.013 | n/a | | |
| Repair, KG-fixed schema rebuild | 48/48 at 90 %; 45 to 48 of 48 at 95 to 99 % | n/a | about $0 | |
| Compute for the migration experiment | 1,440 evaluations, 98.2 GPU-hours, about $221 | n/a | | |
| Latency | not stated | | | |

Judge and system share a model: not applicable (exact scoring, no judge).

## Mechanism details you could implement
- A swap test for a memory store has at least three independent axes: writer model, reader model, embedder version. Test each direction separately; the notes result changes sign with direction.
- "Strict embedding space isolation": never serve one index holding vectors from two embedder versions. If a migration is staged, route per index rather than mixing (the routing upper bound was +17.03 pp against +4.96 pp for the mixed index).
- Keep the raw source history next to any model-written store. Store-only repair of notes reached the 90 % recovery target in 0 of 48 histories.
- Fixed-schema records are the portable form: the reader does not depend on the writer's phrasing.
- Loss decomposition recipe: measure (a) answer accuracy with oracle evidence (reader residual), (b) whether the needed fact exists in the store (store construction), (c) whether retrieval returned it. The three components add to the total loss.

## Limitations, caveats, counter-evidence
- Stated: "We tested only two similarly sized models on a scripted, objective workload whose histories fit comfortably within both context windows." Larger models, natural conversations and longer histories are untested.
- Stated: the result does not show "that knowledge graphs universally outperform natural-language notes".
- Stated: the retrieval result reflects "a single-stage dense retriever migrating between two same-dimensional embedding spaces".
- Stated: "The signed study plan served as an internal analysis lock rather than a full preregistration."
- Code and data: "available upon request". Not released, so reproducibility is low.
- (inference) The histories are synthetic with randomised codes. Engineering artifacts (requirements, decisions, pull requests) are longer and less regular, so the KG-fixed extraction accuracy (0.85 to 0.99 here) will not transfer; the portability ordering may.
- (inference) Only two writers are tested, so "direction" is confounded with "stronger versus weaker model".

## Takeaways for tuning a memory stack
- P0 step 2 already mutates "the curating model". Add two mutations: swap the embedder version with a partly migrated index, and swap the writer model for any summarised store. Record accuracy per direction.
- Treat Consumer 4 summaries as model-coupled. A model upgrade is a migration event for them, and the raw ledger is what makes repair possible (supports B1 and the ledger-first stance; supports B5's caution on summaries: 80 % of the notes deficit arose at construction).
- Typed nodes with a fixed schema are the portable part of the context graph. This is an argument for the ontology work that does not depend on retrieval lift.
- Put an embedder-version field on every vector and refuse mixed-version search.

## Open questions
- Does the ordering hold with frontier models as writer and reader, where notes are better written?
- Does a hybrid (BM25 plus dense) retriever reduce the mixed-index penalty, since the lexical leg does not depend on the embedder?
- What is the analogue for a decision model at the write gate: do stored gate decisions survive a change of decision model?
