# Worker extraction boundary review

2026-10-07. Read-only review of the worker extraction boundary changes in LLM client, worker factory/consumer and their focused tests. No test execution, cloud or services by this reviewer.

## Verdict

**Initial verdict: implementation acceptable within the narrow boundary; verification correction required. Current verdict after the recheck below: approved for this narrow worker extraction boundary.** No production correctness blocker identified in the inspected changes. Recorded run `20261007-local-worker-boundary-01/tests.txt` reports **2 failed, 88 passed**.

## Actionable finding

**P2 — Correct the core Entity write assertion.** `tests/unit/test_extraction_pack_boundary.py:88` expects `graph.merge_typed_node` to be awaited, but `worker/extraction.py:496` writes core Entity nodes using `merge_entity_node_raw`. Both optional-user-disabled cases therefore fail before reaching their REFERENCES/no-user-write assertions. Assert the actual graph port, preferably its entity ID/type, retain the REFERENCES and no-user-calls checks, and record a fresh registered recheck. This is a verification defect, not evidence that core Entity writes stopped.

## Boundary assessment

- `_build_consumer` resolves/validates composition before `open_stores`. The resolved `user.extract.v1` capability controls the LLM client's target flag and the injected user store; the consumer independently disables a supplied user store when its configured bundle excludes that capability.
- The flag changes both system schema and user instructions. The entity-only schema retains human-user entities. This avoids removing legitimate people from core Entity extraction.
- Disabled-user LLM results are reduced to their entities field before parsing persona/preferences/skills/interests. Unsolicited malformed user fields cannot become accepted outputs. Malformed overall JSON or entity payloads follow existing exception/retry/empty-result handling rather than enabling user writes.
- All profile, preference, contradiction, skill, interest and associated user provenance writes remain behind the unavailable user-store reference. Graph access remains available independently for Entity resolution, Entity writes and REFERENCES edges.
- Session-end and mid-session triggers both invoke the same configured client and result-writing method. Existing defaults preserve the full user extraction prompt and user store when the default user pack is selected. The fixture now supplies concrete OntologySettings to satisfy construction-time composition.

The new tests inspect both message roles, unsolicited user output, factory flag/store alignment, and validation before storage. The core-write tests need the correction above. This review does not establish ordinary API/retrieval gating, tenant isolation, historical policy, complete runtime optionality, or Spanner acceptance.

## Verification recheck

Read-only inspection confirms the finding is **resolved**: the test now asserts `merge_entity_node_raw` was awaited once, checks `entity:Python`/Python identity, retains the exact REFERENCES edge assertion, and verifies zero user-store calls. Recorded `runs/20261007-local-worker-boundary-02/tests.txt` reports **90 passed in 11.69s**; observations/results record the local acceptance and scope. This reviewer executed no additional tests. The original -01 failures remain historical evidence.

**Current verdict: approve the narrow worker extraction boundary; no outstanding findings in the reviewed scope.** This approval does not establish API/retrieval gates, tenant isolation, complete runtime optionality or Spanner acceptance.
