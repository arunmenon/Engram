# AI-native UI review skill

Created 2026-11-06 at the user's request for research-grounded, clean, domain-agnostic
operator UX. Installed at `/Users/arunmenon/.codex/skills/ai-native-ui-review/SKILL.md`.
Invoke as `$ai-native-ui-review`. `demo/frontend/AGENTS.md` routes substantive frontend
work to it; a fallback is included for machines without the local installation.

## Scope

Main view clarity, visual hierarchy, component/state coverage, accessibility,
grounded AI explanations, steering/proposals, real progress, stale-context handling,
recovery and cross-domain consistency. It does not impose chat, a framework, fixed
screen count, blanket approval dialogs or a particular visual theme.

## Research

References are maintained with links and applicability limits inside the skill:
Microsoft HAX, Google PAIR Explainability/Trust and Feedback/Control, NN/g progressive
disclosure, GOV.UK Details, WCAG 2.2 and WAI form notifications. Local recovery and
versioning lessons are explicitly distinguished from research and normative criteria.

## Validation and bounded rehearsal

- Bundled skill validator passed. Local reference links resolve. Invocation metadata
  includes the skill name and leaves implicit selection enabled.
- Rehearsal against existing CRM evidence: a correct live repair still receives
  **revise for clarity**, because the explanation repeats technical settings and the
  main result summary narrates repair diagnostics. Functional success is not polish.
- Rehearsal against existing M1a evidence: **accept bounded request preparation**, not
  self-serve resolution. Fixture responses and simulated personas retain those labels.
- Disclosure edge case: moving an unexpected deletion warning behind details fails
  the skill's review even if the screen looks cleaner. Optional event names may move.
- These are author-run applications to existing evidence, not a fresh browser run,
  independent skill evaluation or human study. No product-wide conformance claim.

## Suggested next use

Use the skill on CRM and delivery's explanation -> prepared request -> author result
screens. Inventory affected components and states, identify the smallest clarity fixes,
and verify rendering and behavior. Preserve warnings, inputs and expected answers.
Report functionality, visual clarity, AI helpfulness and tested accessibility separately.

Installing instructions does not automatically audit or correct every UI element.
The review must still run on actual screens and expose untested coverage.


## Review additions incorporated

All twelve requested areas are now covered: reproducible run identity; independent
reviewer-owned copies; token-safe automation; explicit recovery-state matrix;
vocabulary inventory; density measurements; coherent blocker/remedy guidance; honest
placeholder attribution; inline focus checks; uncoached-first ordering; Claude-local
availability; and WAI-ARIA APG implementation references.

Two important qualifications: implementer regression checks remain permitted but are
not independent acceptance; vocabulary/height measurements diagnose friction rather
than impose arbitrary failures. Source presence does not prove understandable wording.

Repository inspection found no prior `.claude/skills/skill-rules.json` or routing section
in this checkout's CLAUDE.md. Added a portable skill copy, declarative keyword index
and explicit CLAUDE.md instruction. No hook was installed and runtime Skill-tool
activation was not exercised. Both skill copies pass the bundled validator; all five
files match byte-for-byte and reference/routing paths resolve. No product code, packs,
fixtures or runtime data were changed in this skill-refinement turn.
