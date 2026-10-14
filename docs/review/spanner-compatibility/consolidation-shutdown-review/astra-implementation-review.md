# Independent #60 implementation / pre-cloud review

2026-10-14. **Source direction accepted; correct the two proof gaps below before cloud reset.** Read-only inspection of the ConsolidationConsumer diff, nine local lifecycle cases and the draft real-Spanner runner. No tests or cloud execution performed by this review.

## Production source

No concrete source blocker found. The parent waits without propagating cancellation into children, sets cooperative stop when either completes, retains one gather future and shields it through repeated cancellation. Both child outcomes are inspected after drain. Fencing takes precedence over other child failures, which take precedence over parent cancellation; this is an explicit acceptable policy. The timer wakes via the stop event, and its timeout cancels only the event waiter. Ordinary cycle exceptions retain the previous logged/swallowed policy. No storage or BaseConsumer redesign is introduced.

Local cases exercise stop during synchronous work, one/three parent cancellations, long sleeping timer, repeated/pre-run stop, ordinary/fenced SDK-boundary failure, and ordinary/fenced subscription failure. These reference-storage/thread fixtures are appropriately separate from live Spanner proof.

## Correct before cloud

1. **SS02's promptness oracle is ineffective.** The manifest fixes the timer interval at five seconds, but the assertion permits stop to take almost ten seconds. A timer that simply finishes its full five-second sleep can pass. Require an elapsed bound comfortably below five seconds, or use an independently configured long interval for SS02 and a correspondingly small stop bound. Preserve no-cycle evidence.

2. **Successful later cycles can inherit their exact graph from SS01.** SS03 and SS06 only require the first gated transaction to commit, all tracked calls to return, and the final graph identities/evidence to exist. Those summaries already exist after SS01, so this does not independently prove that cancellation/subscription failure allowed the remainder of the admitted cycle to run. Extend SDKGate's records to capture Summary mutation identities for each successfully returned transaction, and require the three expected Summary IDs on every successful admitted cycle. Record commit outcomes, not just scheduled mutations from an aborted SDK retry. Current `scheduled_summary_ids` records only the first gated write. Exact final state remains necessary as a separate check.

## Narrow oracle tightening

`exact_graph` currently discards edge endpoint labels and checks Summary scope/count/nonempty content, but not scope_id/time_range. Validate labels, expected Summary scope IDs/range, actual Event source owner/session/occurred_at, and Episode owner/range against the two submitted fixtures. This is a small extension of the declared exact graph contract, not a new feature. If exact scripted summary content is asserted, apply it only to episode/session scopes; agent summaries currently use the existing deterministic producer.

## Safety assessment

The transaction gate is inside the actual SDK callback after Summary mutation scheduling, so it reproduces the relevant uncancellable synchronous-work boundary. Baseline reads occur before holding the transaction, avoiding the obvious snapshot-behind-write-lock deadlock. The 30-second gate watchdog raises a failing operation rather than pretending work drained. Cleanup releases gates and cooperatively joins workers before closing stores; no external consolidation lock is used. Expected cancellation/fence outcomes are observed before their task is removed from generic cleanup.

Keep same-database verified export/owner fencing, failed evidence retention and post-process fingerprints. The final full-table no-write observation is only authoritative after all other writing workers are joined. Controlled callback/subscription fences are not actual tenant revocation, and healthy task cancellation support is not process-kill or direct-child-cancellation safety. No wider scope is needed.

## Corrected pre-cloud recheck

2026-10-14 — **Go for the bounded cloud run once the in-progress targeted checks pass.** Rechecked the corrected runner; no remaining concrete blocker found. SS02 now requires less than three seconds against a five-second timer. SDK evidence deep-copies snapshots, resets its write set for each actual callback attempt, and records Summary commits only after run_in_transaction returns successfully. SS01/03/06/07 each require exactly the three expected committed Summary identities/scopes, preventing previous-cycle state from satisfying the whole-cycle proof. Failed attempts are separately retained.

The exact graph check now validates typed edges, Summary scope IDs/ranges and applicable scripted content, both Event identities/owners/keywords, Episode bounds and source membership, and bound ontology metadata. No undeclared Episode agent property is assumed. Source shutdown behavior and safe export/reset conditions remain as reviewed; final acceptance requires actual run records and post-process retention verification.
