# Existing onboarding flow — AI-native UI skill review

## Evidence identity and scope

- Reviewer: Codex, implementation-side assessment. **Not independent acceptance** and
  not a human study. Prior implementation familiarity is substantial; no uncoached
  first-use claim. Screens were inspected before targeted code reads in this pass.
- Date: 2026-11-06; local timezone Asia/Kolkata. Record timestamps are UTC in JSON.
- Branch/HEAD: `feature/engram-walkthrough`, `27b4ba8`. Extensive dirty tree (525 entries
  at the initial status check); HEAD alone does not identify this application.
- Browser: headed Google Chrome through Python Playwright; token read directly from
  file inside automation, never printed. Operator label `remediation-review`.
- Service: `http://127.0.0.1:8105/workbench.html`, reused process PID 2093; controlled
  fixture author/explainer, isolated memory. No new live-provider or Spanner calls.
- Frontend: `workbench-BsLJar0G.js`, SHA256
  `902df75fee983c23313faf30032c09afa08937f92933d2eca67da012eceeb625`;
  CSS `workbench-CqPRbaYs.css`, SHA256
  `17c28b658d354acb8e45cbdd498839d100c261a9e79c3e1c643364481267a160`.
- Story result reports engine revision
  `sha256:a6b08267ef177e9d6d84c09e6741ba9db611a4a736a5d649468fd13e606b4fb2`.
  This is the engine identifier reported by the run, not proof of a freshly restarted
  server or a complete fingerprint of Python modules already loaded into its process.
- Desktop viewport 1440×1000; narrow 430×932; default browser scale. No zoom or
  screen-reader study. Screenshots, visible text, accessibility snapshots and DOM
  dimensions are in `output/playwright/ai-native-onboarding/full-flow-review-20261106/`.
- Copy identities and source hashes: `copies.json`. CRM
  `97cea632-599d-45fc-bf3e-be69ccd07aaa`, revision 2→2; delivery
  `5d520fc1-6fd9-4334-8bcc-1c7abadde720`, 2→4. Original implementer/Fable drafts untouched.
  New local-only intake and PDLC story workspaces were created through the UI; their
  identities/revisions are also recorded. No pack approval or activation was performed.

## Verdict

| Dimension | Verdict | Accepted scope / limit |
| --- | --- | --- |
| Functionality | **Revise** for whole-flow acceptance | Navigation, source intake and selected recovery paths work; fresh prepared PDLC story reports one failed check. Authoring/approval end-to-end was not executed here. |
| Visual clarity | **Revise** | Consistent colors, typography and controls; information hierarchy and domain-language problems remain. |
| AI helpfulness | **Revise / live reasoning not exercised** | Useful contextual controls, but existing generated output still burdens operators with internal rules. No new reasoning claim from fixture service. |
| Accessibility | **Partial, tested scope only** | Inline request focus, restore/clear behavior and narrow overflow checked. No full keyboard, contrast, zoom, graph accessibility or screen-reader acceptance. |

This review does not reopen Fable's accepted M1a claim of safe request preparation.
It identifies work across the existing milestone plan. A complete self-serve onboarding
or a clean professional presentation cannot yet be claimed from this evidence.

## Screen coverage

Method: directed screen inspection, DOM measurements and scripted interactions with
CRM/delivery domain contexts. **No persona task log was collected**; actions are
recoverable from scripts, but hesitations, help needed and task timings were not logged.
Do not interpret this table as simulated uncoached persona-task evidence.


