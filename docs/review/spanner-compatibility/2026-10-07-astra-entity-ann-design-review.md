# Entity-only native ANN design review

2026-10-07. Narrow #44 review of Spanner schema/query code, schema-handshake tests and the retrieval composition report. Read-only inspection and official documentation lookup; no implementation, tests or cloud calls. This is not #34 completion review.

## Verdict

Approve the candidate with a **new filtered index name**, strict physical-schema validation and an explicit additive migration. Google documents precisely the nullable generated BOOL membership pattern, storing that column in the vector index, filtering both the embedding and membership columns for non-null values, and using matching predicates in the ANN query. [Official filtered vector-index documentation](https://docs.cloud.google.com/spanner/docs/vector-indexes#filter_a_vector_index).

Recommended target DDL, preserving the existing embedding type and configured dimensions:

```sql
ALTER TABLE GraphNodes ADD COLUMN entity_embedding_member
  BOOL AS (IF(label = 'Entity', TRUE, NULL)) HIDDEN;

CREATE VECTOR INDEX GraphEntitiesByEmbeddingV1
  ON GraphNodes(embedding)
  STORING(entity_embedding_member)
  WHERE embedding IS NOT NULL AND entity_embedding_member IS NOT NULL
  OPTIONS(distance_type = 'COSINE');
```

Fresh table DDL includes the same generated column. Native search forces `GraphEntitiesByEmbeddingV1` and includes both non-null predicates before `ORDER BY distance LIMIT @top_k`. Preserve current score conversion, threshold, dimensions and search-breadth settings in this narrowly scoped repair.

## Blocking requirements

1. **Do not replace the old index in place.** Keep `GraphNodesByEmbedding` during migration so running older binaries can continue using their existing index. New binaries require the new index; a legacy-only database is incompatible. Extra legacy indexes are tolerated, as the handshake already tolerates additional objects. Fresh installations can create only the new index; supporting rollback to old binaries on a fresh database would additionally require the legacy index. Removing the old index is a separately authorized cleanup after rollout, not part of startup or this repair. Old binaries remain behaviorally unfixed while deployed even when the new index exists.

2. **Validate membership semantics, not merely names.** `schema_differences` currently checks columns by name and vector index type/distance/dimensions. Require the membership column to be generated, nullable BOOL with the reviewed expression yielding TRUE only for Entity and NULL otherwise. Reject an ordinary writable BOOL, constant TRUE, wrong label or FALSE alternative: `FALSE IS NOT NULL` still includes non-Entities. Require the new vector index on exactly GraphNodes.embedding, COSINE distance, membership STORING, both non-null filter conjuncts and READ_WRITE readiness. Reject broad `OR` predicates and similarly named ordinary indexes. Missing physical definitions must fail closed.

3. **Use physical metadata after reload.** Keep the existing `database.reload()` safeguard. Prefer structured metadata where available; otherwise narrowly normalize actual DDL tokens, preserving string literal case and expression meaning. Do not accept any DDL merely because isolated substrings match. Tests should cover quoting, whitespace, redundant parentheses and conjunct order without weakening semantics. A small recognizer for the supported definition is sufficient; no general SQL parser is required. If Spanner returns a different canonical expression, capture it in cloud evidence and support that exact equivalent form deliberately.

4. **Canonical Entity identity remains necessary.** The index guarantees label membership, not JSON consistency. Require returned `props.entity_id` to be a nonempty string equal to row `node_id`; never manufacture an Entity identity from an inconsistent row. Reject/drop corrupt rows explicitly and instrument the outcome. Post-result validation protects consumers but can underfill top_k on malformed Entity data; do not promise otherwise. If malformed-row recall becomes an acceptance requirement, move that additional invariant into index membership with its own migration. It is separate from inactive-label exclusion.

5. **Preserve stored data.** The current `_embedding_column` projects only Entity embeddings into the physical column; that does not sanitize historical/directly written non-Entity embeddings. The filtered index must exclude those independently. Do not delete, rewrite or clear any existing embedding or `props.embedding`, and do not change vector dimensions. Keep mutation column lists explicit so generated membership is never written. Broadening future embedding projection for domain nodes is unnecessary for this repair.

## Minimal rollout

Provide one explicit admin migration planner/executor: inspect physical state, return exact missing additive DDL, apply in dependency order, wait for each DDL operation, reload, and run the target handshake. If membership exists with the wrong definition or the target name denotes an incompatible index, refuse with a diagnostic; never silently drop/recreate. A partially completed migration resumes from existing valid objects. After timeout, inspect operation/schema state before issuing duplicate DDL. AlreadyExists races require reload-and-validate, not blind success. Building indexes are pending, not complete.

Deploy the migration before new application binaries. Normal startup only checks and rejects incompatibility; it performs no repair. The admin path must inspect legacy schemas independently of the target startup handshake, otherwise the very database needing migration cannot be opened for repair. Preserve existing explicit database-creation behavior separately. Skipping schema checks must not cause a fallback to the broad legacy ANN index.

## Required verification

- Handshake fixtures distinguish actual physical DDL/metadata from `expected_schema()` output. Current mocks derive both from the target schema and can mask migration gaps. Add an independent frozen legacy fixture.
- Accept new-only and legacy-plus-new valid schemas; reject legacy-only, missing/writable/nonnullable/wrong-expression membership, wrong vector type/dimension/distance, missing STORING/filter conjunct, broadened filter, wrong target column and non-READ_WRITE state.
- Migration tests cover fresh target, legacy, column-only partial success, valid complete no-op, incompatible-name collision, timeout/retry, concurrent AlreadyExists, and zero startup DDL. Assert no DROP, embedding rewrite or dimension change.
- Query/identity tests assert new FORCE_INDEX and both predicates; inconsistent/missing/nonstring entity_id is never returned. Keep dimension-mismatch fallback and current threshold/score behavior covered.
- Real Spanner acceptance: begin with a legacy populated database containing valid Entities plus more non-Entity embedded rows than top_k, including identical IDs across labels. Apply migration twice; verify generated membership, actual DDL/readiness and forced-index execution. ANN must return only canonical Entities despite closer non-Entity vectors, before and after later inserts/updates. Compare against an exact Entity-only baseline with ANN-appropriate recall expectations; do not require deterministic approximate rankings.
- Capture unchanged original embeddings/properties and dimensions, legacy-index coexistence, legacy-only startup rejection and successful post-migration startup. Record target, revision, DDL operation IDs, executed query and exact returned IDs. Local mocked tests cannot establish real index/filter behavior.

This closes the Entity ANN corpus defect only. Broader retrieval composition, privacy operations and tenant routing retain their existing scopes.

## Addendum: commit budgets during index coexistence

**Required in the minimal repair.** `commits.py` currently budgets `NODE_ROW_MUTATIONS = 4 + 4 + 3`, `NODE_DELETE_MUTATIONS = 1 + 2`, and bytes as `2 * (keys + props + embedding) + overhead`. These estimates describe the session index plus one vector index. Retaining the legacy index while adding the filtered index introduces another vector/index-key copy and stored membership value; the old estimates must not remain unchanged.

Use one conservative coexistence estimate even on fresh databases with only the new index. This avoids discovering mutable schema state on each write. Under the module's existing column-copy approximation, account for the base row, generated session/membership values, the session index, the legacy vector index, and the new vector index including STORING membership. A conservative column allowance is `6 + 4 + 3 + 4 = 17`; deletion allowance is at least `1 + 3 = 4`. These are application estimates, not a claim of exact vector-index internal mutation accounting. Retain existing budget headroom and validate actual commits in cloud acceptance.

Replace the byte shorthand with explicit component accounting: four copies of graph keys (table and three indexes), two props copies, three physical embedding copies (table and two vector indexes), session values in table/session index, membership allowance in generated/index storage, and overhead for each structure. `props` already contains its own JSON embedding and must still be counted independently. Charging both vector indexes to rows that do not actually qualify is acceptable conservative overestimation. Include allowances for removing old index entries when updates null or replace embeddings; do not infer zero historical index work solely from the new value.

The initial estimates in `graph.py` often pass `embedding=None` before reading current properties. Preserve the subsequent `_node_rows` check over complete merged rows and transaction rollback/splitting; updating only the initial chunk size is insufficient. Node deletion and detach-retention paths both use `NODE_DELETE_MUTATIONS` and must inherit the larger cost. DDL backfill is managed by the schema operation, not by application row chunking.

Add focused regressions for smaller coexistence-budget write/delete chunks, byte-dominant embeddings, property-only updates retaining an existing vector, embedding removal, and detach deletion combining node/index and incident-edge costs. Assert chunks against independently calculated coexistence costs, not merely the same production constant. Real migration acceptance should include bounded bulk writes/updates/deletes with both indexes present and actual commit statistics where available. No tests or cloud calls were executed for this addendum.
