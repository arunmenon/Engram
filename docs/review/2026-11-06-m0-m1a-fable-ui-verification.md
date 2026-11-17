# Fable verification script: M0 baseline and M1a operator experience

Date: 2026-11-06. Repository: `/Users/arunmenon/projects/Engram`.
Review only. Do not implement fixes, edit product code, change expected answers, approve
packs, activate tenants, start M2, or call a live provider. Save an independent verdict.

## 1. Review contract and scope

Answer: **Can a domain-team operator understand an issue, explain their business rule,
review an agent-assisted request and choose a next action without an engineer translating
Engram terminology? Does the evidence justify the M0 and M1a completion claims?**

M0 is baseline preparation and evidence capture, not a new screen. Audit its evidence,
known gaps and honest presentation. Do not treat baseline usability failures as failures
to capture a baseline. M1a is explanation, clarification and safe request preparation;
it does not establish live agent reasoning or successful pack repair.

The current tree includes M1b backend context improvements. Record what you actually
review; do not claim you ran a frozen historical M1a build. Attribute those later context
changes to M1b. This UI pass uses controlled responses, not M1b's live provider.

Record branch, HEAD, dirty-file status, asset names/build timestamp, service capabilities,
draft IDs and revisions. Recorded branch/HEAD at handoff: feature/engram-walkthrough /
27b4ba8. Extensive uncommitted and untracked implementation exists; HEAD alone is not
its identity. Do not reset the tree to reproduce an old milestone.

Use computer use or headed Chrome with Playwright. Python Playwright is available at
`/tmp/engram-video-venv/bin/python`; native computer use was previously unavailable.
Say which you used. Run actual interactions; screenshots/source inspection alone do not
establish behavior. No subagents are required; if using previously authorized persona
agents, keep their task passes separate and record that they are simulated.

## 2. Start the UI safely

Verified listening at handoff; recheck before use:

| URL | Token file — fill directly, never print | Available scenarios |
|---|---|---|
| http://127.0.0.1:8102/workbench.html | `/tmp/engram-m1a-token` | `M1a — explanation review (fixture agent)`; `M1a — procurement recovery (fixture agent)` |
| http://127.0.0.1:8103/workbench.html | `/tmp/engram-m1a-domain-token` | `Delivery inline review`; `CRM inline review` |

Both report fixture agents and isolated-memory sandbox. Read `/admin/capabilities`
with the same token to confirm. Never print the Authorization header. Do not use port
8104 (live M1b) or ports 8101/5174 and `.workbench/drafts.sqlite3` for this exercise.
Do not restart or reconfigure live services to make this review pass.

8103 deliberately has an author that fails if invoked. Its capabilities say authoring
is available, but it cannot prove successful authoring. You may test preparation there;
for a send-failure test intercept the author endpoint or record its controlled failure.
8102 returns canned authoring output: do not count a successful fixture author as reasoning.

Some older study drafts are intentionally stale: `Delivery team — release review`,
`Procurement team — receipt matching`, and `Delivery send...`. Do not start there and
mistake deliberate failure state for a fresh case. Prefer the named inline-review drafts.
Procurement recovery has no executable pack; that is an expected scenario, not a success.

For mutation/race tests, use Fable-owned isolated copies. A reproducible setup command
is below; it creates three copies in the existing fixture store without touching original
drafts or running authoring. Run only after verifying the services above are fixture-only.
It deliberately does not copy review/approval/sandbox successes. If it reports stale
source or unavailable input, stop that setup and record the limitation; do not clear guards.

```bash
.venv/bin/python - <<'PY'
from copy import deepcopy
from pathlib import Path
from context_graph.workbench.store import Store
store = Store(Path('/tmp/engram-m1a-domain-study.sqlite3'))
rows = store.list('domain-study')
for source_name, suffix in [
    ('Delivery inline review', 'delivery'),
    ('CRM inline review', 'crm'),
    ('CRM inline review', 'save-race'),
]:
    name = 'Fable M0-M1a — ' + suffix
    if any(r['content']['name'] == name for r in rows):
        print(name, 'already exists; inspect its revision before reuse')
        continue
    source = next(r for r in rows if r['content']['name'] == source_name)
    assert not source.get('proposal_stale'), 'Source draft is stale'
    content = deepcopy(source['content'])
    content.update(name=name, environment='fable-isolated-ui-review', instruction='')
    draft = store.create('domain-study', content)
    draft['proposal'] = deepcopy(source['proposal'])
    draft = store.put('domain-study', draft, draft['revision'], 'seed-fable-fixture-copy')
    print(name, draft['id'], 'revision', draft['revision'])
PY
```

