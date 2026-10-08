# Pack property removal primitive review

2026-10-08. Astra low, source-only review against the approved property-update design. No tests, services or cloud calls executed by reviewer.

## Verdict

Approve the bounded storage primitive. No blocking P1/P2 found. This does not approve strict pack grammar/evaluation, required domain-field enforcement, writer permissions, general ordering/effect attribution or cloud compatibility.

The shared validator checks the complete supplied batch before reads or mutations. It rejects malformed/non-tuple names, duplicates, set/remove overlap (including ordinary None), node key removal, declared system fields, source_trust, status and event_id. Every backend refuses an explicit create_only edge with removals before I/O. Appended empty tuple defaults preserve existing callers.

Both public conversions filter legacy None first and inject explicit removal None afterward. Memory/shared merge and Spanner apply defaults only on creation before updates/removals; clear-only creation and absent-property clears retain the documented semantics. Spanner uses its existing transaction-local merge and final-row cost path: removed properties disappear from JSON, embedding is recomputed from final properties (and becomes SQL NULL when removed), and prior physical embedding costs remain included. The generated Entity membership discriminator remains label-derived; the index predicate excludes the NULL embedding. No separate removal transaction or weakened fence was introduced.

Neo4j uses parameterized null-valued maps with SET +=, with defaults in ON CREATE SET. Removal names are not interpolated into Cypher. This review does not establish backend execution ordering for repeated identities or repair existing mixed create_only behavior; those remain the design's explicitly retained limitations.

## Evidence and limits

Inspected test_pack_property_removals.py, including the added actual Spanner edge transaction callback test: repeated writes to one edge produce one final row with score 3 and label absent. The node callback test similarly verifies simultaneous set/removal. Invalid late batches use pre-I/O spies across all three adapters; memory tests cover defaults, absent fields and missing endpoints; Neo4j coverage checks generated query parameters rather than a running service.

Retained run 20261008-local-pack-removals-02 reports **123 passed, 10 skipped**, with Ruff clean. The unchanged runtime's preceding run 20261007-local-pack-removals-01 reports mypy clean for four selected files. These are local recording/mock/unit results, not real Spanner or Neo4j proof. Embedding removal was checked in source through the existing final-row derivation, not independently executed in this review.
