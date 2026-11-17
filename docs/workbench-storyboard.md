# Workbench storyboard: telling the pack story to an operator

Status: proposal, 2026-11-02. Companion to `docs/review/2026-11-02-workbench-usability-review.md`. This document rewrites the copy and ordering of every workbench screen so that an operator with no Engram background can say, after each step, what they just did and why. No engine behaviour changes are assumed; where a line depends on a future capability (Spanner sandboxes, activation) it is marked **future**.

## 1. The story in one breath

Shown once, on the landing page, under the title:

> Engram answers questions about a tenant's world. A pack teaches it that world. Here you build a pack from the tenant's own documents and events, prove it with real examples, and hand it off.

## 2. Vocabulary rules

One word per concept, used identically in headings, buttons, banners and the glossary.

| Use | Instead of | Where the old word may still appear |
|---|---|---|
| tenant | tenant | Use throughout; define at first use. Use tenant draft for an unprovisioned workspace. |
| pack | model (domain), ontology pack | Explain ontology in the glossary; use "selected packs" for a composed bundle |
| the assistant | the model, author, gpt-5.2, provider | Provider name in a tooltip on the permission control |
| story | journey, fixture, scenario, test | Never in operator-facing copy |
| test / test results | proof | Keep checks, answer scoring and approval distinct; explain sandbox as an isolated test environment |
| understanding | proposal, proposed model | Never |
| example events | samples | Never |
| trusted producer | trusted source, source trust | Never |
| hand off / approve | approve exact revision, artifact | "Revision" shown as a number only |

Digests, revisions, engine hashes and file paths are never in the primary reading line. They live under a disclosure titled **For engineers**.

## 3. Landing page

Current: "Control plane / Tenant workspaces / Give each ontology a clear purpose and a traceable source."

New:

```
Tenants
Engram answers questions about a tenant's world. A pack teaches it that world.
Here you build a pack from the tenant's own documents and events, prove it
with real examples, and hand it off.

[ Start a new tenant ]

See how a finished pack behaves
Software delivery (PDLC) is a complete pack with prepared stories you can run
without building anything. Pick a story to watch Engram answer it.

  Was this requirement implemented, reviewed and tested?        [Run story]
  Did design approval carry across revisions?                   [Run story]
  Which deployment shipped this change?                         [Run story]
  Where does a reference stop being trustworthy?                [Run story]

  More stories about answering questions ▸   (the 13 retrieval scenarios, each
  renamed to its question, under one disclosure)

Your tenants
  [card] Northstar checkout incidents · development
         Pack understood · 2 questions · not yet proved
```

Card status line uses five phrases only: *Needs documents*, *Pack understood*, *Proved*, *Needs attention*, *Approved for handoff*.

Empty state keeps the existing sentence, it is the best in the product: "Your first tenant starts with a draft. Add a domain goal, then bring the documents and events that describe it."

## 4. Prepared story page

Current eyebrow "PDLC · PREPARED JOURNEY" and heading "From requirement to reviewed and tested change".

New:

```
SOFTWARE DELIVERY · PREPARED STORY
Was this requirement implemented, reviewed and tested?

What happens in this story
A password-reset requirement is written, designed, ticketed, implemented in a
pull request, reviewed twice, and tested until it passes. Along the way an
unrelated feature reuses the same ticket and PR numbers, an event is delivered
twice, and four malformed events arrive. Engram must keep the two features
apart and leave the graph unchanged by retries and bad input.

23 events · 111 things to check · runs on an isolated copy

[ Run story ]

For engineers ▸  (sources, frozen pack digest, coverage of original assertions)
```

Result block:

```
Story result: 110 passed · 1 needs attention

Needs attention
  Event 19 reused an event ID with different content.
  Engram treated it as a duplicate. The story expected it to be refused as a
  conflict.
  Why it matters: a producer that resends an ID with new content must not
  silently overwrite or be silently ignored.
  Details ▸  (expected / observed JSON)
```

