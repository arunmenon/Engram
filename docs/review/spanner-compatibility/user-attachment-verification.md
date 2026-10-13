# User attachment and retry safety — verification walkthrough

## Scope and acceptance

This bounded remediation follows the pack-composition assessment. It addresses #20 and the User portions of #42 under #34, with conformance evidence in #39 and Spanner evidence in #41. Enrichment ordering (#29), concurrent tenant isolation (#43) and the pilot remain separate checkpoints. Core is mandatory. No historical-data migration is included. Final assessment data is retained.

The accepted path is authenticated Engram HTTP writes → real Spanner ledger → five real worker loops → graph adapters → Spanner → Engram HTTP reads. Storage inspection is independent evidence, never an application write or repair. All runs use only `engram-assess-1010a-pdlc`; ownership and retained fingerprints must match, and an export is verified before exact-key reset. The private bound entrypoint and development unevaluated-bundle gate do not establish public tenant service or pack-wide evaluation.

| Case | Expected result before running |
|---|---|
| UA01 | Real configured LLM extracts Alice's profile, a positive short-answer preference and Rust interest; interest evidence references exactly the observation; all five groups finish without pending or dead letters. |
| UA02 | Specialized User API, composed reader and personalization return the same canonical `profile:user:alice`. |
| UA03 | Reposting the exact accepted end event changes no User artifacts. Overlapping extraction windows count each quoted source Event once. |
| UA04 | Controlled interruption after prepare leaves no partial User preference; restart consumes the first frozen result without another provider call. Interruption after commit but before ACK also converges without extra support/count. |
| UA05 | Explicit correction replaces only the matching support-context preference; predecessor remains with its original support, replacement has only correction-event support, reviews-context preference remains unchanged. A later trigger does not replay the historical correction. |
| UA06 | Bob's profile/preferences/personalization positively return for Bob and stay out of Alice's personalization. This tests logical owner scope, not tenant authorization. |
| UA07 | Core+User and Core+User+Memory run; Memory Episode and core Summary coexist with User. Core+PDLC with User off preserves Event/Change retrieval and writes no User artifacts or receipts. |

Primary prose uses the real configured LLM. Correction and interruption fixtures replace only the external extraction provider with explicitly labeled deterministic results: their purpose is to isolate worker/storage correctness. They do not prove autonomous correction inference or additional model quality. Expected controlled identities, counts and memberships are fixed before admission. The final audit independently recomputes real-model output identities and quoted source membership from frozen receipts and submitted inputs, then checks the exact artifact set, owner edges, evidence and counts.

## Implementation

User endpoints use an explicitly authorized test principal with both `api` and `admin` roles; this exercises existing role checks.

A selected User extraction first persists a validated snapshot on its trigger Event. The first stored snapshot wins. User outputs, support unions, corrections and the applied marker then commit in one existing backend transaction. Retry reuses that snapshot. Source evidence is the set of accepted events containing the actual quote, not every event in the session. Existing core Entity resolution remains outside this new User atomic guarantee.

UserProfile identity now agrees across schema and specialized storage (`profile_id`). Interest provenance supports core Entity sources. Preference and Skill identities are owner-qualified. Explicit corrections require matching owner/category/key/scope/context and cannot create competing successors. Applied receipts prevent later windows from reinterpreting historical corrections. Selected User provider failure or unavailable accepted source does not become an empty successful extraction. Receipts are hidden from normal retrieval and included in owner export/deletion; owner-specific Skills are erased while legacy shared Skills are preserved.

## Accepted execution results

Execution and [independent Astra completeness review](user-attachment-review/astra-final-review.md) passed for UA01–UA07. No remaining blocker was identified for the bounded defects #20 and #59.

| Selected packs | Accepted run | Live assertions | Ledger / nodes / edges | Final pending / DLQ |
|---|---|---:|---|---|
| Core + User | [User 08](runs/user-attachment-1013-08/user.json) | 134 passed | 13 / 49 / 94 | 0 / 0 |
| Core + User + Memory | [User+Memory 08](runs/user-attachment-1013-08/user-memory.json) | 131 passed | 13 / 52 / 127 | 0 / 0 |
| Core + PDLC, User off | [PDLC 06](runs/user-attachment-1013-06/pdlc.json) | 12 passed | 3 / 11 / 18 | 0 / 0 |