If these temporary services/files are gone, report setup blocked. Existing evidence is
still reviewable but must not be presented as your own fresh browser execution.

## 3. Uncoached persona task cards — do these before reading the detailed criteria

Use only rendered UI for task decisions in this pass. Do not inspect implementation
code, helper scripts, prior verdicts or API payloads to discover the next action. Record
where you hesitate and what additional help you need. This is an agent simulation,
not a human-comprehension study; do not fabricate human quotes or timings.

**Persona A: delivery lead.** You know release practices and CI, but not Engram's rule
names or graph syntax. Your team keeps failed test attempts visible even after a rerun
passes. Release decisions use the latest completed attempt for the same change.

Task: open the delivery review, understand the unresolved issue, communicate your policy,
inspect what would be sent, briefly visit supporting material and return. Decide whether
to send or leave it unresolved. Stop before sending in this first pass. Explain what,
if anything, has changed in the pack.

**Persona B: CRM operations owner.** You know contacts and account history, but not YAML
or node IDs. A contact can change email while retaining the same source-system contact
identifier and history.

Task: open the CRM review and do the same work using your own domain wording. Identify
whether the proposal has already adopted your policy or only contains your request.

For each pass record: task completed/partial/blocked, actual interactions/click count,
help needed, business wording you entered, technical terms you had to supply, unexpected
navigation, and confidence in what happens next. Do not score success because buttons work.

## 4. Detailed UI verification steps

Run these after the uncoached pass. Use fresh state or record any prior-task learning.
Screenshots should include the relevant action and result; pair them with behavior notes.

### UI-01 — Find the active issue and decide where to start

1. Open `Fable M0-M1a — delivery` (or the original inline review read-only).
2. Select `How Engram understands them`.
3. Locate `Review these items first`, the business-policy issue and `Your answer`.
4. Inspect the next-action banner, readiness disclosure and optional technical details.

Expected: the issue precedes the schema inventory; the answer box is available without
an explanation request. Missing setup and the current decision have an understandable
order. A zero count of recorded decisions must not imply no unresolved issues. Identifier
and state detail is collapsed initially. The page must not claim that missing samples
are already present. Record technical language that remains in the issue itself.

### UI-02 — Answer immediately and review in place

1. Type the persona's policy in your own words into `Your answer`.
2. Click `Review my request` without invoking Explain.
3. Read the resulting `Your request to the agent` panel and edit `Request to send`.
4. Verify the request is beside the issue, not at a distant authoring form.
5. Click `Review my request` again while the request contains text.

Expected: the business meaning is preserved, including exceptions and identity scope.
Preparing does not call `/explain`, `/author`, `/review`, `/sandbox` or `/approve`.
The existing request is not silently overwritten. No draft pack, expected answers,
review or approval is changed. The page labels this as your instruction, not a verified
agent interpretation or an applied correction. A request that merely repeats your words
must not be credited as proof of agent understanding.

### UI-03 — Optional help, grounding and uncertainty

1. On 8103, click `Explain this` once. No second click should be necessary to start.
2. Inspect the loading message, the returned business question, and whether you can answer.
3. Expand `Ask a different question` and submit a follow-up in business language.
4. On 8102, inspect `Explain problem 1` for the invalid setting; expand the supporting
   evidence and the exact proposed instruction. Click `Propose this change` but do not send.
5. On the procurement-recovery draft, explain the authoring failure without assuming a
   generated pack exists.

Expected: help is attached to the selected issue and distinguishes engine checks, source
material and agent-reported limitations. Unsupported/missing information produces a
concrete next question rather than an invented relationship. Evidence references should
support the claim; an ID that resolves is not sufficient semantic grounding. An available
instruction is inspectable/editable before explicit send. Ask: does this explain the
business consequence, or simply restate the failure in technical language?

All responses here are scripted. A follow-up may return the same canned answer. Record
that limitation; do not claim adaptive reasoning, retrieval relevance or live correction.
If engine-limit, conflicting-evidence or invalid-citation cases are not reachable in these
UI fixtures, mark those UI cases NOT EXERCISED and assess their backend tests separately.

### UI-04 — Material detour, deferral and deliberate discard

