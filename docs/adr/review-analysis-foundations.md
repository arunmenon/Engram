# ADR Review Analysis: Foundations (ADR-0001, ADR-0003)

Reviewer: reviewer-foundations
Date: 2026-02-11

## Scope

This analysis examines ADR-0001 (Traceability-First Context Graph) and ADR-0003 (Dual Store Postgres+Neo4j) for compatibility with the newly proposed research-backed ADRs 0007-0009.

---

## Tension 1: ADR-0001 vs ADR-0003 Internal Conflict

### The Contradiction

- **ADR-0001** (Accepted, 2026-02-07) explicitly says: "Start with Postgres as the sole data store... Defer Neo4j to a later phase." It lists "Full dual-store (Postgres + Neo4j) from day one" as Alternative #3 and rejects it. Its phased approach defines Phase 1 as Postgres-only.
- **ADR-0003** (Proposed, 2026-02-07) says: "Use Postgres + Neo4j in a dual-store architecture" from MVP. It lists "Postgres-only (recursive queries)" as Alternative #1 and rejects it.

These are directly contradictory. ADR-0001 rejects what ADR-0003 proposes, and ADR-0003 rejects what ADR-0001 proposes.

### Analysis

ADR-0001 is the more thoroughly researched decision. It cites four research reports, explicitly acknowledges the dual-store complexity tax (~$180/mo vs ~$70/mo, projection lag management, dual-store failure modes), and arrives at the Postgres-only Phase 1 as a deliberate complexity constraint. ADR-0003 is a thin, single-page proposal with no research references and a weaker rationale ("MVP requires both reliable event ledger semantics and graph-native traversal performance" -- ADR-0001 directly challenges whether this is true for MVP).

ADR-0001's status is **Accepted**. ADR-0003's status is **Proposed**. The Accepted decision takes precedence.

### Recommendation: Supersede ADR-0003

ADR-0003 should be marked as **Superseded by ADR-0001**. Its core premise -- that Neo4j is needed from day one -- was explicitly evaluated and rejected in ADR-0001 Section "Alternatives Considered #3". Keeping ADR-0003 in Proposed state creates confusion about whether the project intends Postgres-only Phase 1 or dual-store from day one.

The useful content in ADR-0003 (Postgres as source of truth, Neo4j as projection, replay/rebuild capability) is already captured in ADR-0001's Phase 2 description and in ADR-0007's tier architecture. ADR-0003 adds no information that is not already present elsewhere.

**Action**: Change ADR-0003 status to `Superseded by ADR-0001`. Add a note at the top: "The dual-store architecture described here is adopted as Phase 2 of the phased store evolution defined in ADR-0001. It is not part of the MVP."

---

## Tension 2: ADR-0001 Phased Approach vs ADR-0007 CLS Architecture

### The Issue

ADR-0007 formalizes the Complementary Learning Systems (CLS) mapping:
- Postgres = hippocampus (rapid encoding, episodic traces)
- Neo4j = neocortex (consolidated relational knowledge)
- Projection worker = systems consolidation

This framing inherently assumes both stores exist. The inter-tier flow diagram shows: `Episodic (Postgres) --> Semantic (Neo4j)`. If Phase 1 is Postgres-only, there is no neocortex and no systems consolidation. Does this invalidate the CLS model?

### Analysis

**The CLS model is still valid for Postgres-only Phase 1, but the framing needs adjustment.** Here is why:

1. **The tier model is a conceptual architecture, not a deployment mandate.** ADR-0007 defines what each tier IS, not what must be running on day one. In Phase 1, the semantic tier can be empty (not yet deployed) while episodic and working tiers function fully. Biological organisms also develop their neocortical consolidation capability gradually -- infants have hippocampal encoding before full neocortical consolidation matures.

2. **Working memory can be assembled from episodic memory alone.** ADR-0007 defines working memory as "bounded, priority-ranked context window." In Phase 1 this can be assembled from Postgres directly using recursive CTEs, without Neo4j. The scoring formula (recency + importance + relevance) can operate on Postgres columns.

3. **The phased approach IS CLS.** Phase 1 = hippocampal-only (fast encoding, direct recall). Phase 2 = add neocortical consolidation (Neo4j projection). This actually mirrors the neuroscience more closely than deploying both from day one, because biological CLS develops incrementally.