Timeline keeps its current design. Rename "Event checkpoint" to "Step", "Observed handling: created" to "Engram stored this event", and "Observed · stored domain relationships" to "What Engram knows after this step".

The "What this journey covers, and what stays in the test suite" panel moves under **For engineers**.

Rules: the eyebrow ("SOFTWARE DELIVERY") is the pack's display name read from the pack, never a literal in the page, so a second domain's stories are labelled correctly. Counts in the summary line come from the story file, not from prose.

## 5. Step 1: Tenant setup

Current: "Tenant setup / What should this tenant track, and what data may we use?"

New:

```
1 · Tenant setup
Describe their world in a few sentences, and tell us what we may do with their material.

What should the pack cover?
[ Track checkout incidents from detection through postmortem. Exclude on-call scheduling. ]
Say what is in and what is out. The assistant uses this to avoid inventing concepts.

Reuse an existing pack ▸
  Software delivery (PDLC): requirements, changes, reviews, tests, deployments.
  Memory: lets Engram summarise and forget over time.   (future: one line each)
  User: lets Engram remember who people are across sessions.

Before anything is sent to the assistant
  May the assistant read this tenant's material?
    ( ) Not yet, keep everything local
    (•) Yes, send it to the assistant   ⓘ provider: gpt-5.2
  [ ] I removed secrets and personal data from everything I will add.
```

