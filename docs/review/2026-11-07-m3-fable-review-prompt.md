Review M3 independently before accepting it. Do not implement fixes or alter existing packs,
expected answers, reviewer services or implementer drafts.

Read the project and frontend instructions and apply the ai-native-ui-review skill.
Plan: docs/ai-native-onboarding-milestone-plan.md, M3.
Implementation: docs/review/2026-11-07-m3-decision-preview-implementation.md.
Evidence and runnable fixture scripts:
output/playwright/ai-native-onboarding/M3/review-20261107/.
M2b acceptance: docs/review/2026-11-07-m2b-blocker-fable-re-review.md.

Create fresh reviewer-owned copies and a separate service/store. Read credentials directly
inside automation; never print them or type them through assistant tool arguments. Record
build hashes, source snapshots, draft IDs/start/end revisions, operator label and port.

First attempt these operator tasks without inspecting implementation details:
1. Support operator: decide whether case 42 in two accounts is one history or two.
2. CRM operator: inspect what happens to contact history when email changes.
3. Support operator: compare resolution guards, then repeat without a resolution example.
Log actions, confusion and help needed. Simulated personas are not human comprehension.

Then verify:
- Options are neutral and grounded; planned counts match genuine planner output.
- State requests are not represented as executed/accepted transitions.
- Missing sample coverage disables the option and explains what to supply.
- Conflicting source material is preserved; neither agent nor UI silently settles it.
- Prepare uses one request editor, preserves existing text, focuses it and allows Clear.
- Choice never mutates pack, oracle or approval; revision/proposal changes invalidate it.
- Options cannot escape allowed edit paths; bad evidence and unsupported scopes fail closed.
- No-lifecycle types are not forced into lifecycle decisions.
- Timeouts retain capacity while background read-only planning finishes.
- Inspect 430px layout, keyboard focus, density, business wording and duplicated actions.
- Check source-change/reload/stale request behavior and the M2b failure-recovery regressions.

Separate functionality, visual clarity, AI helpfulness and accessibility verdicts. Name any
scope gap against M3. Fixture success is not live reasoning, successful authoring, Spanner
execution or self-serve acceptance. Preserve all outstanding M2b/M0/M6 gates.
Save report to docs/review/2026-11-07-m3-fable-independent-review.md with evidence path.
