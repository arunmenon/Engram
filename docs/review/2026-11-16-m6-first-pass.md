# M6 first verification pass

Status: **in progress, not accepted or complete**. This pass establishes current execution results and identifies remaining verification work. No product code or expected outcomes were changed for this pass. The M5 clarity remediation still needs independent recheck before human sessions.

## Reproducibility

Codex implementer verification, 2026-11-16, Asia/Kolkata. Not independent acceptance, uncoached persona research or human comprehension testing. Headed Google Chrome via Python Playwright at 1440×1000/default zoom; tokens read within scripts, never recorded. Fresh SQLite stores with copies of identified historical artifacts; original drafts untouched.

Evidence: `output/playwright/ai-native-onboarding/M6/baseline-20261116/`.
`manifest.json` identifies branch, HEAD, dirty-tree limitation, source/bundle hashes, engine revision, service configuration and copy IDs/end revisions. Start snapshots are `copies-start.json`, `live-copies-start.json`, `pdlc-before.json`, `pdlc-memory-before.json` and `crm-story-before.json`.

Service 8133: no author/explainer, real registered Spanner pool; historical pack proposals and prepared stories. Service 8134: live agent gpt-5.2-2025-12-11, isolated memory. Do not conflate the live authoring results with the Spanner runs; they used different copies/artifacts.

## Current results

| Check | Result | Scope |
| --- | --- | --- |
| Architecture checks | 431 passed | `architecture-tests.txt`; prior historical architecture failures do not reproduce in this suite now |
| Workbench backend | 194 passed | `workbench-tests.txt` |
| Frontend tests | 19 passed | `frontend-tests.txt`; pure/helper coverage is not full UI acceptance |
| Workbench lint/types | Ruff pass; mypy 24 files pass | `ruff.txt`, `mypy.txt`; current built bundle from the M5 clarity build, identified in manifest |
| Spanner preflight | Registered sandbox ready, epoch 28 | Read-only check, no provisioning/adoption |
| PDLC implementation story, Chrome → Spanner | 111 passed, overall pass | Epoch 29, cleanup verified/released; story and expectations unchanged |
| Saved Northstar proposal, Chrome → Spanner | Pass; mean F1 1.0 | Epoch 30, cleanup verified/released; pack, sources and questions unchanged |
| Existing CRM authored proposal | Blocked before acceptance | Known technical trust question remains; no invented answer or gate bypass |
| Prepared CRM story, Chrome → Spanner | 13 passed, overall pass | Separate frozen CRM story copy, epoch 31, cleanup verified/released; not the blocked authored proposal |
| Same PDLC story, Chrome → memory | 110 passed, 1 failed | Same story and pack digest. Check-97 expects HTTP 409 but records duplicate with HTTP not exercised. Historical M0 difference persists |
| Fresh live CRM author job | Engine-valid pack after three provider responses | 84.6 seconds; no decisions, but trust and lifecycle limitations. Not complete onboarding or preserved lifecycle proof |
| Fresh live procurement author job | No pack; three unresolved decisions | 21.2 seconds, one provider response. Supplier linkage, unit identity and reopening policy surfaced without those problems named in the submitted instruction |

Spanner resource: `projects/portiq-mvp/instances/engram-experiment/databases/engram-sandbox-01`, existing pool `engram-workbench`. No new databases, schema edits, tenant ownership changes or production activation. Cleanup records remain in run results and capacity was restored. SDK Cloud Monitoring export warnings remain in logs; application run results and cleanup checks passed independently of those warnings.

## Important findings and limits

1. **M0 discrepancy reproduced:** `pdlc-backend-comparison.json` records the same story passing Spanner and failing the duplicate/conflict check on memory. Do not edit the expected 409, change the frozen pack, or call both backends green. This needs a separate engine/HTTP-contract disposition.
2. **Known CRM operator-language problem remains:** `crm-blocked-ui.txt` asks about `trust_reviewed` and `trusted_ids` in free text. It correctly prevents acceptance, but does not satisfy the plain-language self-service requirement. This is the historical F04/F5 family, not a newly invented blocker.
3. **CRM live control was not a fully specified initial-authoring case:** the seed came from a revision task and says “Deal lifecycle remains unchanged,” but this fresh draft had no prior pack. The agent explicitly omitted the state machine and captured properties instead. The UI/job label contains “CRM complete”; this report corrects that label. This run establishes initial authoring and engine validation, not the M6 complete-input/revision control. Next run must supply a reviewed lifecycle specification or retain the actual prior pack in a revision task; do not silently treat the omitted behavior as success.
4. **Procurement is a bounded new live observation:** the neutral request says to use supplied material and ask for missing facts. It does not name the conflict or missing relationship. The agent surfaced them, but one case is not a general claim of unprompted detection. No executable procurement pack or query result follows from it.
5. **Transient capacity wording:** Northstar's first result screenshot shows “0 of 1 available” alongside “cleanup verified/available for reuse.” Capacity is refreshed separately; the post-run capacity response is ready. Inspect this timing/wording before recording or claiming a consistently clear operator experience.

Provider metadata (`provider-metadata.jsonl`) records four response IDs, models, latency and usage across the two author jobs. No manual engineering repair was supplied during these jobs. Sources/questions were held unchanged. There was no live explanation → decision → revision → evaluated outcome sequence in this pass, so that M6 row remains open.