**277 live assertions** cover the bounded UA01–UA07 matrix. These are assertions, not 277 separate journeys. Configurations ran sequentially with verified export and reset between them. The final Core+User+Memory dataset remains in the assessment database at epoch 29; preceding data is preserved in verified exports. A [fresh post-process retention recheck](runs/user-attachment-1013-08/post-process-retention-recheck.json) matches the owner and all fingerprints; [all 214 recorded source/harness hashes match](runs/user-attachment-1013-08/final-source-recheck.json). The PDLC06 result remains applicable because the later User timestamp correction does not execute in its User-disabled path.

Latest local verification: 24 focused User tests; 124 affected tests; broad unit suite **2,809 passed, 13 skipped** with `tests/unit/test_pdlc_end_to_end.py` excluded because of its separately known evaluation-gate failure. The earlier full run including that file is preserved and is not relabeled green. Ruff and mypy passed for the changed code (mypy: eight source files). Raw logs are in [user-attachment-review](user-attachment-review/).

## Stakeholder demo walkthrough

1. **Start with Alice's actual statement.** The HTTP write contains “My name is Alice. I am a software engineer. I prefer short answers. I am interested in Rust language development.” The real configured LLM processes the accepted observation and session end. User API reads return `profile:user:alice`, a positive short-answer preference and Rust interest. Source relationships point to the observation, not the empty session-end record. The exact request/response and worker outcomes are saved in each accepted User record.
2. **Read through the different entrypoints.** The specialized profile API and actual composed reader return the same profile. `/v1/query/subgraph` with `intent=personalize` now includes that profile and its supported preferences. This previously failed in attempt02 and became issue #59. Shared Entity first/last timestamps remain chronological after User writes.
3. **Show why a retry is safe.** The controlled provider creates one preference, one Python Skill and one RetryTopic interest. An exception after preparation leaves a durable snapshot with no probe Preference. A new worker/store instance resumes it without calling the provider again. A second exception after the actual transaction commits but before ACK also resumes without adding another observation. The provider counts and both raw checkpoints are retained. Reprocessing an overlapping prefix still counts the supporting observation once.
4. **Change a preference without erasing history.** A declared negative correction says “I no longer prefer short answers.” It replaces only the `support` context. The prior positive preference remains with its original support and a SUPERSEDES relationship; the negative replacement has only correction-event support. A separate `reviews` preference remains active. A later session-end does not reinterpret that old correction.
5. **Read another owner positively, then check exclusion.** Bob's API and personalization return `profile:user:probe-bob` and Bob's preference. Alice's personalization excludes those User artifacts. This is logical owner selection inside one tenant, not tenant authorization proof.
6. **Show selection and honest failure handling.** With Memory enabled, the same User cases work alongside a complete Memory Episode and core Summary. With User disabled and PDLC enabled, no User artifacts or receipts appear; the Change and core Event are retrieved through Engram. A malformed envelope returns 422 with identical whole-database fingerprints after workers become idle and stop.

The final independent audit derives expected artifact IDs and quoted source membership from frozen results plus submitted inputs, then compares the exact final artifact set, owners, support unions, observation counts and relationships. It does not derive expectations from the artifact rows being checked.

## Failures retained and what changed

