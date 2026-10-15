# Artifact Quality Gate — creation and validation

Created at the stakeholder's request to unpack “AI slop” into an actionable review gate. The [versioned skill](../../../.agents/skills/artifact-quality-gate/SKILL.md) is installed at `~/.codex/skills/artifact-quality-gate` as a symlink to that source. A clone contains the repository-local `.agents/skills` package; the personal installation is specific to this machine.

## Definition and evidence

The working concern is avoidable output that appears useful/complete but fails to provide justified value for its purpose. This is our operational definition, broader than the cultural label and applicable regardless of authorship. It is not a validated scientific detector.

Research distinguishes lexical meaning, philosophical commentary, empirical studies and engineering guidance. The seven dimensions are our synthesis, not a published standard. See [research grounding and primary sources](../../../.agents/skills/artifact-quality-gate/references/research-grounding.md).

The gate checks grounding, reasoning/assumptions, audience/task fit, necessary detail/complexity, verification honesty, consistency/presentation and usability/handoff. Each finding needs a location, observation, source/requirement, consequence, smallest correction and meaningful recheck. Missing evidence stays unverified; optional style is not a blocking defect.

## Use in the workflow

- `$artifact-quality-gate Review docs/guide/engram-architecture.html for a junior engineer. Include its pilot template and source-ground consequential runtime claims. Report only; do not edit.`
- `Run a slop check on this PR against its issue. Separate unsupported behavior and needless complexity from optional style.`
- `$artifact-quality-gate Review this verification document before handoff. Check that each completion claim matches actual evidence and declare any unverified scope.`

Default is review-only. “Apply the fixes” or an already authorized implementation task can authorize targeted changes; the skill does not itself authorize deployment, agents, cloud operations or issue closure. Implicit discovery is allowed by default, but no unconditional global or CI gate was added. It complements the existing explanation, code-review and verification workflows rather than replacing them.

## Validation performed

- Skill Creator initializer produced the package/UI metadata; structural validation passed for the repository and installed path.
- Local reference links resolve. The installed path resolves to the versioned source, avoiding independent copies drifting.
- Reviewed the nine authored calibration cases against the instructions: material unsupported claims, legitimate long-form depth, missing authority, legacy/current branch selection, misleading diagrams, protective wrappers, self-fulfilling tests, style-only accusations and broken initial visuals. The rubric provides the required distinctions. This was an author desk check, not nine executed tests, independent forward testing or measured detection accuracy.
- No independent reviewer or learner validation is claimed for this new skill. Earlier Astra reviews concern the explanation skill/guide and pilot; they do not certify this gate.

## Bounded application to the existing guide

**PASS for the source explanation scope below**, not certification of every HTML page or of pilot readiness.

Reviewed pages 8, 9, 15, 24 and 27, the corresponding pilot template and builder at guide revision `07dcbd7`; reused the recorded source grounding for worker construction, User receipt preparation/application and prior rendered checks. No new browser or runtime execution was performed for this gate application.

The current bound User explanation now traces construction to UserExtractionStore, distinguishes accepted owner/session windows and quote-matching User evidence from core Entity associations, and separates textual support from semantic truth. Page 27 explicitly distinguishes reproduction requirements from a full runnable suite. The artifact does not claim all pilot candidates passed or a human learner validated it.

The historically incorrect assessment is a decisive gate example: a reviewer could cite a real legacy writer and still issue a false finding. The correction is to inspect the selected caller/runtime branch, not to make the accurate guide match the wrong helper. The skill therefore requires construction/caller tracing for code-dependent claims.

This source-scoped PASS does not establish that all code is correct, every paragraph is necessary, current cloud activation works, or arbitrary readers understand the guide. Broader artifact runs must declare and inspect their own scope.

## Unchanged pilot boundary

The requested pilot resume remains blocked by the missing supported model-only interpretation transition and the pending derived-data policy decision under #63. A fresh read-only audit confirmed both retained owners and all application table fingerprints match the previous final snapshots; A still has one pending extraction, B none. No API/workers or mutating run started during this skill task.
