# Controlled pilot completion: verification walkthrough

This is the checkpoint record for the [approved P01–P12 goals](completion-goals.md). Each goal records its own result. An input count is not a count of complete journeys, and a completed checkpoint is not acceptance of the whole pilot.

## P01 — PDLC catalog: complete, with a composite evidence verdict

### What this demonstrates

We send PDLC activity through the authenticated Engram write API, let the ordinary workers create the graph in retained Spanner, then ask Engram's public read API for the resulting artifacts and evidence. The catalog includes requests, decisions, tickets, pull requests, commits, tests, releases, deployments, rollbacks, malformed inputs and retries. A skipped test must remain skipped. An absent reference must not become an invented relationship.

This checkpoint uses two evidence records. It is **not** a claim that the original 161-input run passed unchanged.

The [per-type input crosswalk](../review/spanner-compatibility/runs/pilot-p01-1016-07/catalog-input-crosswalk.json) covers all 28 PDLC event types represented in the catalog. It links recorded scenarios and admission statuses to their original runs; projection, reads and preservation still depend on the full results below.

| Evidence | What actually happened | What it can establish |
|---|---|---|
| [Continuation06](../review/spanner-compatibility/runs/pilot-1016-continuation-06/results.json) | 157 catalog steps matched their individual checks; three intermediate reads passed. The next normalized input used a reserved native-webhook actor and was rejected. The overall run remains failed. | The recorded successful steps and intermediate states, with their individual source evidence. |
| [Selected continuation07](../review/spanner-compatibility/runs/pilot-p01-1016-07/results.json) | All 243 checks passed, including shutdown and preservation. Twelve requests produced nine new Events, two duplicates without material writes and one reserved-actor rejection without material writes. | The corrected normalized cases, explicit reserved-actor refusal and scoped reads, with final Astra review accepted. |

### What changed, and why

- **Ticket fixture identity (#69):** a slash prefix left a valid trailing Jira key in commit text. The fixture now uses a unique valid Jira key throughout, so its declared reference and the parser's reference identify the same ticket. The runtime parser was unchanged.
- **Skipped-test expectations (#70):** the old fixture expected properties that the pack did not declare on EXECUTES/RAN_AGAINST. Those unsupported property expectations were removed. Directed relationships, the declared commit SHA, artifact evidence and public source positions remain required.
- **Normalized input actor (#72):** independently authored normalized HTTP Events now use an ordinary producer actor. They do not claim native-webhook authority. A separate reserved-actor request must still be rejected with no material writes.

### Reads and their limits

The fresh verification graph has ten artifacts. Starting from its Change returns the nine explicitly linked artifacts; starting from its TestCase also reaches the no-reference TestRun, for ten. These are separate checks: sharing a test case does not create a missing Change relationship.

The thirteen retained catalog reads include an additional TestCase-scoped check. The earlier mixed graph lacks two normalized records that were never admitted, so its expected retained identities remain explicitly partial. The seedless request/spec question searches the retained dataset; it is checked against an independently constructed eligibility set and directed REFINES links, rather than being presented as an empty-database three-node result. Exact identity checks are recorded separately.

### Final conservation and review

1. All worker tasks finished; all 166 observed provider invocations returned; shutdown reported no errors. The invocation count includes consolidation of retained sessions and is not a count of catalog scenarios.
2. Exact ledger append and receipt/source checks passed. Tenant A appended no Events; B appended precisely the nine accepted unique Events.
3. Prior ledger records, tenant owners, material graph content and exact old Episode membership remained intact. Permitted Summary/importance refresh is recorded separately. Both pending-delivery and dead-letter sets ended empty.
4. All 176 recorded execution-source hashes match commit `1536ed0` in the [source audit](../review/spanner-compatibility/runs/pilot-p01-1016-07/recorded-source-audit.json).
5. Astra accepted the final composite evidence with no technical blocker. The bounded fixture issues #69, #70 and #72 are closed; #63 and broader #34/#39/#41/#42 remain open. Actual comments and reread states are in the [GitHub reconciliation](../review/spanner-compatibility/runs/pilot-p01-1016-07/github-reconciliation.json).

### Reproduction

Continuation07 executed source commit `1536ed0` on `feature/engram-memory-episodes`. Its [manifest](../review/spanner-compatibility/runs/pilot-p01-1016-07/reproduction-manifest.json) records the executed source hashes. The [frozen selected plan](pilot-p01-1016-07-journeys.json) contains the inputs and read expectations; it has no P02 business inputs.

Use a clean checkout of the recorded source and satisfy the credentials, model and binding prerequisites in the [team instructions](team-walkthrough.md). Stop competing workers. Inspect a fresh retained baseline, choose a new run ID/output directory, generate fresh fixture identities, then invoke `engram_pilot_first_run.py` with `--journeys-only` and that selected journey file. Reusing old Event identities tests retries rather than reproducing fresh creation. Do not reset a database or insert artifacts directly.

This establishes a technical verification record. A stakeholder walkthrough and an independent human reproduction remain separate deliverables.


## P02 — PDLC history: first attempt failed; corrected rerun prepared

The first attempt sent eleven accepted inputs through the real flows. At H09, extraction applied but the expected proposed VERIFIES edge was absent. The [failed result](../review/spanner-compatibility/runs/pilot-p02-1016-01/results.json) stays failed; later hotfix inputs and final queries were not reached. All171observed provider invocations returned, shutdown was clean and final source/owner/material graph/oldEpisode preservation checks passed, with empty pending/DLQ. Those operational results do not repair the missing business relationship.

The candidate list is capped at30. The worker filled it by searching artifact types alphabetically. A [deterministic reconstruction](../review/spanner-compatibility/runs/pilot-p02-1016-01/candidate-reconstruction.json), using the saved baseline plus admitted projections and the original committed worker method, found11DesignElements,13Requirements and6Specs; the fresh Requirement was offered but its explicitly named TestCase was absent. This is source-grounded reconstruction, not a captured original provider prompt. The actual provider output proposed a Constraint, a Decision and a link to a historical DesignElement, not the required coverage link.

Issue[#73](https://github.com/arunmenon/Engram/issues/73), under#63, tracks candidate starvation. The fix offers existing registry-valid endpoint IDs explicitly named in the source before lexical fill. It keeps the same30candidate ceiling, type/key eligibility, persistence checks, trust and model-output validation. It creates no relationship by itself. The exact proposed-VERIFIES expectation remains unchanged.

Astra accepted the bounded implementation;38targetedtests,ruff andmypy passed. The regression uses35historical matchingDesignElements and checks the actual worker prompt, both fresh endpoints, the candidate bound and rejection of a nonexistent endpoint. The [corrected reconstruction](../review/spanner-compatibility/runs/pilot-p02-1016-01/candidate-reconstruction-corrected.json) now offers both endpoints. The new live run must still demonstrate an actual model proposal, saved edge/source evidence and public retrieval. Full fresh pack prompts are captured for that run. #71and#73 remain open.
