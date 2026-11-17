# M5 independent review (thin intake assistance)

## Verdict

**M5 passes its bounded scope and M6 may start.** No blocking finding.

The exit condition is met: an operator reaches an honest unresolved state without being asked for
engine syntax, nothing is sent before consent, and sources, questions and expected answers are not
rewritten.

**Two medium findings should be fixed before any M6 human session**, because they are the places where
I hesitated as an operator:

1. **M5-1.** The sample inventory gives counts only. It says an ID repeats once; it does not say which
   ID, or that it repeats across two units. That is the fact the identity decision depends on.
2. **M5-2.** The unresolved proposal asks for the same answers in two places, and "Apply answers with
   the agent" stays disabled with no reason until all three decisions have text.

Seven low findings are listed. The remaining technical wording is rated low: it did not stop me
understanding what was being asked.

One limit on the live evidence: the recorded instruction told the agent to flag the policy conflict and
the missing supplier relationship. The run shows the agent complying honestly with that instruction. It
does not show unprompted detection, except for the unit-scoped identity question, which was not
prompted.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent review. Not the implementer. No fixes made. |
| Date | 2026-11-16, Asia/Kolkata |
| Prior familiarity | I reviewed M0 to M4 of this workbench. I did the three operator tasks in the browser before reading the M5 reports or code; I had read the implementer's server scripts and input texts to start my own service. Simulated persona, not human comprehension. |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Bundle | `workbench-DP1IaDfs.js`, sha256 d2899232…f7ba9, the bundle the page served |
| Backend | `authoring.py` sha256 500511b0…94533 and `test_workbench_intake.py` 9608f00b…fdd42f, both matching the recovery manifest |
| Engine | sha256:d19b5a5c…9c129, read from my own freshly started process; matches the manifest |
| Seed snapshot | `M5/recovery-20261116/copies-end.json` (sha256 8b5a6077…), unchanged after my review |
| Service | http://127.0.0.1:8131, operator `fable-m5-review`, own SQLite store |
| Browser | Headed Chrome through Python Playwright, 1440x1000 and 430x900, zoom 100% |
| Agent | None. Author and explainer are refusing stubs that record every call. No live call made. |
| Evidence | `output/playwright/ai-native-onboarding/fable-m5-20261116/` |
| Not exercised | Live provider, Spanner, sandbox run, file types other than JSON, screen reader, full keyboard pass, human participants |

### Copies

| Copy (names prefixed "Fable M5") | ID | Start to end revision | Note |
|---|---|---|---|
| Procurement intake | 0373bfea | 1 to 9 | Blank draft; material added through the page |
| Sales contact intake | 248f90f7 | 1 to 8 | Blank draft; material added through the page |
| Live unresolved copy | fdbaeb37 | 2 to 2 | Read only. Sources, questions and proposal equal the recorded live draft |
| Live unresolved probes | 2ed0381f | 2 to 9 | Decisions answered; sources, questions and proposal equal the recorded live draft; no approval |

## Operator tasks

### 1. Add material, correct suggestions, reload

- **Suggestions are format-only and say so.** Written rules: "This looks like written material." The
  schema: "This contains schema declarations." Events: "Each record has an event name and a payload
  object."
- **Ambiguous JSON is not called a schema.** A single object, an array without event names and a bare
  `{"type": "object"}` all read: "This JSON does not clearly identify events or a schema. Choose its
  category; nothing has been changed." Broken JSON and prose with braces are treated as written
  material.
- **Nothing is applied for me.** The suggestion is a button, "Use suggested category". The category
  stays where I left it.
- **Correction works before and after saving.** I changed categories from the evidence list; the text
  was untouched.
- **Reload keeps everything.** After a full reload and sign-in, all names, categories and texts were
  identical, in both domains. Saved texts equal what I pasted, byte for byte.
- **No provider call.** Intake produced only draft saves. The stub log did not exist at that point.

### 2. Sample inventory

Procurement, four request events plus one I added with zero, false and empty values:

| Field | Shown | Correct |
|---|---|---|
| id | 4 present, 3 distinct, repeats 1 | Yes |
| unit | 4 present, 2 distinct, repeats 2 | Yes |
| value | 3 present, 1 missing, 1 empty, 2 distinct, repeats 1 | Yes: zero counts as a value, null as empty |
| urgent (false) | 1 present, 0 empty | Yes: false is not treated as empty |
| note (empty text) | 1 present, 1 empty | Yes |

Sales contact updates: contact_id repeats once, email is missing once, company repeats once. Correct.

- **Qualification is present and repeated:** "A repeated value can be an update to the same record or a
  collision; the samples alone cannot decide" and "Sample uniqueness is not a global key guarantee."
- **Search** filters by event or field name. It found "value", "unit" and "purchase.approved".
- **What I could not do:** see which ID repeats, or that it repeats across east and west (M5-1).

### 3. The recorded live unresolved proposal

- **Missing supplier evidence:** identifiable from the first review item and the first decision: "How
  is a supplier connected to a purchase request in your system, and what document/event shows that
  link?"
- **Conflicting policy:** identifiable. Under "Where this came from", both sentences are quoted with
  their source names, "Process rules" and "Conflicting policy". Both sources also remain in the
  evidence list.
- **Identity choice:** "should that be treated as the same request shared across units, or as separate
  requests per unit?" I could answer in my own words.
