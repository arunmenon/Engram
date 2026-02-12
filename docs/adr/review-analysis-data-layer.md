# ADR Review Analysis: Data Layer (ADR-0004 and ADR-0005)

**Reviewer**: reviewer-data
**Date**: 2026-02-11
**Scope**: ADR-0004 (Event Ledger) and ADR-0005 (Projection Worker) evaluated against ADR-0007, ADR-0008, and ADR-0009

---

## 1. ADR-0004: Immutable Event Ledger with Idempotent Ingestion

### Recommendation: AMEND (minor, backward-compatible)

### Analysis

ADR-0004 defines the core event schema with seven required fields (`event_id`, `event_type`, `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`) and one optional field (`tool_name`). The question is whether `importance_score` (proposed in ADR-0007, SMALLINT, optional) should be added to this schema.

**Arguments for adding `importance_score` to the Postgres schema (ADR-0004):**

1. **Ingestion-time importance is distinct from enrichment-time importance.** ADR-0008 Stage 2 computes importance from graph context, but callers may have domain knowledge at ingest time (e.g., an agent knows a tool failure is important). Capturing caller-supplied importance in the event record preserves this signal in the immutable ledger.

2. **Working memory assembly (ADR-0007, Tier 2) needs importance for scoring.** The formula `score = w_recency * recency + w_importance * importance + w_relevance * relevance` requires importance to be available at query time. If importance only lives in Neo4j, the Context API must always consult Neo4j even for simple Postgres-backed queries. Storing an optional importance hint in Postgres enables the event store to return pre-scored results without a graph round-trip.

3. **ADR-0007 explicitly proposes it.** Line 148-149 of ADR-0007 state: `importance_score SMALLINT DEFAULT NULL -- LLM-rated or rule-based (1-10 scale)`. It is described as optional and backward-compatible.

**Arguments for keeping ADR-0004 minimal (importance only in Neo4j):**

1. **Purity of the event ledger.** Importance is arguably a derived attribute, not a fact about what happened. The ledger records "what occurred" while importance is "how much we value it" -- a judgment that may change over time. Storing it in Postgres implies it is immutable like the other fields.

2. **Enrichment should own scoring.** ADR-0008 defines importance scoring as part of Stage 2 enrichment. If importance also arrives at ingestion, there are two sources of truth for importance (caller-supplied in Postgres, enrichment-computed in Neo4j), creating reconciliation complexity.

3. **Schema discipline.** Every optional field added to the event envelope increases validation surface area and client contract complexity.

**Resolution:**

AMEND ADR-0004 to add `importance_score` as an optional field with the following constraints:

- Field is `SMALLINT DEFAULT NULL`, nullable, range 1-10
- Represents a **caller hint**, not the authoritative importance score
- The authoritative importance score lives in Neo4j and is computed by enrichment (ADR-0008 Stage 2), which MAY use the Postgres hint as one input signal
- ADR-0004's amendment text should explicitly state: "The `importance_score` field is an optional ingestion-time hint. The canonical importance score is computed during enrichment and stored in Neo4j. The Postgres value is a seed, not the source of truth."

