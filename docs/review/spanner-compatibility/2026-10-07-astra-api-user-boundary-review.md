# API user-read boundary review

2026-10-07. Read-only inspection of app startup, user dependencies/routes and focused tests. No test execution, services or cloud by this reviewer.

## Verdict and finding

**Initial verdict: changes requested for owning-pack validation. Current verdict after recheck below: approve the narrow API user-read boundary.**

**P2 — A foreign-owned UserProfile type reopens disabled historical user reads.** `src/context_graph/api/dependencies.py:75` checks only whether the global node vocabulary contains `UserProfile`. With optional built-ins empty, a custom domain can declare a type of that name: the registry reserves OntologyState, not UserProfile, and processing prerequisite ownership validation does not require a user handler for an otherwise ordinary domain type. This makes every ordinary user route return the historical UserStore even though the built-in user pack is inactive. Preferences/skills/patterns/interests are also exposed by this single name check.

Require the selected owning `user` pack (available in immutable `pack_identities`), or an explicit schema-owner-aware read capability. Do not simply require `user.extract.v1`: read availability is separate from whether a producer runs. Add a regression with core plus a custom domain-owned UserProfile and no user pack, asserting rejection and no store calls. This finding follows directly from inspected code; no exploit probe was executed.

## Other assessed behavior

- Startup resolves a bundle and reconstructs its registry before constructing embedding/LLM providers or stores; malformed composition fails before those effects.
- Missing bundle returns 503 before storage. The ordinary no-user selection returns 404 before any graph access, and all five ordinary endpoints use that dependency.
- Export and erasure use a deliberately separate dependency, preserving access to historical data after user selection is disabled. Existing middleware/auth wiring is unchanged; this is not a tenant-authorization review or assertion.
- Defaults retain the user pack and therefore ordinary reads. Tests cover all five disabled reads with zero store calls, missing configuration, historical export/erasure and existing default behavior. They currently miss the foreign-owned-name case above.

The recorded local run is `20261007-local-api-user-boundary-01`; its success cannot close the missing ownership case without a regression and recheck. This review excludes general retrieval, tenant routing, runtime-wide optionality and cloud acceptance.

## Remediation recheck

Read-only inspection confirms the finding is **resolved**. `api/dependencies.py:75` now checks the immutable effective pack identities for `user`, independently of global type names and producer enablement. The regression composes core with a lab-owned UserProfile, verifies 404 and zero graph-store calls. The auth fixture now mirrors startup's bundle setup. Additional privacy tests verify absent and ordinary API credentials receive 401, while the admin credential retains export/erasure access with the user pack disabled.

Inspected recorded `runs/20261007-local-api-user-boundary-03/tests.txt` and results: **62 passed, 21 dependency deprecation warnings**, 2.21 seconds. No additional tests executed by this reviewer; earlier failed runs remain historical evidence. **No outstanding findings in this narrow reviewed boundary.** General retrieval, tenant authorization/routing, full runtime optionality and cloud acceptance remain outside this approval.
