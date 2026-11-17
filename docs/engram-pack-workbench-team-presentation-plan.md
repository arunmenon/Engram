# Engram pack workbench — presentation content agreement

**Status: content baseline carried into the four-act script for review, 2026-11-17.** This consolidates the earlier video brief, the 17-slide team plan, Fable's structure review and the independently accepted bounded M6 results. It is not yet an approved script, deck or recording. Scripting has been authorized. Do not begin final deck/recording production before script/storyboard review. Preserve earlier review documents as historical records.

## Purpose, audience and story

Audience: team engineers, product colleagues and domain operators. Assume business/software familiarity, but no prior knowledge of Engram, ontologies, packs or graph retrieval.

The presentation must answer, in order:
1. What problem does Engram solve, and why use a context graph?
2. Why do explicit ontology packs matter, and how does one reusable engine execute different domains?
3. How are tenants configured, and what stays separate between them?
4. What must an operator supply, and how does the agent help author and revise a pack?
5. How do we prove the rules behave as intended, including sequences and failures?
6. What does approval deliver, what is verified today, and what remains outside the workbench?

Central message: **Engram turns events into connected records using explicit domain rules. The workbench helps an operator supply those rules, review agent proposals and test the resulting behavior before handoff.** This is the intended value proposition, not a claim of measured business ROI or general autonomous correctness.

The overview is domain-agnostic. Start with a 20-second concrete hook—request 42 in east and west units—then explain the general design before introducing PDLC. The hook is an illustration of identity ambiguity, not a procurement pack execution. Use “unit” consistently. Ann's CRM email change is the worked executable revision; PDLC supplies prepared stories; incident operations supplies the deliberate failure. Announce each switch so these never look like successive states of one tenant.

## Content inventory — 17 baseline slide IDs, approximately 35–40 minutes

The table below preserves requirement IDs for coverage. The presentation order is now the four-act sequence in `docs/engram-team-presentation-script.md`, following Fable’s intuitive revision. Baseline IDs are not final deck numbers.

Timing includes approximately five minutes of clips and reading pauses; rehearse before fixing final duration. Each slide has one main takeaway. Detailed settings belong in speaker notes or the required appendix, not tiny text.

