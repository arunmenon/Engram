# M4 — failed-check guidance and story coverage

## Status and run identity

Implemented and verified by the implementer; **independent acceptance pending**.
2026-11-10, Asia/Kolkata. Branch feature/engram-walkthrough; HEAD 27b4ba8 with an
extensive pre-existing dirty/untracked tree. Final frontend: workbench-COwj1mXB.js.
Source, bundle and snapshot hashes, copy IDs and start/end revisions are recorded in
`output/playwright/ai-native-onboarding/M4/review-20261110/final/manifest.json`.
Fresh isolated service: port 8117, operator m4-implementer, SQLite draft store.
Real ingest/ledger/projection/retrieval executions in isolated memory. Fixture explainer
and fixture outline author; no live provider, Spanner, deployment or human study.
Headed Chrome through Python Playwright, 1440×1000 and 430×932, default zoom.
Credentials read within scripts, never emitted. Reviewer services were untouched.

M3 is independently accepted for its bounded fixture scope per
`docs/review/2026-11-10-m3-clarity-fable-re-review.md`. M3 lows and other milestone gates
remain open. M4 does not imply live reasoning or self-service acceptance.

## Operator behavior

Results appear before the coverage inventory. A failing check first explains what was
observed and where to inspect: event handling, graph/mapping, answer scope, unsupported
capability or execution failure. Guidance is deterministic and does not infer a root
cause from a mismatch. Missing domain specification is called out explicitly.

The operator may ask the agent about that check through the existing explain endpoint.
The server assembles the reviewed expectation, recorded output, checkpoint event and
matching projection rules. For final-graph questions it includes the explicit intent's
pinned retrieval settings; it does not invent a single causal event. Missing or oversized
evidence is refused or described honestly. The response is revision-bound and read-only:
repair instructions and options are rejected for this scope. The operator must explicitly
review and save provider permission before the first call. Existing ownership, running-job,
capacity and timeout controls remain in force; the result/snapshot is also bound across
an in-flight explanation.

Coverage lists domain event handling, rejection scenarios, state assertions, declared
question intents and the story's questions/checks. Built-in root capabilities are outside
this inventory. States distinguish no check, defined, executed, passing, stale and an
assertion whose strength needs review. Unsupported/not-run results do not count as executed
proof. Event delivery counts are not behavioral coverage. State assertions associate a
record type and checkpoint; they are not proof of causality or exhaustive guard coverage.
Final-graph checks without an event checkpoint remain in the complete check list.

The default list shows gaps, is searchable, and expands in groups of eight. Named checks
behind each status remain inspectable. A missing item or failed check can append a goal
to the existing story-authoring form without overwriting the brief. The operator still
reviews the specification, outline and each assertion through the existing gates.
Nothing is generated or approved merely by clicking a coverage action. Inspect event
moves focus to the actual observed timeline.

The story and pack snapshots remain pinned. Engine/story/pack identity changes make
results stale; invalid snapshot identity makes coverage incomplete. A parent pack's newer
version is not silently substituted into a frozen story.

## Assertion safeguards

Existing strict expected-value/type validation and per-check review are reused.
Newly generated property checks with no asserted fields are refused. Reviewed historical
presence-only property assertions are preserved and visibly flagged as insufficient proof
of a property update. Relationship assertions with impossible declared endpoint types
are rejected, including negative assertions; raw Event provenance identities remain valid.

A passed absence check with missing relationship endpoints, a missing record in an evidence
absence check, and a question without answer assertions are flagged as weak proof. The
recorded result remains intact; the UI does not turn it into full behavioral proof or
rewrite the oracle. These are specific deterministic checks, not a claim that every
possible vacuous or semantically incorrect assertion can be detected automatically.

## Verification

- Full workbench unit suite: **187 passed**, recorded in `backend-tests.txt`.
- Final focused check/explain suite: 36 passed; 18 existing frontend helper checks pass.
- TypeScript/Vite build, Ruff and mypy pass for touched backend modules.
- Real isolated-memory support story and CRM story pass; their coverage still shows
  behavior not checked. The investigation fixture intentionally retains a wrong-account
  answer, mismatched title, unsupported scalar question and weak relationship-absence check.
- Chrome verifies distinct guidance, source uncertainty, explicit consent, check-scoped
  explanation, no repair/expectation-edit controls, follow-up outline through the existing
  workflow, and a real rerun. Intentional failures remain failures after rerunning.
- A separate real-engine unit case uses a valid but semantically wrong projection (title
  mapped from the incident ID). The explanation context retains the input title, wrong
  rule and observed mismatch. Unknown payload paths are already rejected by compilation.
- Additional tests cover stale pack/story results, untouched oracles, owner isolation,
  consent refusal, evidence references, no repair instruction and assertion validation.
- Narrow browser layouts have no horizontal overflow. Screenshots inspected. Keyboard
  focus reaches the follow-up brief; graph inspection has an explicit focus target.

A browser check found that tenant-card clicks during sign-in/navigation could be ignored
by the existing busy guard. Cards are now disabled while that operation finishes.
The coverage select now has an explicit accessible label. These are small fixes directly
encountered while exercising the operator journey.

The first runtime test for an undeclared projection path was correctly rejected by the
existing compiler. The wrong-field case instead uses a declared field of the wrong business
meaning; no payload contract or reviewed expectation was weakened to make a test pass.
Legacy PDLC presence-only property assertions were preserved, not rewritten.

## Evidence boundaries and outstanding work

This was a directed implementer check, not an uncoached operator study. Fixture reasoning
and outline text demonstrate wiring and controls, not live-agent quality. The UI does not
repair a pack, determine which business expectation is correct, or silently approve a
follow-up. The test rerun retains the deliberate failures; the separate passing stories
provide the positive control.

Functionality: pass for tested cases, independent review pending.
Clarity: inspected result-first flow, domain coverage inventory and narrow layout; Fable
should review whether the guidance is actionable without engine knowledge.
AI helpfulness: deterministic guidance and fixture explanation verified; live reasoning
not exercised. Accessibility: narrow reflow/focus tested; no screen reader/WCAG claim.

Recovery matrix: consent change and rerun observed; source/snapshot staleness and owner
fencing tested at API/unit level. Reload/restore, failed author send, legacy restore,
sign-out clearing, late explanation after cancel, and save during editing were not
re-exercised in the final browser pass. Existing regression suites pass; this does not
replace fresh browser evidence for those states. No Spanner or deployment testing.

M0 replay reconciliation, remaining M2b gates, M3 low findings and M6 human comprehension
remain open. M5 has not started. Next is an independent M4 review.