| Surface | Fresh observation / action | Boundary |
| --- | --- | --- |
| Landing / tenant list | Viewed prepared stories, tenant cards and new-draft form. | Multi-tenant scale, search and deletion not tested. |
| Create / tenant setup | Created local-only tenant, filled scope and permission/redaction fields. Viewed CRM/delivery setup. | Pack catalog expansion not exercised. |
| Source intake | Added one synthetic sales-process source; inspected existing spec/schema/sample inventory. | Pasted text only; upload errors/PDF unsupported path not tested. |
| Explain / review / steer | Viewed CRM generated proposal and delivery issue, typed answer and prepared request. Inspected shared preview. | No fresh explain or successful author call in this pass. |
| Under the hood | Viewed both domain screens through the default Continue/navigation sequence. | Did not edit technical rules. |
| Questions / expected answers / trust | Viewed CRM populated candidates and delivery empty state; searched for Bo and observed no match. | Expected answers and trust approvals not changed to enable a pass. |
| Test examples | Viewed blocked run state and its guidance for both copies. | No authored-pack sandbox submission; prerequisites intentionally unresolved. |
| Prepared PDLC story | Ran 23 deliveries/111 checks through UI in isolated memory. Inspected report and stored-graph view. | Not Spanner, deployed networking or all PDLC stories. |
| Approve / handoff | Inspected disabled approval and activation-unavailable messaging for both copies. | No approval, download, provisioning or deployment executed. |

The CRM copy is a real previous live-agent result, including its limitations and diff.
The delivery authoring copy is a controlled issue fixture with incomplete samples and
no accepted proposal; its inability to run is not itself a product defect. The separate
prepared PDLC story provides runnable delivery evidence.

## Findings (stable IDs; priority order is in the recommendation below)

### F01 — Prepared PDLC replay outcome disagrees with its fixed expectation

**Medium functional; blocks claiming the story passes. Owner: M4, with engine diagnosis.**
Fresh UI run: **110 passed, 1 failed, 0 unsupported, 0 errors**. After event 19, changed
content using an existing event ID is reported as duplicate; the story expects conflict.
Evidence: `story-result.png`, `story-result.txt`, `story-end.json`.
The UI clearly surfaces the discrepancy. Root cause is **not diagnosed** by this review.
M0 consequence: the historical 111-pass baseline is not reproduced by this fresh run.
Keep that historical evidence, but mark its current-engine replay unresolved in the M0
reconciliation table until duplicate-versus-conflict semantics and cause are established.
Smallest next action: trace input, admission/ledger outcome and assertion to distinguish
runtime behavior from stale fixture semantics. Preserve oracle until intended semantics
are established. Verification: rerun the original case with justified behavior and
negative/duplicate controls; never merely weaken the assertion.

### F02 — Entity choices omit available names; name search fails

**Medium usability; owner M2b.** On CRM Questions, Bo is `Contact · C2`, Ann is C1.
Typing **Bo** into the second question's search gives **No matching sample entities**.
The control explicitly promises “Search by account, name or title”; its behavior
contradicts its own guidance, beyond merely showing weak labels.
The source samples contain names. After observation, source inspection confirmed
`EntityPicker.tsx` uses title/display_name but not name for its label; search uses that
label. Evidence: `crm-name-search.png`, `crm-name-search.txt`, `crm-5.png`.
Smallest correction: generic readable-name fallback with type/key context for ambiguity;
search the displayed meaningful attributes. Do not add CRM-specific branching.
Verification: exercise each advertised search category (account, name, title), including
Bo by name; distinguish same-name contacts; preserve internal IDs. If a category is
unsupported, change the promise rather than leaving a misleading control.

### F03 — Incident-specific guidance leaks into CRM

**Medium cross-domain usability; owner M2b (intake copy M5).** CRM expected business
outcome placeholder says “Only US incidents should be returned…”; scope placeholder
also assumes incidents/postmortems. Evidence: `crm-5.png`, `crm-1-aria.txt`; source
confirmed the former literal at `Workbench.tsx`'s expectation field.
Smallest correction: neutral task guidance or a data-grounded domain example; no invented
business expectation. Verify CRM, delivery and an empty draft without incident defaults.

### F04 — Engine speculation dominates the operator's next action

