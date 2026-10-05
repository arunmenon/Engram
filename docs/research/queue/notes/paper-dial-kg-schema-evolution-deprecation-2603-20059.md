---
schema_version: 1
artifact_id: N-SURVEY-20261001-03
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:06:00Z
idempotency_key: note:survey:arxiv:2603.20059
input_refs: []
pillar_primary: R10
pillar_secondary: [R2, R9]
memory_stage: ingestion
priority: 3
beliefs_affected:
  supports: [B3]
  contradicts: []
related_notes: [N-SURVEY-20260928-25]
evidence:
  directness: 3
  control: 3
  independence: 3
  reproducibility: 1
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2603.20059
secondary_sources:
  - https://arxiv.org/abs/2609.34789
found_via: survey
claim_cluster: incremental-schema-evolution-llm-kg
---

# DIAL-KG: Schema-Free Incremental Knowledge Graph Construction via Dynamic Schema Induction and Evolution-Intent Assessment (arXiv 2603.20059), with GRAFT property-graph schema transformations (arXiv 2609.34789)

- **URL:** https://arxiv.org/abs/2603.20059 (read: https://arxiv.org/html/2603.20059v1). Companion: https://arxiv.org/abs/2609.34789 (read: html v3), code https://github.com/GauvainD/GRAFT
- **Type:** paper (two papers)
- **Author / org:** not captured in this read
- **Date:** DIAL-KG 2026-03-20; GRAFT v3 2026-09-28
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R10 plan question 3 (schema evolution). Extends N-SURVEY-20260928-25 (EDC and AutoSchemaKG: how learned types are kept from multiplying) with the incremental case and a deprecation step.
- **Relevance to a memory stack:** high for ingestion into a typed graph whose schema must grow. One of DIAL-KG's three datasets is built from Kubernetes release logs, which is close to PDLC material.

## TL;DR
- DIAL-KG grows a graph schema batch by batch: relation and event types are proposed from clusters of extracted facts, admitted only past frequency and coherence thresholds plus an LLM check, then merged across batches by canonicalisation.
- A separate **evolution-intent** step labels each incoming event "Informational" or "Evolutionary" ("deprecated", "removed", "replaced"); evolutionary events soft-deprecate older facts, keeping evidence and timestamps.
- On SoftRel-Delta (1,515 Kubernetes release-log entries) F1 0.922 vs EDC 0.897 and AutoKG 0.891; deprecation-handling precision 0.986 / 0.983 in the two change windows.
- Ablation: without intent assessment, Delta-precision fell from 0.976 to 0.848 and deprecation disappears; without coreference alignment, deprecation precision fell to 0.322.
- Judge (DeepSeek-V3) differs from generator (Qwen-Max). No code released. Latency and cost not measured; the authors propose distilling the governance step into small models, which is a System One opening.
- GRAFT (companion) is logic-only: 11 atomic schema edits composed in Datalog and compiled to Cypher, lossless at schema level, 1.57 s for a 10-step transformation on ICIJ Paradise Papers. No LLM involvement.

## What it claims / describes
DIAL-KG pipeline, per batch:
1. Extract triples and events with the LLM, verify them.
2. Relation schema induction: cluster verified triples by relation embedding (BGE-M3, cosine); when a cluster passes frequency threshold theta and is coherent, the LLM judges "semantic completeness and generalizability"; passing types go to a Meta-Knowledge Base (MKB) with domain, range and symmetry properties.
3. Event schema induction: cluster events by trigger, argument roles and time; same gating; relationalise each event as a node with `rdf:type` and `has_role` facts.
4. Governance adjudication: intent "Informational" adds facts; "Evolutionary" marks targeted facts Deprecated (soft, not deleted).
5. Cross-batch canonicalisation merges duplicates such as "acquired_by" and "acquisition_of".
Retrieval of existing schema for the extractor: top-K = 30 schema entries.

GRAFT: edits `AddLbl, RmvLbl, Add, Rem, AddE, AddProp, RmvProp, ReLbl, UpdTgt, UpdSrc` over a finite fragment of PG-Schema; searches for a sequence of reusable "meta-transformations" taking schema S to S'; instance data is migrated by generated Cypher, "possibly requiring human input for new properties". Schema constraints are not supported.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| F1 SoftRel-Delta (batch / stream-end) | 0.922 / 0.920 | EDC 0.897; AutoKG 0.891 | Qwen-Max extracts, DeepSeek-V3 judges at T 0.1 | LLM judge, not human labels |
| P / R SoftRel-Delta (batch) | 0.933 / 0.909 | EDC 0.901 / 0.892 | same | |
| F1 WebNLG (batch / stream-end) | 0.865 / 0.857 | EDC 0.848; AutoKG 0.791 | static benchmark sliced into a stream | |
| F1 Wiki-NRE (batch / stream-end) | 0.853 / 0.844 | EDC 0.808; AutoKG 0.815 | same | |
| Delta-precision (new facts in change windows) | 0.972 to 0.978 | none | Table 2 | "only fully_supported counts as correct" |
| Deprecation-handling precision, SoftRel-Delta | 0.986 (window 2), 0.983 (window 3) | none | Table 2 | precision only; deprecation recall not reported |
| Ablation, full / w/o intent / w/o event repr. / w/o coreference: Delta-precision | 0.976 / 0.848 / 0.850 / 0.860 | | Table 3, SoftRel-Delta | |
| Ablation D-HP | 0.985 / N/A / N/A / 0.322 | | Table 3 | |
| Relation types vs EDC | up to 15% fewer; redundancy 1.6 to 2.8 points lower | EDC | Figure 4 | read from a figure |
| GRAFT runtime | 1.57 s, 10-step transformation | | ICIJ Paradise Papers, Ryzen 9 5900X, Neo4j 5.24.0 | schema-level only |
| GRAFT exact target reached | similarity 1.0 on 4 of 5 synthetic scenarios (greedy) | random, weighted distance | | |
| Cost, tokens, latency (DIAL-KG) | not reported | | | authors call LLM governance latency a "strategic trade-off" |

## Mechanism details you could implement
- Admit a new node or edge type only when a cluster of instances passes a frequency threshold and a coherence check, then canonicalise across batches. This is the "learn new kinds from use" arm of PC-SURVEY-20260928-10 with a concrete gate.
- A per-event intent decision (informational vs evolutionary) before writing: a two-option typed question that a System One model could answer (inference). Evolutionary events trigger SUPERSEDES-style soft deprecation that keeps the old fact with its timestamp, matching our `superseded` state (P5).
- Coreference alignment is load-bearing for deprecation: without it, the deprecation targets the wrong fragment (0.322 precision).
- For declared-schema migrations (our ADR-0011 amendments), GRAFT's 11-operation vocabulary is a usable checklist for what a migration can do, and it compiles to Cypher.

## Limitations, caveats, counter-evidence
- No code; one LLM generator; judged by another LLM, not by people.
- Deprecation recall is not reported, so missed supersessions are invisible.
- SoftRel-Delta is the authors' own dataset (1,515 entries).
- GRAFT has no learned component and leaves schema constraints to future work.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- Treat schema growth as a gated write: frequency plus coherence plus a check, and merge synonyms across batches, or types multiply (consistent with N-SURVEY-20260928-25).
- Separate "is this a change to something we hold?" from extraction. That decision is where supersession quality comes from in this ablation (0.976 vs 0.848).
- Evaluate deprecation with both precision and recall on a seeded change history.

## Open questions
- Would a small decision model match the LLM on the informational vs evolutionary decision for release notes, ADRs and ticket updates?
- How does the induced schema compare with a hand-declared PDLC schema on the same tickets and PRs?
