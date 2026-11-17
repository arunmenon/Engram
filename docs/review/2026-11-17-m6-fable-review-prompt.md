# Fable independent M6 verification request

Work in `/Users/arunmenon/projects/Engram`. Review M6; do not assume the implementer handoff means acceptance. Apply `ai-native-ui-review`. Use fresh reviewer-owned stores/copies and record bundle/source hashes, service/operator, snapshot IDs and start/end revisions. Read credentials inside automation; do not print them. Do not change packs, source material, expected answers or runtime data to obtain a pass.

## Operator tasks first

Before reading implementation details, attempt these on your copies:
1. Procurement operations: find request 42 and explain why east and west may be different records without opening JSON. Correct a source category and reload. On incomplete input, leave unknown facts unresolved and identify the next action.
2. CRM operations: explain why an email change can split a person's history, prepare a business-language revision request, recover from a failed send without losing it, and distinguish planned changes from tested results.
3. Incident operations: inspect the wrong title and wrong-account answer, recognize that a total-cost question is unsupported, and identify what should be investigated without changing the oracle.
4. Handoff: identify the exact tested/approved artifact and whether anything was activated.

Log actions, hesitations and help needed. This is a simulated reviewer persona unless actual human participants are present; do not relabel it as human comprehension.

## Then inspect

- `docs/review/2026-11-17-m6-verification-handoff.md`
- `docs/review/2026-11-16-m6-first-pass.md` (historical failures retained)
- `docs/ai-native-onboarding-milestone-plan.md`, M6 acceptance and earlier open gates
- `output/playwright/ai-native-onboarding/M6/final-20261117/manifest.json`, README, result JSON and scripts
- `output/playwright/ai-native-onboarding/M6/completion-20261116/` for before/after fixes and recovery
- `output/playwright/ai-native-onboarding/M6/baseline-20261116/` for original Spanner, Northstar and incomplete procurement observations

The M5-1/2 independent clarity recheck is still required before any human session. Fold in the focused tasks from `docs/review/2026-11-16-m5-clarity-fable-review-prompt.md`; do not silently waive it.

## Decisive checks

1. Memory event identity: review the actual diff in `src/context_graph/adapters/memory/log.py` and `tests/unit/test_memory_event_identity.py`. Confirm identical retry versus conflicting content, metadata handling, expiry behavior and compatibility of `_store` for imports/direct append. The claim is batch request comparison, not tenant authorization. Verify frozen story expectations were not edited.
2. Explain scope: review `src/context_graph/workbench/explain.py`. Instructions now match existing server rules; verify no grounding or consent gate was relaxed. Retain the first rejected live response and successful later call in the disposition.
3. Live CRM chain: compare baseline, explanation, operator answer, submitted request, author output, review and sandbox. Verify source/question preservation and normalized lifecycle/deal projection/retrieval equality. Judge usefulness and engine-vocabulary leakage separately from HTTP success. One successful chain does not prove general self-service.
4. Oracles: graph assertion Acme exists is sourced and recorded before execution, but implementer-reviewed. Existing question oracles must be unchanged. Do not call these independently reviewed unless you actually review them.
5. Spanner: inspect failed epoch 32, later ready check, and successful epoch 33 cleanup/release. A successful rerun is not a root-cause fix for the earlier timeout. Compare current memory/Spanner story, pack and engine identities. No new cloud run is necessary for artifact review; report if live re-execution is needed.
6. UI failure/recovery: wrong answers remain failures; scalar remains unsupported; read-only explanation cannot change the story; rerun preserves expectations. Retry/restore uses one request editor and an explicit review gate. Confirm no-lifecycle and relationship-free cases are distinct fixtures, not cosmetic domain renames.
7. Source race: the browser response was not observed; only stale API 409 and withdrawal/no displayed old claim are recorded. Decide whether the remaining late-response trace is material to bounded M6 acceptance. Do not report it as a full UI 409 reproduction.
8. Graph review friction: selecting nodes and ticking confirmation in one save clears the tick. The operator must revisit and confirm saved selections. Judge severity and whether this needs correction before human sessions; no server gate was bypassed.
9. Reconcile exact test selection, build identity, reused process disclosure and new frontend bundle hash. Preserve earlier M0/M2b/M3/M4/M5 findings instead of assuming this handoff closes them.

## Output

Save `docs/review/2026-11-17-m6-fable-independent-review.md` and evidence under `output/playwright/ai-native-onboarding/fable-m6-20261117/`. Give separate functionality, visual clarity, AI helpfulness, integration and tested-accessibility verdicts. List blocking findings with smallest correction/recheck, and explicitly separate technical acceptance from the outstanding real-operator study. Do not modify product code or recorded expectations as part of the review.
