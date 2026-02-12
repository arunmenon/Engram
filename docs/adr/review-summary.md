# ADR Review Summary

**Date**: 2026-02-11
**Lead Reviewer**: review-lead
**Reviewers**: reviewer-foundations (ADR-0001, ADR-0003), reviewer-data (ADR-0004, ADR-0005), reviewer-api (ADR-0002, ADR-0006)

## Scope

Reviewed all six original ADRs (0001-0006) for consistency with three new research-backed ADRs (0007-0009) covering cognitive memory tier architecture, consolidation/decay, and multi-graph schema with intent-aware retrieval.

---

## Changes Applied

### ADR-0001: Traceability-First Context Graph
**Action**: Amended (Status: Accepted -- Amended)

Key changes:
- Phased Store Evolution revised: Phase 1 (Postgres-only) is skipped; implementation begins at Phase 2 (Postgres + Neo4j + projection worker) based on research validation from ADR-0007/0008/0009
- Complexity Constraint item 6 ("Start Postgres-only") superseded by dual-store adoption
- `importance_hint` added as optional field to minimal schema (item 8)
- W3C PROV-DM clarified as conceptual vocabulary; operational edge types defined in ADR-0009 with compatibility mapping
- Core Commitments (items 1-5) unchanged: immutable events, causal lineage, provenance pointers, deterministic replay, Forgettable Payloads

**Rationale**: Nine research papers (ADR-0007) independently confirmed dual-store maps to Complementary Learning Systems model. ADR-0008/0009 require Neo4j for consolidation pipeline and multi-graph schema. Postgres-only Phase 1 would negate research-validated design.

### ADR-0002: Service Stack (Python + FastAPI)
**Action**: Amended (Status: Accepted -- Amended)

Key changes:
- Added runtime dependency acknowledgment for ML/NLP libraries (sentence-transformers, spacy, LLM client)
- Documented compute profile shift: CPU-bound enrichment workload alongside I/O-bound API work
- Defined multi-process deployment model: API process, projection worker, enrichment worker, re-consolidation worker
- Added mitigation: embedding computation can be offloaded to sidecar or hosted API

**Rationale**: ADR-0008 enrichment pipeline introduces embedding generation, entity extraction, and summarization -- significant computational additions not anticipated in original stack decision.

### ADR-0003: Dual Store Postgres + Neo4j
**Action**: Promoted to Accepted (Status: Accepted)

Key changes:
- Status changed from Proposed to Accepted
- Added cognitive role clarification: Postgres=hippocampus (episodic), Neo4j=neocortex (semantic), projection worker=systems consolidation
- Acknowledged that ADR-0001's complexity concerns remain valid but are justified by richer value proposition
- Cross-referenced ADR-0007/0008/0009 as validating decisions

**Rationale**: ADR-0007/0008/0009 all assume dual-store architecture. The dual-store approach is now validated by nine research papers as mapping to the CLS model. Keeping ADR-0003 in Proposed state while three new ADRs depend on it would be inconsistent.

**Note on reviewer-foundations' alternative**: reviewer-foundations recommended superseding ADR-0003 by ADR-0001 (keeping Phase 1 Postgres-only). This review chose the opposite resolution because ADR-0007/0008/0009 effectively commit the project to dual-store. Superseding ADR-0003 would leave the project with an accepted Postgres-only plan (ADR-0001) that contradicts three newer proposed ADRs. The pragmatic resolution is to accept dual-store and amend ADR-0001's phased approach accordingly.

### ADR-0004: Immutable Event Ledger
**Action**: Amended (Status: Accepted -- Amended)

Key changes:
- Event schema consolidated as single source of truth for all Postgres-persisted fields
- Added missing fields from CLAUDE.md: `parent_event_id`, `ended_at`, `status`, `schema_version`, `global_position`
- Added `importance_hint` (SMALLINT, optional) with clear "seed not source-of-truth" semantics
- Explicitly excluded Neo4j-only derived attributes (keywords, embedding, summary, access_count, last_accessed_at) with pointer to ADR-0009

**Rationale**: Event schema was scattered across ADR-0004, CLAUDE.md, ADR-0007, and ADR-0009. Field named `importance_hint` (not `importance_score`) per reviewer-data recommendation to avoid confusion with Neo4j enrichment-computed score.

### ADR-0005: Async Projection Worker
**Action**: Amended (Status: Accepted -- Amended)

