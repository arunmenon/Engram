# Whole-flow demo blockers: bounded remediation

Date: 2026-11-06. Implementer-side verification; independent acceptance pending.
Evidence: `output/playwright/ai-native-onboarding/demo-blockers-20261106/README.md`.
No full redesign, production mutation, approval, oracle change or new Spanner run.

## Disposition

- **F02 implemented and verified:** entity names include `name`, `display_name` and `title`; search includes these fields and the unchanged engine identifier. The label now promises “Search names, titles or identifiers”. CRM Bo is selectable by name. Pure tests cover same-name contacts with distinct IDs, delivery titles and unnamed fallback. Account-related lookup is not promised unless that text is in the option.
- **F03 implemented and verified:** scope, source and question placeholders are domain neutral. The event template explicitly requires replacement with the tenant's supported event contract. CRM and delivery browser checks pass.
- **F04 partial:** the next-action banner no longer repeats raw agent diagnostics as operator instructions. Author and explain receive separate, actual engine-derived graph and payload type vocabularies. Author instructions prohibit turning syntax repair into business decisions and duplicating source-trust controls. A real CRM explanation correctly rejected the alleged type conflict; one live author submission completed, validated and removed the duplicate trust question. However the explanation and revised summary still contain `float`, `number`, `payload_contract` and admission terminology. Prompt changes alone have not delivered plain-language self-service. Do not close the operator-clarity finding.
- **F01 diagnosed, not an ontology correction:** memory returns duplicate whenever the event ID exists; tenant-bound Spanner compares acceptance fingerprints and reports conflict for changed content. The existing journey unit test explicitly expects the memory conflict check to fail. Historical 111-pass evidence is Spanner; fresh 110-pass/1-failure evidence is memory. No expected result was weakened. Current-engine Spanner revalidation remains outstanding.

## Exact scope

`entityOptions.ts` is a pure extraction from EntityPicker, with name/search support. EntityPicker uses it. Workbench copy is neutral. OperatorFlow's limitation banner distinguishes agent concerns from confirmed engine errors. Backend authoring and explanation context distinguish graph-property and payload-contract type vocabularies. The authority, validation, consent and revision gates are unchanged.

Live author output preserved all executable pack rules; its sole pack delta was a descriptive SUPERSEDES note. Only the draft instruction changed in content. Source inputs, expected answers and trust review were preserved; approval remains absent. The proposal still exposes real migration and source-trust caveats, including technical wording that needs improvement. A successful validation does not establish the truth of every generated explanatory claim.

## Verification

107 targeted backend tests passed; 13 frontend tests passed; frontend build, Ruff and targeted mypy passed. Headed Chrome exercised isolated CRM and delivery copies on port 8106. CRM advanced revision 2 to 6, delivery stayed at 2. Live explanation returned 200; author completed in 40.29 seconds, one observed attempt, validation passed. Narrow-screen assertion found no horizontal overflow.

This is scripted implementation verification, not a human study or independent acceptance. No screen-reader check, full recovery rerun, fresh sandbox execution or current Spanner acceptance was performed. The evidence README records identities and limitations; implementation-hashes.json pins files and the served bundle. The old M1a acceptance remains bounded to its reviewed behavior and bundle.

## F01 source trail

- `src/context_graph/adapters/memory/log.py`: existing IDs return duplicate.
- `src/context_graph/adapters/spanner/log.py`: tenant-bound acceptance compares source ID and request digest.
- `src/context_graph/workbench/journey_runner.py`: consumes adapter outcomes; expected 409 requires conflict.
- `tests/unit/test_workbench_journeys.py`: memory implementation journey explicitly asserts that conflict check fails.
- Historical `.workbench/drafts.sqlite3`, draft `33223bbf-c1fd-41fb-9ab8-badafd8948c8`, revision 25: backend Spanner, 111 passed, engine `sha256:831eb3a6c475d5ca2aa11a7b7bc53e9f47ab4ef35979850b2721f7968660e767`. Read-only inspection; no database changes.

## Next bounded step

Review F02/F03 for acceptance. Keep F04 open: present business consequence and next action first, with syntax diagnostics under technical detail, without hiding genuine blockers or rewriting the operator's words. Verify on CRM and delivery, with a live CRM explanation rather than a canned fixture. Keep F05–F09 in their assigned milestones; do not roll them into an unbounded redesign.
