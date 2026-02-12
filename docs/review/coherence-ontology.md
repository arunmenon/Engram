# Coherence Review: Ontology and Vocabulary Consistency Across ADRs

**Reviewer**: Coherence Reviewer (agent)
**Date**: 2026-02-12
**Scope**: ADR-0001, ADR-0007, ADR-0009, ADR-0011, ADR-0012, ADR-0013

---

## 1. PROV-O / PROV-DM Mapping Consistency

### 1.1 ADR-0009 (Original) vs ADR-0011 (Corrected)

ADR-0009's amendment section contains the original PROV-DM compatibility table. ADR-0011 explicitly flags two errors in that table and provides corrections:

| Edge | ADR-0009 Original Mapping | ADR-0011 Corrected Mapping | Correction Valid? |
|------|--------------------------|---------------------------|-------------------|
| `SIMILAR_TO` | `wasDerivedFrom` (loose) | No PROV-O equivalent; custom `cg:similarTo` | **Yes** -- derivation implies transformation, similarity does not. Correction is semantically accurate. |
| `SUMMARIZES` | `alternateOf`, `specializationOf` | `prov:alternateOf` only; `specializationOf` removed | **Yes** -- `specializationOf` means "more specific", but summaries are *less* detailed. Correction is correct. |
| `CAUSED_BY` | `wasGeneratedBy`, `wasInformedBy` | `prov:wasInformedBy` only | **Yes** -- `wasGeneratedBy` applies to Entity generation, not Activity-to-Activity communication. Activity-to-Activity causal dependency maps to `wasInformedBy`. Correction is correct. |

**Finding**: All three corrections in ADR-0011 are semantically valid and improve PROV-O alignment.

### 1.2 Cross-ADR PROV-DM Consistency

ADR-0001 Section 10 commits to PROV-DM vocabulary: `GENERATED_BY`, `USED`, `DERIVED_FROM`, `ATTRIBUTED_TO`, `INFORMED_BY`. ADR-0011 refines this to a dual-vocabulary approach where:
- **Operational vocabulary** (FOLLOWS, CAUSED_BY, etc.) is used in Neo4j
- **Conceptual vocabulary** (PROV-O terms) is used in documentation and interchange

This is consistently described in:
- ADR-0001 amendment (line 139): "W3C PROV-DM is retained as the conceptual provenance vocabulary"
- ADR-0009 amendment (line 318): "ADR-0001's commitment to W3C PROV-DM is maintained as the conceptual provenance vocabulary"
- ADR-0011 (line 43): "PROV-O as conceptual layer, not implementation layer"
- ADR-0012 (line 40): "preserving the dual-vocabulary approach (operational names for Neo4j traversal, PROV-O grounding for conceptual documentation)"

**Finding**: The dual-vocabulary approach is consistently described across all four ADRs. No inconsistencies found.

### 1.3 ADR-0012 PROV-O Grounding for New Edges

ADR-0012 Section 14 provides PROV-O grounding for all nine new edge types. Two mappings deserve note:

| Edge | PROV-O Mapping | Assessment |
|------|---------------|------------|
| `DERIVED_FROM` | `prov:wasDerivedFrom` | **Correct and significant** -- this is the only edge type across all ADRs that directly reuses a PROV-O term as its operational name. This is intentional (preferences are literally derived from events) and creates a natural alignment. |
| `ABSTRACTED_FROM` | `prov:wasDerivedFrom` | **Correct** -- abstraction is a form of derivation. Using a distinct operational name (`ABSTRACTED_FROM` vs `DERIVED_FROM`) for a different relationship type that maps to the same PROV-O concept is good practice. |

**Finding**: ADR-0012's PROV-O grounding is internally consistent and aligned with ADR-0011's dual-vocabulary approach.

---

## 2. Edge Type Total Count

### 2.1 Enumeration

**ADR-0009 (5 original edge types):**
1. FOLLOWS
2. CAUSED_BY
3. SIMILAR_TO
4. REFERENCES
5. SUMMARIZES

**ADR-0011 (2 new edge types for entity resolution):**
6. SAME_AS
7. RELATED_TO

**ADR-0012 (9 new edge types for user personalization):**
8. HAS_PROFILE
9. HAS_PREFERENCE
10. HAS_SKILL
11. DERIVED_FROM
12. EXHIBITS_PATTERN
13. INTERESTED_IN
14. ABOUT
15. ABSTRACTED_FROM
16. PARENT_SKILL

**Total: 16 edge types.**

