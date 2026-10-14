# Independent Entity correction / matrix rerun review

2026-10-14. **One small source correction remains before rerun.** No wider resolver redesign is needed.

The added `canonical_entity_id` carries actual selected identity through exact, fuzzy and semantic resolution. This addresses the observed ResetToken/resettoken mismatch across the relevant branches. However, `worker/extraction.py` still falls back to `entity:<canonical_name>` for both MERGE and SAME_AS/RELATED_TO targets. A missing or empty candidate identity therefore retains the original silent failure behavior. Validate a nonempty string matched key before any related node/edge write and fail visibly rather than reconstructing it. Keeping the result field optional for backwards-compatible name-only pure-domain tests is reasonable; production writes cannot rely on that fallback. Add a public-worker missing-key regression alongside the normal exact/alias/fuzzy/semantic tests.

The new exact five-user-session REFERENCES set and exact Entity identities are the correct matrix oracle under the existing whole-window core extraction contract. This does not claim source-quote-granular REFERENCES or redesigned mention counting. Preserve matrix01 as failed/incomplete evidence, including its separate artifact-oracle disposition; none of its earlier configuration passes establishes the now-required entity evidence.

The Artifact API correction is legitimate, not gaming the expectation. `retrieval/artifacts.py` explicitly excludes provenance edges from artifact traversal and exposes the newest observing Event as node provenance. The revised public check requires that Event's UUID, owner/session, occurred_at, trace and global position, backed by exact stored DERIVED_FROM links. Memory subgraph responses still require their full evidence edges. No API behavior should be changed to satisfy the earlier incorrect oracle.

After removing the worker fallback and checking the targeted regression, rerun all five configurations against frozen inputs with unchanged safe export/reset and retention requirements. Final source hashes and exact evidence remain prerequisites to acceptance. #62 is the bounded producer repair; isolation/pilot and unrelated vector-evidence work remain outside scope.

## Matched-identity validation recheck

2026-10-14 — **Go for the all-five rerun after the final lint/type checks pass.** Inspected the corrected writer: any matched resolution must carry a nonempty string storage identity before the MERGE or relationship branches execute. Both branches use that identity directly; the normalized-name reconstruction fallback is gone. This closes the remaining source finding without broadening the resolver's behavior. The reported six invalid-result regressions and 117 affected passes supplement the exact identity cases; final cloud acceptance still requires fresh evidence from all configurations. Preserve original matrix01 and epoch43 export/fence history unchanged.