| # | Audience question / working title | Required content | Visual or demonstration | Takeaway |
| --- | --- | --- | --- | --- |
| 1 | Why can two records numbered 42 give us the wrong answer? | East and west each have request 42. Explain the consequence of merging them when asking what needs approval in east. Briefly state Engram's purpose. | Two source snippets and a clearly labelled illustrative wrong merge. | Identity and connections affect answers; matching text alone does not settle business meaning. |
| 2 | What does Engram add? | Define a context graph as records and their connections built from events; explain source traceability and state over time. Describe the benefit to applications/agents: reusable domain rules and inspectable context. Introduce ontology as the explicit record/relationship/rule definitions. Research basis: a short, source-backed connection to relevant graph retrieval and memory research, with exact implemented versus inspired mechanisms distinguished. | One small labelled graph; business links and source links visibly distinct. Research references in notes and appendix. | The graph and rules make context inspectable; they do not make every answer automatically true. |
| 3 | How do packs fit together? | Mandatory core, optional memory/user add-ons, and domain packs. Explain what each contributes using actual declarations. Show PDLC and the bundled CRM example separately; authored incident/Northstar artifacts are drafts/fixtures, procurement remains incomplete intake. Pack concerns: types/identity, event contracts, mappings, lifecycle, retrieval, evaluation artifact. Dependencies and name collisions matter across the composed bundle. | Core/add-ons/domain composition diagram plus a compact pack anatomy. | Common engine, extensible domain rules; adding a pack does not mean replacing the engine. |
| 4 | What happens from an event to an answer? | Trace one generic event through API admission, event ledger, worker projection, stored graph and query retrieval. Explain where keys, transitions, source trust and expected answers influence behavior. Separate the agent authoring loop from deterministic engine execution. Show storage adapters and where Spanner fits. | Progressive architecture diagram adapted from the study guide after current-code reconciliation. | YAML supplies supported rules; the Python engine validates and executes them. Storage is a separate responsibility. |
| 5 | How are tenants configured? | Compare real example workspaces by purpose, environment, roots/domain pack, inputs, producers and questions. Explain authenticated runtime tenant routing, pinned configuration and database boundaries from code/runbook. Distinguish workspace ownership from runtime isolation. | Side-by-side configuration table and workbench/runtime boundary diagram. | Creating a draft does not provision a tenant, deploy a service or demonstrate deployed isolation. |
| 6 | Start a tenant draft | Name/environment/scope; consent and redaction before provider calls; declared and trusted producers. Explain private draft status and known versus unresolved decisions. | Actual Tenant setup screen, highlighting only the current action. | The operator defines the boundary and data policy before using the agent. |
| 7 | What inputs does the operator provide? | Scope/exclusions; process specifications/glossary; source contracts/schemas; redacted sample events; identity and lifecycle rules; desired questions/expected outcomes; producer trust and constraints. Explain what each input can establish and what samples cannot prove. Inputs may arrive in any order; distinguish conceptual-start, runnable and approvable readiness. | Intake worksheet with one concrete example per input and when it is needed. Include upload/paste support and actual format limits. | Specs ground vocabulary; schemas and events ground executable rules; business decisions and expected outcomes need review. |
| 8 | Inspect the supplied data | Category suggestions/corrections, saved-source preservation, inventory, missing/empty values and repeated 42 in east/west. Show that repeats can mean updates or collisions. | Clip 1: procurement intake and repeated-value search. | The UI exposes facts to decide from; it does not infer global identity from a small sample. |
| 9 | Review the ontology the agent proposes | Plain-language summary, schema graph/table, record identity, relationships and lifecycle; where statements came from; open decisions/conflicting excerpts; validation/unsupported or inert features. Inspect mappings as sample → planned delta. Show technical inspection as optional. | Proposal review with a source excerpt and one before/after or state diagram. | A valid pack can still encode the wrong business rule; review its meaning and support. |
| 10 | Ask questions and steer the agent | Explain selected pack/record/relationship/issue; distinguish explanation from revision. Operator answer → prepared request → consequence preview → explicit send → revised artifact/diff. State that this is a constrained authoring/explanation loop, not a coding agent that changes engine code. | Clip 2: the verified guided CRM identity revision. Keep the operator's wording distinct from generated instructions. | The operator can steer a reviewable proposal; the agent cannot silently approve or activate it. |
| 11 | What happens when information is missing or work fails? | Procurement supplier gap, unit identity and conflicting reopening policies; no invented relationships. Failed/stale request, retained text, reload/restore, review before retry, cancel-versus-stop-waiting boundary. Show removals as choices and source edits invalidating advice. | Unresolved procurement still plus a clearly labelled controlled-failure recovery still. | Unknowns remain visible, and failures should not erase work or manufacture approval. |
| 12 | Test the pack with reviewed questions and events | Questions, business expectations, searchable entity selection, graph expectations, explicit review, sample run, stored results, expected versus found, mean F1 and limits. Separate schema graph, planned delta and observed graph. Explain graph-review reset guidance. | CRM steps 4–5; guided identity revision has two existing question checks and one observed Ann contact. | F1 1.0 means no regression on these two questions; neither directly tests Ann's email change. Candidate answers are not an independent oracle. |
| 13 | Run a prepared story | Ordered events, checkpoints, questions and pinned pack/engine identity; timeline and graph inspection. Explain sequence testing versus a single event or graph-seeded retrieval fixture. | Prepared PDLC implementation story: 111 checks, matching memory/Spanner outcomes; show backend and cleanup labels. | Saved stories make behavior repeatable; one story is not exhaustive domain coverage. |
| 14 | Create a new story with the agent | Domain goal/specification → outline → consistent events → checkpoints/questions → review each expectation → save/run. Include positive, negative and state-sequence examples; coverage list distinguishes absent checks from passing checks. | Labelled saved result from a fixture story author, with review ticks. | Story generation proposes tests; the operator must review what would count as correct. Live pack authoring is not proof of live story authoring. |
| 15 | Learn from a failed or weak check | Wrong title, wrong-account answer and unsupported scalar question; expected versus recorded outside JSON; failure explanation read-only; follow-up planning and rerun. Explain vacuous/weak checks and remaining limitations. | Clip 3: existing incident-operations failure, 4 passed / 2 failed / 1 unsupported; unchanged expectations on rerun. | Investigate the rule, data or scope; do not rewrite the expected answer simply to pass. |
| 16 | Approve and hand off | Reviewed artifact/version/digest, pinned engine/input identity, export/handoff. Explain change classification only as currently supported. Approval is not activation. Runtime deployment/target-data evaluation are separate; an empty tenant may not yet have data to evaluate. | Actual approved package, then a labelled boundary to operational work. | A tested, approved artifact is what the workbench delivers; production activation is unavailable here. |
| 17 | What is verified, and what should the team try? | Domain/artifact inventory and separate fixture/live/memory/Spanner/human statuses. Bounded M6 independent acceptance; real-operator sessions outstanding; remaining limitations. Concrete feedback tasks and next steps. | Compact evidence-status table, not an aggregate score or release badge. | The team knows what is demonstrated, what remains unverified and how to evaluate it. |

