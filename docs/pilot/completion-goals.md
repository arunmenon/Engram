# Controlled pilot completion goals

Approved by Arun on 16 October 2026: execute P01–P12 autonomously, with checkpoint reporting and no per-goal acknowledgement wait. These IDs are bounded pilot milestones, not a resumption of the retired broad #34/#41 native goal. Continuation06 is the active execution at approval.

Current checkpoint: P01–P05 are complete with bounded evidence and Astra acceptance. P06 is complete as an Astra-accepted bounded composite proof, with both failed attempts retained. P07 is complete with Astra acceptance; P08 is in preparation and P09–P12 remain queued. P04 retains one verified stale-action dead letter; subsequent runs must explicitly admit that proof-backed negative before startup. See [the verification walkthrough](completion-verification.md) for actual results, retained failures and limitations. The historical approval context below is not a current run status.

## Purpose and current evidence

Finish a reproducible two-tenant pilot: A uses Core+User+Memory; B uses Core+PDLC+Memory. All business inputs and acceptance reads go through the authenticated Engram public API, real workers and retained Spanner databases. Snapshots support diagnosis and preservation checks; they do not replace API acceptance.

Already established selected evidence: entry06; planning in spectrum01; connected queries in continuation02; incident38-input family in continuation04. Failed overall attempts stay failed. Catalog reached28inputs before continuation05's unsupported edge-property expectation; #69 fixes ticket fixture namespaces and #70 reconciles skipped-test contracts. Continuation06 is the current retry, not yet a pass.