Readiness strip (replaces the three tiers' "Unsaved"):

```
Ready to build a pack ○   Ready to prove it ○   Ready to hand off ○
```

Hover or expand shows what is missing, in the same voice: "Add at least one document or set of events."

## 6. Step 2: What describes their world?

Current: "Tenant evidence / Give the assistant the material it needs."

New:

```
2 · What describes their world?
Documents tell us the concepts. Schemas tell us the fields. Real events tell
us what actually happens. Any order is fine; events are what make the pack
testable.

You have: concepts ✓  fields ✓  events —      Add events to make this pack provable.

Add material
  What is it?   (•) A document or glossary  ( ) A schema (JSON)  ( ) Example events (JSON)
  Name          [ Incident process, section 2 ]
  Contents      [ paste or choose a file: .txt .md .json, up to 40,000 characters ]
                [ Insert an example event ]   ← inserts a template envelope
  [ Add ]

Material added (3)
  Incident process (synthetic)            document
  PagerDuty webhook schema (synthetic)    schema
  Redacted incident events (synthetic)    8 events · 1 expected to be refused
```

Rules: the form stays open after Add; the confirmation line appears inside the list, not as a page banner, and disappears on the next keystroke. The sample envelope fields are never shown as fine print.

## 7. Step 3: How Engram now understands them

Current: "Proposed model / Build, discuss and review the model in one place."

New, before the assistant has run:

```
3 · How Engram understands this tenant
Ask the assistant to read the material and propose a pack. You will review
what it understood, where it got each idea, and what it is unsure about.

Anything the assistant should pay attention to? (optional)
[ Keep US and EU incidents separate. ]
[ Build the pack ]      Uses 3 pieces of material. Takes a few minutes.
```

After the assistant has run, in this order:

```
In plain words
  An Incident is identified by its region and number. It starts open and
  moves through mitigated, resolved and closed. It affects Services and
  Merchants, and may have one Postmortem.
  (generated from the pack: one sentence per type, one per lifecycle, one per
  relationship)

[ schema graph ]

Where this came from · 7 statements
  Incident numbers repeat across regions, so region is part of the identity.
    From "Incident process (synthetic)": "Incident numbers are assigned per
    region, so INC-1042 in the US and INC-1042 in the EU are different incidents."
    [ That's wrong ]
  ...

What the assistant is unsure about · 2 questions
  Should incident.closed and incident.reopened be stored without updating the graph
  until we have reviewed mappings for them?
    If yes: valid events use ledger-only handling: stored without graph updates.
    Unsupported handling is different: the event is refused.
    If no: they are removed from the pack.
    [ answer ]
  ...
  Answers are applied by the assistant in one pass. [ Apply answers ]

What the assistant changed or could not do · 3 notes
  Removed Incident.severity because it could not find an accepted number type.
    ⚠ This drops tenant data. [ Keep severity as a whole number ]  [ Accept ]

Engram's check   ✓ This pack loads and all 8 example events are handled as expected.
                 ✗ Engram refused this pack: Incident.severity has an unknown type
                   "number". Accepted types: text, string, int, float, bool,
                   datetime and json; lists use list<scalar>, enums use {enum: [values]}.   [ Ask the assistant to fix it ]

[ I have reviewed this understanding. Continue to questions ]

Ask for a change ▸
  [ Explain the change you need. ]  [ Send to the assistant ]
  History ▸

Under the hood ▸   (types, contracts, mappings, planned writes; becomes a
                     named sub-step "3b · Under the hood" in the sidebar)
```

Rules: the two standing questions about identity and lifecycle become part of "What the assistant is unsure about" only when the assistant actually asks them. Typing an answer queues an "Apply answers" revision. Unapplied answers are visibly pending and block testing and approval; applying them invalidates prior review and test evidence. Do not treat pending decisions as already implemented. A repair that removes a property is presented as a choice, never applied silently.

More rules for this step:
- Typed text is never lost. Every textarea keeps its own local state while the job poll runs and while a save is in flight; recovery is scoped to the signed-in operator and draft, with an explicit retention/clear policy and no stored access token. A conflict or reload offers "Restore what you typed"; recovery never silently overwrites server state.
- Work in progress is always visible. While the assistant runs, the page shows "The assistant is reading 3 pieces of material · started 2 min ago" with the attempt number, whether the job was started here or elsewhere; the page polls whenever the server reports a running job, not only when this tab started it.
- A failed job says what failed. The server logs the exception type and a redacted message, and the page shows "The assistant could not finish: {reason}. [Try again] [Send the details to an engineer]" instead of a generic error.
- The valid property types (text, string, int, float, bool, datetime, json; lists use list<scalar>, enums use {enum: [values]}) are in the assistant's instructions as well as in the error text, to reduce avoidable retries; this does not guarantee the assistant succeeds on its first attempt.
- Relationships render once, as "Incident affects Service", never with doubled arrows.
- The pack version is shown as "draft revision 16"; the semantic version only appears at approval, bumped once according to the change class.
- A revision conflict shows what differs before anything is discarded: "Someone saved revision 17 while you were editing. Keep my answers / Take the saved version".
- Reopening a tenant lands on the step the operator left, named in the card ("continue at Prove it").

## 8. Step 4: Questions to answer

Current: "Expected results / Choose the answers and graph behavior that would make this model correct."

New:

```
4 · Questions to answer
Write the questions in the tenant's words and pick the right answers from
the example events. These examples test whether Engram returns the expected answers.

Question 1
  [ Which services were affected by incident INC-1042 in the US? ]
  Right answers:  card-auth ×  checkout-web ×  wallet ×   [ pick from examples ]
  Starting from:  Incident US INC-1042
  [ ] I checked these answers against the tenant's material
  Details for engineers ▸  (intent, node type, raw ids)

[ Add a question ]

What must exist after the example events run
  Incident US INC-1042 ×   Incident EU INC-1042 ×   Postmortem US INC-1042 ×
  Must not exist: Incident INC-bad ×
  [ ] I checked this list before running

Who do we believe?
  Choose which producers this test trusts. The pack’s retrieval rules determine
  how untrusted evidence is used; corroborated or explicitly requested evidence
  may still appear. This grants no production access.
  [x] pagerduty   [x] confluence
  [ ] I understand how trust affects the answers
```

## 9. Step 5: Prove it

Current: "Test the model / Fresh in-process memory stores → event ledger → projection worker → graph → retrieval."

New:

```
5 · Prove it with examples
Engram replays the tenant's 8 example events and answers your 2 questions,
through the real processing pipeline in an isolated in-memory sandbox.
This does not test a deployed service or live database.
Today: an in-memory copy.   future: "on sandbox database 2 of 5" with slot state.

[ Run the proof ]

Report card · revision 16
  ✓ Which services were affected by INC-1042 in the US?   expected 3 · got 3
  ✗ Which merchants did EU INC-1050 affect?               expected 1 · got 0
      Engram found no Merchant linked to this incident. The incident.opened
      rule writes merchants only when the list is non-empty; check the example
      event and the mapping under the hood.
  ✓ Everything that must exist, exists.  ✓ Nothing forbidden was created.
  Overall: needs attention · average answer score (F1): {mean_f1}% · required {min_f1}%
  The score compares which answers were returned, not just how many.
  Missing/forbidden entities and processing failures also block approval.

  [ Ask the assistant about this failure ]

What Engram knows after each event ▸   (timeline with the stored graph)
Limits of this proof ▸                  (memory only, no live database, time and size caps)
```

## 10. Step 6: Approve and hand off

Current: "Review and handoff / Approve an exact artifact. Activation remains separate."

New:

```
6 · Approve and hand off
Approval freezes this pack, its material, its questions and this proof as
one reviewed package. Nothing changes in production.

This package
  Pack: northstar_checkout_incidents 1.0 · 4 types · 7 events · 2 questions
  Proof: passed on revision 16, today
  Change since last approved version: first version
  For engineers ▸  (digests, engine revision, YAML)

What happens next
  An operator activates this pack for the tenant in a separate step.
  Engram may start accepting the tenant's events before its questions are
  ready to answer; that becomes ready once real data has been checked.
  (future: activation request and status appear here)

[ Approve this package ]      [ Download the package ]
History ▸
```

## 11. Next-action banner and readiness copy

The banner is the operator's narrator. Its lines, in order of the flow:

1. Describe the tenant and say what we may do with their material.
2. Add the documents, schema and example events that describe their world.
3. Ask the assistant to build the pack.
4. Answer what the assistant is unsure about, then apply the answers.
5. Review Engram's understanding and continue.
6. Write the tenant's questions and pick the right answers.
7. Run the proof.
8. Fix what needs attention, or approve the package.

Readiness tiers: *Ready to build*, *Ready to prove*, *Ready to hand off*. Each missing item is a sentence in the same voice as the banner.

## 12. Glossary (one screen, linked from every page as "What do these words mean?")

- **Tenant**: an isolated Engram environment with its own data and pack configuration. One customer may have several tenants, such as development and production. A tenant draft does not provision or activate that environment.
- **Pack**: the description of a tenant's world: the kinds of things in it, how they are identified, how they change, and what events say about them.
- **Event**: a report that something happened, sent by one of the tenant's systems.
- **Producer**: the system that sends events. The pack’s trust rules govern how their evidence is used in answers.
- **Graph**: what Engram knows: things and the relationships between them, built from events.
- **Understanding**: the assistant's proposed pack, with the source of every idea.
- **Story**: a prepared sequence of events plus what should be true afterwards.
- **Proof**: running example events and questions against a pack on an isolated copy.
- **Report card**: the result of a proof, question by question.
- **Approval**: freezing a pack and its proof as one reviewed package for handoff.
- **Activation**: a separate operational step that puts an approved pack to work for a tenant.
- **Under the hood**: the engineer's view of a pack: types, contracts, mappings and planned writes.

## 13. Failure sentence templates

Every check kind gets one template. Examples:

| Check | Sentence |
|---|---|
| duplicate vs conflict | "Event N reused an event ID with different content. Engram treated it as {observed}. The story expected {expected}." |
| contract refusal | "Event N was refused: {field} is {problem}. The story expected it to be {expected}." |
| missing node | "After event N, {label} should exist but does not." |
| forbidden node | "After event N, {label} exists but must not." |
| missing edge | "{from} should be linked to {to} by {relationship}, but is not." |
| retrieval miss | "For \"{question}\", Engram answered {got} and should have answered {expected}." |
| unsupported | "This check only runs in a deployed environment and was skipped here." |

## 14. Order of work

1. Existing text replacements first, preserving actual controls and semantics. Generated summaries, dynamic display metadata, sidebar changes and new failure actions are behavior changes, not copy-only work.
2. Behaviour fixes the story depends on, from the usability review:
   - material form stays open after Add and the confirmation clears on the next edit (finding 15);
   - textareas never drop input during polls or saves, with browser autosave and restore (20, 29c);
   - "Apply answers" and "Send to the assistant" are never left disabled by a stuck busy state, and show why when disabled (21);
   - decision answers are applied by the assistant in one revision instead of marking the pack stale (29a);
   - a repair that removes a property becomes an operator choice (29b);
   - the accepted property-type list goes into the authoring prompt and the error text (22);
   - job failures are logged server-side with a redacted reason and shown as a sentence (23);
   - running jobs are visible regardless of which tab started them (24);
   - failed checks and proof results are rendered from the sentence templates in section 13 (7, 32);
   - doubled relationship arrow (26), climbing version number (28), reopen on the last step (29d).
3. Spanner sandbox pool, so step 5 can say "on a sandbox database" and show the slot (usability review, product gap).
4. Activation status on step 6.

## 15. Traceability to the usability review

Every finding in `docs/review/2026-11-02-workbench-usability-review.md` maps to a section here.

| Finding | Storyboard section |
|---|---|
| 1, 2, 3, 4 landing vocabulary, jargon, scenario names, empty state | 2, 3 |
| 5, 6, 7, 8, 9 prepared story page | 4, 13, 14.1 |
| 10, 11, 12, 13 tenant setup, two meanings of "model", packs, Unsaved | 5, 11 |
| 14, 15, 16, 17 material form | 6, 14.2 |
| 18, 19, 25, 27, 29 understanding step, decisions, explain mode, counts, under the hood | 7 |
| 20, 21, 22, 23, 24, 26, 28, 29a, 29b, 29c, 29d defects | 7 rules, 14.2 |
| 30, 31, 32 questions and trust | 8, 9 |
| 33, 34 proof wording, not verified | 9, 14.3 |
| 35, 36, 37 handoff placeholders, activation sentence | 10, 14.4 |
| Product gap and Spanner sandbox requirement | 9 (future lines), 14.3 |

The video walkthrough review (`docs/review/2026-11-02-video-walkthrough-review.md`) is not merged here because it concerns the recording plan. Two of its corrections should use this storyboard's wording when the script is rewritten: the memory-sandbox sentence (its C2) becomes the step 5 sentence in section 9, and the prepared journeys in its chapter 3 take the story names from section 3.


## 16. Implementation objectives and acceptance

Active goal scope: milestones M1–M6 below. Spanner pooling and activation remain separately scoped follow-ups; this goal does not provision infrastructure or change live tenant configuration. Recording waits for the revised video script/storyboard approval.

| Milestone | Findings / scope | Acceptance | State |
| --- | --- | --- | --- |
| M1 Accuracy and traceability | All section 15 findings; correct handling, trust, mean F1 and runtime claims | Each finding mapped to copy, behavior or deferred infrastructure with a truthful expected outcome | Complete: corrections and acceptance mapped |
| M2 Operator copy | 1–6, 8–14, 16–19, 25, 27, 29, 30–31, 35–37 | Purpose and next action visible; technical detail optional; no invented runtime capability; navigation covers technical inspection | Complete; see final audit below |
| M3 Editing and jobs | 15, 20–21, 23–24, 29c–29d | Input survives polling/saving; conflicts offer explicit choices; progress and safe errors visible; reopen restores step; recovery scoped and cleared appropriately | Complete; see final audit below |
| M4 Assistant review | 22, 28, 29a–29b | Correct property vocabulary; decisions applied together; pending answers block approval; removed data requires review; release version distinct from draft revision | Complete; see final audit below |
| M5 Results | 7, 9, 26, 32–34 | Human-readable supported failure kinds, truthful fallback, mean-F1/identity correctness, stored graph context and visible limits | Complete; see final audit below |
| M6 Verification | All implemented findings | Focused automated checks plus computer-use PDLC and real-provider incident walkthrough; preserve expectations and record failures, stale state and recovery | Complete; see final audit below |
| Deferred infrastructure | Product gap / section 14.3–4 | Separate Spanner pool and activation design/authorization; no live capability implied by current copy | Not part of this goal |

Acceptance refinements: unresolved decisions and destructive repairs block approval; equal expected/returned counts do not mean correct answers; unsupported reasons must reflect the actual reason rather than always claiming deployment is required. A story may begin with a saved graph rather than events. Tenant drafts do not imply deployed tenants, and multiple packs can serve one tenant. Technical details remain available when they affect an operator decision.


### Implementation evidence current local session

Initial slice only; the overall goal is not complete. Current UI has tenant/pack/story headings, question-based prepared-story entry points, the 3b technical sidebar, and accurate in-memory/mean-F1 result wording. Editing reconciles late responses with newer typed input, polls saved drafts for externally started jobs, and offers explicit conflict and operator/draft-scoped tab-session recovery. Requests have a 30-second browser timeout so a lost connection cannot leave the busy state indefinitely. Source add remains open.

Browser evidence: a separate synthetic editing-verification draft retained unsaved scope across polling; reopening after reload restored the evidence step and offered recovery; explicit Restore recovered unfinished source name/text. Screenshot: `output/workbench/usability/recovery-restored.png`. The existing Northstar draft was not edited. Live two-tab conflict and external-job acceptance remain to be exercised.

Checks: 2 Node edit-reconciliation/recovery tests passed; standalone workbench build passed; 35 workbench/backend journey tests passed; scoped Ruff passed. Backend now supplies the engine's actual scalar vocabulary plus list/enum syntax to the assistant, and logs a safe failure category and correlation reference without raw provider exceptions. A regression test verifies timeout feedback and secret-free logs. Backend changes have not yet been loaded into the currently running dev service.

Still required: full storyboard ordering, glossary and coverage completion; pending-answer/repair review behavior and version treatment; complete failure sentences and domain metadata; browser conflict/jobs verification; real-provider onboarding and final PDLC runs; video-plan synchronization. No Spanner provisioning, activation or recording occurred.


### Second slice progress 2026-11-03

Pending decision answers now have an explicit server flag and block review, sandbox execution and approval until one assistant revision applies them. New server tests exercise direct API bypass attempts. Proposed removals of declared nodes, edges, properties, lifecycle states, events and intents are retained across model repair attempts and later revisions, and require explicit operator acceptance. The operator can instead prepare a request to restore the data. Removal coverage does not yet classify every projection-expression change; those still require ordinary pack/mapping review. Assistant retries keep the draft pack version stable.

The UI now keeps decision fields visible while typing, shows pack-derived identity/lifecycle text before the graph, puts sources before limitations, provides a glossary, and explains every current story-check family without placing JSON in the primary reading line. Unsupported and error outcomes are distinct. PDLC implementation rerun through the browser retained 110 passing checks and the original duplicate-versus-conflict failure. The failure's headline and explanation now state that discrepancy without claiming an observed HTTP response. Evidence: `output/workbench/usability/pdlc-failure-readable.png`.

The backend was refreshed locally with the existing settings and draft store after confirming no jobs were running. A second browser tab correctly discovered a real assistant job started in the first (`external-job-visible.png`). A real-provider synthetic incident exercise has supplied process text, schema, events, identity/lifecycle decisions and a question through the UI. Its first generation failed proposal validation; inputs and job history remained intact. Diagnostic categories were refined, and one bounded retry is underway. This is not yet a successful onboarding acceptance result.

During that exercise, a source-add reconciliation defect was found and fixed: submitted additions must be merged relative to the local state at request start, not the modified submitted payload. A regression test and two successful browser source additions verify the correction. Current focused frontend checks: 5 passing. Current full scoped backend run before the diagnostic refinement: 37 passing; diagnostic refinement subsequently passed all 13 workbench tests. Builds and Ruff pass. Final broad acceptance remains pending.


### Autonomous follow-through

Spanner integration is now an explicitly queued execution goal, not an optional follow-up. See `docs/workbench-execution-goals.md`. Finish the current UI acceptance, then register and pursue the Spanner pool goal without requiring another start request. Production activation and video recording retain their separate gates.

### Third slice acceptance 2026-11-03

The real-provider incident exercise has now completed its UI sandbox flow. Draft `f2845ca3-d663-4780-abf4-df6e28367ddd`, revision 22, uses the assistant-generated `incident_ops` pack. The unresolved-decision contract was clarified after the model repeated previously answered questions with new identifiers; the next revision returned no outstanding questions. Four omissions from earlier repair attempts were explicitly reviewed: custom source/state/state_changed_at fields and the superseded incident_timeline intent. Lifecycle state uses the core status fields and the final intent is incident_status. Remaining assistant limitations stay visible; this is not a claim that arbitrary missing-title opened events are handled correctly.

Through the browser, the operator selected the incident by its readable account/ID/title label as both the expected answer and required graph entity, reviewed expectations and ran the examples. Two events were admitted; the malformed opened event was rejected as payload_invalid. The resolved snapshot retained “Payments outage” and showed status resolved. Mean F1 was 1.0 against the reviewed 0.8 threshold, with an exact entity match. Evidence is in `output/workbench/usability/incident-acceptance.json` and `incident-sandbox-passed.png`. This ran through the real in-memory processing pipeline, not Spanner, a deployed API or production activation. Approval/handoff has not yet been exercised.

The two-tab editing exercise also completed: an external save produced an explicit conflict without replacing local text, Keep my changes preserved it, and saving against the latest revision persisted the chosen content. Evidence: `two-tab-conflict.png`; the tenant card subsequently displayed the retained local scope. Recovery and external-job screenshots above cover separate checks.

Follow-up code hardening clears omission acceptances when the operator chooses to keep the data. Partial malformed model sections no longer crash the omission inventory before the validator can request a repair. Focused regression cases cover malformed sections. The five frontend logic tests, standalone production build and scoped Ruff passed after these edits. The scoped backend suite passed 41 tests and mypy passed all 14 workbench files. The remaining requirement-by-requirement audit is still pending. Actual attempt-number progress, persistent resume across new tabs, all removal semantics, keyboard/responsive verification and final PDLC rerun need reconciliation before M6 can be marked complete.

### Fourth slice acceptance 2026-11-03

The synthetic incident package was approved through the UI at revision 23. The handoff screen now describes activation as a separate procedure rather than showing placeholder deployment-status badges; the artifact digest is under an engineer disclosure. Screenshot: `output/workbench/usability/approval-resume.png`. No activation occurred.

Tenant cards now name the last visited step, and opening the incident draft in a fresh authenticated browser tab landed directly on Approve and hand off. Only the numeric navigation step persists across tabs, scoped by operator and draft; source text and unsaved edits remain in tab-session recovery. Invalid stored steps fall back to the first screen. Six frontend logic checks and the production build pass. The upload label explicitly lists text/Markdown/JSON and excludes PDF.

Authoring now reports each actual model attempt through the existing revision-fenced job record. The UI can show the reported attempt without inventing progress. A targeted API test observes the attempt through a separate GET and verifies cancellation remains terminal; the model repair test observes attempts 1 and 2. Existing author test doubles were updated for the optional progress callback, preserving their assertions. These backend changes still need loading into the local service and final browser verification. Mypy and Ruff pass; the scoped regression suite passes 42 tests. The remaining browser verification and completion audit are pending.

### Goal 1 completion audit

The following supersedes the historical “pending” notes above. It closes the workbench usability scope, not the queued Spanner work or the engine's known PDLC discrepancy.

| Requirement / review findings | Current evidence and disposition |
| --- | --- |
| M1; all finding groups in section 15 | Copy and behavioral findings are implemented below; the explicit Spanner product gap remains Goal 2. Activation and recording retain separate scope/gates. |
| M2; 1–4, 10–14, 16–19, 25, 27, 29–31 | Tenant/pack/story language, question-based story choices, six steps plus 3b, glossary, next action/readiness, input format guidance and sample insertion are in Workbench/OperatorFlow. The incident walkthrough exercised setup, supplied sources, decisions, readable entity selection and trust. Standing identity/lifecycle fields are explicitly operator policies, distinct from assistant questions. |
| M2/M5; 5–9, 26, 32–33, 35–37 | Prepared stories expose readable check outcomes and pack versions; JSON/digests are disclosures. Selected graph records now show labeled fields. Mean F1 and exact entity match are distinct from counts. Approval has no placeholder deployment badges. Chrome checked the rendered PDLC failure, incident report and handoff. |
| M3; 15, 20–21, 23–24, 29c–29d | Late-response/source-add reconciliation and recovery tests pass. Browser evidence covers retained source inputs, externally started jobs, two-tab conflict resolution and fresh-tab resume. Cards show the resume destination. Only numeric step metadata persists across tabs; drafts/credentials do not move to localStorage. Job errors are categorized and correlated without raw secrets. Actual attempt progress uses the existing revision fence; API regression observes it and cancels terminally. |
| M4; 22, 28, 29a–29b | Engine type vocabulary is supplied to authoring and safe diagnostic text. Tests preserve draft pack version across repair, retain removed declarations and block acceptance until reviewed. Pending answers block review/sandbox/approval. Real-provider revision applied operator decisions; omissions were explicitly reviewed before the browser test. Removal detection covers declarations (types, properties, states, events, intents); it does not replace normal review of changed mapping expressions. |
| M5/M6; 7, 32–34 | Final incident artifact revision 27 approved after refreshed-engine revalidation and rerun: two admitted, one malformed rejected, title retained on resolution, exact expected entity, mean F1 1.0 / threshold 0.8. The independent expected answer was not regenerated to match the model. `incident-final.json` captures evidence. |
| M6; frozen PDLC and honest failure reporting | Final saved PDLC run revision 10: 110 passed, 1 failed, 0 unsupported, 0 errors. Event 19 still reports duplicate where the frozen story expects conflict. The UI improvement goal requires preserving/reporting that failure, not changing engine semantics to remove it. `pdlc-final.json` captures evidence; no frozen pack/oracle edits were made. |
| M6; keyboard/responsive smoke | Chrome Enter opened the technical disclosure and selected a graph node. Tested narrow layouts measured 727 and 391 CSS pixels with document width equal to viewport width. Screenshots `pdlc-narrow-keyboard.png`, `pdlc-phone-layout.png`; viewport override reset. This is a focused smoke check, not formal accessibility certification. |
| M6; regression and documentation | 42 scoped backend/journey tests, 6 frontend logic tests, standalone production build, Ruff and mypy (14 files) pass. The final diagnostic-only wording edit additionally passed all 18 workbench tests. Video alignment below updated to actual rehearsal evidence; recording not started. |

Evidence directory: `output/workbench/usability/`. Browser screenshots include recovery-restored, external-job-visible, two-tab-conflict, incident-sandbox-passed and approval-resume. The local service was refreshed only after confirming no running jobs, using the existing private settings and draft database. Changes remain local and uncommitted; no production activation, cloud resource provisioning or video recording occurred in Goal 1.

Known limits carried forward: current sandbox is in memory; engine conflict behavior remains as reported; model explanations/limitations need operator judgment; new ontology semantics still require representative scenario coverage. These limits are not represented as passing production evidence.

### Spanner integration status — 2026-11-03

Goal 1 is complete; Goal 2 is now implemented locally but not live-Spanner accepted. The current source supports an explicit registered database pool, capacity reporting, exclusive run allocation, cleanup status and expired-run recovery. The local browser demonstration still uses isolated memory. Use `docs/workbench-execution-goals.md` for the requirement audit and `docs/runbooks/workbench-spanner-sandbox.md` for configuration. Do not narrate “on a sandbox database” as demonstrated until actual Spanner run evidence exists. Tenant activation and recording remain separately gated.
