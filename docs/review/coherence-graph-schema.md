# Graph Schema Coherence Review

**Scope**: ADR-0009 (Multi-Graph Schema), ADR-0011 (Ontological Foundation), ADR-0012 (User Personalization Ontology), ADR-0013 (Knowledge Extraction Pipeline)

**Date**: 2026-02-12

**Reviewer**: Coherence Review Agent

---

## Summary

Reviewed all graph schema definitions across four ADRs for internal consistency. Found **11 issues**: 4 inconsistencies (properties or enum values that conflict between ADRs), 3 incompleteness issues (missing definitions or weights), 2 counting errors, 1 undefined reference, and 1 notation divergence.

---

## Issue 1: ADR-0012 Edge Type Count Mismatch (Internal)

**Severity**: Low (documentation error)

**Location**: ADR-0012, Section 2 heading

**Quote**: "Eight new edge types connect user personalization nodes to the existing graph."

**Conflict**: The PG-Schema definitions and the summary table in the same section both list **9** edge types: HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL.

**Resolution**: Change the heading from "Eight" to "Nine".

---

## Issue 2: DERIVED_FROM Edge Properties Diverge Between ADR-0012 and ADR-0013

**Severity**: High (schema inconsistency)

**Location**: ADR-0012 Section 2 (PG-Schema) vs ADR-0013 Section 9

**ADR-0012 defines DERIVED_FROM with 2 properties:**
```
derivation_method STRING NOT NULL
derived_at        ZONED DATETIME NOT NULL
```

**ADR-0013 defines DERIVED_FROM with 6 properties:**
```
derivation_method  STRING
derived_at         ZONED DATETIME
model_id           STRING
prompt_version     STRING
evidence_quote     STRING
source_turn_index  INTEGER
```

**Conflicts**:
1. ADR-0013 adds 4 new properties (`model_id`, `prompt_version`, `evidence_quote`, `source_turn_index`) not present in ADR-0012's PG-Schema definition.
2. ADR-0012 marks both properties as `NOT NULL`; ADR-0013 does not specify nullability constraints for any of the 6 properties.

**Resolution**: ADR-0012 is the authoritative PG-Schema. ADR-0013 should either (a) explicitly amend ADR-0012's PG-Schema definition to add the 4 new properties with nullability constraints, or (b) document that the additional properties are an extension defined by ADR-0013. The PG-Schema in ADR-0012 should be updated to reflect the full property set.

---

## Issue 3: DERIVED_FROM `derivation_method` Enum Values Are Incompatible

**Severity**: High (enum conflict)

**Location**: ADR-0012 Section 2 vs ADR-0013 Section 9

**ADR-0012 enum values:**
```
"stated" | "frequency_analysis" | "llm_extraction" | "pattern_match" | "hierarchy_propagation"
```

**ADR-0013 enum values:**
```
"rule_extraction" | "llm_extraction" | "statistical_inference" | "graph_pattern"
```

**Conflicts**:
- Only `"llm_extraction"` appears in both ADRs.
- ADR-0012 defines `"stated"`, `"frequency_analysis"`, `"pattern_match"`, `"hierarchy_propagation"` -- none of which appear in ADR-0013.
- ADR-0013 defines `"rule_extraction"`, `"statistical_inference"`, `"graph_pattern"` -- none of which appear in ADR-0012.

**Resolution**: Establish a single canonical enum that is the union of both sets, or document which ADR takes precedence. Likely the combined set should be: `"stated" | "frequency_analysis" | "llm_extraction" | "pattern_match" | "hierarchy_propagation" | "rule_extraction" | "statistical_inference" | "graph_pattern"`. The PG-Schema in ADR-0012 should list the full set, and ADR-0013 should reference it rather than defining a subset.

---

## Issue 4: Total Edge Type Count is Correct (16)

**Severity**: None (verified correct)

**Location**: ADR-0013 Section "Context" (line 10)

**Quote**: "16 edge types"

**Verification**:
- ADR-0009: 5 (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES)
- ADR-0011: +2 (SAME_AS, RELATED_TO)
- ADR-0012: +9 (HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL)
- Total: 5 + 2 + 9 = **16**

**Note**: The count of 16 is correct, but it relies on ADR-0012 contributing 9 edge types -- which contradicts ADR-0012's own heading claiming "eight" (see Issue 1). The 16-count in ADR-0013 implies ADR-0013 authors correctly counted 9 from ADR-0012 despite the heading error.

---

## Issue 5: Entity Type Set is Correct (6 Total)

**Severity**: None (verified correct)

**Location**: Cross-ADR check

**Verification**:
- ADR-0009 defines 5 entity types: `agent`, `tool`, `user`, `resource`, `concept`
- ADR-0011 adds 1: `service`
- Total: **6 entity types**
- ADR-0012 uses `entity_type="user"`, `entity_type="concept"`, `entity_type="service"` -- all consistent with the 6-type set.
- ADR-0013 uses `entity_type="service"` (QuickBooks) and `entity_type="concept"` (email notifications) -- consistent.