### 2.2 ADR-0013's Claim

ADR-0013 (line 10) states: "16 edge types". This matches the enumeration above.

**Finding**: The total of 16 edge types is correct. 5 (ADR-0009) + 2 (ADR-0011) + 9 (ADR-0012) = 16. ADR-0013's claim is accurate.

### 2.3 Potential Naming Conflict: DERIVED_FROM

ADR-0012 introduces `DERIVED_FROM` as a new edge type. ADR-0001 Section 10 originally listed `DERIVED_FROM` as a PROV-DM vocabulary term for the *conceptual* layer. Under the dual-vocabulary approach, this should not cause confusion because:
- ADR-0001's `DERIVED_FROM` was a conceptual PROV-DM term (never an operational edge type in the original 5)
- ADR-0012's `DERIVED_FROM` is a new *operational* edge type

However, this is the **only case where the operational vocabulary deliberately reuses a PROV-DM name**. This could cause confusion for developers who read ADR-0001's conceptual commitment and then encounter `DERIVED_FROM` as an actual Neo4j edge type.

**Finding (MINOR ISSUE)**: `DERIVED_FROM` is both a PROV-DM conceptual term (ADR-0001 Section 10) and an operational edge type (ADR-0012). This is semantically correct (the operational edge *is* the PROV-DM concept), but the dual-vocabulary documentation should explicitly note this as an intentional convergence point rather than an exception. Recommend adding a note to ADR-0012 Section 14 or ADR-0011's edge grounding table clarifying that `DERIVED_FROM` is the one edge type where operational and conceptual names intentionally align.

### 2.4 ADR-0013 Consumer 1 mentions PART_OF edge

ADR-0013 Section 3 (Consumer 1, line 127) mentions creating "Session node + PART_OF edges" in the structural projection. `PART_OF` is not listed as one of the 16 edge types in any ADR. This is either:
- An edge type that was inadvertently introduced without formal definition
- A placeholder that should be replaced with an existing edge type or formally defined

**Finding (ISSUE)**: ADR-0013 references a `PART_OF` edge type that is not defined in ADR-0009, ADR-0011, or ADR-0012. It also references a "Session node" that is not one of the 8 defined node types. If these are intended, they need formal PG-Schema definitions and should be counted in the edge/node type totals. If not intended, the reference should be corrected. This would bring the actual total to 17 edge types (or 16 if PART_OF is removed).

---

## 3. Node Type Total Count

### 3.1 Enumeration

**ADR-0009 (3 original node types):**
1. Event
2. Entity
3. Summary

**ADR-0012 (5 new node types):**
4. UserProfile
5. Preference
6. Skill
7. Workflow
8. BehavioralPattern

**Total: 8 node types.**

ADR-0013 (line 10) states: "8 node types (Event, Entity, Summary, UserProfile, Preference, Skill, Workflow, BehavioralPattern)". This matches.

**Finding**: The total of 8 node types is correct. 3 (ADR-0009) + 5 (ADR-0012) = 8. ADR-0013's claim is accurate.

### 3.2 Session Node (ADR-0013)

As noted in Section 2.4 above, ADR-0013 mentions a "Session node" in Consumer 1's structural projection (line 127). This would be a 9th node type if formalized. It is not defined in any existing ADR.

**Finding (ISSUE)**: Same as 2.4 -- "Session node" needs formal definition or the reference needs correction.

---

## 4. Ontology Module List

### 4.1 ADR-0011 Definition (6 modules)

ADR-0011 (lines 424-431) defines:
1. `cg-core` -- Node types, edge types, core properties, PROV-O mapping
2. `cg-events` -- Event type taxonomy, status values, OTel mapping
3. `cg-entities` -- Entity type hierarchy, roles, resolution strategy
4. `cg-memory` -- Memory tier classes, CLS vocabulary, consolidation stages
5. `cg-views` -- Multi-view definitions, intent-aware retrieval vocabulary
6. `cg-retention` -- Retention tiers, decay parameters

### 4.2 ADR-0012 Addition (1 module)

ADR-0012 Section 15 (lines 733-746) adds:
7. `cg-user` -- User personalization types, views, source tracking, decay integration, privacy patterns

### 4.3 Cross-Reference Verification

ADR-0012 line 9 states: "six ontology modules (ADR-0011: cg-core, cg-events, cg-entities, cg-memory, cg-views, cg-retention)". This matches ADR-0011's definition.

