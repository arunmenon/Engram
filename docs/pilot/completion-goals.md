# Controlled pilot completion goals

Draft for Arun's scope review, 16 October 2026. These IDs are pilot milestones, not replacements for the original G01–G18 inventory. Defining them does not activate new native goal tasks. The already-authorized continuation06 remains running.

## Purpose and current evidence

Finish a reproducible two-tenant pilot: A uses Core+User+Memory; B uses Core+PDLC+Memory. All business inputs and acceptance reads go through the authenticated Engram public API, real workers and retained Spanner databases. Snapshots support diagnosis and preservation checks; they do not replace API acceptance.

Already established selected evidence: entry06; planning in spectrum01; connected queries in continuation02; incident38-input family in continuation04. Failed overall attempts stay failed. Catalog reached28inputs before continuation05's unsupported edge-property expectation; #69 fixes ticket fixture namespaces and #70 reconciles skipped-test contracts. Continuation06 is the current retry, not yet a pass.

Existing targets: A `engram-assess-1010a-pdlc`; B `engram-g07-target`. Keep exact tenant ownership, source data and prior Episode memberships. Actual `gpt-6-luna`, no artificial model-call/spend ceiling. Approved derived Summary/importance refresh remains recorded separately. No historical migration, hierarchy authorization (#49), ANN/load benchmark (#48), forced-crash guarantee or remote cohort deployment enters this scope.

## Execution agreement to approve with this inventory

After batch approval, execute P01–P12 in order without requesting approval after every goal. Reuse a goal's completed evidence from the active run where its exact acceptance criteria are satisfied; rerun affected checks only when changes or failures require it. Do not reset databases or repeatedly rerun unrelated completed journey families.

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

Verify: correct owner and source quote, correct meaning/polarity, Python experience distinct from beginner Rust interest, context labels retained, correction/history correct, other owner's information excluded, and absence story creates no preference or commitment. Report automatic context selection and ambiguous-name behavior as separate observed capability/limitation; returning both preferences does not prove selection.

### P04 — Verify Tenant A Memory lifecycle and scope

Objective: execute the frozen A Memory sequence, plus stale-confirmation refusal, agent-versus-session scope and another-owner controls. Include an ordinary progress Event while an existing Goal stays active, followed by its explicit completion action.

Verify: stated/inferred Beliefs and confidence are attributed assertions, confirmation/correction revisions and exact evidence are retained, stale actions make no material writes, scope follows the documented contract, and progress alone never completes a Goal. Completion, abandonment and replacement remain distinct. Include malformed/disabled-action controls relevant to A.

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

Verify: relevant source-backed answers, unrelated controls excluded, exact versus wording discovery reported separately, truncation disclosed and returned edges/sources internally valid. Demonstrate actual vector contribution rather than inferring it from a successful answer. If the supported interface cannot expose/provide that proof, report a concrete unresolved capability gate; ANN stress/performance remains #48.

### P09 — Verify two-tenant routing and identity collisions

Objective: ingest the same Event/session/actor and selected artifact identifiers into A and B with intentionally different content, plus a foreign-only positive control. Interleave writes and reads while both tenant runtimes are active. Try insufficient roles, spoofed routing/database hints and documented unsupported operations.

Verify: rightful positive reads work; no foreign data/evidence appears; authenticated binding controls the target; refused attempts leave both databases materially unchanged after unrelated work settles. Distinguish owner selection inside A from cross-tenant isolation. Existing verified isolation evidence remains separately referenced.

### P10 — Verify delayed work and visible failure

Objective: use labeled test barriers to delay Event projection before enrichment, and delay a Memory parent before its dependent action. Separately use an isolated, predeclared real-provider failure and show the other tenant remains usable. Stop/restart workers cooperatively with the same binding; probe stale-generation refusal using existing guards.

Verify: pending work is visible, delayed prerequisites converge without lost annotations or duplicate observations, missing prerequisites follow documented bounded handling, failed provider work is not represented as successful extraction, unaffected tenant reads succeed, and completed writes remain stable after cooperative restart. Record exact supported recovery; no forced-crash/network-partition guarantee.

### P11 — Prove checkout reproduction and fixture extension

Objective: from a clean checkout at a pinned source revision, use only the published instructions to run one representative journey per tenant and a cross-tenant exclusion. Add one extra story via the documented JSON journey format without changing engine code solely for the test. Audit saved evidence in a fresh process.

Verify: prerequisites, roles, launch commands and manifests are sufficient; expected artifacts/evidence resolve; extension runs using existing machinery; no hidden worktree files or manual graph repair. A fresh agent/operator process proves technical reproduction only. An independent human/team run remains a separately labeled handoff milestone and must not be invented or silently waived.

### P12 — Publish the final demo, coverage and issue reconciliation

Objective: assemble the stakeholder walkthrough and update the HTML pilot chapter with actual outcomes, repeat commands and limitations. Map all25 A candidates,24 B candidates and18 shared probes to full proof, partial proof, unsupported/diagnostic behavior, external prerequisite or explicitly deferred scope.

Verify: every pass links exact source revision, inputs, public responses, relevant worker/source/Spanner evidence and retained failures; no input/assertion count masquerades as journey coverage. Astra reviews final evidence/completeness; artifact-quality-gate checks unsupported claims/assumptions and usability. Update affected sub-issues and umbrellas with evidence and remaining scope, create a new issue only for a concrete uncovered defect, and close only issues fully satisfied. Push everything to the one canonical branch. Publish separate verdicts for engineering checks, stakeholder demo delivery and independent human reproduction.

## Progress tracking

| Goal | Initial status | Evidence |
|---|---|---|
| P01 | Active work already authorized; continuation06 running | runs/pilot-1016-continuation-06 |
| P02–P12 | Draft scope awaiting batch review | This inventory |

Do not label a row complete from the plan alone. At execution, replace each grouped draft row with its own actual status, source/evidence links and issue disposition.