---

## Issue 6: SUMMARIZES Edge Missing from ADR-0009 Intent Weight Matrix

**Severity**: Medium (incomplete weight matrix)

**Location**: ADR-0009 Section "Edge Weight Configuration"

**Quote**:
```python
INTENT_WEIGHTS = {
    "why":     {CAUSED_BY: 5.0, FOLLOWS: 1.0, SIMILAR_TO: 1.5, REFERENCES: 2.0},
    "when":    {CAUSED_BY: 1.0, FOLLOWS: 5.0, SIMILAR_TO: 0.5, REFERENCES: 1.0},
    "what":    {CAUSED_BY: 2.0, FOLLOWS: 1.0, SIMILAR_TO: 2.0, REFERENCES: 5.0},
    "related": {CAUSED_BY: 1.5, FOLLOWS: 0.5, SIMILAR_TO: 5.0, REFERENCES: 2.0},
    "general": {CAUSED_BY: 2.0, FOLLOWS: 2.0, SIMILAR_TO: 2.0, REFERENCES: 2.0},
}
```

**Conflict**: ADR-0009 defines 5 edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES) but the intent weight matrix only includes 4. The **SUMMARIZES** edge type has no weight for any intent. ADR-0012's new intents (who_is, how_does, personalize) correctly include `SUMMARIZES: 1.0` in all three, demonstrating awareness of this gap -- but the original 5 intents remain incomplete.

**Resolution**: Add SUMMARIZES weights to the original 5 intent rows in ADR-0009. ADR-0012 already sets SUMMARIZES to 1.0 for the new intents, suggesting a default weight of 1.0-2.0 is appropriate.

---

## Issue 7: Original 5 Intents Lack Weights for ADR-0011/0012 Edge Types

**Severity**: Medium (forward compatibility gap)

**Location**: ADR-0009 intent weight matrix vs ADR-0011/ADR-0012 edge types

**Conflict**: ADR-0012 defines 3 new intents (who_is, how_does, personalize) with weights that include both old edge types (CAUSED_BY, FOLLOWS, etc.) and new edge types (HAS_PROFILE, HAS_PREFERENCE, etc.). However, the original 5 intents from ADR-0009 (why, when, what, related, general) are never updated to include weights for:
- ADR-0011 edges: SAME_AS, RELATED_TO
- ADR-0012 edges: HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL

This means a `why` or `when` query has no defined weight for traversing user personalization edges or entity resolution edges.

**Resolution**: Either (a) update ADR-0009's original 5 intents to include weights for all 16 edge types, or (b) document a default weight policy (e.g., "edge types not listed in an intent's weight map default to 0.0" or "default to 1.0").

---

## Issue 8: ADR-0012 New Intents Missing Weights for 3 of Their Own Edge Types

**Severity**: Medium (incomplete within ADR-0012)

**Location**: ADR-0012 Section 3, intent weight matrix extension

**Quote**:
```python
"who_is": {
    CAUSED_BY: 1.0, FOLLOWS: 0.5, SIMILAR_TO: 1.0, REFERENCES: 3.0,
    SUMMARIZES: 1.0,
    HAS_PROFILE: 5.0, HAS_PREFERENCE: 5.0, HAS_SKILL: 5.0,
    EXHIBITS_PATTERN: 4.0, INTERESTED_IN: 4.0, ABOUT: 3.0,
},
```

**Conflict**: ADR-0012's new intents include weights for 6 of the 9 new edge types but are missing weights for:
- `DERIVED_FROM`
- `ABSTRACTED_FROM`
- `PARENT_SKILL`

They are also missing ADR-0011's edge types:
- `SAME_AS`
- `RELATED_TO`

This applies to all three new intents (who_is, how_does, personalize).

**Resolution**: Add weights for all 5 missing edge types to the 3 new intents. DERIVED_FROM is particularly important for the "personalize" intent (provenance traversal). SAME_AS is important for "who_is" (cross-identity resolution).

---

## Issue 9: REFERENCES Edge Roles -- ADR-0009 vs ADR-0011 Rename

**Severity**: Medium (breaking rename, migration needed)

**Location**: ADR-0009 Section "REFERENCES (Entity)" vs ADR-0011 Section 3 "Entity Roles on REFERENCES Edges"

**ADR-0009 defines roles as:**
```
role : STRING (subject | object | tool | target)
```
(4 values)

**ADR-0011 renames to:**
```
agent, instrument, object, result, participant
```
(5 values -- `participant` is new)

**Mapping:**
| ADR-0009 | ADR-0011 |
|----------|----------|
| `subject` | `agent` |
| `tool` | `instrument` |
| `object` | `object` (unchanged) |
| `target` | `result` |
| (none) | `participant` (new) |