ADR-0012 Section 15 repeats the full 6-module list from ADR-0011 and adds `cg-user` as the 7th, with explicit module dependencies documented.

**Finding**: The module list is correct and consistent. 6 modules (ADR-0011) + 1 module (ADR-0012) = 7 total modules. ADR-0012 correctly references ADR-0011's 6 modules and adds `cg-user`.

---

## 5. Entity Type Hierarchy

### 5.1 ADR-0009 (Original 5 Types)

ADR-0009 (line 74) defines: `agent`, `tool`, `user`, `resource`, `concept`.

### 5.2 ADR-0011 (Adds `service`, Total 6 Types)

ADR-0011 Section 3 (lines 128-151) adds `service` and provides a two-level hierarchy:
- `prov:Agent` subtypes: `agent`, `user`, `service`
- `prov:Entity` subtypes: `tool`, `resource`, `concept`

### 5.3 ADR-0012 Usage

ADR-0012 uses `entity_type="user"` throughout (consistent with the 6-type hierarchy). ADR-0012 does not introduce new entity types.

### 5.4 ADR-0013 Usage

ADR-0013 Section 3 (line 132) uses entity types `service`, `tool`, and `concept` in the regex fallback patterns. Line 392 uses `entity_type: "service"` for QuickBooks. This is consistent with the 6-type hierarchy from ADR-0011.

**Finding**: All ADRs after ADR-0011 use the 6-type entity hierarchy (`agent`, `tool`, `user`, `resource`, `concept`, `service`). No inconsistencies found.

---

## 6. REFERENCES Edge Roles

### 6.1 Renaming

ADR-0011 Section 3 (lines 156-164) renames REFERENCES edge roles:
- Old: `{subject, object, tool, target}`
- New: `{agent, object, instrument, result, participant}`

### 6.2 ADR-0013 Usage

ADR-0013 does not explicitly reference REFERENCES edge roles in its extraction code. Consumer 1 creates structural edges (FOLLOWS, CAUSED_BY) but does not create REFERENCES edges -- those are created by Consumer 2 enrichment. The extraction Pydantic models in Consumer 2 (lines 155-170) do not include a `role` field for REFERENCES edges, which means the role assignment is handled downstream in the graph write logic, not in the extraction schema.

**Finding**: ADR-0013 does not contradict the role rename but also does not explicitly demonstrate the new role names in its code examples. This is acceptable since role assignment is a graph-write concern, not an extraction concern. However, it would strengthen consistency to show the new role names in the Cypher example (ADR-0013 line 392 shows entity creation but not REFERENCES edge creation with roles).

---

## 7. Event Type Taxonomy

### 7.1 ADR-0011 Event Types

ADR-0011 Section 2 (lines 77-95) defines:
- `agent.invoke`, `agent.create`
- `tool.execute`
- `llm.chat`, `llm.completion`, `llm.embed`, `llm.generate`
- `observation.receive`, `observation.emit`
- `system.session_start`, `system.session_end`

### 7.2 ADR-0012 Additions

ADR-0012 Section 6 (lines 372-376) adds:
- `user.preference.stated`
- `user.preference.revoked`
- `user.skill.declared`
- `user.profile.updated`

These follow the dot-namespaced pattern and add a new Level 1 category (`user`). This is consistent with ADR-0011's extensibility design: "new event types can be added as subtypes without breaking existing queries".

### 7.3 ADR-0013 Usage

ADR-0013 references `session.ended` (line 114) and `user.preference.stated` (line 140). The `session.ended` event type is not explicitly defined in ADR-0011's taxonomy (which has `system.session_start` and `system.session_end`).

**Finding (MINOR ISSUE)**: ADR-0013 uses `session.ended` (line 114) while ADR-0011 defines `system.session_end` (line 94). These are different event type strings. Either ADR-0013 should use `system.session_end`, or the taxonomy should formally include `session.ended` as an alias or alternative. The dot-namespace pattern suggests `system.session_end` is the canonical form.

---

## 8. CLS Vocabulary Consistency

### 8.1 ADR-0007 (Informal CLS)

ADR-0007 (lines 139-141) informally maps:
- **Postgres = hippocampus** (rapid encoding, detailed episodic traces, index-based storage)
- **Neo4j = neocortex** (consolidated relational knowledge, query-optimized, gradually abstracted)
- **Projection worker = systems consolidation** (async replay writing structure from hippocampus to neocortex)

ADR-0007 amendment (line 219) updates Postgres to Redis: **Redis = hippocampus**.