**High AI helpfulness; first demo blocker. Owner M1b presentation follow-up / M2b.** Every CRM step repeats
an agent warning about `number`, `float` and `payload_contract`, while the pack checks
passed and historical memory evaluation passed. The review screen's trust question
asks whether `trust_reviewed=true` and `trusted_ids` should be metadata, rather than
which sample producers the team trusts. Pack overview narrates quotation/type repairs.
Evidence: `crm-1.txt` through `crm-7.txt`, especially `crm-3.png`.
A CRM operator cannot resolve this implementation question from business knowledge.
It violates the rule against making implementation exceptions operator decisions.
The warning is an agent claim, not a demonstrated engine error; successful parsing alone
also does not prove all semantics. Smallest correction: distinguish check evidence from
agent uncertainty; resolve known engine mechanics internally; ask only the remaining
business decision. Keep migration consequences visible. Verify the main guidance is
understandable without type/setting names and does not hide real uncertainty.

### F05 — Review tasks are buried in ungrouped detail

**Medium density; owner M2b, with M3 consequence work.** CRM step 3 is 5,673px with
17 separate change acknowledgements, including empty/default-shaped changes. Delivery
step 3 is 4,878px with 18 entity summaries and many individual edge-evidence links.
Evidence: `metrics.json`, `crm-3.txt`, `delivery-3.txt`.
Smallest correction: group meaningful changes by operator decision, separate overview
from decisions, disclose optional per-rule detail, and retain a complete inspectable diff.
Investigate whether default normalization is semantically equivalent before grouping it
as noise; do not suppress actual changes. Verification: shorter issue-to-decision path,
material removals/unexpected edits still visible, no weakening of acknowledgements.

### F06 — The default Continue path makes technical inspection a required stop

**Medium navigation; owner M2b.** Step 3 Continue says “Continue to under the hood”,
then exposes a technical screen (CRM 3,486px; PDLC 6,196px). This undermines the promise
that technical detail is secondary. Sidebar users can skip it, so this is not a hard
backend gate. Evidence: `crm-3.txt`, `crm-4.txt`, `delivery-4.txt`.
Smallest correction: main Continue goes to the next operator step; keep technical
inspection explicitly optional. Verify back/reopen behavior and no loss of input.

### F07 — Blocking banner and inline remedy still disagree

**Low usability, previously known; owner M1a follow-up / M2b.** Under local-only consent,
the banner asks for more evidence while Explain tells the operator to enable provider
use in setup. New intake with one source shows the same prioritization mismatch.
Evidence: `recovery-local-only.txt`, `intake-no-proposal.txt`.
Smallest correction: use the same prioritized prerequisite for banner and disabled
control; allow local work without suggesting permission has been granted.
Verification: consent, missing sources and unconfigured agent states give coherent routes.

### F08 — Run and approval buttons lack their specific local blocker

**Low usability; owner M4 / M6.** Test step says to open the full readiness checklist;
approval is disabled with no adjacent concise list of unmet requirements. The global
banner repeats the agent's first limitation. Evidence: `crm-6.txt`, `crm-7.png`.
Smallest correction: show the first actionable unmet prerequisite with a link beside the
operation; offer the full checklist secondarily. Verify the inline reason matches the
actual server requirement. Keep approval separate from activation.

### F09 — Empty draft includes a decision-application action

**Low hierarchy; owner M5.** Before any proposal exists, “Apply answers with the agent”
appears above Build a pack. It suggests a decision stage before there are decisions.
Evidence: `intake-no-proposal.png/.txt`. Inspect enabled state before claiming it submits;
this finding is about presence and hierarchy, not a proven unintended call.
Smallest correction: present the relevant first-proposal action; show decision application
when applicable. Verify no missing route once genuine decisions exist.

## Measurements and vocabulary

Desktop 1440×1000, default closed disclosures:

