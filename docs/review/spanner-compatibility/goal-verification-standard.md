# Required verification and stakeholder demonstration for every goal

## Scope decision — disposable experiments (2026-10-08)

Applies to every current goal: historical-data migration, migration adapters, conversion of old pack identities, and cross-version historical upgrade analysis/tests are OUT OF SCOPE. Do not spend implementation, review or analysis effort on them or use their absence as a completion blocker. Runs start with an explicitly owned disposable dataset. Priorities are ontology-pack composition and the actual Engram ingestion → ledger → workers/projection → Spanner graph → retrieval/evidence path.

Revision history, approvals, retries, ordering and recovery/replay of events created within the same experiment and pinned pack configuration remain functional tests. They are not historical migration. A fresh connected demo dataset must be created through Engram ingestion; retaining it for an approved demonstration does not add migration scope. Existing migration tickets/history are preserved as deferred future work; do not silently count their scenarios as passing or close them. A migration-only baseline case is explicitly deferred, not a current-goal sign-off requirement. Migration work requires a separate explicit future authorization.

Every goal requires its own verification document and a walkthrough for the stakeholder. Apply this standard to all goals in the small-goal inventory. A code summary, test count or successful ingestion receipt is insufficient. Documentation alone does not authorize execution.

## Before execution

Record the goal's exact scope, scenario IDs, inputs, expected observable outputs, forbidden effects, dependencies and completion conditions. Explain the business example in plain language. Define exact artifact identities, relationship directions, relevant property values, evidence and retrieval expectations before running; do not rewrite expectations merely to match observed behavior. Record changes to expectations and their reasons explicitly.

## Required contents of each verification document

1. Status and verdict: not run, in progress, failed, blocked or verified; distinguish technical verification from demonstration delivery. Date, issue links and remaining limitations.
2. What the stakeholder should learn: explain the user-facing outcome and the question the demonstration answers.
3. What changed: relevant implementation changes, why necessary, previous behavior and resulting behavior, linked code/review evidence. Separate pre-existing functionality from newly implemented behavior.
4. Reproduction: prerequisites, exact safe commands, fixture/source provenance and hashes, effective packs/capabilities, code/worktree fingerprint, real Spanner target, run IDs and provider substitutions. Never include secrets. State fixture setup and cleanup boundaries.
5. Scenario results: expected versus actual, pass/fail/blocked/not-run, evidence links and forbidden-effect checks. Preserve failed attempts and corrective reruns; do not substitute aggregate counts for cases.
6. A step-by-step trace for every scenario: source input → adapter output → authentication/tenant and admission decisions → API response → ledger → running workers → graph → retrieval. Show actual IDs, material field values, relationships/directions, supporting events and responses. Mark an inapplicable stage explicitly rather than inventing activity. Include the expected rejection stage and absence of writes for rejected inputs.
7. Processing details: enabled and disabled worker responsibilities; observed processing status, delays, retries, ordering and errors; why those observations match the declared behavior. Label inference separately from directly observed evidence.
8. Graph and answer explanation: a small before/after diagram or table where useful, exact artifact and relationship changes, retained history and evidence, and what was deliberately not created. Explain why the retrieved answer follows from the stored evidence.
9. Defects and review: issue links, review findings and dispositions, unresolved risks, untested scope and whether any manual intervention occurred. A required case needing manual repair cannot pass.
10. Demonstration walkthrough: ordered steps, commands or saved requests, what to show at each step, expected visible output, evidence fallback if live credentials are unavailable (clearly labeled recorded), and how to repeat safely.
11. GitHub issue reconciliation and feature-bucket assessment: identify every affected umbrella and sub-issue; link the actual GitHub updates and record status before/after, acceptance criteria satisfied, remaining acceptance and supporting run/review evidence. Distinguish partially advanced from fully verified; do not close an issue because one goal exercised only part of its scope. Update affected issue bodies/checklists or progress comments and umbrella summaries to match observed results, preserving failure history. Search for existing coverage before filing a newly confirmed defect or feature gap; create and link a new issue when needed, with concrete reproduction/expected behavior and acceptance criteria, and attach it to its owning umbrella. Document filing/update failures as pending work, not completed actions.
12. Assess whether discoveries warrant a separate feature bucket: explain whether the work fits an existing umbrella or represents a distinct outcome with separate acceptance, dependencies and scope. Record either the proposed new bucket and rationale or why no new bucket is needed. Do not invent buckets simply to reorganize existing tickets or silently expand the current goal. If a genuinely distinct bucket is needed, create a clearly proposed tracking umbrella with links, explicitly unstarted; implementation still requires user selection. Present all scope/dependency changes in the stakeholder walkthrough.

## Completion and handoff

Rerun all required scenarios on the final code/configuration through actual Engram on real Spanner. Required cases must pass; local/component tests supplement that evidence. Missing evidence, blocked/partial cases, mocked Spanner or bypassed stages cannot establish end-to-end completion. Resolve relevant review findings and align issue/run records.

Present the stakeholder walkthrough at the end of each goal, explaining what entered Engram, what happened internally, what emerged and why it is correct. Clearly distinguish a delivered recorded walkthrough from an executed live demonstration. A verified implementation with the walkthrough still pending must report that pending deliverable; do not claim the entire goal delivered. Stakeholder sign-off, if given, is recorded separately and never inferred from silence. Do not proceed to the next goal without the user's instruction.

Include the ticket reconciliation table and feature-bucket assessment in that walkthrough. Goal delivery requires actual GitHub synchronization for affected issues, not just a local list of intended updates. No issue or bucket is presumed resolved or created without a linked recorded action.