This preserves ledger discipline (the hint is immutable once written, reflecting the caller's assessment at event time) while enabling Postgres-side scoring for working memory assembly without a Neo4j dependency.

### Additional ADR-0004 amendments needed

ADR-0004's event schema should also acknowledge three fields that are referenced in CLAUDE.md and ADR-0005 but missing from ADR-0004's "Each event MUST include" list:

- `parent_event_id` (optional) -- referenced by ADR-0009 for CAUSED_BY edges
- `ended_at` (optional) -- referenced in CLAUDE.md event schema
- `status` (optional) -- referenced in CLAUDE.md event schema
- `schema_version` -- referenced in CLAUDE.md event schema
- `global_position` (BIGSERIAL) -- referenced by ADR-0005 for cursor tracking and by ADR-0009 for provenance

These fields appear in the project's CLAUDE.md event schema definition but are absent from ADR-0004. The ADR should be amended to include them so that it is the single source of truth for the event envelope contract.

---

## 2. ADR-0005: Asynchronous Projection Worker with Replay Support

### Recommendation: AMEND to define it as the foundation, with ADR-0008 as the explicit extension

ADR-0005 should NOT be marked as superseded. Instead, it should be amended to clearly position itself as the Stage 1 foundation that ADR-0008 extends.

### Analysis

#### 2a. Single-pass (ADR-0005) vs. three-stage pipeline (ADR-0008)

ADR-0005 defines four requirements for the projection worker:
1. Restart-safe
2. Track processing position
3. Support full replay/rebuild from event ledger
4. Expose projection lag metrics

ADR-0008 defines a three-stage pipeline:
- **Stage 1**: Event projection (polls events, MERGE into Neo4j) -- this IS ADR-0005
- **Stage 2**: Enrichment (keywords, embeddings, importance, summary, similarity edges)
- **Stage 3**: Re-consolidation (periodic cross-event relationship discovery, summarization, pruning)

**These are complementary, not contradictory.** ADR-0005 defines the architectural principle (async decoupled projection from an immutable ledger) and its foundational requirements (restart-safe, position-tracked, replayable, observable). ADR-0008 extends the worker with additional stages while preserving all four requirements.

The relationship should be: ADR-0005 defines the projection worker contract and Stage 1 behavior. ADR-0008 extends the worker with Stages 2 and 3, decay, forgetting, and reconsolidation. Both remain valid, with ADR-0008 explicitly stating it builds on ADR-0005.

**Amendment to ADR-0005:** Add a section:

> "This ADR defines the foundational projection worker architecture and its Stage 1 (event projection) behavior. ADR-0008 extends this worker with additional consolidation stages (enrichment and re-consolidation), decay scoring, and active forgetting. The four requirements specified here (restart-safe, position tracking, replay support, lag metrics) apply to all stages."

#### 2b. Replay support (ADR-0005) vs. re-consolidation (ADR-0008)

These are related but distinct concepts:

| Concept | Trigger | Scope | Purpose |
|---------|---------|-------|---------|
| **Replay** (ADR-0005) | Manual or failure-recovery | Full ledger, from position 0 | Rebuild entire Neo4j projection from scratch |
| **Re-consolidation** (ADR-0008) | Periodic (every 6 hours) or reflection trigger | Historical graph regions, priority-ordered | Discover new cross-event relationships, generate summaries, prune |

Replay is a disaster-recovery / schema-evolution mechanism: wipe Neo4j and re-project everything. Re-consolidation is a continuous improvement mechanism: revisit existing graph structure to enrich it.

**These should remain separate concepts.** The amendment to ADR-0005 should clarify:

> "Replay is a full-rebuild mechanism (reset cursor to 0, re-project all events). It is distinct from re-consolidation (ADR-0008 Stage 3), which is a periodic enhancement pass over existing graph structure. After a replay, re-consolidation and enrichment must also run to restore the full graph state."

This raises an important operational implication: a replay only restores Stage 1 output. To fully rebuild the graph, the system must run all three stages. ADR-0005 should acknowledge this dependency.

#### 2c. Metrics (ADR-0005) vs. metrics (ADR-0008)

ADR-0005 requires: "Expose projection lag metrics" (singular, underspecified).

ADR-0008 defines seven specific metrics:

| Metric | Description |
|--------|-------------|
| `consolidation_lag_seconds` | Time since last projected event |
| `enrichment_lag_seconds` | Time since last enrichment pass |
| `reconsolidation_last_run` | Timestamp of last re-consolidation |
| `graph_nodes_total` | Total nodes by tier |
| `graph_nodes_pruned_total` | Nodes pruned |
| `reflection_triggers_total` | Reflection threshold crossings |
| `decay_score_p50` | Decay score distribution |

**ADR-0008 subsumes ADR-0005's metrics requirement.** The first metric (`consolidation_lag_seconds`) is the direct expansion of ADR-0005's "projection lag metrics." The remaining six are new.

**Amendment to ADR-0005:** Replace "Expose projection lag metrics" with: "Expose projection lag metrics. See ADR-0008 for the full metric catalog covering all consolidation stages."

Alternatively, ADR-0005 could define the minimal Stage 1 metric (`consolidation_lag_seconds`) and defer Stage 2/3 metrics to ADR-0008. This is the cleaner option since it keeps ADR-0005 focused on its own scope.

---

## 3. Cross-ADR Consistency Issues

### 3a. Event schema fields are scattered across documents

The authoritative event schema is split across:
- ADR-0004 (7 required + 1 optional field)
- CLAUDE.md (adds `parent_event_id`, `ended_at`, `status`, `schema_version`, `global_position`)
- ADR-0007 (adds `importance_score`)
- ADR-0009 (defines derived Neo4j-only properties: `keywords`, `embedding`, `summary`, `access_count`, `last_accessed_at`)

**Recommendation:** ADR-0004 should be amended to contain the COMPLETE Postgres schema as the single source of truth. All Postgres-persisted fields should be enumerated there. Neo4j-only derived attributes (defined in ADR-0009) should be explicitly excluded with a note pointing to ADR-0009.

### 3b. Derived attributes: clear Postgres vs. Neo4j boundary

ADR-0009 correctly places derived attributes (keywords, summary, embedding) in Neo4j only. This is consistent with the "Neo4j is disposable and rebuildable" principle. However, `importance_score` appears in both:
- ADR-0007 proposes it as a Postgres column (ingestion hint)
- ADR-0008 Stage 2 computes it during enrichment (Neo4j property)
- ADR-0009 lists it as a Neo4j Event node property

**Recommendation:** Acknowledge two importance values with different semantics:
- `importance_hint` (Postgres) -- caller-supplied at ingestion time, immutable
- `importance_score` (Neo4j) -- computed by enrichment, mutable, incorporates the hint plus graph-derived signals

Renaming the Postgres field to `importance_hint` avoids confusion between the seed value and the computed score.

### 3c. Re-projection after replay must account for all three stages

ADR-0005 says "support full replay/rebuild from event ledger." ADR-0008 introduces Stage 2 (enrichment) and Stage 3 (re-consolidation) that produce graph state not captured by Stage 1 alone. After a replay, Stages 2 and 3 must also re-run to reach the full graph state.

**Recommendation:** ADR-0005's replay requirement should be amended to state: "Support full replay/rebuild from event ledger. A complete rebuild requires executing all projection stages (see ADR-0008). Stage 1 replay alone produces a structurally correct but unenriched graph."

---

## 4. Summary Table

| ADR | Verdict | Key Actions |
|-----|---------|-------------|
| **ADR-0004** | **AMEND** | (1) Add `importance_hint` (SMALLINT, optional) with clear "seed not source-of-truth" semantics. (2) Include all Postgres fields currently only in CLAUDE.md (`parent_event_id`, `ended_at`, `status`, `schema_version`, `global_position`). (3) Explicitly note that derived attributes (`keywords`, `embedding`, `summary`) live only in Neo4j per ADR-0009. |
| **ADR-0005** | **AMEND** | (1) Add forward-reference to ADR-0008 positioning this as Stage 1 of the consolidation pipeline. (2) Clarify replay vs. re-consolidation distinction. (3) Specify that full rebuild requires all stages. (4) Refine metrics requirement to scope Stage 1 metric and defer Stage 2/3 metrics to ADR-0008. |

Neither ADR should be superseded. ADR-0004 is the event contract foundation; ADR-0008/0009 build on it. ADR-0005 is the projection architecture foundation; ADR-0008 extends it with additional stages. The relationship is layered extension, not replacement.

---

## 5. Open Questions for Discussion

1. **Should `importance_hint` be renamed in Postgres to avoid confusion with `importance_score` in Neo4j?** This review recommends yes, but the team may prefer keeping the same name with documented semantics.

2. **Should ADR-0005's replay mechanism also trigger Stage 2/3 automatically, or should it only reset the Stage 1 cursor and leave enrichment/re-consolidation to their own schedules?** Automatic trigger provides faster recovery; manual control provides operational flexibility.

3. **Should the event schema include `ended_at` and `status` fields (from CLAUDE.md) or are these deferred to a span/lifecycle ADR?** If events represent point-in-time observations, `ended_at` implies duration -- which may warrant its own ADR for span-style events vs. point events.
