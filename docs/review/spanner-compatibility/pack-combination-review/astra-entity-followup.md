# Entity identity/evidence follow-up from matrix01

2026-10-14. Read-only source grounding. **This is a real producer defect and blocks a clean combination acceptance claim.** The current matrix's earlier presence assertions do not establish complete later REFERENCES evidence. Preserve its records; add the missing exact oracle and rerun after the bounded correction.

## Source cause

`domain/entity_resolution.py::resolve_exact_match` normalizes the matched stored name and returns only `canonical_name`. `worker/extraction.py::_write_extraction_results` then constructs `entity:<canonical_name>` for MERGE. First creation instead uses the original extracted spelling, `entity:<entity_name>`. Therefore first extraction can create `entity:ResetToken`, while the next exact match chooses `entity:resettoken`; REFERENCES writes target an absent identity and can silently fail to materialize. Normalization is suitable for matching, not for reconstructing storage keys.

The same information loss exists for fuzzy SAME_AS/RELATED_TO targets. SemanticCandidate already carries entity_id, but `resolve_semantic_match` drops it from EntityResolutionResult, and the writer reconstructs the target from its name. Correcting only the exact spelling branch leaves the same concrete defect in adjacent branches of the same resolver contract.

## Smallest coherent correction

Carry the selected existing Entity's actual key in EntityResolutionResult (for example `matched_entity_id`). Exact/fuzzy resolvers copy it from the selected existing row; semantic resolution copies `SemanticCandidate.entity_id`. Keep canonical_name for matching/display/diagnostics. Worker MERGE REFERENCES and resolution-edge targets must use the carried existing key, never `entity:` plus a normalized name. Preserve the existing CREATE identity convention and resolution action/threshold policy.

The existing ports already provide this identity: `_fetch_existing_entities` calls `GraphStore.get_entities(limit=1000)` and semantic search returns entity_id. No new lookup port, database table, alias registry, migration or resolver framework is necessary. Update result-construction fixtures deliberately. A production match lacking a usable stored key must not silently reconstruct a target or report evidence success; validate the candidate/result contract and fail visibly. Name-only domain fixtures can retain explicit compatibility handling if needed, but must not authorize invented production keys.

Do not rename or merge existing data merely to repair this bug. The retained assessment data is evidence, not a migration target. Preserve existing matched Entity metadata; do not change mention-count, creation-time, scoring, clustering or alias-policy semantics under this correction. Existing clustering behavior can be exercised with real targets, without claiming its broader correctness.

## Required bounded proof

- Regression through the actual extraction worker: first create mixed-case ResetToken, then overlapping session-end and correction extraction. Exact REFERENCES source set must include the five accepted user-session Events under the current whole-window reference contract, and every edge must resolve to the same stored Entity. No lowercase shadow node/target.
- Domain result checks for normalization, known alias, fuzzy and semantic matches with an existing key deliberately unrelated to name spelling. Worker-level typed target checks should cover MERGE and relationship actions; do not substitute a normalized-name assertion for key preservation.
- Existing Entity properties remain unchanged by MERGE except any already-declared producer behavior. No extra Entity is created for a successful exact merge. Verify dangling target absence and exact source membership.
- Add the exact REFERENCES set to each matrix configuration, not just User selections: core entity extraction runs everywhere. Re-run the five real authenticated API/worker/Spanner configurations with frozen fixtures and source hashes, retained failures, safe export/reset and final public retrieval evidence.

This is distinct from whether vector search retrieves enough evidence (#25): the immediate write-side problem is loss of an already selected stored identity. Track it under the appropriate #34 producer/evidence work rather than broadening the current checkpoint into generic entity-resolution redesign, concurrent tenant isolation or pilot work.
