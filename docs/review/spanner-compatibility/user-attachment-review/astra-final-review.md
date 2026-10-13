# Independent final User attachment review

2026-10-13 — scoped verdict: no remaining blocker for UA01–UA07 or closure of the bounded defects #20 and #59. This is evidence review, not a new cloud execution. Keep #34, #42, #39, #41 and the separately filed consolidation shutdown defect #60 open.

## Evidence checked

- [User08](../runs/user-attachment-1013-08/user.json): 134 passing assertions; 13 accepted ledger events, 49 nodes, 94 edges.
- [User+Memory08](../runs/user-attachment-1013-08/user-memory.json): 131 passing assertions; 13 accepted ledger events, 52 nodes, 127 edges.
- [User-off PDLC06](../runs/user-attachment-1013-06/pdlc.json): 12 passing assertions, including public Change artifact retrieval and core Event retrieval with no User artifacts or extraction receipts.

These total **277 assertions, not 277 independent journeys**. Both final User records have no pending deliveries, dead letters or shutdown errors; final and retained snapshots agree. I independently compared all 214 recorded source hashes to current files: no mismatches. The only differences from the PDLC06 manifest are the User planner timestamp fix and User acceptance runner; the User-off production path is unchanged.

## Acceptance findings

| Scope | Finding |
| --- | --- |
| UA01 | Real-provider extraction attaches Rust interests with actual observation evidence. Controlled RetryTopic interest and owned Python Skill survive both interruption/restart boundaries. Shared Entity chronology is checked after extraction. |
| UA02 | Saved User API responses resolve `profile:user:alice`; the composed read check agrees. Actual public personalization responses include that profile, owned preferences and skills. |
| UA03 | Accepted trigger redelivery leaves User artifacts unchanged. Frozen receipts, stable identities and distinct support counts survive overlapping extraction prefixes. |
| UA04 | Saved prepared checkpoint has a prepared receipt with two inputs before User application. Saved committed checkpoint has applied receipts with two/three inputs before ACK. Restart converges without repeating the prepared provider result. These are deliberately injected before-apply and after-commit failures against the actual store and restarted worker, not natural Spanner outages or a claim of partial User transaction visibility. |
| UA05 | One explicitly declared correction retains predecessor support and adds separate correction evidence; the replacement has the correction source, one SUPERSEDES relation, and unrelated reviews context remains. A later trigger does not reinterpret the previous declaration. |
| UA06 | Bob has positive canonical profile/preference and personalization responses. Alice's public personalization contains Alice's User nodes and excludes Bob's. This proves the tested logical owner boundary. |
| UA07 | Both User configurations complete the same bounded flow. User+Memory includes a complete Episode and Summary. The preserved PDLC06 control proves the tested User-off behavior. |

I independently checked exact stored User artifact membership (12 User-only, 11 User+Memory), support sets, observation counts, owner relations and the separately declared correction edges against the saved expectations. Each final configuration has seven applied extraction receipts, exact accepted trigger/ledger coverage and owner/session-consistent input references. Public subgraph responses hide private receipts. The runner additionally reconstructs identities and quoted supports from frozen results plus submitted inputs rather than accepting arbitrary stored output.

## Retention and limits

Both final invalid-envelope requests returned 422 with identical whole-database before/after fingerprints after healthy lock-based quiescence. I verified both previous-export file SHA-256 digests. The post-process retention recheck exactly matches the final User+Memory retained record, including owner epoch 29 and all fingerprints. Attempt07 remains failed evidence: its two late Summary edges were separately reconciled; it is not counted as accepted.

The saved final unit log reports 2809 passed/13 skipped with the known baseline PDLC evaluation gate file excluded; the affected regression log reports 124 passed. These logs were inspected, not rerun for this review. The reported 24 User tests and typing/lint checks remain supplemental local verification.

Real-provider assertions cover the primary extraction/profile/interest/personalization flow. Correction and interruption scenarios use an explicitly controlled provider with actual HTTP admission, workers and Spanner persistence. No live Neo4j, concurrent tenant isolation, general graceful shutdown, pilot readiness, historical migration, autonomous correction inference, or new core Entity alias/replay guarantee follows from this acceptance. Healthy harness quiescence avoids the known shutdown race; it does not fix #60.