## Required depth without crowding the main story

These subjects must remain in the deliverable. Use notes and a navigable appendix, rather than dropping them to hit 17 slides.

| Appendix | Required material | Main slides it supports |
| --- | --- | --- |
| A. Research and design rationale | Primary-source references for selected research; explicit mapping: research idea → relevant Engram mechanism → implemented/inspired/not implemented. No “bleeding edge” or benchmark claim without support. Briefly position graph structure alongside text/vector retrieval without unsupported superiority claims. | 2, 4 |
| B. Engine and pack anatomy | Small YAML-to-Python example, loading/validation, types/keys, payload contracts, processed versus ledger-only handling, mapping expressions, lifecycle guards, provenance, retrieval intents/traversal/admission and evaluation artifacts. Identify inert fields and unsupported capabilities. | 3, 4, 9, 12 |
| C. Composition and tenant boundaries | Core/memory/user responsibilities, current catalog, dependency ordering and global names, tenant credentials/roles/config/database separation, worker binding, workspace versus runtime ownership. Label deployed evidence separately from code contracts. | 3, 5, 6 |
| D. Agent workflow | Inputs/context, citations and operator decisions, engine validation/repair, revision-bound explanations, permission/capacity/cancellation boundaries and unsupported engineering requests. No hidden chain-of-thought presentation. | 7, 9–11 |
| E. Testing and stories | Sample runs versus event stories versus graph-seeded fixtures, expectation review, mean F1, explicit starting points and their traversal limits, weak assertions, coverage, preserved baselines, reproducibility and Spanner cleanup. | 12–15 |
| F. Handoff and change management | Approved package/export contents, semantic diff and supported classification behavior; additive/mapping/breaking concepts and replay/rebuild implications without implying workbench execution of those operations. Activation and target-data evaluation readiness remain separate. | 16 |
| G. Verified scope and open findings | Actual source/build/run identities, residual findings, M6 bounded review, human-session protocol, glossary and links for deeper reading. | 17 |

The study-guide HTML is a visual/source starting point, not current truth. Reconcile `docs/research/2026-10/walkthrough.html` with current code and M6 evidence before using any diagram or sentence. The legacy video plan contains historical limits; this content baseline governs the new team presentation.

## Demonstration choices — explicit and reviewable

Three short narrated clips, captions and still-image fallbacks. Show recording/run identity in production notes; keep fixture/live/backend labels visible. Disclose condensed waits. Never splice different artifacts into an apparent continuous run.