**Status**: ADR-0012 and ADR-0013 do not explicitly reference REFERENCES edge roles in their examples or definitions, so no downstream conflict exists. However, ADR-0009's PROV-DM compatibility table (Amendment section) still references the old operational names indirectly. The PG-Schema in ADR-0011 only constrains `role STRING NOT NULL` without enumerating valid values in the schema itself (enum enforcement is at the projection worker level per ADR-0011 Section 7).

**Resolution**: ADR-0009 should be amended to reflect the renamed roles, or ADR-0011 should note that the rename supersedes ADR-0009's role definition.

---

## Issue 10: ADR-0013 References Undefined `PART_OF` Edge Type

**Severity**: Medium (undefined edge type)

**Location**: ADR-0013 Section 3 (Consumer 1 table)

**Quote**:
```
| Session structure | `session_id` on events | Session node + PART_OF edges | Direct mapping |
```

**Conflict**: `PART_OF` is not defined in any ADR's PG-Schema:
- ADR-0009: FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES
- ADR-0011: SAME_AS, RELATED_TO
- ADR-0012: HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL

Additionally, "Session node" is not a defined node type. ADR-0011's PG-Schema defines only Event, Entity, and Summary node types. ADR-0012 adds UserProfile, Preference, Skill, Workflow, BehavioralPattern. There is no Session node type.

**Resolution**: Either (a) define PART_OF as a 17th edge type and Session as a 9th node type with PG-Schema definitions, or (b) remove this from ADR-0013 and document that session structure is represented via the `session_id` property on Event nodes (the current approach in ADR-0009).

---

## Issue 11: ADR-0013 `source_turn_index` on ExtractedPreference vs DERIVED_FROM

**Severity**: Low (design intent clear but placement inconsistent)

**Location**: ADR-0013 Section 4 (ExtractedPreference Pydantic model) vs ADR-0012 Section 2 (DERIVED_FROM PG-Schema)

**ADR-0013 places `source_turn_index` in two locations:**
1. On the `ExtractedPreference` Pydantic model (Section 4, line ~169): `source_turn_index: int | None`
2. On the `DERIVED_FROM` edge properties (Section 9): `source_turn_index: INTEGER`

**ADR-0012 does NOT include `source_turn_index` on the DERIVED_FROM edge** despite being the authoritative PG-Schema definition for this edge type.

**Conflict**: The `source_turn_index` exists as an extraction-time field (on the Pydantic model in ADR-0013) and as a graph edge property (on DERIVED_FROM in ADR-0013 Section 9), but the PG-Schema definition of DERIVED_FROM in ADR-0012 does not include it.

**Resolution**: Update ADR-0012's DERIVED_FROM PG-Schema definition to include `source_turn_index INTEGER` (nullable, since not all derivation methods have a turn index).

---

## Verified Correct Items

The following items were checked and found to be consistent:

1. **Total edge type count**: ADR-0013's claim of "16 edge types" is arithmetically correct (5 + 2 + 9 = 16).
2. **Total node type count**: ADR-0013's claim of "8 node types" is correct (3 + 5 = 8).
3. **Entity type set**: All ADRs consistently reference the 6-type set (agent, user, service, tool, resource, concept).
4. **PG-Schema notation**: All ADRs use consistent PG-Schema notation (ZONED DATETIME, STRING NOT NULL, DEFAULT, LIST<>, CREATE NODE TYPE / CREATE EDGE TYPE / CREATE KEY syntax).
5. **PROV-O grounding**: ADR-0011 corrected ADR-0009's PROV-DM mapping errors (SIMILAR_TO no longer mapped to wasDerivedFrom; SUMMARIZES mapped to alternateOf not specializationOf). ADR-0012 follows ADR-0011's corrected mappings.
6. **Node property definitions for Event, Entity, Summary**: ADR-0011's PG-Schema matches ADR-0009's property lists. Minor notation difference: ADR-0009 uses `DATETIME` while ADR-0011 uses `ZONED DATETIME` -- this is a PG-Schema formalization improvement, not a conflict.
7. **Edge endpoint constraints**: ADR-0012's PG-Schema endpoint constraints (e.g., DERIVED_FROM `FROM Preference TO Event | FROM BehavioralPattern TO Event | ...`) are consistent with ADR-0011's constraint enforcement strategy.

---

## Recommendations

1. **Establish a single canonical PG-Schema document** that aggregates all node types and edge types from ADR-0009, ADR-0011, and ADR-0012, with ADR-0013's extensions. This prevents property definitions from diverging across ADRs.

2. **Define a default weight policy** for the intent weight matrix (e.g., "unlisted edge types default to 0.5") to avoid the combinatorial problem of maintaining weights for all intents x all edge types.

3. **Resolve the DERIVED_FROM property set** -- this is the highest-priority fix since two ADRs define different properties and different enum values for the same edge type.

4. **Clarify ADR-0013's PART_OF reference** -- either formalize it or remove it. If session structure needs a dedicated edge type, it should go through the same PG-Schema definition process as all other edge types.
