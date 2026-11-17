# Workbench intake implementation — verified local slice

The requested scoped intake-to-handoff journey is implemented and verified locally. Changes remain uncommitted; no tenant runtime has been activated. This is a local operator workspace, not completion of every future phase of the broader control-plane plan.

## Implemented

- Standalone React operator UI in `demo/frontend/src/workbench`, with a separate build from the legacy demo. Seven progressive screens: scope/data handling, grounding inputs, model/decisions, contracts/mappings, questions/trust, evaluation, review/handoff.
- `src/context_graph/workbench`: operator-token authentication, operator-owned SQLite drafts, optimistic revisions, durable audit records, consent-gated bounded author jobs, verified source quotations, real pack composition/admission/planner validation, memory-ledger/projection-worker/retrieval sandbox, digest-bound handoff approval and canonical YAML export.
- Real engine snapshots preserve each event's historical state. A UI check caught shared mutable snapshot data; a regression now asserts open after event one and resolved after event two.
- Job cancellation and newer-input edits prevent stale model results from replacing newer drafts. Lifecycle cleanup and restart recovery are covered by tests. Revision requests carry previous proposals, rejections and validation feedback; removed sources are excluded from that context.
- No live stores are opened by the sandbox. It uses the engine's memory reference backend and simulates source trust; it does not prove Spanner fencing, producer authentication or deployed worker behavior.

## Verification — 2026-10-31

- `pytest tests/unit/test_workbench.py -q`: eight tests passed. Covers real-engine scenario and wrong-answer failure, operator isolation, consent refusal, revision conflicts, cancellation, edit invalidation, persistence, interrupted-job recovery fabricated-citation rejection, rejected-fact revision context, removed-source exclusion, engine-revision invalidation and oversized-request refusal.
- Ruff, mypy and standalone `npm run build:workbench` passed. The legacy `npm run build` has pre-existing demo type errors in graph/user stores and callers; these were not hidden by changing their compiler settings.
- Computer use in Chrome exercised create → scope/privacy → three grounding sources → identity/lifecycle decisions → questions and trust → cited fixture proposal → real engine validation → sandbox → approval for handoff. UI showed mean F1 1.0, correct open/resolved snapshots, rejected malformed event and activation not requested.
- Screenshots: `output/workbench/intake-handoff.jpg`, `intake-schema.jpg`, and `intake-mobile.jpg` (generated locally, ignored by Git). Final browser fixture draft reached revision 31, approved for handoff.
- Browser negative check: an incorrect expected entity reduced mean F1 to 0.6667 against the 0.8 threshold and disabled approval. Correcting it required fresh review and evaluation. Reject/accept controls, comma-separated entry, review invalidation and keyboard graph selection were exercised.
- Switching tenants cleared unsaved source text and showed no inherited evidence. Narrow-screen measurement showed page width equal to viewport width (354 CSS pixels) and zero unlabeled grounding-form controls. Viewport reset afterward. This is a focused check, not a full accessibility audit. Browser console inspection returned no captured errors.
- Restarting the API after engine changes required revalidation; the refreshed positive browser scenario passed again.
- Fixture author is explicitly labelled TEST FIXTURE and only exists in the opt-in development launcher. The normal API does not simulate model output.
- Live configured model checks on synthetic input initially exposed invalid quotations and engine-invalid declarations. The author loop now includes bounded repair using quotation and engine validation feedback. The revised configured-model run passed engine validation and the real memory sandbox with mean F1 1.0. Evidence: `output/workbench/model-proposal.json`, `model-validation.json`, and `model-sandbox.json`. It proposed nine facts and left one account-modeling decision open. That candidate was not approved: successful mechanics do not settle the open domain decision. The live-model component check and fixture-driven browser journey are separate evidence.

## Scope and remaining product work

- New tenant drafts run through artifact handoff. Live-tenant updates, replay/rebuild, production identity integration, deployment provisioning and runtime activation remain future work. Activation and target intent readiness are explicitly separate and unavailable here.
- Text/JSON intake is supported. PDF/OCR, external document connectors, retention/decommissioning policies and richer visual editing are future work. Pack changes are requested through the author; model/contracts/mappings are inspected in the UI and generated YAML is read-only.
- Authoring is a bounded, tool-free model loop with real validation and repair. It cannot edit engine code, access live tenant databases or run shell commands. Quotation validation establishes excerpt existence, not correctness of every inference; operator review remains necessary.
- Sandbox evidence covers deterministic projection and retrieval on fresh memory stores. It does not cover deployed ingress, Spanner fencing, extraction workers, production producer authentication or target evaluation recording.
- UI testing used the clearly labelled fixture author. A separate synthetic-input check exercised the live configured model. No claim of a real-provider browser run is made.
- No unrelated working-tree changes were reverted or committed.

## Requirement-to-evidence map