- **No engine syntax was asked of me** in any question.
- **Leaving it unresolved:** "Left unresolved. Nothing was sent or approved." No request was made and
  the revision did not change.
- **No apparent approval:** "Run the examples", "Approve this package" and "Complete" are disabled. The
  API refuses validate, sandbox and approve with 409. The engineer view reads "Conceptual draft".
- **430px:** no horizontal overflow on the proposal, test and approval steps.

## Code and recorded evidence

- **Pattern capability matches the engine.** The author is told: regular expressions, first capture or
  whole match, looked up against the last key field, no composite identity or account scope. The engine
  (`retrieval/artifacts.py`) does exactly that and adds no scope to the lookup.
- **Missing-evidence guidance** tells the author to return no executable pack and business questions,
  including when a question has no internal intent identifier, and to preserve supported behaviour on
  revisions. This is prompt text, not enforcement; the implementer says the same.
- **Gates unchanged in my probes.** A local-only draft returns 409 for authoring and 403 for explain,
  with no stub call. The three stub calls I caused all came after consent, each from an explicit click.
- **`pack=null` is treated as unresolved.** Readiness lists "Generate an executable pack proposal" and
  each open decision; nothing is marked validated or answered.
- **Live run.** The recorded history has one author start, one attempt and one completion, took 26.3
  seconds, and the implementer's service had no fixture author installed. No provider request
  identifier was retained, so I cannot verify the call beyond that. Sources and questions before and
  after are identical.
- **Failure handling.** With the refusing stub: "The task did not finish… Your saved inputs are
  retained. Your previous pack is retained." Answers, sources and the proposal were unchanged.

## Findings

### M5-1, Medium: the inventory does not show which values repeat

- **State:** "What your samples contain" with procurement requests.
- **Consequence:** I can see "repeats: 1" for id, but not that it is 42, or that it appears under both
  east and west. I had to read the raw JSON to learn the one fact the identity question turns on.
  Searching "42" or "east" returns an empty list with no message.
- **Correction:** list the repeated values for a field, and let the operator see the other field values
  on those events. Say "no matches" when search finds nothing.
- **Verify:** from the inventory alone, name the repeated ID and the units it appears in.

### M5-2, Medium: two answer areas and an unexplained disabled button

- **State:** "How Engram understands them" on the unresolved proposal.
- **Consequence:** three "Review these items first" panels each have "Your answer", "Review my
  request", "Add supporting material" and "Leave unresolved". Below, three "Recorded decisions" have
  their own answer boxes and "Apply answers with the agent". Supplier evidence and reopening policy
  appear in both. I did not know which box to use. After answering only the identity question and
  saving, "Apply answers with the agent" stayed disabled with no reason shown. It enabled only after I
  typed "not known" into the other two.
- **Correction:** one answer area per topic; when a limitation and a decision cover the same topic,
  show one. State next to the button what is still needed, or allow "not known yet" as a choice.
- **Verify:** with one decision answered, the page says what to do next.

### Lows

| ID | Finding | Correction |
|---|---|---|
| M5-3 | Technical wording in agent text: "cannot be implemented as a graph retrieval intent", "stable key", "deduplication", "executable projection pack", "lifecycle modeling". The questions themselves are plain; I understood each ask. | Keep the prompt guidance; consider showing the question first and the effect as secondary text. |
| M5-4 | "No specific pack rule is linked to this statement. Check the rule before accepting it." appears on all six statements although no pack exists. | Omit when the proposal has no pack. |
| M5-5 | Setting written rules to "Sample events" shows the raw message "Expecting value: line 1 column 1 (char 0)". The change is refused and nothing is lost. | Plain message: this material is not valid JSON events. |
| M5-6 | Adding a recognised schema or events under the default "Process document" category saves with no warning; the inventory then stays at zero without saying why. The evidence list shows "specification", "schema", "samples" instead of the category names. | Note the mismatch on save; use the same labels as the selector. |
| M5-7 | Count wording: null is counted as present and as empty, so "3 present, 1 missing, 1 empty" describes four events. "1 examples". An empty list is not counted as empty. | Separate "has a value", "empty" and "missing". |
| M5-8 | Focus drops to the page body after "Add and save source". "Leave unresolved" leaves no lasting mark once the message scrolls away. | Move focus to the saved source or the form heading; show a persistent "left unresolved" state. |
| M5-9 | The change-request placeholder says "keep the account-specific services separate" on a procurement draft. | Neutral example. |

## Verdicts

| Area | Verdict | Scope |
|---|---|---|
| Functionality | Pass | Intake, correction, reload, inventory counts, consent and readiness gates, unresolved state, two domains |
| Visual clarity | Revise | M5-1 and M5-2; the rest of the tested screens read clearly |
| AI helpfulness | Pass, narrow | One recorded live proposal: honest, cited, business questions. Guided by the operator instruction. No live call in this review. |
| Tested accessibility | Pass, narrow | 430px reflow, labelled controls, disabled reasons on "Explain this". Focus loss in M5-8. No full keyboard or screen reader pass. |

## Before M6

Nothing blocks M6. Fix M5-1 and M5-2 before a human session. Still open: M5-3 to M5-9, M4 RR-2 to RR-4
and M4-4 to M4-12, the M0, M2b and M3 lows, and the M6 human and Spanner gates.

My services on ports 8109, 8112, 8114, 8116, 8118, 8120, 8124 and 8131 are still running and can be
stopped.
