# Claude review prompt

Review the Engram architecture and UI walkthrough video plan in this repository:

`/Users/arunmenon/projects/Engram/docs/engram-video-walkthrough-plan.md`

The user wants a professional narrated walkthrough for a complete beginner. Required order: Engram design/architecture using the existing HTML study guide; tenants and how their configurations differ; the complete implemented pack-framework UI; agent-assisted onboarding of a new ontology; running journeys and evaluations; agent-assisted journey creation. The user wants story and script reviewed before recording. Review only; do not change code, run model jobs, provision resources, deploy, or record the video.

Ground your review in the actual implementation, selectively inspecting:

- `docs/research/2026-10/walkthrough.html`
- `docs/tenant-admin-workbench-plan.md`
- `docs/pdlc-journey-workbench-plan.md`
- `docs/runbooks/tenant-api.md`
- `demo/frontend/src/workbench/`
- `src/context_graph/workbench/`
- Relevant pack/runtime code and tests when needed to substantiate a claim.
- `output/workbench/pdlc/acceptance-verification.json`, if available; historical evidence is not a fresh test run.

Evaluate:

1. Story and prerequisites: can a beginner follow every concept before operating it? Does architecture explain why the components exist?
2. Completeness: do we cover tenant configuration, new pack authoring, agent grounding/decisions, validation, graph inspection, question evaluation, prepared journeys, agent-authored variants and handoff?
3. Reality: identify each proposed scene that current UI/code cannot support. Distinguish UI features, backend capabilities, historical evidence and planned behavior.
4. Agent workflow: are input documents/schemas/events, source grounding, unresolved assumptions, independent expected outcomes and operator review concrete enough to film?
5. Tenant correctness: draft workspace versus active tenant, authentication/configuration/storage boundaries, activation versus intent readiness.
6. Evidence: event-driven versus graph-seeded scenarios, local versus deployed behavior, known failures, fixture evaluation limits and stale results.
7. Production feasibility: duration, example continuity, screen readability, missing prerequisites, sensitive-data handling and tool assumptions.

Return a verdict, then findings ordered by consequence with plan section, supporting code/doc reference, why it matters and the smallest correction. Include a concise scene-feasibility matrix and any essential missing scenes. Separate blockers from optional improvements. Do not propose broad product development to polish the video. Do not treat the design plan as proof of an implemented feature. State what you did not verify.
