# Independent review: complete agentic onboarding remediation

Review the current implementation in `/Users/arunmenon/projects/Engram` on
`feature/engram-walkthrough`. Review all onboarding remediation since the independent
November 4 assessment, including the latest trust-provenance change—not only the last patch.
Give an independent verdict; do not treat implementation notes or passing tests as proof.

## Scope and baseline

Read these first:
- `docs/review/2026-11-04-agentic-onboarding-independent-review.md`: independent baseline findings.
- `docs/review/2026-11-04-agentic-onboarding-review.md`: original assessment plus all implementation and verification follow-ups. Later sections qualify earlier claims.
- `docs/tenant-admin-workbench-plan.md` and `docs/workbench-storyboard.md`: intended operator experience; distinguish future scope from implemented behavior.
- `docs/review/2026-11-05-onboarding-review-manifest.json`: HEAD and hashes of current review inputs.

The working tree contains extensive older unrelated changes. Most workbench files are
untracked: inspect their contents, not just `git diff`. Do not attribute the entire dirty
tree to this remediation. Report baseline uncertainty explicitly. Follow dependencies
into engine code when necessary, but do not expand this into a review of all historical
Spanner, tenancy, retrieval or video work. Detect file drift against the manifest.

## Changes to assess together

1. Failed/cancelled author jobs preserve the last usable proposal, review, validation,
   sandbox and approval where compatible. Check revision fencing and stale evidence.
2. Structural pack changes require acknowledgement, including keys, guards, handling,
   retrieval and removals. Repeated regeneration must not erase the comparison baseline.
3. Identity/lifecycle attestations replace standing questions. Decisions link to pack
   elements; acceptance and readiness remain enforced on the server.
4. Structured expected IDs, graph expectations and business expected-answer text stay
   out of author prompts. Check previous feedback, revisions and story prompts as well.
5. Authored packs can create story workspaces with immutable composed-pack snapshots.
   Check dependencies, digest validation, parent isolation and review before execution.
6. Generated stories use typed assertion schemas, correct event envelopes, zero-based
   checkpoints and canonical node IDs. Check PDLC compatibility, meaningful negative
   assertions, malformed-input rejection and honest failure guidance.
7. Direct revision requests can support operator facts via exact `instruction_quote`.
   Check stale/replaced requests, invented quotes, persisted history and UI explanation.
8. Every model-generated edge needs a specifically linked source/operator fact. Assess
   both enforcement and its limits: an exact quotation does not establish entailment.
   Can unrelated citations or operator instructions launder invented relationships?
9. Initial edge-free packs whose requested intents are rejected by the engine can
   become conceptual drafts with clarification questions. Check that this neither
   conceals syntax errors nor modifies questions/expected answers, and that revisions
   retain appropriate prior-pack handling. Look for duplicate or misleading questions.
10. `Fact.trusted_producers` snapshots reviewed trust settings. Verify exact membership,
    reviewed-empty versus unreviewed, changed settings, backwards compatibility, and
    that trust evidence cannot justify domain relationships. Does the UI show the
    evidence clearly? Do ingest acceptance and retrieval trust remain distinct?

## Primary code

Backend: `src/context_graph/workbench/`—especially `api.py`, `authoring.py`,
`models.py`, `changes.py`, `draft_stories.py`, `journey_authoring.py`,
`journey_checks.py`, `journey_runner.py`, `journeys.py`, `engine.py`, `store.py`,
`execution.py`, `job_errors.py` and `storage_views.py`.

Frontend: `demo/frontend/src/workbench/`—especially `Workbench.tsx`,
`OperatorFlow.tsx`, `JourneyAuthor.tsx`, `JourneyWorkspace.tsx`, `types.ts`,
`results.ts` and `editing.ts`.

Tests: `tests/unit/test_workbench*.py`, `tests/fixtures/workbench/`,
`demo/frontend/tests/workbench-*.test.ts`.

## Evidence to challenge

- `output/playwright/onboarding-live-20261105/`: earlier full real-provider UI and
  Spanner exercise. Inspect verification-summary.json, final-parent.json,
  final-story.json and screenshots. Reported: Northstar F1 1.0, story 16/16 checks,
  cleanup verified. These runs predate the latest provenance changes.
- `output/playwright/onboarding-improvements-20261105/`
- `output/playwright/onboarding-improvements-grounded-20261105/`
- `output/playwright/onboarding-improvements-final-20261105/`
- `output/playwright/onboarding-improvements-clarification-20261105/`
  These retain failed and corrected attempts; do not cherry-pick the successes.
- `output/playwright/onboarding-trust-20261105/`: latest direct provider checks and
  actual Chrome authoring attempt. Direct complete case validated in one attempt
  without blocking questions; incomplete case used reviewed trust but still generated
  two relationship questions. The Chrome attempt returned a conceptual proposal
  asking about quoting JSON source excerpts. It was NOT successful full onboarding,
  and did not visually demonstrate the new trust label with a live trust fact.

Latest reported checks: 54 authoring/API tests + 46 execution/story/Spanner-API
regressions, seven frontend tests, production build, Ruff and mypy. Independently
rerun meaningful checks. Distinguish real provider, fixture author, memory sandbox,
Spanner test doubles, real Spanner and browser proof. Do not infer a new real-Spanner
run or production rollout from these latest regression results.

Suggested commands:
```sh
.venv/bin/python -m pytest tests/unit/test_workbench.py tests/unit/test_workbench_execution.py tests/unit/test_workbench_draft_stories.py tests/unit/test_workbench_journeys.py tests/unit/test_workbench_spanner_api.py -q
.venv/bin/ruff check src/context_graph/workbench/authoring.py src/context_graph/workbench/models.py tests/unit/test_workbench.py
.venv/bin/mypy src/context_graph/workbench/authoring.py src/context_graph/workbench/models.py
```
In `demo/frontend`, run `npm run build:workbench` and the `workbench-*.test.ts`
Node tests using a Node version supporting `--experimental-strip-types`.

## Review method and boundaries

Review correctness, operator usability, semantic grounding, oracle independence,
state recovery, compatibility, security/privacy and unnecessary complexity. Prioritize
reproducible behavioral defects over style. Use focused negative probes in isolated
temporary stores, without modifying accepted packs or expected answers to make tests pass.

The architecture remains a constrained, tool-free LLM authoring loop. Check whether
it now meets its intended use; do not assume converting it to a coding agent is needed.

Review only: do not edit product code, packs, expectations or original reviews. Do not
restart the live workbench, alter existing drafts/databases, or issue new paid-provider
or cloud-write operations just to complete this review. Use saved live evidence and
isolated local probes; state any fresh verification still needed. Never print credentials.
If inspecting the live UI, preserve its state and report exactly what you observed.

## Deliverable

Write `docs/review/2026-11-05-agentic-onboarding-remediation-independent-review.md`.
Include:
- Verdict and precise scope/commit/working-tree identity.
- Findings by severity, with file:line, trigger, observed versus expected behavior,
  operator impact, reproduction/evidence, and smallest adequate correction.
- A closure table for every November 4 finding: fixed, partially fixed, open, or
  unverified. Separate newly introduced regressions from pre-existing issues.
- An assessment of each of the ten change groups above, including whether safeguards
  are server-enforced, prompt-only, or merely demonstrated by one model response.
- Verification actually performed, with failures and limits.
- Explicit disposition of duplicate clarification questions, exact-JSON-quote failures,
  trust evidence UI coverage and live non-PDLC behavior.
- What must change before calling this a reliable operator-assisted onboarding flow.

Do not implement fixes during the review. If you find no new defects, explain the
remaining limitations rather than substituting an unconditional approval.
