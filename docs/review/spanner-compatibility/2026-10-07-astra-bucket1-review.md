# Bucket 1 review — 2026-10-07

Scope: issues #4/#5/#14/#15/#16/#17/#19/#28/#33 against current working tree, implementation waves, plan implementation section, checkpoint and prior implementation review. Static findings below are code-confirmed sequences unless explicitly marked untested. No runtime edits, cloud calls or Redis/Neo4j runners. No compatibility sign-off.

## Severity-ranked findings

1. **P1 — #19, existing data-loss bug.** `src/context_graph/adapters/spanner/log.py:808` selects documents for expiration solely by occurrence age; `:828` clears them without delivery/cursor protection. Accept an old historical event, leave it unread or pending, then run retention: its required document disappears although `trim()` protects its log position. Projection skips absent documents (`worker/projection.py:308`) and nevertheless ACKs the entire batch (`:183`); enrichment (`worker/enrichment.py:68`) and pack extraction (`worker/pack_extraction.py:112`) return successfully and are also ACKed. Separately, `worker/consolidation.py:352` supplies four groups, omitting pack extraction. Fix expiration and trim together with all five groups, including an explicit policy for groups without initialized cursors; absence of a cursor currently supplies no unread protection. Missing required content must retry or reach an explicit observable terminal outcome, never success.

2. **P1 — #5, existing trust-boundary bug.** `src/context_graph/domain/pack_projection.py:301` derives trust from caller-controlled `event.agent_id`; pack extraction does likewise (`worker/pack_extraction.py:140`). Generic ingress only reserves the `webhook:` prefix (`api/routes/events.py:98`). Configure a trusted non-webhook producer, submit its ID using ordinary API credentials, and the resulting pack evidence becomes trusted. Persist an ingress-authenticated source independently from the descriptive agent ID; carry it through import and signed webhook ingress. Existing webhook-prefix refusal does not solve arbitrary configured trusted IDs.

3. **P1 — #14, existing live recovery bug.** `src/context_graph/worker/consumer.py:240` reclaims and drains only at startup; the live loop at `:251` reads only new deliveries. A processing exception after startup leaves pending work indefinitely while the worker remains healthy; work orphaned after startup is also unreclaimed. Projection compounds this: `worker/projection.py:113` clears its buffer before fetch/write; a non-transient flush failure strands all buffered entries. Add bounded periodic pending/reclaim work interleaved with new work. Preserve durable retry counts, backoff and cursor progress. Deferred batches require position deduplication and recovery of every member, not just the entry whose processing triggered the flush. Repeated pending reads also increment Spanner delivery counts (`adapters/spanner/subscription.py:217`), so avoid counting healthy buffered waiting as failed processing.

4. **P2 — #4, existing validation gap.** `src/context_graph/api/ingest.py:113` silently converts a non-object payload to `None`; subsequent validation checks the envelope and declaration only. A declared pack event with an absent required identity field or wrongly shaped payload is accepted and appended, leaving deterministic projection failures downstream. Introduce pack-declared payload checks before append, shared across single/batch/import/webhook routes. Preserve input indexes and existing valid-item outcomes.

5. **P2 — #17, existing webhook validation gap.** `src/context_graph/api/routes/webhooks.py:177` calls translators after checking only the top-level object. A correctly signed `{"repository":"bad"}` reaches `sources/github.py:57` and raises `AttributeError`; truthy non-object `pull_request`/nested `head` cause similar failures. After translation, `webhooks.py:184` appends without `validate_event`, so a future timestamp can bypass the generic ingress refusal. Validate source-specific nested shape and every normalized envelope/payload before the first delivery append. Invalid dates currently fall back to now (`:102`); explicitly decide whether refusal or normalization is intended.

6. **P2 — #33, existing pruning progress/bounded-read gap exposed by scoped fix.** `src/context_graph/adapters/graph_ops.py:1028` reads all Event nodes, sorts them, and returns the oldest 10,000 before eligibility filtering in `api/routes/admin.py:254`. If those oldest nodes are retained but a later cold node is eligible, repeated calls inspect the same prefix and never reach it. `truncated=true` exposes a limit but supplies no continuation. Also the read itself is unbounded (`adapters/spanner/graph.py:282`). Keep deletion restricted to previewed IDs, but advance candidate scanning or filter eligible candidates before the cap. This does not invalidate the verified warm-score fix. Real-cloud boundary acceptance remains untested.

## Per-issue disposition

| Issue | Disposition |
|---|---|
| #4 | Planned; preappend pack payload validation still absent |
| #5 | Planned; authenticated trust binding still absent |
| #14 | Planned; startup recovery does not meet live retry contract |
| #15 | Scoped fix remains sound: Event timestamps require timezone and normalize UTC |
| #16 | Scoped fix remains sound: bounded gzip decode checks EOF, integrity and trailing data |
| #17 | Planned; source shape and shared boundary still absent |
| #19 | Planned; highest-priority data protection work, coordinated with #14 |
| #28 | Retain scoped single/batch readiness; streaming import failures remain unproved |
| #33 | Warm-score/bounded-deletion scope ready; scan progress/read bound outstanding |

No new regression established within these nine issues. Prerequisite #27's newly introduced legacy escape-marker reinterpretation remains a blocking regression from the earlier review; #26's acquisition-cancellation leak remains unresolved. Do not imply either was repaired here.

## Smallest coherent order and decisive tests

1. Resolve #27 legacy decoding policy before relying on payload round trips; repair #26 before cancellation/shutdown acceptance. Define #4/#5 together, then route #17 through that boundary while retaining #15/#16.
2. Coordinate #14/#19 immediately: test live fail-once recovery without restart, orphan reclaim after startup, poison entries ahead of healthy entries, and failed deferred flush containing multiple entries. Verify bounded retries across restarts and no duplicate buffered positions. Retention tests must cover unread/pending entries in each of five groups, absent cursors and old imported timestamps.
3. Finish #28 import proof: first/middle chunk failure, commit-response loss, preserved committed prefix, one outcome per input and duplicate-safe replay. This is an untested risk, not a newly proved bug.
4. Finish #33 with 10,001+ nodes, a retained oldest prefix, ties, missing scores, and preview/live ID agreement; prove eventual scan progress and bounded reads.

Verification: backend-neutral `test_ingress_time_and_gzip.py` and `test_admin_pruning_scores.py`: **11 passed** using the designated review venv. Prior cloud evidence was not rerun.
