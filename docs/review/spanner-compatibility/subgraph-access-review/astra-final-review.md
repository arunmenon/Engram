# Independent final #61 subgraph access review

2026-10-14 — **No remaining blocker for bounded closure of #61.** The one-line change selects returned Event nodes by validated node type after pagination, so accepted UUID identities reach the existing access-accounting port. It preserves the narrow intended behavior without a new identity convention or storage implementation.

## Accepted evidence

Accepted run: [subgraph-access-1014-01](../runs/subgraph-access-1014-01/manifest.json).

| Configuration | Passing assertions | Final snapshot |
| --- | ---: | --- |
| Core | 97 | 4 accepted Events; 9 graph nodes; 9 edges |
| Core + PDLC + Memory | 131 | 4 accepted Events; 17 graph nodes; 36 edges |

Total **228 assertions**, not independent journeys. Both records are passed; all five workers joined; no shutdown errors, pending deliveries or dead letters remain. Final and retained snapshots agree. All 217 recorded runtime/harness source hashes match current files.

I independently reconstructed each read's before/after node property delta against the actual HTTP response:

- Both full reads return all three session UUID Events and an Entity. The composed configuration also returns Episode/Summary history snapshots. Every returned Event increments exactly once on each read; non-Event properties remain unchanged.
- The first one-node page in each configuration is positively an Event page. Only that Event increments; the other Events remain unchanged.
- Cursor10000 returns an empty result and produces no graph-property or inspected snapshot change. This is an exhausted-page proof, not an empty-session isolation claim.
- Access timestamps are populated and advance; the runner separately checks their request-time bounds. All other Event properties are unchanged. The unrelated owner/session Event stays at access_count0 throughout.
- The runner's per-read checks compare all six other application-table fingerprints and all physical GraphNodes columns except props, in addition to exact JSON property changes. All pass. Public Event provenance matches the expected owner/session, and full reads are untruncated.

The test-only composed-read regressions additionally cover UUID/Event–Entity identity collision and an Entity with an evt-prefixed key. They exercise the production ComposedGraphReads access-forwarding seam rather than permitting writes through a read-only view.

## Retention and validation dispositions

I independently verified both previous-export file digests. The [post-process recheck](../runs/subgraph-access-1014-01/post-process-recheck.json) exactly matches the final retained owner at epoch39 and all seven fingerprints. The epoch37 dataset was preserved before reset to38; the Core result was exported before reset to39. Final composed data remains retained.

The broad rerun log is now complete: **2834 passed, 13 skipped**, with the known baseline PDLC evaluation-gate file excluded. Saved targeted/affected runs report **25 passed** and **89 passed** respectively. These logs were inspected, not rerun by this review.

The initial broad run's 23 PermissionError failures exposed test helpers passing `selected.reads` directly, bypassing the production `ComposedGraphReads(selected)` wrapper. Inspection confirms that the registry supplies that wrapper and its deliberate `record_access` forwarding in production. Correcting the three test construction sites aligns them with production; no Memory/User expectations were relaxed and no runtime change was made during the cloud run.

The initial post-process audit failed because its timestamp comparator assumed an absent key rather than an existing null `last_accessed_at`. Treating null as the pre-access empty value corrects the audit oracle. The failed log remains retained; the correction changed no database rows, runtime or acceptance runner.

## Closure limits

Close #61 only. This verifies sequential access accounting for returned Events under the two tested selections. It does not establish concurrent counter atomicity, broad session filtering, tenant isolation, full pack-producer reacceptance, live Neo4j or pilot readiness. Scripted external extraction/summary providers are fixture producers, not model-quality evidence. Broader #34/#39/#41/#42 work and separately tracked issues remain open.

Update the draft verification result table and published closure with these accepted results and retained failure dispositions. No further implementation or next slice is requested by this review.