| Requested behavior | Evidence |
| --- | --- |
| Tenant/environment drafts | Owner-scoped durable records; second-tenant browser check |
| Privacy before model calls | Server-side consent/redaction gates; refusal tests |
| Flexible grounding inputs | Source inventory and field statistics; browser three-source journey |
| Grounded proposals and decisions | Verified excerpts, inference labels, accept/reject and decision queue |
| Executable model and mappings | Real composition/admission/planner, sample paths, schema graph, lifecycle guards and observed graph |
| Canonical questions and trust | Shared EvalSet export; wrong-answer failure; explicit sandbox source policy |
| Truthful readiness | Engine/input digests, edit invalidation and failed-evaluation approval refusal |
| Agent iteration | Prior review context and bounded repair; live-model validation/sandbox pass |
| Actual UX testing | Computer-use positive/negative flows, screenshots, narrow layout and keyboard checks |

## Local run commands

Set `ENGRAM_WORKBENCH_TOKEN` to a random token of at least 24 characters and `ENGRAM_WORKBENCH_DB` to a local control-store path. Set `ENGRAM_WORKBENCH_MODEL` explicitly to the desired configured LiteLLM model for real authoring. Do not put provider keys into browser forms or tenant inputs.

```sh
.venv/bin/python scripts/engram_workbench_dev.py
npm --prefix demo/frontend run dev:workbench
```

Open `http://127.0.0.1:5174/workbench.html`. The API binds to loopback port 8101. It is a single-process local operator workspace, not a deployed production control plane. Use `--fixture-author` only for synthetic UI testing; the fixture is `tests/fixtures/workbench/incident.json`.

```sh
.venv/bin/pytest tests/unit/test_workbench.py -q
.venv/bin/ruff check src/context_graph/workbench tests/unit/test_workbench.py scripts/engram_workbench_dev.py
.venv/bin/mypy src/context_graph/workbench --follow-imports=silent
npm --prefix demo/frontend run build:workbench
```

## Operator usability redesign — 2026-10-31 (verified local slice)

Review verdict on the previous UI: **REVISE**. It exposed engine structure instead of guiding the operator's task. The Northstar walkthrough supplied direct evidence: users could not tell whether an uploaded file was saved or correctly classified; raw node IDs were required; the questions screen did not explain its purpose; the assistant produced 21 separate approval items; and a failed query provided little help choosing the next action.

| Finding | Correction | Verification target |
| --- | --- | --- |
| Seven technical sections and a permanent assistant competed for attention | Six task-oriented stages, one next-action panel, contextual assistant inside model review | Operator can locate next step on a blank, pending and failed draft |
| Source upload silently filled a form and defaulted everything to specification | Explicit preview → confirm category → add-and-save; JSON category inference and editable saved categories | Source is persisted by Add, wrong category can be corrected without re-upload |
| Review required repetitive per-fact approvals | One model acceptance covering identity, lifecycle, evidence and limitations; citations and individual rejection remain available | Rejecting evidence blocks acceptance; acceptance remains server-enforced |
| Agent panel repeated the last message and buried output | Fresh request composer, concise grouped proposal instructions, elapsed task state, saved request/response history | Real model request produces a reviewable reply with honest limits |
| Choosing expected answers invalidated the model | Scenario-only edits revalidate and invalidate tests/approval while preserving model review | Integration test adds questions after model review and reruns without another author call |
| Revision request lost failure feedback | Carry prior evaluation into author context; retain previous sandbox as explicitly historical evidence | Regression test proves exact failure reaches revised author call |
| Internal IDs and tuning dominated question editing | Searchable expected entities; starting points and retrieval settings optional; readable result labels | Browser search and selection, unchanged canonical evaluation artifact |
| Failure lacked an actionable path | Evidence comparison and contextual request for agent analysis, preserving oracle; warn that seed selection is not scope filtering | Northstar failure remains visible and approval stays blocked |

The existing engine, storage and permissions are reused. No retrieval scope behavior is changed by this redesign. The Northstar 0.65 F1 failure and unsupported service-cardinality constraint are not fixed or waived. This is an operator-perspective inspection and browser test, not a measured usability study with independent operators.

### Verification and disposition

The redesign is implemented locally. Computer-use testing exercised all six screens in the existing Northstar workspace and a synthetic source-only test in the existing second test tenant. Add-and-save persisted immediately (r2); changing that source to schema persisted (r3). The real configured model returned a valid concise proposal with eight grounded statements and no unresolved decisions. Model acceptance occurred at r45; toggling answer review and saving at r46/r47 preserved that acceptance without another model call. The real sandbox at r49 reproduced mean F1 0.65 (US 0.8, EU 0.5); handoff approval was visibly disabled. No expected answers were relaxed. The latest model correctly identifies the engine limitation. The new history and failure-context regression tests pass.

Scoped verification: 10 backend integration tests pass; Ruff and mypy pass; standalone workbench TypeScript/Vite build passes. Desktop screenshot inspected; narrow viewport showed no horizontal document overflow (354 CSS pixels content and viewport), then override was reset. Browser evidence is in `output/workbench/northstar/revised-model-review.jpg` and `revised-test-result.jpg`. File chooser upload was not re-exercised because the earlier browser approval gate denied it; pasted synthetic source persistence and category correction were exercised instead. No deployment or live activation occurred.

Remaining limits: assistant requests still produce a pack proposal rather than a separate conversational-only answer; prompt quality cannot guarantee every model reply is concise. The UI is a locally tested operator workflow, not a production control plane or an independently measured usability result. The account-scoped retrieval failure and service-cardinality constraint remain engineering work, clearly surfaced rather than bypassed.