| Item | Source of truth | Allowed claim / constraint |
| --- | --- | --- |
| Clip 1: intake, 60–90 sec | M5 clarity snapshots and Fable M6 review; current fresh intake in `output/playwright/ai-native-onboarding/M6/final-20261117/intake-result.json` | Repeated 42 with both units and source preservation are independently reviewed. Procurement has no executable pack. |
| Clip 2: guided CRM revision, about 2 min | `M6/final-20261117/copies-start.json`, `live-explanation.json`, `operator-request.json`, `live-revision-result.json`, `preservation-proof.json` | Recorded live guided revision. Baseline already names the identity problem; do not call it autonomous diagnosis. Agent wording can contain technical syntax; do not hide or dub it as a different response. |
| Pack evaluation still | `M6/final-20261117/live-flow-sandbox.json`, `approved-package.json` | F1 1.0: no regression on two existing questions. Ann appears as one contact in the recorded graph; a dedicated pre-reviewed email-change assertion was not run. |
| Procurement unresolved still | `M6/baseline-20261116/` live procurement result and provider metadata | One neutral incomplete-input observation with unresolved decisions, not broad detection reliability or a completed procurement ontology. Keep separate from the earlier explicitly prompted M5 case. |
| Recovery still | `M6/completion-20261116/recovery/`; Fable M6 independent recovery evidence | Controlled/fixture provider failure; retained input and explicit retry. Do not label it live reasoning. |
| PDLC execution still or short screen sequence | `M6/final-20261117/pdlc-result.json`, `memory/pdlc-memory-result.json`, `capacity-after-pdlc.json` | Same story, pack digest, engine and outcomes: 111 checks on memory/Spanner, verified cleanup epoch 33. Earlier timeout remains in notes; not every PDLC story or deployed service path was tested. |
| Story-authoring still | `output/playwright/ai-native-onboarding/fable-m4poll-20261113/`, saved fixture-author proposal/save | Fixture story author; no live story-authoring claim. |
| Clip 3: deliberate failure, about 2 min | `M6/final-20261117/failure-rerun.json`; incident-operations fixture and Fable M6 rerun | 4 passed, 2 failed, 1 unsupported; preserve expectations. Never relabel this as PDLC, payments or procurement. |

Final captures need a current-build rehearsal. M5-1/2 are independently closed. The M6-1 reset guidance is independently closed in `docs/review/2026-11-17-m6-1-fable-recheck.md` and may be recorded. M6 technical acceptance permits correctly labelled live/Spanner material; it does not close the human-study gate.

## Coverage agreement — nothing silently omitted

| Original requirement | Where covered |
| --- | --- |
| Domain-agnostic value proposition before PDLC | 1–4; PDLC execution begins at 13 |
| Engram architecture / study guide | 4; appendix B/C; current-code reconciliation |
| Research grounding | 2 and mandatory appendix A; primary sources required before script approval |
| Ontology packs, ontology engine, core and add-ons | 2–4; appendix B/C |
| Different tenant configurations and isolation boundaries | 5–6; appendix C |
| Inputs/specifications and onboarding order | 6–8; appendix D |
| Agentic ontology authoring and human steering | 9–11; appendix D |
| Types, identity, contracts, mappings and lifecycle | 3, 9; appendix B |
| Source references, trust, conflicting/unknown facts | 6–7, 9, 11 |
| Failed/stale request, restore and cancellation | 11; appendix D/G; observed versus untested distinguished |
| Retrieval questions, entity selection and evaluation | 12; appendix E |
| Planned versus stored graphs and execution trace | 4, 9, 12–13, 15 |
| Existing PDLC stories and new agent-assisted stories | 13–14 |
| Negative scenarios, weak assertions and coverage | 14–15; appendix E |
| Spanner integration and cleanup | 4, 13, 17; appendix E |
| Approval/export, versioning and runtime boundary | 16; appendix F |
| Domain diversification and honest artifact inventory | 3, 5, 8, 10–15, 17 |
| Professional video/voiceover and plain language | Production contract below |
| Fable review and user approval before production | Approval sequence below |

