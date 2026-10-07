# Astra implementation review — 2026-10-07

Reviewer: gpt-6-astra, low effort, /root/astra_implemented_review. Read-only review of seven uncommitted fixes against baseline6a30dcfd376d21b2732ffc36b8ed8847abb2a9de. Request/source fingerprints: implementation-astra-review-request.json. No cloud calls or repository edits by reviewer.

## Verified findings

- **P1 — #27 — src/context_graph/adapters/spanner/log.py:152–158.** Existing literal objects are silently reinterpreted. A pre-upgrade cell containing `{"payload":{"$engram_object":[["x",1]]}}` now reads as `{"payload":{"x":1}}`. Reproduced directly with json_value. New-write escaping passes, but existing cells have no version signal distinguishing this formerly ordinary object from the new escape marker. Define a migration/version policy preserving existing literals; add a pre-upgrade-cell regression test. The documented legacy $float ambiguity does not cover this newly introduced ambiguity.
- **P2 — #26 — src/context_graph/adapters/registry.py:145.** Cancellation during database acquisition leaks the eventual handle. Cancel open_stores while to_thread(open_database, ...) is running; allow that thread to return a database. The coroutine exits before registering its closer, and the returned database is never closed. Reproduced with synchronized thread events: close call count0. Preserve ownership through cancellation and add a deterministic acquisition-cancellation test.

## Coverage limits, not verified defects

- #26: failures before prepare_cleanup in schema.py and cancellation during multi-resource shutdown lack decisive tests.
- #28: local test uses /events, so it does not verify ingestion retry guidance. Recorded cloud evidence covers single/batch uncertain commits; streaming-import failure behavior is not established.
- #33: small-batch predicate consistency is established; the10,000-event boundary is not established.

## Per-issue disposition

| Issue | Disposition |
|---|---|
| #15 timezone validation | Ready for scoped fix |
| #16 gzip completeness | Ready for scoped fix |
| #23 physical vector schema handshake | Ready for scoped fix |
| #26 owned SDK shutdown | Needs changes |
| #27 JSON marker collisions | Needs changes |
| #28 transient503/retry guidance | Ready for evidenced single/batch scope |
| #33 admin pruning | Ready for scoped fix; boundary coverage remains |

## Checks performed

Inspected uncommitted runtime diff, lifecycle module, six requested test modules, checkpoint, and observations from exactly the three named cloud runs. Ran those six test modules:27 passed, using /private/tmp/engram-ontology-review-venv/bin/python. Ran both deterministic reproductions above successfully. Did not independently rerun the claimed188-test suite or rerun cloud checks. No full compatibility sign-off; scoped review readiness is not whole-issue acceptance or closure.

Parent disposition: both verified findings accepted for correction; no runtime fix made during this review step. Issues remain open. Larger coverage limits remain tracked.

Source fingerprints unchanged through review: True.
