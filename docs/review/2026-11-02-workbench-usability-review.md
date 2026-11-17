# Workbench usability review: onboarding and testing a pack

Date: 2026-11-02. Method: live walkthrough of `http://127.0.0.1:5174/workbench.html` with the backend restarted on the real model (`gpt-5.2-2025-12-11`), one prepared PDLC journey run, and one new synthetic tenant ("Northstar checkout incidents") taken through setup, evidence, a real-model proposal and one revision attempt. Question asked at every step: would an operator who is onboarding a pack for a tenant understand what this screen is for?

## The one product gap

**Nothing in the workbench runs on the context graph.** The sandbox and the journey runner hardcode every store to `memory` (`workbench/sandbox.py:47-57`, `workbench/journey_runner.py:225-236`) and then call the engine's normal `open_stores`. There is no flag or setting. The activation capability is a literal `False` (`workbench/api.py:225`) and the review step's "Runtime activation" pill is a fixed label. What exists is the full real pipeline, pointed at in-process stores. Making the backend selectable per run is a small change; a sandbox-database lifecycle and a tenant activation API are the real build. This is the user's stated must-have.

### Requirement stated during the review (2026-11-02)

Sandbox mode must run on Spanner, not memory. Reserve a pool of four or five Spanner databases for sandboxes. A sandbox run or draft claims one database, runs the real ingest, projection worker, graph and retrieval against it, and releases it after verified cleanup. The UI shows slot capacity and refuses a run when the pool is busy rather than failing. Each run records which database it used. Live tenant activation remains a separate step.

Smallest implementation: make the storage settings in `run_sandbox` and `run_journey` come from a sandbox-pool allocator instead of the hardcoded memory settings; add the pool (slot table, claim, release, cleanup check) to the workbench store; surface slot state in `/admin/capabilities`.

## Findings by screen

### Landing page: Tenant workspaces
1. Three nouns for one thing. Header "Tenant workspaces", subtitle "Give each ontology a clear purpose", button "New tenant draft". Pick one and define it once on this page.
2. "Explore an existing ontology" leans on undefined jargon: "frozen pack", "prepared journeys from the existing test suite", "retrieval fixture". A journey is never defined before you click one.
3. The retrieval scenario dropdown is thirteen internal test names with no reason to choose any.
4. Good: the empty state "Your first tenant starts with a draft. Add a domain goal, then bring the documents and events that describe it" is the clearest sentence in the product. Promote it.

### Prepared journey page
5. Good: story headline, plain-English timeline steps, and the observed graph with typed nodes and named edges. This is the strongest stakeholder demo in the product.
6. The "What this journey covers" panel is test-suite bookkeeping (assertion sites, file paths, line numbers, "G03 fixture", "oracle", "dispositions are semantic"). Hide it behind a developer toggle.
7. The failed check shows raw JSON only: expected `http_status: 409`, observed `semantic_outcome: duplicate`. An operator cannot tell whether the pack, the engine or the test is wrong. Add one sentence of explanation per check kind.
8. "Sources and frozen pack identity" shows a bare hash and script paths. Show pack name and version; keep the digest under a disclosure.
9. Journey screens are labelled "PDLC" by a literal in the code, so they would mislabel any other domain.

### Step 1: Customer setup
10. Good: "Data handling comes first" is well written, and the next-action banner tells you exactly what to do.
11. "Model" means two things on this screen: the domain model being built, and the language model under "Model-provider permission" and "Configured author". Neither is defined. This caused a direct question during the review.
12. Advanced panel offers "memory", "user" and "PDLC domain pack" checkboxes with no explanation of what they add or when a new tenant would want them.
13. The readiness checklist shows "Unsaved" for all three tiers before the first save, which reads as an error.

### Step 2: Customer evidence
14. Good: the three categories are explained in one line each, and the inventory shows a category pill per source.
15. Defect: after the first source is saved, the form collapses into "Add another source" and the green "Source added and saved" banner stays on screen. Subsequent entries typed into the collapsed form were silently lost; the stale banner still said saved. The banner must clear on the next edit, and the form should stay open after a save.
16. The sample-envelope hint (`event_type, payload, producer_id, occurred_at, event_id, expect_admitted`) is fine print. Make it an "Insert example" button.
17. Uploads accept text, Markdown and JSON only. Say "no PDF" where the file chooser is.