### 8.2 ADR-0011 (Formal CLS)

ADR-0011 Section 6 (lines 346-356) formalizes:
- `cg:FastLearningSystem` -- implementedBy: Redis event store, CLSAnalogy: hippocampal encoding
- `cg:SlowLearningSystem` -- implementedBy: Neo4j graph projection, CLSAnalogy: neocortical consolidation
- `cg:ConsolidationProcess` -- implementedBy: Projection worker (Stages 1-3), CLSAnalogy: systems consolidation / hippocampal replay

### 8.3 Consistency Check

| CLS Concept | ADR-0007 (informal) | ADR-0011 (formal) | Consistent? |
|-------------|--------------------|--------------------|-------------|
| Fast learning system | Redis = hippocampus | `cg:FastLearningSystem`, Redis event store, hippocampal encoding | **Yes** |
| Slow learning system | Neo4j = neocortex | `cg:SlowLearningSystem`, Neo4j graph projection, neocortical consolidation | **Yes** |
| Consolidation | Projection worker = systems consolidation | `cg:ConsolidationProcess`, Projection worker (Stages 1-3), systems consolidation / hippocampal replay | **Yes** |

**Finding**: CLS vocabulary is consistent between ADR-0007 (informal) and ADR-0011 (formal). The formal version adds class names and `CLSAnalogy` qualifiers but preserves the same mapping. Both reference Redis (post-ADR-0010 amendment), not Postgres.

---

## 9. DERIVED_FROM Edge: ADR-0012 vs ADR-0013 Property Mismatch

### 9.1 ADR-0012 Definition

ADR-0012 (lines 206-212) defines the DERIVED_FROM edge with properties:
```
derivation_method STRING NOT NULL
derived_at        ZONED DATETIME NOT NULL
```

### 9.2 ADR-0013 Extension

ADR-0013 Section 9 (lines 319-327) shows DERIVED_FROM with additional properties:
```
derivation_method STRING NOT NULL
derived_at        ZONED DATETIME NOT NULL
model_id          STRING
prompt_version    STRING
evidence_quote    STRING
source_turn_index INTEGER
```

ADR-0013 adds four properties (`model_id`, `prompt_version`, `evidence_quote`, `source_turn_index`) that are not part of ADR-0012's PG-Schema definition.

**Finding (ISSUE)**: ADR-0013 extends the DERIVED_FROM edge schema with four additional properties not defined in ADR-0012's PG-Schema. This is not a contradiction (ADR-0013 extends rather than conflicts), but the authoritative PG-Schema definition in ADR-0012 should be updated to include these properties as optional fields, or ADR-0013 should explicitly note that it extends ADR-0012's edge definition. Currently, the two ADRs define different property sets for the same edge type.

---

## 10. ADR-0013 Consumer 1 mentions `derivation_method: "rule_extraction"`

ADR-0013 line 129 states Consumer 1's resilience fallback uses `derivation_method: "rule_extraction"`. ADR-0012's PG-Schema for DERIVED_FROM (line 207) defines `derivation_method` as `STRING NOT NULL` but does not enumerate valid values. ADR-0013 Section 9 (lines 322-323) defines four valid values:
- `"rule_extraction"` | `"llm_extraction"` | `"statistical_inference"` | `"graph_pattern"`

ADR-0012 lists different values in its definition (line 207):
- `"stated"` | `"frequency_analysis"` | `"llm_extraction"` | `"pattern_match"` | `"hierarchy_propagation"`

**Finding (ISSUE)**: ADR-0012 and ADR-0013 define different `derivation_method` enum values for the DERIVED_FROM edge:

| Value | ADR-0012 | ADR-0013 |
|-------|----------|----------|
| `stated` | Yes | No |
| `frequency_analysis` | Yes | No |
| `llm_extraction` | Yes | Yes |
| `pattern_match` | Yes | No |
| `hierarchy_propagation` | Yes | No |
| `rule_extraction` | No | Yes |
| `statistical_inference` | No | Yes |
| `graph_pattern` | No | Yes |

Only `llm_extraction` appears in both. The two ADRs need a reconciled enum. Some values may be synonyms (e.g., `pattern_match` and `graph_pattern`; `frequency_analysis` and `statistical_inference`), but this should be explicitly resolved.

---

## 11. Confidence Scoring Defaults

### 11.1 ADR-0012 Defaults (Section 5)

| Source | Default Confidence |
|--------|-------------------|
| `explicit` | 0.9 |
| `implicit_intentional` | 0.7 |
| `implicit_unintentional` | 0.5 |
| `inferred` | 0.3 |