1. With an answer and prepared request, click `Add supporting material`.
2. Do not add anything yet. Click `Return to the question review`.
3. Confirm the answer, explanation (if requested), edits and prepared request remain.
4. Click `Leave unresolved`; read what it says about retained unsent work.
5. Click `Clear prepared request`.

Expected: same-revision navigation needs no repeat provider call. Deferral does not
submit, resolve or approve; it explains that any prepared request remains. Clear removes
only the prepared request, retaining the business answer. Do not infer persistence after
closing the tab: same-revision navigation and reload recovery are different promises.

### UI-05 — Saved evidence invalidates old explanations

Use only the `save-race` copy.
1. Obtain an explanation and prepare a request.
2. Add a clearly labelled synthetic policy note through the material screen, then save.
3. Return to review and inspect the draft revision, old explanation and available actions.
4. Check that an old instruction cannot be newly prepared from the obsolete answer.

Expected: the previous explanation is discarded/nonactionable; the page explains that
changed inputs require an updated proposal. Retained user-written request text must not
be described as freshly verified. Do not require all authoring to be disabled: authoring
is the path to update a stale proposal. Server revision checks must reject stale requests.
A source save by itself must not make the question resolved or approval ready.

### UI-06 — Failure, cancellation, reload and explicit send

Use controlled delayed/error responses or isolated fixtures; no live-provider outage.
Use the browser's actual controls for the operator steps.
1. Prepare a request, then start a delayed explanation. Click `Stop waiting`.
2. Deliver the late response; verify it never appears as a current answer.
3. Repeat with a provider error/timeout. Preserve request text and prior pack/review state.
4. Reload with unsent request text. Reauthenticate if needed; inspect and use
   `Restore what you typed?` / `Restore my input`. Confirm the request is restored.
5. On a dedicated copy, intercept `/author` with a controlled 503. Explicitly click
   `Send request to the agent`; verify one submission, visible failure and retained,
   editable request. Confirm deliberate retry is possible after the failure.

Expected: no automatic submission/retry, no false success, no discarded accepted pack,
no late answer displayed, and no claim that browser cancellation stopped remote work.
Explain text can be transient on reload; typed revision requests have a separate recovery
mechanism. Report whether the unsent **business answer before preparation** is recoverable;
do not assume it is covered by revision-request recovery.

Browser interception proves UI handling only. Use backend tests/source for actual
30-second total deadline, concurrency bounds, malformed output rejection, owner isolation,
and consent revocation. Do not substitute a fake 503 for a real backend timeout test.

### UI-07 — Consent, tenant boundaries and cross-domain neutrality

1. In a dedicated copy, set provider use to disallowed or redaction unconfirmed, save,
   and return to review. Confirm explanation/send cannot dispatch and the remedy is clear.
2. Switch delivery -> CRM -> delivery. Check that answers, requests and evidence do not
   leak into the other tenant. Sign out and verify sensitive transient context is cleared.
3. Repeat the normal task in CRM and inspect procurement recovery.

Expected: no consent bypass through a shortcut; cross-draft requests do not mix. These
are UI checks, not proof of backend credential isolation. Record incident-specific
placeholders, PDLC literals or policies imposed on another domain. Procurement recovery
must not imply a generated ontology or passed test exists.

### UI-08 — Keyboard and narrow-screen usability

Use Tab/Shift+Tab/Enter and a ~430px-wide viewport. Verify labels, visible focus, disabled
control explanations, reading order, status announcements and absence of horizontal
scrolling. Check whether a long request is readable/editable without losing context.
DOM accessibility inspection can assess roles/live regions; do not claim screen-reader
usability unless a screen reader was actually used. Record scrolling burden separately
from “no overflow.”

## 5. AI-native features to assess — current, not aspirational

| Implemented capability | What useful behavior looks like | Do not over-credit |
|---|---|---|
| Issue-specific explanation | Helps decide the next action using the selected saved problem and evidence | A generic explanation or matching citation IDs alone |
| Business-language clarification | Operator can supply policy and uncertainty without engine syntax | A visible text box alone |
| Grounded uncertainty | Specific missing decision/material; no invented business relationship | “More information needed” with no usable action |
| Explain-or-propose with explicit control | Inspectable instruction; edit/clear/send separated from acceptance | Preparing a request as if a pack change had been applied |
| Context continuity | Same-revision return retains work; changed evidence invalidates old answers | Treating stale context as current, or promising cross-tab persistence |
| Safe failure recovery | Clear failure, retained work, explicit next action and deliberate retry | Silent retries, stuck busy states, generic blame on user inputs |
| Domain-agnostic operation | Same interaction supports delivery and CRM; incomplete procurement is honest | Hardcoded policy, fixture realism mistaken for reusable reasoning |

