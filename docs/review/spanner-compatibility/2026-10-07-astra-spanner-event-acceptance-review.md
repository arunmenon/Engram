# Atomic Spanner event acceptance and normalized API review

2026-10-07. Astra low source-only review and recheck. Runtime/evidence remain local and uncommitted. No reviewer tests/cloud calls.

## Implemented scope

- Immutable acceptance JSON on Events, separate from mutable document. Explicit additive column planner and strict nullable/nongenerated JSON schema handshake; no startup DDL or historical adoption.
- Fenced append stamps receipt with event in the same transaction. Database and same-chunk duplicate IDs compare producer and full request digest. Equal retries preserve original position/receipt, including across epoch-only advances; changed content or producer returns per-item conflict. Current admission control still precedes duplicate reads/writes. Existing missing/malformed/foreign-binding receipts refuse control before writes.
- Existing row identity survives document/dedup flag expiry; no claim beyond physical purge. This implements the bounded existing-ledger retention policy, not permanent tombstones or historical restore.
- Frozen request writer binds authenticated server-configured producer context without mutating the shared ledger. Normalized single/batch API routes use that view and report identity conflicts (409 when none accepted, per-item errors in mixed batches).
- Bound imported/bare unstamped appends refuse. Bound enrichment changes only summary/keywords; original payload and receipt cannot be changed through this method.
- Commit estimates count acceptance bytes and column mutation. Caller event/payload values are copied before transaction-thread handoff.

## Review finding

P2: the old codec kept integral floats as native JSON. Spanner numeric normalization could change 1.0 to 1 or erase negative zero, disagreeing with immutable json-v1 identity. Resolved by tagging all floats on new writes using the existing escaped codec; legacy native numbers remain readable. New tests simulate server integral-number normalization and assert decoded payload fingerprint equality, including negative zero and literal marker escaping. Existing codec test now asserts decoded float/int preservation instead of native integral-float wire representation.

Astra source-only recheck: numeric P2 resolved; scoped append/API slice approved pending executor rerun evidence.

## Executor evidence

Tracked `runs/20261007-local-spanner-acceptance-04`:151 passed,10 integration deselected,50 warnings. Selected Ruff passed. Scoped mypy on six changed adapter/port/API modules passed with `--follow-imports=silent`; this does not supersede the retained full-worktree type-check failure in acceptance-contract-02. Attempts01–03 retained, including parser square-bracket gap, argument-binding expectation and obsolete codec-wire expectation.

Tests use actual Engram adapter and HTTP handlers over transaction fakes, not a real Spanner service. They cover atomic receipt/duplicate/conflict, same/different chunks, producer rotation/separation, stale/epoch recovery, retained document/dedup expiry, malformed receipt, frozen/draining owner, wrong/missing source context, unstamped paths, enrichment protection, caller mutation, additive/noop/incompatible schema, numeric roundtrip and authenticated HTTP single/mixed batches. No Redis/Neo4j runners used.

## Required next work

No cloud DDL was applied. Existing cloud databases still need explicit tracked acceptance-column upgrade before current schema handshake can succeed. Extend the existing durable operation harness, review it and apply only the reserved target first. Then run real adapter/API duplicate, conflict, numeric roundtrip, retention, stale-owner and recovery assertions with exact cleanup. Update historical cloud fixtures to use authenticated admission contexts rather than bare bound writes.

Worker authoritative receipt reads/interpretation, archive export preserving receipt, replay compatibility, trusted restore, deterministic signed-webhook normalization, and remaining pack payload admission remain open. Translate interpretation mismatches into RuntimeFencedError before worker fallbacks/ACK/DLQ. Public tenant service remains disabled. No baseline promoted, issue closed or compatibility sign-off claimed.