### 11.2 ADR-0013 Defaults (Section 7)

| Source | Confidence Prior |
|--------|-----------------|
| `explicit` | >= 0.7 |
| `implicit_intentional` | >= 0.4 |
| `implicit_unintentional` | >= 0.3 |
| `inferred` | >= 0.15 |

**Finding (ISSUE)**: Confidence defaults differ significantly between ADR-0012 and ADR-0013. ADR-0013's values are lower across the board, described as "priors" that serve as floors, whereas ADR-0012's values are described as "default confidence". Since ADR-0013 describes the extraction pipeline that creates these values, and ADR-0012 describes the conceptual model, ADR-0013's lower values may be intentional (reflecting that the LLM's confidence adjustment can only reduce from the floor). However, the two ADRs use different terminology ("default" vs "prior") and different numbers for the same source types. This should be reconciled.

---

## Summary of Findings

### No Issues (Consistent)

| Check | Status |
|-------|--------|
| PROV-O/PROV-DM mapping corrections (ADR-0011 vs ADR-0009) | Consistent -- all three corrections valid |
| Dual-vocabulary approach description | Consistent across ADR-0001, 0009, 0011, 0012 |
| ADR-0012 PROV-O grounding for new edges | Consistent with dual-vocabulary approach |
| Edge type total count (16) | Correct: 5 + 2 + 9 = 16 |
| Node type total count (8) | Correct: 3 + 5 = 8 |
| Ontology module list (7) | Correct: 6 + 1 = 7 |
| Entity type hierarchy (6 types) | Consistent across all ADRs post-ADR-0011 |
| CLS vocabulary (ADR-0007 informal vs ADR-0011 formal) | Consistent |

### Issues Found

| ID | Severity | ADRs Affected | Description |
|----|----------|---------------|-------------|
| O-1 | Minor | ADR-0012, ADR-0011 | `DERIVED_FROM` is both a PROV-DM conceptual term and an operational edge type -- this intentional convergence should be explicitly documented |
| O-2 | Medium | ADR-0013 | `PART_OF` edge type and `Session` node type referenced but not formally defined in any ADR. Adds undocumented types to the schema |
| O-3 | Minor | ADR-0013, ADR-0011 | `session.ended` event type used in ADR-0013 vs `system.session_end` defined in ADR-0011 taxonomy |
| O-4 | Medium | ADR-0012, ADR-0013 | DERIVED_FROM edge property sets differ: ADR-0012 defines 2 properties; ADR-0013 defines 6. The PG-Schema definition needs reconciliation |
| O-5 | Medium | ADR-0012, ADR-0013 | `derivation_method` enum values are mostly disjoint between the two ADRs. Only `llm_extraction` appears in both. Needs a unified enum |
| O-6 | Medium | ADR-0012, ADR-0013 | Confidence scoring defaults differ significantly (ADR-0012: 0.9/0.7/0.5/0.3 vs ADR-0013: >=0.7/>=0.4/>=0.3/>=0.15). Terminology also differs ("default" vs "prior/floor") |

### Recommendations

1. **O-2 (PART_OF / Session node)**: Either add formal PG-Schema definitions for `PART_OF` edge and `Session` node to ADR-0009 or ADR-0013, or replace the ADR-0013 reference with existing constructs (e.g., use `session_id` property on Event nodes as the session grouping mechanism, which is the current pattern).

2. **O-3 (session.ended vs system.session_end)**: Standardize on `system.session_end` throughout, or formally add `session.ended` to the event type taxonomy with a note explaining the choice.

3. **O-4 + O-5 (DERIVED_FROM properties and derivation_method enum)**: ADR-0013 should explicitly state that it extends ADR-0012's DERIVED_FROM edge definition with extraction-pipeline-specific properties. The `derivation_method` enum should be unified into a single authoritative list across both ADRs, likely: `stated`, `rule_extraction`, `llm_extraction`, `frequency_analysis`, `statistical_inference`, `graph_pattern`, `hierarchy_propagation`.

4. **O-6 (Confidence defaults)**: ADR-0013 should reference ADR-0012's defaults and explicitly state how its "priors" relate to ADR-0012's "defaults". If ADR-0013's lower values are intentional floor values (with the expectation that extraction may adjust upward toward ADR-0012's defaults), this should be stated. If ADR-0013 supersedes ADR-0012's defaults, that should be noted as an amendment.