Not delivered/proven by M1a: live-agent semantic correctness, autonomous pack repair,
agent tools/coding workspace, generated effect simulation for every answer, a new chat
platform, broad journey synthesis, tenant activation or a fully self-serve end-to-end
production onboarding service. M1b's later live repair cannot retroactively prove M1a
fixture reasoning. The request panel is explicitly an instruction preview, not an agent
interpretation preview.

## 6. Usability directives and verdict rules

For every major task answer these in plain language:
- **Purpose:** Can I tell why I am here and what decision is needed?
- **Domain fit:** Can I answer with knowledge of my team rather than Engram internals?
- **Helpfulness:** Did the agent reduce uncertainty or just rephrase the problem?
- **Consequence:** Can I tell what my answer may change and what is still unverified?
- **Control:** Can I distinguish answer, prepared request, submitted job, proposed pack,
  validation, acceptance and deployment? These are not interchangeable states.
- **Grounding:** Can I distinguish source quotations, operator input, engine checks,
  hypotheses and unknowns? Are citations readable and relevant?
- **Continuity:** Are edits retained, staleness honest and recovery discoverable?
- **Density:** Does optional detail stay optional? Count unnecessary clicks and long jumps.
- **Next action:** Is there one understandable next step, including when blocked?
- **Accessibility:** Can I complete the task with keyboard and at narrow width?

Do not give numeric scores without an anchored rubric. Use PASS / REVISE / BLOCKED /
NOT EXERCISED per task. Separate functional correctness from usability and live reasoning.
A provider fixture limitation is not automatically a UI defect, but it limits the claim.
Never average away data loss, unintended submission, consent bypass or stale-result use.

## 7. M0 evidence audit — after the uncoached UI pass

Read:
- `docs/ai-native-onboarding-milestone-plan.md` — later amendments supersede old prose.
- `output/playwright/ai-native-onboarding/M0/baseline-20261105/README.md` and manifest.
- `.../capability-probes.json`, `crm-workbench.json`, `crm-result.json`, `pytest.log`.
- `output/playwright/ai-native-onboarding/M0/personas/summary.md` and both persona reports.

Check these exact limits:
1. Baseline personas used the UI, but they are simulations, not recruited humans.
2. Historical PDLC 111 checks and Northstar success are not fresh current-engine passes.
3. CRM's copied contract adaptation covers two questions; three answer.reasons cases are
   outside that carrier. No independent expectation reviewer was recorded.
4. Procurement inputs exist; M0 did not establish a runnable procurement pack.
5. Seeded no-intent/relationship-free lookup can pass. Do not repeat “every question
   requires a domain relationship.” A missing named intent is a different case.
6. Old README headings say baseline “not yet run” even though later persona reports
   exist. Record documentation inconsistency and apply the stated chronology; do not
   invent evidence for any still-unexecuted cases.

My earlier chat statement “M0 complete” must be assessed against these qualifications,
not taken as an acceptance oracle. Say which deliverables are complete, partial or still
unverified, particularly independent fixture review and baseline task coverage.

## 8. Required output

Save your independent report to:
`docs/review/2026-11-06-m0-m1a-fable-ui-verification-result.md`
Save browser evidence to:
`output/playwright/ai-native-onboarding/fable-m0-m1a-20261106/`

Include:
1. Separate M0 and M1a verdicts, plus “safe request preparation” versus “self-serve
   issue resolution” verdicts. Do not collapse these into one claim.
2. Environment/build/draft identities; actual browser method; fixture/live labels.
3. Persona outcomes with actual action counts, hesitations and help required.
4. UI-01 through UI-08 results with screenshot/log links and unexecuted cases.
5. A prioritized finding table: severity, exact screen/control, observed behavior,
   operator consequence, smallest correction and meaningful recheck.
6. An AI-native assessment using section 5, including what still feels like a form
   wrapped around agent output rather than useful assistance.
7. M0 evidence/claim reconciliation, inherited versus introduced defects, and scope gaps.
8. Explicit decision: accept M1a, accept only a narrower claim, or request named changes.

Review without editing implementation. Do not invent findings to fill a quota, broaden
into a redesign, or claim the implementation agent's own review is independent evidence.
Stop when the script is assessed and the bounded verdict is written.
