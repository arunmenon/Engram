# M5 recovery: Fable checkpoint

M5 is ready for independent review of the bounded intake/unresolved-input flow.
It is **not independently accepted**, and M6 has not started.

## Identity and scope

Codex implementer-directed check, 2026-11-16 Asia/Kolkata. Branch
feature/engram-walkthrough, HEAD 27b4ba8, large existing dirty tree. No deployment/commit.
Fresh service http://127.0.0.1:8126/workbench.html, operator m5-implementer; separate
SQLite store. Same synthetic procurement inputs as the failed November 13 case,
seeded into a fresh draft. Engine/source/snapshot hashes in the evidence manifest.
Frontend unchanged, bundle workbench-DP1IaDfs.js.

Headed Google Chrome through Python Playwright, 1440×1000 and 430×932, default zoom.
Tokens read inside scripts only. One explicitly consented live author job using the
previously configured gpt-5.2-2025-12-11. No Spanner, sandbox run, activation or human study.
No reviewer service or draft was modified.

Evidence: output/playwright/ai-native-onboarding/M5/recovery-20261116/.
Earlier deterministic intake evidence: M5/intake-20261113/.

## What changed

Only authoring.py and its focused intake test changed in this correction.

1. The author receives the real retrieval-pattern contract: regular expressions, not
   brace templates; first capture (or whole match) is searched against the final key
   field. Multiple captures do not construct a composite identity or restrict account
   scope. A tested example is supplied; patterns are optional, not a required guess.
2. For initial requests missing relationship evidence, including questions with no
   internal intent identifier, instructions explicitly require a conceptual proposal
   with no executable pack. Do not substitute an unrelated simpler intent. Existing
   revisions must preserve supported behavior.
3. Operator-facing questions must ask business facts and supporting material, not
   demand internal edge names, interfaces or pack syntax. Conflicting policies remain
   explicit decisions.

These are prompt/capability improvements, not a deterministic language enforcement
layer. Existing engine, citation, consent, ownership and review gates are unchanged.
No silent pack repair, oracle edit, regex rewrite or invented domain relationship.

## Verification

- 194 workbench backend tests pass; Ruff and targeted mypy pass.
- Added test verifies the example regex compiles, captures the intended token and
  does not match empty text, and checks the supplied capability/clarification contract.
- Earlier final frontend build/19 helper checks and mixed-source Chrome cases apply:
  no frontend product changes in this correction.
- Live initial authoring: completed in 26.3 seconds, returned pack=null, three unresolved
  decisions and cited concepts. One job; attempt count was not retained, so no claim
  of a particular attempt count.
- The three decisions ask: what links a supplier to a request and where is the evidence;
  whether an approved request can reopen; whether identical IDs across units refer to
  one request or separate requests. No request for an engine edge name or syntax fix.
- Source material and canonical saved questions/expected answers are identical to
  before the run. No expectation rewritten to turn a failure into a pass.
- Author request before consent returns 409. UI policy/redaction confirmation precedes
  the live call. Final state is visibly unresolved; test/handoff readiness is false.
- Read-only final 430px inspection has no horizontal overflow; recorded revision,
  proposal and content stay unchanged. No new provider call in that inspection.

## Known limits for Fable to judge

The decisions are now business questions, but their effect text and summary still
contain terms including "graph retrieval intent", "stable key" and "lifecycle".
The limitation panels are long and repeat some decision content. Do not claim these
are fully polished or that prompting guarantees plain language. Judge whether they
block the bounded task; preserve the finding if further copy/presentation work is needed.

This run demonstrates an honest unresolved outcome, not a working procurement pack,
not successful recovery of the old invalid pack, and not successful question answering.
The valid-regex branch is unit-tested but was not needed in the live clarification.
Existing invalid-pack/failure behavior is unchanged.

## Review gate

Fable must review M5 before M6. Ask is in
`docs/review/2026-11-16-m5-fable-review-prompt.md`.
Earlier M0/M2b/M3 findings, M4 RR-2–4/M4-4–12, broader live reasoning, Spanner and human
comprehension remain open. Do not promote earlier evidence into new acceptance claims.