## UI method and continuity

Runs were invoked with actual Chrome controls. For Northstar, the script checked the existing synthetic proposal's policy/removal acknowledgements to exercise acceptance and testing; this is implementer test acknowledgement, not an independent domain review. The prior historical repair-removal label remains visible. Questions/expected outcomes were not rewritten.

Harness corrections: an exploratory script was renamed because `inspect.py` shadowed Python's standard library. A sidebar locator was scoped after matching both the sidebar and next-action button. The script then respected an already accepted proposal instead of looking for a vanished acceptance button. These were automation failures before a sandbox launch, not hidden product retries. No failed product check was replaced with a passing expectation.

Current-browser coverage: prepared story execution, pack validation/acceptance, sandbox results and stored graph display, capacity/cleanup, live initial authoring on copied source bundles. Not exercised here: fresh UI uploads, live explanation/steering, failed send/restore, source edits during an agent call, full keyboard/screen reader, approval/export, concurrent tenant execution, cancellation/restart cleanup. Historical reviews and unit tests remain distinct from fresh M6 UI results.

## Remaining M6 objectives

- Obtain Fable's focused M5-1/2 recheck before any human session.
- Reconcile the persistent PDLC memory-versus-Spanner difference without changing the oracle.
- Complete a properly grounded live non-PDLC revision and subsequent evaluation; include the operator-language gate and meaningful state behavior.
- Run remaining current-build recovery/negative cases: no lifecycle, relationship-free/unsupported questions, wrong answers, stale/late responses and source edits during calls. Preserve failures and inputs.
- Exercise handoff/approval with accurate unavailable-activation wording and recorded package identity.
- Complete the fixed-manifest independent Fable review of technical results and outstanding findings.
- Run actual human tasks if full usability acceptance is required. Simulated operators cannot close that gate; no session has been performed.

Do not label M6 “technically verified; operator study pending” yet: technical rows also remain open. Presentation drafting can proceed separately, but final live/Spanner recordings and readiness claims remain gated.

## 2026-11-17 — Continued verification (not final acceptance)

Evidence is now also in `output/playwright/ai-native-onboarding/M6/completion-20261116/`, with a new `manifest.json`. These are implementer checks; no independent or human acceptance is implied. The initial section remains the historical first pass.

- **Memory discrepancy fixed in code:** batch outcomes now compare the existing canonical request fingerprint rather than treating every repeated ID as a duplicate. Identical retries remain duplicate; changed requests conflict. Direct legacy append behavior and tenant authorization are not claimed changed. Three new regression cases, 25 memory conformance checks and the 628-test combined regression pass. The unchanged PDLC story passes 111 checks in current Chrome/memory. Frozen story expectations were not edited.
- **Properly grounded live CRM revision succeeded:** this time the prior pack was retained. The business request asks for permanent CRM contact identity and preservation of deal behavior. The generated Contact key is `contact_id`; the Deal lifecycle is unchanged. Sources and both existing question expectations remain unchanged. The initial explain call failed closed because the agent supplied structured options in a limitation scope. Explicit scope instructions were added to the agent prompt without relaxing verification; a fresh frozen-copy UI explanation subsequently returned 200. The revision was operator-authored, not proof that that later explanation caused it.
- **CRM testing and handoff:** both questions scored F1 1.0 in isolated memory, and the UI reached “Approved for handoff” with activation unavailable. One graph existence assertion was added before execution from the supplied account-created event: Acme must exist. This is an author-reviewed synthetic expectation, not independent review. Existing question expectations were not changed. The UI requires a second confirmation save when graph selections change; record this as an operator-friction finding, not a hidden bypass.
- **Current-browser recovery:** fixture failure/retry preserves answer and request; restore returns them to the single editor; named Keep-data request and Clear work; ticks survive navigation/reload. At 430px tested screens have no document overflow. No screen-reader or real-human claim.
- **Additional negative checks:** directory without lifecycle does not demand lifecycle confirmation. The unchanged incident-operations deliberately failing story still fails when rerun. A concurrent source edit invalidated the browser explanation observation; a subsequent stale revision API probe returned 409, and no old claim was shown. Do not claim the first browser response was observed as 409: the response wait timed out. Two harness corrections (Run story again label; no summary field in a story result) are retained in the record; no expected result was changed.
- **Latest Spanner rerun did not pass:** error reference `0e217992b5ca`, cleanup DeadlineExceeded. The job has no completed check result. A subsequent read-only check shows the registered slot ready at epoch 32; no manual ownership reset or forced release was performed. Earlier 111/13/F1-1.0 Spanner successes remain evidence on their original engine, not a substitute for this failed run. The current failure needs disposition/recheck before final technical acceptance.
- **Verification after prompt edit:** 27 focused explain tests pass; the broader 628-test run preceded that prompt-only edit. This distinction is explicit rather than claiming every test was rerun on identical files.

M6 remains open: dispose/recheck the latest Spanner failure; complete the remaining integrated negative/unsupported/intake coverage and fixed-manifest independent review; obtain the M5 clarity recheck and actual operator study. Known historical engine-language cases are not closed by the successful controlled CRM example. No production deployment or activation occurred.
