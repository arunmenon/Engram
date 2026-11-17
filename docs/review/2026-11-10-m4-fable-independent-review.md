# M4 failed-check guidance and story coverage: independent review

## Verdict

**M4 does not yet pass its bounded scope.** The safety boundaries hold: explanation is consent-gated,
read-only, pinned to the selected check and refuses stale results; reruns keep deliberate failures;
tampered or missing pack snapshots fail closed. Three items must change before M5:

1. **M4-1.** Several vacuous assertions are accepted, pass, and are reported as "Passing check" with no
   flag. M4 acceptance says vacuous negative checks cannot count as proof.
2. **M4-2.** After a follow-up brief is submitted, its unreviewed text is treated as the existing story's
   reviewed specification. The missing-specification warning disappears and the text is sent to the agent
   as source evidence.
3. **M4-3.** The main view never says what differed. Expected and observed values appear only as JSON
   under "For engineers".

All three are small. A focused recheck of those three is enough. Nine lower findings are listed and do
not block.

Fixture agent and fixture story author only. Nothing here is evidence of live reasoning, Spanner
execution, self-serve readiness or human comprehension. M0, the remaining M2b items, the M3 lows and M6
stay open.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent review. Not the implementer. No fixes made. |
| Date | 2026-11-13, Asia/Kolkata |
| Prior familiarity | I reviewed M0 to M3 of this workbench. I did the operator tasks in the browser before reading the M4 implementation report or code; I had read the fixture service script to start my own. Simulated persona, not human comprehension. |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Frontend bundle | `workbench-COwj1mXB.js`, sha256 60c08773…, `workbench-CqPRbaYs.css`. All 13 file hashes and the snapshot hash match the implementer manifest. |
| Engine revision | sha256:774e129b…, loaded by my service; equals the manifest |
| Service | http://127.0.0.1:8118/workbench.html, operators `fable-m4-review` and `fable-m4-other`, own SQLite store. The implementer's 8117 was not running and was not used. |
| Agent and storage | Fixture explainer with adversarial modes; fixture outline and variant author that calls the real `validate_variant`; real isolated-memory ingest, projection and retrieval. No provider or Spanner. |
| Browser | Headed Google Chrome through Python Playwright, 1440×1000 and 430×932, default zoom |
| Credentials | Generated and read inside scripts; never printed or passed through tool arguments |
| Evidence | `output/playwright/ai-native-onboarding/fable-m4-20261113/` |

### Reviewer-owned copies

All seeded from `M4/review-20261110/final/copies-start.json`. Names carry the prefix "Fable M4".

| Copy | Draft ID | Source | Revisions | Why it moved |
|---|---|---|---|---|
| Support passing story | e14a2dff | 8440195a | 2 → 2 | |
| Support investigation story | 84e0fbf5 | c545df6e | 2 → 11 | Consent, outline, rerun, two generations |
| CRM story checks | 65620dca | fe8ac759 | 2 → 2 | |
| Support identity change | f27fc666 | c545df6e | 2 → 24 | Deliberate story, engine and pack identity changes; reruns |
| Support assertion probes | 2b932507 | c545df6e | 2 → 3 | Consent only; 30 explain probes left it unchanged |
| Support replacement during call | cfed6ee0 | c545df6e | 2 → 5 | Consent, one rerun during an explanation |
| Fable follow-up variant | 6f2be30b | Created by the product from the investigation copy | 2 → 4 | Saved after per-check review, then run |

Events, expected values and pack snapshots equal the start snapshot on every seeded copy. The identity
copy differs only in one check description that I edited on purpose. Outcomes after every rerun are
unchanged: pass, fail, pass, pass, fail, unsupported, pass.

## Operator tasks

### 1. Passing story against investigation story

What I could tell without help: the investigation story has two failures, one unsupported check and one
pass flagged as weak. Each has a different "Where to inspect" label: graph or mapping (title), answer
scope (wrong account), unsupported (scalar total), uncertain plus a weak-proof warning (missing endpoint).
Each says the mismatch alone does not show which side is wrong, and that no domain specification is
attached.

Where I needed help: I could not say what the title should have been or what it was, nor which answer
was expected and which was found, without opening "For engineers" and reading JSON (M4-3). On the weak
pass, the one sentence that matters comes last, after generic inspect and rerun text (M4-7).

### 2. Ask about one failure