### Step 3: Proposed model
18. Good: this is the best-grounded part of the product. Every fact carries a "From a source" / "Operator decision" / "Assumption to check" pill with the verbatim quote and source name, limitations are listed in plain language, and the engine error is shown next to a Revalidate button.
19. The two standing decisions ("What identifies one entity?", "What happens when it changes?") are well phrased with the incident-number example. But they are free text asked before any evidence is read, and nothing shows what an answer changed.
20. Defect: a recorded decision was saved as a single character ("S") after a full sentence was typed, and the assistant's "What should change?" textarea dropped its contents twice. Both are controlled textareas that re-render during the 700 ms job poll or on save. Reproduce with a long paste while a save is in flight.
21. Defect: "Apply my changes" could not be triggered from three attempts in the browser once the first proposal existed. Sending the same request through the `/author` endpoint worked. Suspect the button is disabled by a stuck `busy` state after a save, with no visible indication.
22. The real model does not know the pack property vocabulary. It proposed `integer`, was rejected, proposed `number`, was rejected, and exhausted its three repair attempts. The valid name is `int`. The engine's accepted type list should be in the authoring prompt, and the UI should show the valid vocabulary next to the error.
23. The revision job then failed after about four minutes with "ValueError: job failed; check inputs or server provider configuration." The handler at `workbench/api.py:467-476` deliberately drops the exception and logs nothing server-side, so the failure is undiagnosable from the UI and from the log. Log the exception type and a redacted message.
24. The UI only polls while it believes a job is running. A job started elsewhere, or a job whose start it missed, is invisible until the draft is reopened.
25. The assistant panel heading says "change or explain", but there is no explain mode: any text triggers a full rewrite and another multi-minute model call.
26. Relationships render as "Incident → → Service" (doubled arrow).
27. "3 decisions need your answer" is shown above five boxes, because the two standing questions are always injected.
28. The pack version climbs with each repair attempt (1.0.2 after one build), which will confuse anyone who reads it as a release number.
29a. Answering a decision that the assistant itself raised marks the proposal stale, and readiness then demands "Regenerate the proposal after input changes". Every answer costs another multi-minute model run before the sandbox can be used. Decisions the assistant asked for should be applied by the assistant in one revision, not treated as new inputs.
29b. The repair loop deleted data to pass validation. Asked to set `severity` to `int`, the model removed the property entirely with the note "the engine rejects numeric node property types", which is false. The only trace is a limitation line. A repair that drops a property should be a decision for the operator, not a silent change.
29c. Decisions and other edits live in browser state until a save. After a revision conflict, "Reload saved version" discards them without warning. Two typed answers were lost this way.
29d. The draft always reopens on step 1 regardless of where the operator left off.
29. "Technical inspection" is the real pack view (types, contracts, mappings, planned delta) but it is a collapsed expander with no step in the sidebar.

### Step 4: Expected results
30. Good: "Trust pagerduty in this test. This grants no production access" is exactly the right tone. Producer ids are read from the samples automatically.
31. The entity picker is empty until a model is validated, and the empty state says so. Good.
32. Per-question pass/fail is not labelled on this flow; only F1 numbers are. The journey screens do show PASSED/FAILED.

### Step 5: Test the model
33. The pipeline line "Fresh in-process memory stores → event ledger → projection worker → graph → retrieval" is engineering vocabulary. Say "runs your sample events through the real Engram pipeline in an isolated test copy".
34. Not verified in this session with a real-model pack: the sandbox never became runnable because the proposal never validated. The memory sandbox is covered by unit tests and by the Oct 30 records.

### Step 6: Review and handoff
35. "Runtime activation: Not requested · unavailable here" and "Deployment intents: Not evaluated" look like status but are placeholders. Replace with one sentence: "Activation is a separate operational step and is not available from this workbench."
36. The sentence about activation succeeding with an empty graph while intents stay pending is correct and will confuse a first-time operator. Move it to the activation runbook.
37. Good: approval text says what it does and does not do.

## Vocabulary to define once, in a glossary strip
Tenant, draft, ontology, pack, model (domain), model (language), mapping, projection, planned versus observed graph, journey, sandbox, evaluation, activation.

## Answers to the stakeholder question
- Pre-built packs with end-to-end journeys: showable now; reframe as customer stories and hide test bookkeeping.
- Operators running packs on the context graph: not available; see the product gap above.
- Agentic onboarding of a new ontology: mechanics complete; vocabulary and the three defects above (lost input, Apply not firing, opaque failure) must be fixed before a stakeholder demo, and the model prompt needs the engine's type vocabulary.

## Not verified
- Sandbox run, graph preview and approval with a real-model pack (proposal never validated in this session).
- Journey authoring with the assistant.
- Behaviour on a reloaded page: the operator token is held in memory, so a reload returns to the login screen.