Key changes:
- Positioned as Stage 1 foundation for ADR-0008's three-stage consolidation pipeline
- Clarified replay vs. re-consolidation: replay is full rebuild from position 0; re-consolidation is periodic enhancement
- Noted that full rebuild requires all three stages (Stage 1 alone produces unenriched graph)
- Scoped metrics to Stage 1 (`consolidation_lag_seconds`); deferred Stage 2/3 metrics to ADR-0008

**Rationale**: ADR-0005 and ADR-0008 are complementary, not contradictory. ADR-0005 defines the architectural principle; ADR-0008 extends with additional stages. Neither should supersede the other.

### ADR-0006: Query API
**Action**: Amended (Status: Accepted -- Amended)

Key changes:
- Event ingest endpoints accept optional `importance_hint` field
- Context endpoint (`GET /v1/context/{session_id}`) expanded: `max_nodes`, `max_depth`, `query` parameters; decay-scored ordering; async reconsolidation side-effects
- Subgraph and lineage endpoints gain `intent` parameter (why/when/what/related/general) per ADR-0009
- Atlas response pattern extended: per-node `scores`, edge `properties`, expanded `meta` with intent echo and capacity info
- New endpoints: `GET /v1/entities/{entity_id}`, `POST /v1/admin/reconsolidate`
- Known edge types enumerated: FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES

**Rationale**: ADR-0007 transforms context endpoint into working memory assembly; ADR-0009 adds intent-aware retrieval. All changes are backward-compatible additions.

### ADR-0007: Memory Tier Architecture
**Action**: Minor amendment

Key changes:
- `importance_score` field renamed to `importance_hint` in Postgres schema section
- Added dual-source importance semantics clarification (hint vs. computed score)
- Added phased deployment alignment note confirming CLS model compatibility

### ADR-0008: Memory Consolidation and Decay
**Action**: Minor amendment

Key changes:
- Added cross-reference clarification for importance scoring source (importance_hint as seed)
- Added explicit back-reference to ADR-0005 as Stage 1 foundation

### ADR-0009: Multi-Graph Schema
**Action**: Minor amendment

Key changes:
- Added W3C PROV-DM compatibility mapping table (CAUSED_BY -> wasGeneratedBy/wasInformedBy, REFERENCES -> wasAttributedTo/used, etc.)
- Clarified that PROV-DM is the conceptual interchange vocabulary while ADR-0009 edge types are the operational graph vocabulary

---

## ADRs Left Unchanged

None. All nine ADRs received at least minor amendments for cross-reference consistency.

---

## Key Design Decisions Made During Review

1. **Dual-store from initial build**: ADR-0001's Postgres-only Phase 1 is superseded. The project adopts Postgres + Neo4j from the start, validated by research. ADR-0001 is amended (not superseded) to preserve its core commitments.

2. **importance_hint vs importance_score**: Two distinct values with clear ownership. Postgres stores `importance_hint` (caller seed, immutable). Neo4j stores `importance_score` (enrichment-computed, mutable). Enrichment may use the hint as input.

3. **PROV-DM as conceptual vocabulary**: W3C PROV-DM terms are retained for interoperability but the operational graph uses MAGMA-inspired edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES). A documented mapping bridges both.

4. **ADR-0005 as Stage 1 foundation**: The projection worker ADR is extended (not superseded) by ADR-0008. Four foundational requirements apply to all consolidation stages.

5. **ADR-0004 as schema authority**: The complete Postgres event schema is consolidated into ADR-0004, resolving the previous scatter across multiple documents.

---

## Open Questions for Future ADRs

1. **Span-style events**: Should `ended_at` and `status` warrant their own ADR defining span vs. point event semantics?

2. **Replay automation**: Should a full rebuild (replay) automatically trigger Stages 2 and 3, or should operators control this manually?

3. **importance_hint rename in CLAUDE.md**: The project CLAUDE.md references `importance_score` in the event schema. This should be updated to `importance_hint` to match ADR-0004's amendment.

4. **Embedding service architecture**: ADR-0002 amendment notes embedding computation can be offloaded. A future ADR should decide between in-process, sidecar, or hosted API approaches.

---

## Reviewer Analysis Files

- [Foundations Analysis](review-analysis-foundations.md) -- reviewer-foundations
- [Data Layer Analysis](review-analysis-data-layer.md) -- reviewer-data
- [API Layer Analysis](review-analysis-api-layer.md) -- reviewer-api