However, ADR-0007 currently reads as if both stores must exist simultaneously. This creates a perceived conflict with ADR-0001's phased approach.

### Recommendation: Amend ADR-0007

ADR-0007 should add a section acknowledging the phased deployment model from ADR-0001:

> **Phased Deployment Alignment (per ADR-0001)**
>
> The tier architecture is a logical model that guides design decisions across all phases:
> - **Phase 1 (Postgres-only)**: Sensory, Working, and Episodic tiers are active. Semantic tier is absent. Working memory assembly queries Postgres directly using recursive CTEs with decay scoring.
> - **Phase 2 (Postgres + Neo4j)**: All four tiers active. Semantic memory projected to Neo4j. Working memory assembly can query both stores.
> - The transition from Phase 1 to Phase 2 does not require schema changes -- it adds a new projection target for events that already exist.

This makes the CLS model explicitly compatible with incremental deployment.

---

## Tension 3: ADR-0001 Event Schema vs ADR-0007 `importance_score`

### The Issue

ADR-0001 defines the minimal required event fields:
- Required: `event_id`, `event_type`, `occurred_at`, `session_id`, `trace_id`
- Optional: `agent_id`, `parent_event_id`, `tool_name`, `payload_ref`, `ended_at`, `status`, `schema_version`

ADR-0007 proposes adding `importance_score SMALLINT DEFAULT NULL` to the event schema. This field does not appear in ADR-0001's field list.

### Analysis

This is a **non-breaking extension**, not a contradiction. ADR-0007 specifies the field as optional with `DEFAULT NULL`, backward-compatible with existing event producers. ADR-0001 says "Minimize required event fields to lower producer friction" -- adding an optional field does not violate this principle.

However, there is a design question: should `importance_score` be stored in the Postgres event table or only as a derived attribute in Neo4j? ADR-0008 lists `importance_score` as a "Derived Attribute" in its enrichment stage, computed by "Rule-based from event_type + payload heuristics." If it is purely derived, it belongs in Neo4j only, not in Postgres.

But ADR-0007 places it on the Postgres event schema ("the event schema SHOULD be extended with: importance_score"). This creates two sources for the same field: one optionally provided at ingestion time, one derived during enrichment.

### Recommendation: Amend ADR-0001 (minor) + Clarify ADR-0007/0008

1. **ADR-0001**: Add `importance_score` to the optional fields list in Section 8. This is a minor addendum that does not change the decision. Rationale: "Added as optional field per ADR-0007 to support memory tier scoring."

2. **ADR-0007/0008**: Clarify the dual-source semantics: "If `importance_score` is provided at ingestion, it is stored in Postgres. If absent, the enrichment stage (ADR-0008) computes it and stores it in Neo4j. When both exist, the ingestion-time value takes precedence as the producer is closer to the event context." This prevents ambiguity about which score is authoritative.

---

## Tension 4: ADR-0001 PROV-DM Vocabulary vs ADR-0009 Edge Types

### The Issue

ADR-0001 Section 10 says: "Adopt W3C PROV-DM vocabulary for graph edge types: `GENERATED_BY`, `USED`, `DERIVED_FROM`, `ATTRIBUTED_TO`, `INFORMED_BY`."

ADR-0009 defines four primary edge types: `FOLLOWS`, `CAUSED_BY`, `SIMILAR_TO`, `REFERENCES`, plus `SUMMARIZES`.

These are different vocabularies. ADR-0001's PROV-DM types do not appear in ADR-0009's schema. ADR-0009's types do not appear in PROV-DM.

### Analysis

This is the most significant tension in the foundations review. There are two possible interpretations:

**Interpretation A: They are complementary.**
PROV-DM describes provenance relationships (who generated what, what was derived from what). ADR-0009 describes memory/cognitive relationships (temporal sequence, causal chains, similarity, entity references). These serve different purposes and could coexist. For example, a `tool.execute` event could have:
- `CAUSED_BY` edge (causal, ADR-0009) pointing to the `agent.invoke` that triggered it
- `GENERATED_BY` edge (provenance, PROV-DM) pointing to the agent entity that produced it
- `FOLLOWS` edge (temporal, ADR-0009) pointing to the previous event in the session

