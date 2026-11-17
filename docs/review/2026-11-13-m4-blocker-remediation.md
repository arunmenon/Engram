# M4 blocker remediation — implementer verification

M4-1, M4-2 and M4-3 are implemented and ready for focused independent re-review.
M5 has not started. This is not independent acceptance.

## Reproducibility

- Codex, implementer self-check, 2026-11-13 Asia/Kolkata; directed tests with prior familiarity, not an uncoached persona study.
- Branch feature/engram-walkthrough, HEAD 27b4ba8; existing large dirty/untracked tree, no commit or deployment.
- Fresh isolated service http://127.0.0.1:8119/workbench.html; operator m4-implementer.
- Bundle workbench-CjVMcSvA.js. Source, bundle, engine and snapshot hashes in the evidence manifest.
- Headed Google Chrome through Python Playwright, 1440×1000 and 430×932, default zoom. Credentials read inside scripts, never printed.
- Real isolated-memory runner; fixture explainer and outline author. No live provider or Spanner.
- Evidence: `output/playwright/ai-native-onboarding/M4/remediation-20261113/`.
- Fresh support passing, support investigation and CRM copies; IDs and start/end revisions in manifest.json. Story and pack snapshot equality verified after the run. Originals and reviewer copies untouched.

## Changes

### M4-1: distinguish runner pass from useful proof

Added weak-proof warnings for never-observed absent records, forbidden-only answers absent from the graph, undeclared absent fields, zero evaluation threshold, and properties limited to type/identity fields. These use the existing `needs_review` coverage state. Historical expectations and runner outcomes are unchanged.

The warning for an unseen record is deliberately conservative: it says the story never observes it and asks for a relevant comparison. It does not claim static proof that no possible event could create it. Existing absent-endpoint, empty-assertion and no-answer warnings remain. This is not an exhaustive vacuity detector; seed-only retrieval and unchanged-noop behavior remain outside these corrections.

### M4-2: bind specification to the accepted story

Inspection and explanation now share one source accessor: only `journey_origin.brief.specification` with the saved origin reviewer qualifies. The pending `journey_brief` is never source evidence for the existing story. If the story lacks a reviewed origin, the missing-specification warning remains and the evidence slot stays null, including after an outline is proposed.

### M4-3: show actual differences before technical detail

Failed property checks show expected and recorded field values. Evaluation checks show expected and found records with separated account/key values. Retrieval checks show missing, forbidden and unexpected answers when recorded. JSON remains in the existing technical disclosure. No diagnosis or expected-answer correction is inferred from the mismatch.

## Verification

- Reviewer vacuity matrix reproduced unchanged in meaning, with output redirected to implementer evidence. All six M4-1 cases now report `needs_review`; the substantive title control remains `passing`. Full results in vacuity-matrix.json.
- Focused story-inspection suite: 12 passed, including real validator/runner cases, pending versus accepted source provenance, unchanged artifacts and plain comparisons.
- Frontend: 18 helper tests passed; TypeScript and production build passed. Ruff and targeted mypy passed.
- Full workbench suite: 190 passed in 32.06s, recorded in backend-tests-final.txt. Initial new-test fixture setup failures are retained in earlier logs; fixed the fixture's required query fields and explicit review step, not product expectations or gates.
- Chrome: passing support and CRM, failing support; consent before explanation; visible title and wrong-account comparisons with technical details closed; outline submission preserves missing-source warning and null source evidence; rerun retains failures; 430px has no horizontal overflow. Desktop failure screenshot visually inspected; narrow layout checked by browser assertion and captured.
- Pack snapshots and all story definitions/expected answers unchanged in all three copies. Investigation revision 2→7 reflects consent, outline and rerun; passing copies remain 2→2.

## Verdict and remaining scope

Functionality: implementer checks pass for these three corrections; independent acceptance pending.
Visual clarity: both reviewed mismatches now visible without JSON; broader density findings remain open.
AI helpfulness: live reasoning not exercised. A cited prose claim can still assert an unverified cause; carry into live evaluation.
Accessibility: existing form focus on follow-up and 430px reflow exercised; no screen-reader or WCAG claim.

Recovery coverage: consent change exercised; tenant navigation exercised. Save while editing, failed author send, legacy restore, sign-out clearing, cancellation and late responses were not re-exercised in this focused pass. Existing independent M4 evidence is not replaced.

M4-4 through M4-12 remain open lows, along with prior M0/M2b/M3/M6 gates. No reviewer services were stopped.