Any feature discovered during scripting must be added to this table as main slide, notes/appendix, or explicitly out of scope with a reason. Do not silently remove content to meet timing.

## Language and production contract

Use tenant, pack, agent and story consistently. Explain node/relationship/ontology once with an example. Use source material, where this came from, test results and approved package for their distinct meanings. No unexplained engine names in narration; retain actual screen text faithfully and explain necessary technical detail.

For every slide, production must supply: the audience question, one takeaway, speaker transcript, visual/shot description, artifact/source reference, claim boundary and transition to the next slide. For every clip: start state, exact actions, expected end state, narration, captions, reading pauses and a still fallback. Leave result screens visible long enough to read. Do not narrate an empty create form as saved history, or use different chapter titles from the visible screen.

Required deliverables after approval: 17-slide deck, speaker transcript/notes, required appendix, three captioned narrated clips or declared still replacements, and a source/claim checklist. The presentation and recordings receive their own Fable review; product acceptance alone does not approve them. Output format is a later packaging choice and must not change the agreed coverage.

## Approval sequence

1. **Now: user approves or edits this content baseline.** No slides/recordings yet. Proposed choices: mixed team audience, 17 main slides plus required appendix, 35–40 minutes, three clips, guided CRM as the executable revision and procurement as the illustrative/incomplete case.
2. Reconcile technical/research sources and create slide-level speaker text and shot list against this baseline. Have Fable review content accuracy, narrative, omissions and claim boundaries; return material content changes to the user.
3. Obtain script/storyboard approval, rehearse identified artifacts; the focused M6-1 recording gate is independently closed.
4. Produce deck/clips, visually inspect and check narration-to-screen alignment. Fable reviews the assembled presentation before sharing.
5. Internal teaching can proceed with bounded claims; unassisted self-service, production readiness and human-comprehension claims wait for their separate evidence.

## Review probes

Can a newcomer explain why 42 may need a unit, how a pack differs from the engine, what input the agent cannot invent, why an accepted proposal may still fail tests, why a graph candidate is not a correct-answer oracle, and why approved is not activated? If Ann's identity changed but neither question mentions Ann, what does F1 1.0 prove? Answer: no regression on those questions, not direct proof of the identity change. These are script review probes, not human-study results.

## Governing references

- Original request/long-form scope: `docs/engram-video-walkthrough-plan.md`
- Structure review: `docs/review/2026-11-16-team-presentation-fable-review.md`
- Prior narration pitfalls: `docs/review/2026-11-04-walkthrough-narration-review.md`
- Current plan/status: `docs/ai-native-onboarding-milestone-plan.md`
- Independent M6 acceptance: `docs/review/2026-11-17-m6-fable-independent-review.md`
- Pre-session corrections: `docs/review/2026-11-17-m6-pre-session-disposition.md`
- Technical handoff/evidence: `docs/review/2026-11-17-m6-verification-handoff.md`
- Runtime boundaries: `docs/runbooks/tenant-api.md`, `docs/runbooks/pack-authoring.md`
- Pack catalog: `src/context_graph/workbench/catalog.py`, `src/context_graph/ontology/packs/`, `src/context_graph/workbench/packs/`

## Four-act script and current gates

`docs/engram-team-presentation-script.md` is the speaker transcript and storyboard for review. Order: Ann problem and early overview (1–2); full operator loop (3–11); other-domain stories (12–14); detailed architecture, tenants and status (15–17). Early overview includes core/add-ons/domain packs; the deep architecture remains at the end. Required appendices and all three clips remain. Baseline-to-script coverage is mapped in its appendix G. Labels distinguish planned baseline contacts from the observed revised graph. M6-1 is independently closed; M6-2 wording is corrected. Two-Ann/one-Ann capture rehearsal and script/deck review remain. Real-operator sessions and product lows remain separate.