**Interpretation B: ADR-0009 supersedes PROV-DM in practice.**
ADR-0009 explicitly addresses the provenance gap in its context section and notes that the `CAUSED_BY` edge "aligns with W3C PROV-DM `GENERATED_BY` / `INFORMED_BY` vocabulary." This suggests the authors of ADR-0009 intended `CAUSED_BY` to be the operational replacement for the more formal PROV-DM types, with a simpler vocabulary that is more intuitive for agent-specific queries.

**I recommend Interpretation B with a mapping table.** The PROV-DM vocabulary is designed for provenance interchange between systems, not for graph traversal query patterns. ADR-0009's vocabulary is optimized for the intent-aware retrieval patterns that MAGMA validates. However, we should not abandon PROV-DM entirely -- it is valuable for external interoperability.

### Recommendation: Amend ADR-0001 + Amend ADR-0009

1. **ADR-0001 Section 10**: Amend to say: "Adopt W3C PROV-DM as the conceptual vocabulary for provenance semantics. The graph projection edge types (defined in ADR-0009) SHOULD maintain a documented mapping to PROV-DM terms for interoperability."

2. **ADR-0009**: Add a PROV-DM compatibility table:

| ADR-0009 Edge | PROV-DM Mapping | Notes |
|---------------|----------------|-------|
| `CAUSED_BY` | `wasGeneratedBy`, `wasInformedBy` | Direct causal lineage |
| `FOLLOWS` | (no direct mapping) | Temporal ordering; PROV-DM uses `qualifiedStart`/`qualifiedEnd` |
| `REFERENCES` | `wasAttributedTo`, `used` | Entity reference; maps to provenance attribution |
| `SIMILAR_TO` | `wasDerivedFrom` (loose) | Semantic similarity; weakest PROV-DM alignment |
| `SUMMARIZES` | `alternateOf`, `specializationOf` | Hierarchical compression |

This preserves ADR-0001's commitment to standards alignment while acknowledging that the operational edge types are what the graph actually uses.

---

## Summary of Recommendations

| ADR | Recommendation | Action |
|-----|---------------|--------|
| **ADR-0001** | **Amend (minor)** | (1) Add `importance_score` to optional fields list. (2) Soften PROV-DM commitment from "adopt as edge types" to "adopt as conceptual vocabulary with documented mapping." |
| **ADR-0003** | **Supersede** | Mark as "Superseded by ADR-0001". The dual-store architecture is adopted as Phase 2, not as the MVP starting point. ADR-0003 adds no unique content not already covered by ADR-0001 and ADR-0007. |
| **ADR-0007** | **Amend** | Add phased deployment alignment section clarifying that the CLS model works with Postgres-only Phase 1. Clarify `importance_score` dual-source semantics (ingestion vs enrichment). |
| **ADR-0008** | **Keep as-is** | No direct conflict with foundations. Operates exclusively on the Neo4j projection, which is consistent with ADR-0001's Phase 2+ scope. Implicitly depends on Neo4j existing. |
| **ADR-0009** | **Amend** | Add PROV-DM compatibility mapping table. Explicitly state that ADR-0009 edge types are the operational vocabulary and PROV-DM terms are maintained for interoperability. |

---

## Cross-Cutting Concern: Phase 1 Viability of ADRs 0007-0009

ADRs 0007, 0008, and 0009 all assume Neo4j exists (semantic tier, enrichment into Neo4j, multi-graph schema in Neo4j). In ADR-0001's Postgres-only Phase 1, these ADRs describe future-state architecture.

This is acceptable IF:
1. The ADRs are clearly labeled as defining the target architecture across all phases, not just Phase 1
2. Phase 1 implementations can satisfy a subset of the requirements (e.g., working memory from Postgres, basic decay scoring on Postgres columns) without Neo4j
3. The transition to Phase 2 activates the full ADR-0007/0008/0009 capabilities without breaking changes

All three conditions appear to be satisfiable with the amendments recommended above. The key insight is that ADR-0001's phased approach and ADR-0007-0009's CLS architecture are not in conflict -- they describe the same system at different stages of maturity.
