# M4 RR-1: retain generated-story acknowledgements during polling

## Change

Only product file changed: `demo/frontend/src/workbench/JourneyAuthor.tsx`.
The review reset effect now depends on serialized proposal content, draft ID and draft
revision. Identical polling responses no longer clear the per-check or overall review.
A changed proposal, revision or tenant still clears both. Save and server acceptance
requirements are unchanged. No backend, pack, expected answer or runner change.

This closes the reported object-identity defect; it does not add persistence across
reloads or navigation, and does not change the existing conservative revision reset.

## Verification identity

Codex implementer directed recheck, not independent or human acceptance; 2026-11-13,
Asia/Kolkata. Existing feature/engram-walkthrough branch at 27b4ba8 with a large dirty
working tree. Bundle `workbench-CjndwSEA.js`. Hashes and draft identities in manifest.json.

Fresh isolated fixture service on port 8121, operator `m4-poll-implementer`, its own SQLite
store. Seeded copies originate from the identified M4 remediation snapshots; no reviewer
store or original was modified. Headed Chrome via Python Playwright; 1440×1000 then
430×932 at default zoom. Token read inside the script, never printed.
Fixture outline/variant author uses the real validator. No live provider, Spanner,
deployment or human study. This check does not execute a story; it tests review and save.

Evidence: `output/playwright/ai-native-onboarding/M4/poll-remediation-20261113/`.

## Focused browser check

1. Generate a variant containing 15 checks through the UI.
2. Select each check slowly enough to span multiple refreshes, then select overall review.
3. Wait ten seconds. Every tick and the enabled Save button remain, with real polling
   responses counted and a per-second timeline recorded.
4. Generate a replacement variant. All check ticks and overall review clear; Save disables.
5. Review again, wait another ten seconds, then save at 430px. The server returns 201
   and creates the new workspace. No horizontal overflow or page errors.

Build/TypeScript and all 18 frontend helper tests pass. Backend unchanged; the prior
190-check result is inherited evidence, not a new backend run.

Two automation setup corrections are disclosed: the first attempt did not reopen the
regenerated check disclosures; the second expected 200 instead of the documented 201
creation response. Both logs are retained. The final script opens disclosures through
the UI and asserts 201. Neither workaround changes polling or saves within one refresh.

## Scope and next review

Functionality: the focused ten-second check verifies retention and genuine-generation
reset. Visual scope: review controls and narrow-layout save; existing JSON/density lows
remain. AI helpfulness not exercised. Accessibility evidence is limited to native checked
controls and 430px overflow; no screen-reader or WCAG claim.

Fable has independently closed M4-1–3. RR-1 is now implementer-rechecked; the final
record is available for the focused reviewer confirmation. M5 has not started in this
remediation. RR-2–4, M4-4–12, live-agent verification and prior M0/M2b/M3/M6 gates remain
open. Reviewer services were left untouched.
