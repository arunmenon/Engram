# M2b interaction changes and independent review ask

The operator can now ask about a record, relationship or whole pack using the existing revision-bound explanation service. Review separates what the agent understood from required decisions. Change acknowledgements are grouped by category; removals remain explicit. Trust controls are in Tenant setup. Normal navigation skips the optional engineering screen.

Technical verification: 99 targeted backend tests, 13 frontend helper tests, build, Ruff and mypy pass. Real Chrome fixture checks cover CRM, delivery and the final authored Northstar artifact. Consent changes preserve a prepared request and block sending. Switching the selected pack element does not hide the request. Clearing it returns focus to the selector.

Evidence/reproducibility: `output/playwright/ai-native-onboarding/M2b/review-20261106/README.md`.

**Bounded status:** interactions verified; live plain-language helpfulness and independent acceptance remain open. CRM still measures 4,890px and delivery 4,362px. F04 is not closed by this work. No provider, sandbox, Spanner or activation run occurred.

## Fable ask

Apply `.claude/skills/ai-native-ui-review/SKILL.md`. Use fresh reviewer-owned copies and record actual bundle, backend and draft identities. Attempt a domain task before reading detailed implementation findings; disclose prior familiarity. Do not modify original or implementer drafts as acceptance cases.

Verify:
1. Pack/node/edge questions select the correct revision-bound evidence; no cross-draft or previous-selection result leaks. Unsupported questions remain unknown rather than invented engine limits.
2. A prepared request stays visible exactly once when the selector changes, through local-only consent, and after recovery. Clear returns focus meaningfully. Extend browser coverage to reload, failed send, legacy restore and late responses; distinguish unexecuted cases.
3. Group acknowledgements carry every reviewed change ID; omitted changes/removals remain blocked server-side. Material consequences remain visible. Grouping must not conceal unexpected scope changes.
4. Trust settings are easy to find in setup; banners and disabled actions agree. Trust confirmation is not silently supplied.
5. Continue/Back skip optional engineering details; direct technical navigation still works. Inspect keyboard and narrow layouts.
6. Assess clutter and vocabulary against operator-authored business sources, excluding schema contracts. Measure issue-to-action distance and page height. The new fixture explanations do not establish live reasoning quality.

Report functionality, visual clarity, AI helpfulness and accessibility separately. Preserve the high-severity F04 wording finding until live evidence and operator-oriented review justify closure. No code changes or oracle edits during review. Do not initiate provider/cloud runs without corresponding review authorization.