Existing targets: A `engram-assess-1010a-pdlc`; B `engram-g07-target`. Keep exact tenant ownership, source data and prior Episode memberships. Actual `gpt-6-luna`, no artificial model-call/spend ceiling. Approved derived Summary/importance refresh remains recorded separately. No historical migration, hierarchy authorization (#49), ANN/load benchmark (#48), forced-crash guarantee or remote cohort deployment enters this scope.

## Approved execution agreement

Execute P01–P12 in order without requesting approval after every goal. Reuse a goal's completed evidence from the active run where its exact acceptance criteria are satisfied; rerun affected checks only when changes or failures require it. Do not reset databases or repeatedly rerun unrelated completed journey families.

For each goal: freeze concrete inputs/questions and expected/forbidden results before execution; implement only necessary bounded corrections; run through real API/workers/Spanner/read APIs; review applicable code and final evidence with Astra, reusing unchanged prior reviews; append a goal section to the verification walkthrough; reconcile affected GitHub issues; commit and push to `feature/engram-memory-episodes`. Report a checkpoint without waiting for acknowledgement before the next approved goal.

A failed expectation remains failed. Investigate and correct a demonstrated defect or a source-grounded oracle error, retain the original attempt, review the correction and rerun. Do not silently rewrite questions, use returned answers as expectations or count component tests as pilot journey proof. A requirement outside this approved batch or an external permission/credential/user-policy dependency requires a clear blocker report. Continue independent work that remains possible.

Each goal finishes with a stakeholder-readable demo section: what we sent, what Engram accepted, what applicable workers produced, what was saved, what the public read returned, expected versus actual, source/receipt evidence, preservation, exact repeat command/source revision, remaining limitations and issue dispositions. Engineering execution can finish without the stakeholder attending synchronously; the final stakeholder walkthrough and independent human reproduction keep their own explicit statuses.

## Ordered goals

### P01 — Complete the PDLC event catalog

Objective: finish the frozen161-input catalog, including requests, decisions, ticket/PR lifecycles, commits, skipped/finished tests, releases, deployments, rollbacks, placeholders, duplicate/conflict and malformed-input cases. Reuse continuation06 if it satisfies this goal.

Verify: every expected status, node property, directed link and forbidden output matches its predeclared oracle; exact accepted source membership and public receipt position resolve; skipped stays skipped; optional absent links stay absent; duplicate/rejected requests make no material writes. Produce per-scenario actual results and a catalog-only verdict. Related issues: #63, #69, #70; broader #39/#42/#41 remain open unless their complete scope is independently satisfied.

### P02 — Close the specific PDLC history gaps

Objective: add four bounded sequences to the completed planning/implementation evidence: (1) revise a requirement and show old work/test links remain attached to the original revision; (2) keep a model proposal distinct from an explicitly accepted engineering decision; (3) distinguish missing coverage, proposed coverage and an actual failed test; (4) connect a hotfix's explicit work, review/test and operational records.

Verify: exact version identities and links, lifecycle states and source evidence through public reads; no inferred link transfer, approval or successful verification. Existing connected/planning/incident records can provide prerequisites through their retained accepted Events; new business state is ingested normally.

### P03 — Finish diverse User journeys and correction

Objective: run the eight frozen User stories (coding, contexts, research, travel, work journal, household, paraphrase, absence). Add one explicit supported preference correction in a named context, preserving a second context, and one third-person attribution control.

Verify: correct owner and source quote, correct meaning/polarity, Python experience distinct from beginner Rust interest, context labels retained, correction/history correct, other owner's information excluded, and absence story creates no preference or commitment. Run two diagnostic questions for the incident/design-review contexts and one same-name Mercury project/planet example. Record which preference/Entity is actually returned and whether the interface supports disambiguation; a source-grounded unsupported result is a diagnostic verdict, not a pass for context selection. Returning both preferences does not prove selection.

### P04 — Verify Tenant A Memory lifecycle and scope

Objective: execute the frozen A Memory sequence, plus stale-confirmation refusal, agent-versus-session scope and another-owner controls. Include an ordinary progress Event while an existing Goal stays active, followed by its explicit completion action.

Verify: stated/inferred Beliefs and confidence are attributed assertions, confirmation/correction revisions and exact evidence are retained, stale actions leave Belief/Goal state unchanged, scope follows the documented contract, and progress alone never completes a Goal. Completion, abandonment and replacement remain distinct. Explicitly reuse one agent-scoped Goal across two sessions, with a second owner holding a similar Goal; verify identity continuity and owner exclusions. Include malformed/disabled-action controls relevant to A.

P04 source-grounded negative-case contract: a schema-valid stale action is accepted into the ledger (HTTP201), then projection records `memory_status=conflict`, `memory_reason=state_conflict` and an exact dead letter. It is not an HTTP409/no-ledger-write case. Freeze the expected failed delivery before sending it, prove the subject and its evidence unchanged, retain the audit Event and dead-letter record, and reject any unexpected pending/DLQ. Subsequent goals must explicitly preserve that verified negative-test record rather than delete it or silently ignore arbitrary dead letters. Malformed inputs remain admission rejections. Both pilot bindings enable Memory; disabled-pack runtime behavior must not be inferred from an enabled-binding test.

### P05 — Verify Tenant B Memory alongside PDLC

Objective: execute the frozen B Memory sequence; tie the narrative to PDLC through supporting Events, then send a merged PR/passing test while an existing delivery Goal stays active. Complete that Goal only with its explicit supported action; retain abandoned/replaced alternatives. Include a correction that does not explicitly assert contradiction.

Verify: Memory and PDLC records coexist and are publicly retrievable with their own sources; PDLC success creates no automatic Goal completion; the noncontradictory correction invents no contradiction; asserted contradiction remains separately tested. No automatic prose-to-Belief/Goal inference is claimed.

### P06 — Verify Episode history with late activity

Objective: on both tenants ingest two separated activity groups, then a late Event whose timestamp bridges them. Read before and after through the supported session/temporal flow.

Verify: exact memberships and declared grouping rules; the resulting snapshot cites the right source Events; earlier Episode identities and membership edges remain unchanged and inspectable. Include an unrelated session with overlapping wording as a negative control. Distinguish scoped recall from unsupported automatic cross-session discovery.

### P07 — Prove actual Summary meaning on both tenants

Objective: run all four frozen summary cases: A/B forward and inverse outcomes. The same vocabulary expresses different facts, such as investigation completed versus incomplete and rollout uncertain versus completed.

Verify: actual provider input contains the accepted source content/IDs; the stored Summary is the actual returned text; its meaning matches the independently declared outcome and uncertainty; public temporal reads return the Summary and exact Episode/source members. Missing/fallback text does not count as an actual-model quality pass.

### P08 — Verify retrieval discovery and bounded answers

Objective: retrieve selected retained knowledge by exact identity, ordinary wording and a paraphrase; compare a sufficient read budget with deliberately small node/depth budgets. Run a targeted Entity similarity query with actual embedding/vector-channel evidence.

Verify: relevant source-backed answers, unrelated controls excluded, exact versus wording discovery reported separately, truncation disclosed and returned edges/sources internally valid. Add nonexistent-claim reads on both tenants and a trusted-versus-untrusted source contrast, using explicit authenticated source grants and predeclared trust semantics. Demonstrate actual vector contribution rather than inferring it from a successful answer. If the supported interface cannot expose/provide that proof, report a concrete unresolved capability gate; ANN stress/performance remains #48.

### P09 — Verify two-tenant routing and identity collisions

Objective: ingest the same Event/session/actor and selected artifact identifiers into A and B with intentionally different content, plus a foreign-only positive control. Interleave writes and reads while both tenant runtimes are active. Try insufficient roles, spoofed routing/database hints and documented unsupported operations.

Verify: rightful positive reads work; no foreign data/evidence appears; authenticated binding controls the target; refused attempts leave both databases materially unchanged after unrelated work settles. Distinguish owner selection inside A from cross-tenant isolation. Existing verified isolation evidence remains separately referenced.

### P10 — Verify delayed work and visible failure

Objective: use labeled test barriers to delay Event projection before enrichment, and delay a Memory parent before its dependent action. For one marked A extraction request only, pass a known-invalid test credential to the real provider from the test observer; record the actual rejection and remove the override in finally. Keep the configured model/binding and all other provider calls unchanged; prove B remains usable. Stop/restart workers cooperatively with the current binding. Probe stale startup using the recorded predecessor binding from the model-transition evidence: require RuntimeFencedError before effects and unchanged owner/table fingerprints. Do not run the older isolation operator that advances TenantControl or introduce an owner transition solely for this probe.

Verify: pending work is visible, delayed prerequisites converge without lost annotations or duplicate observations, missing prerequisites follow documented bounded handling, failed provider work is not represented as successful extraction, unaffected tenant reads succeed, and completed writes remain stable after cooperative restart. Record exact supported recovery; no forced-crash/network-partition guarantee.

### P11 — Prove checkout reproduction and fixture extension

Objective: from a clean checkout at a pinned source revision, use only the published instructions to run one representative journey per tenant and a cross-tenant exclusion. Add one extra story via the documented JSON journey format without changing engine code solely for the test. Audit saved evidence in a fresh process.

Verify: prerequisites, roles, launch commands and manifests are sufficient; expected artifacts/evidence resolve; extension runs using existing machinery; no hidden worktree files or manual graph repair. A fresh agent/operator process proves technical reproduction only. An independent human/team run remains a separately labeled handoff milestone and must not be invented or silently waived.

### P12 — Publish the final demo, coverage and issue reconciliation

Objective: assemble the stakeholder walkthrough and update the HTML pilot chapter with actual outcomes, repeat commands and limitations. Map all25 A candidates,24 B candidates and18 shared probes to full proof, partial proof, unsupported/diagnostic behavior, external prerequisite or explicitly deferred scope.

Verify: every pass links exact source revision, inputs, public responses, relevant worker/source/Spanner evidence and retained failures; no input/assertion count masquerades as journey coverage. Astra reviews final evidence/completeness; artifact-quality-gate checks unsupported claims/assumptions and usability. Update affected sub-issues and umbrellas with evidence and remaining scope, create a new issue only for a concrete uncovered defect, and close only issues fully satisfied. Push everything to the one canonical branch. Publish separate verdicts for engineering checks, stakeholder demo delivery and independent human reproduction.

## Progress tracking

| Goal | Status | Evidence |
|---|---|---|
| P01 | Complete: bounded composite verdict; Astra accepted final evidence | [Verification](completion-verification.md); continuation06 remains failed; continuation07 passed243checks |
| P02 | Complete: Astra accepted composite history/coverage/hotfix/Decision proof; original runs stay failed | [Verification](completion-verification.md); runs02/03; #71/#73 closure reconciliation |
| P03 | Complete: Astra accepted diverse User stories and explicit correction with retained failed runs | [Verification](completion-verification.md); final retained-read checkpoint09 |
| P04 | Complete: 260 live checks; Astra accepted lifecycle, conflict and scope proof | [Verification](completion-verification.md); pilot-p04-1016-01 |
| P05 | Complete: 246 live checks; Astra accepted Memory/PDLC coexistence and retained-negative proof | [Verification](completion-verification.md); pilot-p05-1016-01 |
| P06 | Complete: Astra accepted bounded composite history proof; original01/02 remain failed | [Verification](completion-verification.md); run03 passed 271 retained-read checks over the original eight full-flow inputs |
| P07 | Complete: four actual-model contrasts,133 live checks; Astra accepted evidence | [Verification](completion-verification.md); pilot-p07-1016-01 |
| P08 | Prepared: nine frozen inputs, retrieval budget/vector/trust probes; launch review in progress | pilot-p08-1016-01-journeys.json |
| P09 | Approved; queued | This inventory |
| P10 | Approved; queued | This inventory |
| P11 | Approved; queued | This inventory |
| P12 | Approved; queued | This inventory |

Update each row with actual status, source/evidence links and issue disposition. Plan approval alone is not completion evidence.