| Probe | Result |
|---|---|
| Before consent | Button disabled with adjacent reason; API 403 |
| After explicit permission | 200. Context holds exactly the selected check, its recorded result, the checkpoint event, that event's projection rules, the guidance and the specification slot. No other check leaked. |
| Final-graph question | Context says no single event is attributed; carries the intent's pinned retrieval settings |
| Repair instruction, repair options, extra field, invented or missing evidence reference, engine-limit kind, explainer error | 502 each; draft unchanged |
| Index 99, negative, a passed check, the weak passed check | 422 each |
| Old or future revision | 409 |
| Other operator: read, explain, run | 404 each; list shows only their own draft |
| No token | 401 |
| Rerun started during a 4 s explanation | Explanation returns 409, never the old evidence. Second explain on the same draft 429. Explain works again after the rerun. |
| Timeout | 504 after 6 s, then 200 |
| Stale result | 422 "Rerun the current pinned story before explaining an old result"; no Explain buttons shown |
| After 30 probes | Story, result, snapshot and revision identical |

Limit: a prose claim that cites a valid reference passes through, even if it asserts a cause or tells
the operator to change the expectation. It cannot change anything and is labelled "Agent explanation ·
not a verified diagnosis", but the server cannot stop an agent from asserting a cause in words. This
needs live-agent evaluation, not a fixture.

### 3. Checkpoint graph, follow-up, rerun, CRM

- Graph: step selector changes the observed handling and stored records. Nodes are keyboard reachable
  with labels, and selecting one shows its fields as text. "Inspect event 1" moves focus to the timeline.
- Follow-up: clicking a coverage gap appends "Also cover: …" to my typed situation, keeps my typed rule,
  focuses the brief and sends nothing. A second gap appends again.
- Outline: disabled until the brief's own consent tick. Double click produced one call.
- Generation: disabled until the outline is reviewed. A generated empty property check was refused by the
  real validator. A valid variant produced one review tick per check; Save stayed disabled with one
  check unreviewed; the API refused a partial accept with 409. Double click created one new workspace,
  unreviewed-by-run, with the parent story untouched. Typed material survived a reload.
- Rerun: double click sent one run. Failures stayed failures.
- CRM: 13 of 13 pass, and the coverage list still shows 13 gaps, including "Deal: crm.deal.won → won — No
  check" with one delivery. The question is labelled "Reviewed incident answer"; that label comes from
  the shared test helper, not the product.

### 4. Coverage

| State | Seen as |
|---|---|
| No check | "No check", with "An event appearing in the story does not verify this behavior" |
| Defined, not executed (including unsupported) | "Defined · not executed" |
| Executed, not passing | "Executed · inspect outcome" |
| Passing | "Passing check" |
| Stale | "Stale result", on every row and check |
| Weak proof | "Review assertion strength" with the reason |

Search is case-insensitive and filters correctly. Built-in root terms ("core", "follows") return nothing.
"Every defined check" lists all seven. The list expands in groups of eight. The header says this is an
inventory, not a completeness score, and that state assertions are not guard coverage.

### 5. Pinned identity changes

| Change on the isolated copy | Result |
|---|---|
| Story edited after the run | Card "Run needs refreshing"; banner; all rows stale; explain 422; rerun restores fresh results with the same outcomes |
| Result from another engine revision | Same |
| Domain pack snapshot altered | Stale plus "The pinned pack could not be verified. Coverage is incomplete". Rerun fails; no result is produced. |
| Parent `core` pack given a newer version in the snapshot | Refused the same way; nothing newer is loaded |
| Snapshot removed | "Journey pack digest differs from the frozen bundles"; run fails |
| Original snapshot restored | Runs again with the same outcomes |

### 6. Assertion strength

Rejected by the validator: new empty property check; relationship checks with impossible endpoint types,
positive and negative; undeclared edge type; undeclared node type; wrong key shape. Flagged as weak:
absent relationship with a missing endpoint; evidence-absence on a missing record; a question with no
assertions; a historical presence-only property check, which is accepted unchanged, passes and is flagged
rather than rewritten.

Not caught: see M4-1.

## Findings

### M4-1, Medium, blocking: vacuous assertions reported as "Passing check"

Each of these is accepted by `validate_variant`, passes in the real runner and gets coverage status
`passing` with no warning (`vacuity-matrix.json`):

| Assertion | Why it proves nothing |
|---|---|
| `node_absent` for `Incident:nobody|NONE` | No event could create it. The equivalent relationship case is flagged. |
| `retrieval` whose only assertion forbids `Incident:nobody|NONE` | Forbids something that cannot be returned |
| `property_absent` for a field the type does not declare | Always true |
| `evaluation` with a wrong expected answer and `min_f1: 0` | Any answer passes. The question row reads "Passing check". |
| `properties` asserting only `node_type` or only the key field | True for any record with that identity |

Correction: flag these through the existing weak-proof warning so they read "Review assertion strength";
refuse or flag a zero threshold. Do not rewrite existing expectations. Verify with the matrix script.

### M4-2, Medium, blocking: a follow-up brief becomes the story's reviewed specification

