# M5 clarity remediation — implementer verification

M5 remains independently accepted for its bounded scope per `2026-11-16-m5-fable-independent-review.md`. M5-1 and M5-2 are implemented and locally verified. Independent recheck is pending before an M6 human session.

## Identity and evidence

- Reviewer: Codex implementer, **not independent acceptance**, 2026-11-16, Asia/Kolkata. Implementation was read before browser checks; this is not an uncoached persona study.
- Branch/HEAD, changed-source and served-bundle hashes: `output/playwright/ai-native-onboarding/M5/clarity-20261116/manifest.json`. Large pre-existing dirty tree; no commit or deployment.
- Fresh isolated service: `http://127.0.0.1:8132`, operator `m5-clarity-implementer`, SQLite authoring storage, refusal stubs for author and explainer. No provider or Spanner call.
- Headed Google Chrome via Python Playwright; credentials read inside script from local file, never included in evidence. Viewports 1440×1000 and 430×932, default zoom.
- Procurement copy seeded from M5 recovery `live-result.json`; sales copy from intake `copies-end-full.json` (Sales contact continuity intake). Exact IDs/revisions in manifest and start/end snapshots. Originals untouched.

## Changes

**M5-1:** The authenticated inventory response includes each sample's payload, source name and example number once. Repeated values expand into labelled fields from the corresponding examples, so ID 42 can be inspected alongside unit east and west. Search includes values, not just field/event names; an empty result names the search and suggests another value. No identity rule is inferred.

**M5-2:** When a proposal has recorded decisions, those fields are the answer area; limitation panels retain explanation but no longer add competing answer boxes. Decision explanations also do not create a second answer area for an unknown response. Earlier notes are retained, and existing prepared-request rendering is unchanged. One shared link leads to the recorded questions, and one Add supporting material action returns to intake. Apply explains whether work is running, answers are missing, no new answers exist, or answers are ready. Unknown facts can stay blank: no fabricated “not known” decision is inserted and server readiness is unchanged. This consolidates by explicit decision presence, not guessed semantic similarity between sentences.

## Verification

- 194 workbench backend tests and 19 frontend tests pass; frontend typecheck/build, targeted ruff and mypy pass.
- Procurement inventory: search 42, expand repeat, read east and west without JSON. Search east works; unmatched search gives an explicit message.
- Sales inventory: repeated value and surrounding fields visible at 430px.
- Procurement decisions: three questions, three recorded answer boxes, zero competing Your answer boxes. Partial answers keep Apply disabled with a reason; all three answers enable it; clearing unknown answers disables it again. No submission made.
- Typed decision retained after four seconds of polling, navigation and reload/sign-in. Keyboard link focuses recorded-question heading. Narrow layouts have no horizontal overflow; no page errors.
- Sources, expected questions and proposal unchanged on both copies; only procurement operator-decision text changed.

Functionality: pass for these checks. Visual clarity: implementer pass for touched states. AI reasoning: not exercised. Accessibility: tested focus/reflow only; screen reader and full keyboard audit not exercised.

Recovery coverage: polling/navigation/reload exercised. Failed send, legacy answer restoration, consent change, tenant switch while editing, sign-out storage clearing, cancel and late responses not re-exercised. Retained historical notes and prepared requests need targeted independent regression coverage because consolidation touches their surrounding UI.

## Next checkpoint

Use `2026-11-16-m5-clarity-fable-review-prompt.md` on fresh reviewer-owned copies. M5-3–9, earlier milestone lows, M0, and live-agent/Spanner/human gates remain open. The previous live run demonstrated compliance with explicit conflict/linkage instructions, not unprompted detection; it retained no provider request ID. No broad self-service or shipping claim follows from this remediation.
