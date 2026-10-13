# Independent final #29 enrichment ordering review

2026-10-13 — **No remaining blocker for closing the bounded #29 enrichment-ordering slice.** Keep #34, #39, #41, #42, #18, #60 and #61 open. This verdict is an independent inspection of source and saved evidence, not a new cloud run or broad compatibility/pilot sign-off.

## Accepted evidence

Source revision: `79d8779`. Accepted run: [enrichment-ordering-1013-03](../runs/enrichment-ordering-1013-03/manifest.json).

| Configuration | Passing assertions | Final data |
| --- | ---: | --- |
| Core | 58 | 5 Events + active ontology metadata, no edges |
| Core + User | 58 | 5 Events + active ontology metadata, no edges |
| Core + User + Memory | 58 | 5 Events + active ontology metadata, no edges |
| Core + PDLC | 58 | 5 Events + active ontology metadata, no edges |
| Core + PDLC + Memory | 58 | 5 Events + active ontology metadata, no edges |

Total: **290 assertions**, not 290 independent journeys. All five records are passed, with zero pending deliveries, dead letters and shutdown errors. Their final and retained snapshots agree.

I independently verified the following from each saved record:

- Exactly five accepted event identities and their five Event nodes; one reserved `OntologyState:active` with the selected configuration's pack identities; no extra business artifacts or edges.
- Submitted source identity fields, exact keywords, importance 7/8/5 by case, and exact 384-element JSON vectors where required. Provider-absent/failed cases have no vector. All six physical embedding columns are null, consistent with the existing Entity-only ANN contract.
- Successful public subgraph responses with matching keywords, owner/session and no truncation. EN04's session-context GET produces access count 1 and a timestamp; the declared graph-port importance adjustment produces 8. Projection plus enrichment replay preserves this owned state.
- Exact enrichment group/event pending observations while projection is absent and during the vector-storage fault, with no dead letters. The stopped consumer retains its delivery; the fresh consumer waits until projection and then converges.
- Provider-failure probe executes twice as declared; vector-storage retry executes the provider once. These counts accompany final exact state rather than replacing it.

## Issue acceptance and boundaries

EN01–EN03 demonstrate both actual worker orders and stop/restart recovery through authenticated admission and real Spanner. EN04 demonstrates duplicate ingestion and persisted-state projection/enrichment replay without resetting annotations, adjusted importance or access metadata. EN05–EN06 demonstrate optional provider absence/failure and retention of an existing vector. EN07 injects a storage-boundary outage after keywords commit, observes the pending delivery, and verifies exact vector convergence after recovery.

The external embedder is deliberately scripted; vector quality is not tested. The partial-storage failure is injected at the actual graph port and labeled accordingly, not represented as a natural cloud outage. Missing-ledger re-fetch and transaction-current null/zero/adjusted importance are supplemental local/SDK tests. The SDK fixture is not evidence of a live concurrent transaction abort/retry.

The existing retry helper caps backoff delay, not total dependency wait. Permanently missing data can block until stop, and repeated restarts remain subject to the existing pending-delivery/DLQ policy. #14/#19 are not claimed resolved. The accepted replay uses a fresh projection worker; the cached self-FOLLOWS defect remains #18. Subgraph retrieval's UUID access-update gap remains #61; session-context GET supplies the tested access side effect. Healthy harness quiescence avoids the known timer-cancellation window but does not fix general shutdown (#60).

These five configurations establish core enrichment behavior under selected pack bundles. They do not rerun full User/Memory/PDLC producer journeys, prove concurrent tenant isolation, live Neo4j behavior, general vector-search support for Events, or pilot readiness.

## Retention and local verification

I independently matched all **215 source hashes** to current files and verified all five previous-export file digests. The [post-process recheck](../runs/enrichment-ordering-1013-03/post-process-recheck.json) exactly matches the final retained owner at epoch **36** and every stored fingerprint. Final data remains retained; no reset is requested by this review.

Saved logs report 51 passed/48 skipped targeted checks, 2819 passed/13 skipped in the broad run with the known baseline PDLC evaluation-gate file excluded, clean Ruff and mypy on five source files. The later SDK cases were covered by the targeted run; do not describe the earlier broad run as including them. I inspected these logs rather than rerunning the suites.

Failed01 remains failed evidence for the separately tracked #61 API access behavior. Failed02 remains failed evidence for the omitted ontology housekeeping node in its final oracle. Neither is counted as completed acceptance, and neither required a production fix during accepted03. The final result table and published issue closure should reference accepted03 and retain these dispositions.