Reproduction on the investigation copy: type a rule into "Domain rules and expected behaviour" and
propose an outline. Afterwards the failed title check no longer says "No reviewed domain specification
is attached", and the explain context carries `specification: "Reviewer typed rule: a resolved incident
stays resolved unless support reopens it."` as kind `source` (`p5.json`). That text was typed for a
different, not yet generated story and has not been reviewed against this one.

Correction: take the specification only from the story's own origin, not from the workspace's pending
brief; keep the missing-specification warning otherwise. Verify the warning and the evidence slot stay
unchanged after proposing an outline.

### M4-3, Medium, blocking: the difference is only in JSON

Title check main view: "an entity is missing or its recorded fields differ from the expected values."
The values ("A different reviewed title" against "Payments outage") are under "For engineers · expected
and observed evidence". The wrong-account check says "Compare missing and unexpected answers" and shows
neither outside JSON. The M4 exit asks that a failing story be understandable with linked observed
evidence.

Correction: one plain line per failed check, for example "Expected title: A different reviewed title.
Recorded: Payments outage." and "Expected: Incident other-account / INC-1042. Found: Incident payments /
INC-1042." Keep the JSON where it is.

### Lower findings

| ID | Severity | Finding | Smallest correction |
|---|---|---|---|
| M4-4 | Low | A rerun on an unverifiable pack fails with "The returned proposal did not meet the required format or pack checks", which describes authoring, not a story run. The earlier result leaves the screen; the record keeps it but nothing shows it, although the guidance says to keep the prior result as historical evidence. "Run story" stays enabled. | Story-specific failure text; show or link the previous result; disable Run with the pack reason. |
| M4-5 | Low | Coverage row text runs together ("No checkrejection scenario"). Rejection and question rows always say "0 matching event deliveries", including a passing rejection scenario. "An event appearing in the story…" also shows on rows whose event never appears. | Separator; omit the count where it is not computed; conditional sentence. |
| M4-6 | Low | `incident.opened` reads "Passing check" although a property check at that checkpoint failed. Failed property checks and checks without a checkpoint appear only in the collapsed "Every defined check". | Attach checkpoint checks to their event row, or say so on the row. |
| M4-7 | Low | Three boilerplate paragraphs repeat on every check. On the weak pass the warning comes last, after "Where to inspect: uncertain" and rerun text that do not apply. | State the boundary once per story; lead a weak pass with its warning. |
| M4-8 | Low | Focus stays on the page body after an explanation arrives, after an outline completes and after saving a variant. Disabled "Explain this check" has no `aria-describedby`, though the reason is adjacent. | Move focus to the result heading; associate the reason. |
| M4-9 | Low | After "Save permission for explanations" the panel disappears. Nothing shows that permission is on or how to withdraw it. | Show the saved state with a way to change it. |
| M4-10 | Low | Story errors say "Your pack is unchanged" and "The proposal changed; ask again". | Story wording. |
| M4-11 | Low | "Explain this check" and "Inspect event 1" are both primary buttons in one card. | One primary action. |
| M4-12 | Low | Generated expectations are reviewed as raw JSON, and a refused generation gives no reason. Inherited from the authoring form. | Carry to the language work already open. |

## Other checks

- **Keyboard:** every control reached in a sensible order with a visible 3px ring; graph nodes focusable.
- **430px:** no horizontal overflow, collapsed or fully expanded. The page is 5,090px tall collapsed.
- **Single submission:** outline, generate, save and run each fired once on double click.
- **Tenant cards:** immediate click after sign-in, double click after returning to the list, and keyboard
  Enter each opened the right story. No navigation regression seen.
- **Tests:** 187 workbench unit, 9 story-inspection, 18 frontend helper tests pass.

Not exercised: screen reader, contrast, reload during a running explanation, sign-out clearing, legacy
restore, cancel of a story run, live agent, Spanner.

## Verdicts

| Area | Verdict | Scope |
|---|---|---|
| Functionality | Revise | Consent, read-only explanation, pinning, staleness, rerun and per-check review pass. M4-1 and M4-2 open. |
| Visual clarity | Revise | Distinct guidance and honest coverage states; M4-3 blocks; M4-4 to M4-7 and M4-9 to M4-12 open. |
| AI helpfulness | Not exercised | Fixture explainer and fixture author only |
| Accessibility | Pass, tested scope | Keyboard, focus ring, labels, 430px reflow. M4-8 open. No screen reader or WCAG claim. |

## Before M5

Fix M4-1, M4-2 and M4-3, then a focused recheck: the vacuity matrix, the specification slot after an
outline, and the two failed-check cards. The lower findings can be tracked. All other milestone gates
stay open.

My services on ports 8109, 8112, 8114, 8116 and 8118 are still running and can be stopped.