| Screen | CRM height | Delivery height |
| --- | ---: | ---: |
| Setup | 1,198 | 1,155 |
| Sources | 1,584 | 1,490 |
| Review | 5,673 | 4,878 |
| Technical inspection | 3,486 | 6,196 |
| Questions | 3,179 | 1,423 |
| Test | 1,000 | 1,000 |
| Approval | 1,045 | 1,000 |

Delivery with request prepared: 5,506px. Issue-region top y=599.55; Send y=1428.02,
about **0.83 viewports apart**, with exactly one visible-in-document send control.
This measurement starts at the explanation region, not the preceding issue heading.
CRM narrow review: 7,126px at 430×932; no horizontal page overflow. Narrow approval
also had no horizontal overflow. Height is diagnostic, not a pass/fail threshold.

`vocabulary.json` preserves the original all-source probe for audit. It counted schema
JSON as source familiarity and therefore overstated grounding for operators.
`vocabulary-operator-material.json` recomputes the same bounded inventory against
specification/process material and samples, **excluding schema/contract sources**:
CRM 17 candidates, 6 absent; delivery 40 candidates,
38 absent. Included/excluded source IDs and per-token flags are recorded.
These are synthetic supplied materials, not proven human-authored language. Sample
presence also does not establish comprehension. This is not exhaustive tokenization;
manual unexplained technical cases remain F04–F06.

## Recovery matrix

| Scenario | This pass | Evidence / limit |
| --- | --- | --- |
| Save while editing | Not exercised | No deliberate concurrent typing/save race. Earlier tests are not relabelled fresh evidence. |
| Reload with sign-in | Exercised, pass | Delivery answer/request restored visibly; Send requires review. |
| Failed send | Exercised, pass | Browser-injected HTTP 503 after real save; one request, retained words, stale send blocked. Not live-provider failure. |
| Legacy restore missing metadata | Not exercised | Earlier Fable report covers it; no fresh claim. |
| Consent change | Exercised, mixed | Explain disabled correctly; banner/remedy mismatch remains F07. |
| Tenant switch | Exercised, pass | Delivery request absent in CRM; return offers recovery. |
| Sign-out storage clearing | Exercised, bounded pass | No `engram-edit:` session keys remained. Not an exhaustive credential/storage security audit. |
| Cancel during long call | Not exercised | No new provider call induced. |
| Late response after cancel | Not exercised | No fresh asynchronous-response injection. |

Prepare and restore focus the request; Clear returns focus to retained answer. These
were browser assertions, not screen-reader observations. `recovery-results.json` and
screenshots capture tested states. Dirty field values, source material and original
expectations were not changed to manufacture successful checks.

## Recommended milestone order

1. **Before any demo:** F04 first (operators are being asked to resolve engine mechanics),
   then F02 and F03 (misleading search/readable labels and domain leakage).
2. **Engine diagnosis and M0 reconciliation:** F01. Historical 111-pass evidence must not
   stand in for a current passing replay. Do not edit expectations to remove the failure.
3. **Existing milestone work:** F05–F09 remain with M2b/M3/M4/M5/M6 as assigned; retain
   the bounded M1a acceptance rather than reopening it as a blanket milestone failure.

## Bundle lineage and acceptance boundary

Fable's bounded M1a acceptance used `workbench-D_Nw0CpH.js`; this review used
`workbench-BsLJar0G.js`. The intervening recorded product change is in RequestReview.tsx:
the existing current-rule list is now inside a closed **Current rules · technical details**
disclosure. Keys, states and event names remain inspectable; requested outcome and
unverified-consequence text stay visible. This lineage is based on the implementation
record, not an independently reconstructed bundle source map.

Reload, failed send, tenant-switch recovery and clear-focus paths were freshly exercised
on the newer bundle. That is targeted regression evidence, not automatic transfer of
all independent acceptance or an assertion that every prior case was repeated.
The accepted safe-request-preparation claim remains bounded as Fable stated.

No product code was modified in this pass. Scripts seeded isolated copies and exercised
the UI; records and evidence are retained. No deployment or live database was touched.