| Attempt | Outcome and disposition |
|---|---|
| 01 | Real extraction and five-worker completion succeeded; User API returned 403 because the harness principal lacked the existing admin role. Corrected test authorization only. |
| 02 | User APIs and composed profile read passed; personalization omitted existing User artifacts. Real engine defect filed as #59 and fixed without changing the expected answer. |
| 03 | Core+User passed; User+Memory failed a whole-database rejection oracle while timed consolidation could write. Retained as failed; the rejection expectation remains unchanged. |
| 04 | HTTP ReadError; cause unproven. Exact retained-ledger reconciliation confirms the attempted PR Event ID absent. Fresh connections and intent/error journaling added; no automatic retries. |
| 05 | PDLC ingestion and User-off processing passed; artifact fixture used unsupported API fields and correctly received 422. Corrected to `seed_node_ids`, with real request-model preflight. |
| 06 | PDLC passed 12; User+Memory passed 133. Final review confirmed User writes could regress existing core Entity `last_seen`; chronological preservation and a worker/replay regression were added before final User reruns. |
| 07 | User functional/chronology/audits passed; the rejection fingerprint exposed two late consolidation writes after task joins. [Exact row-hash reconciliation](runs/user-attachment-1013-07/late-edge-reconciliation.json) identifies the Summary→Bob-source links. Fresh post-process owner/fingerprint recheck matches the retained record. Production defect logged separately as #60. |
| 08 | Final-source Core+User and Core+User+Memory passed with healthy idle coordination before stopping and fingerprint checks. Final data retained. |

The harness waits for the existing consolidation lock, holds it while healthy workers stop and join, then performs the unchanged 422/no-write assertion. This avoids the observed cancellation window; it does not fix production shutdown or certify SDK work already detached by cancellation. Shutdown errors prohibit reuse. All application writes continue to enter through Engram; no manual graph repairs were used.

## Repeat and evidence boundaries

Run the same harness with a **new run ID** and the latest matching retained record. It verifies owner and fingerprints, exports and verifies the prior dataset, then resets only registered keys. Do not reuse an old record or overwrite a run directory. Example for the authorized assessment database:

```bash
PYTHONPATH=src:scripts python scripts/engram_user_attachment_demo.py \
  --run-id user-attachment-repeat-01 \
  --previous-record docs/review/spanner-compatibility/runs/user-attachment-1013-08/user-memory-retained.json \
  --configurations pdlc user user-memory
```

Real-provider extraction and labeled deterministic-provider/fault probes remain separate. The restart probes replace worker/store instances within the harness process; they are not OS-crash or network-partition tests. Stable identities use validated keys and exact context, not semantic deduplication of differently worded independent model results. Existing core Entity resolution remains outside the new User atomic guarantee. No live Neo4j acceptance, mixed User+PDLC journey, public/concurrent tenant isolation, pack-wide evaluation, 65-scenario baseline sweep or pilot-readiness sign-off is claimed. Cloud Monitoring export still returns 403; no telemetry readiness claim is made. Historical migration remains excluded.

## Ticket reconciliation and publication

| Issue | Final state | Action |
|---|---|---|
| [#20](https://github.com/arunmenon/Engram/issues/20) | CLOSED | Interest provenance/worker acceptance met; body updated with current scope, evidence and limits. |
| [#59](https://github.com/arunmenon/Engram/issues/59) | CLOSED | Personalization defect fixed, rerun and independently reviewed; native child of #34. |
| [#34](https://github.com/arunmenon/Engram/issues/34#issuecomment-6149368301) | OPEN | Umbrella body and checkpoint updated; original feature buckets remain the owning scope. |
| [#42](https://github.com/arunmenon/Engram/issues/42) | OPEN | Body updated with completed User cases and remaining broader composition scope. |
| [#39](https://github.com/arunmenon/Engram/issues/39#issuecomment-6149368941) | OPEN | Exact conformance evidence added; wider coverage remains. |
| [#41](https://github.com/arunmenon/Engram/issues/41#issuecomment-6149369535) | OPEN | Spanner evidence added without claiming the baseline of 65 scenarios or wider isolation passed. |
| [#60](https://github.com/arunmenon/Engram/issues/60#issuecomment-6149370234) | OPEN | New native child of #34; production consolidation shutdown is unresolved and a pilot prerequisite. |

GitHub states and parent links were reread after mutation and saved in [reconciliation evidence](user-attachment-review/github-reconciliation.json). No additional feature bucket is needed. Enrichment #29, wider combinations, tenant isolation and the pilot have not started in this slice. Stop here for stakeholder review.

Published on `feature/engram-memory-episodes`:

- `782ab1e` — runtime changes, bounded harness and tests.
- `61475be` — verification walkthrough, raw accepted/failed runs, independent review, inventory and assessment checkpoint.
- Subsequent documentation reconciliation records the final GitHub states and comment links; it changes no runtime source.
