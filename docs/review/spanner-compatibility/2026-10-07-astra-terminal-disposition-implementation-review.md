# Terminal disposition implementation and harness review

Astra low implementation review against medium design: scoped approval, no blocking findings. Source-only; reviewer ran no tests/cloud or edits. Bound ACK/DLQ validate current control, pending consumer/full position, ledger position, receipt and content inside the same retrying transaction. Batch ACK validates every present member before deletion. Repeated dispositions follow documented no-op rules. Bound DLQ metadata comes from validated authority. Exhausted-retry control refusals stop before DLQ metrics or later deliveries. Same-consumer-name lease ambiguity and atomicity of prior graph writes remain outside this slice.

Local `20261007-local-terminal-disposition-02`:251tests passed,2warnings; scoped mypy4files and selected Ruff passed. First failed attempt retained: obsolete bareappendtest corrected to use authenticated append, import order and3readmode typing issues corrected.

Harness review found P2: a fixed count7 might not exceed configurable retry threshold. Resolved: compare persisted deliverycount with constructed consumer threshold, then assert an instrumented process_message was never entered. The harness now compares DLQ acceptance exactly to the original receipt. Astra recheck: P2 resolved; bounded harness approved pending executor evidence.

Local `20261007-local-terminal-harness-02`:46tests passed,Ruffclean. Prior46passingtestattempt retained with7loopbindinglint failures; closures corrected before rerun.

Cloud phase covers mutation after an earlier processingread, not a forced concurrent transaction-race schedule. Exact oneevent/16groups cleanup, schema/owner/source preservation. Cloud results tracked separately. No baseline promotion, publication or Spanner sign-off.

## Real Spanner execution

`20261007-cloud-terminal-disposition-01`:54/54 scoped checks passed. Repeated12four-worker receipt refusal cases and12restored pending ACK recoveries. Four terminal faults (missing receipt, unknown engine contract, changed payload, missing document) injected after a successful processingread each refused direct ACK and DLQ, and actual retry-exhausted consumer disposal. Persisted count exceeded actual retry threshold and normal processing was never entered. Restoring original content permitted valid DLQ; authoritative metadata and exact original acceptance were verified, then repeated DLQ and absent-pending ACK preserved that committed disposition.

One owned event/16groups removed by exact keys. All7application-table fingerprints, existing schema, owner(activeepoch5) and runtime sourcehashes preserved. Redacted execution/intents/results retained in the run directory. This proves the mutation-between-read-and-terminal window, not a forced simultaneous transaction race. Local transactionretry tests separately simulate control/content changes on retry. No baseline promotion, issue closure, publication or full Spanner sign-off.
