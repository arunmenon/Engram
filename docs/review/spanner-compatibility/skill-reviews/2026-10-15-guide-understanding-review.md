# Guide review: understanding and hidden assumptions

Reader: a junior engineer with basic HTTP and database knowledge, but no Engram history. Desired outcome: explain a write, an independent worker delivery, a graph change and a read; distinguish pack declarations from execution and evidence from inference. Applied `explain-with-depth`; Astra supplied an independent read-only educational review with targeted source checks.

Verdict: a useful architecture reference with several effective teaching examples; not yet demonstrated to work as independent developer onboarding. Correct prose and diagrams alone do not establish learner comprehension.

## Hidden assumptions and smallest changes

| Location | Assumption or likely misunderstanding | Disposition |
|---|---|---|
| Page 1 | Putting providers under “runs in Engram” suggests model execution is local. | Corrected: provider clients call external services. |
| Pages 9, 15, 24 | Session provenance is equivalent to the precise supporting statement or quotation. | Corrected pages 15/24 to match page 9. Current extraction sends `source_quote` while the graph writer reads `evidence_quote`; session links alone do not prove exact support. No runtime fix claimed. |
| Pages 8–10, 12 | Knowing the word “schema” means understanding types versus records; repeating generic schema text teaches each worker's mechanism. | Kept the full explanation on page 8; later lessons link back and retain their distinct schema tables. Added a transition from allowed connections to example records. |
| Pages 8–12 | A configuration table is operational proof for every selected bundle. | Existing qualification remains visible. Consider moving repeated matrices into optional reference detail after the mechanism; not applied in this pass. |
| Page 11 | Readers know the time-gap rule behind the late-event grouping example. | Needs an explicit example-specific gap and boundary explanation grounded in the grouping settings. Do not present one fixed gap as universal. |
| Pages 10, 12, 15, 27 | ANN, extraction profile, evidence spine, owner/epoch and frozen fixtures are understood because their names are familiar to the author. | Define at first use with purpose and consequence. Definitions on a distant page are insufficient when a lesson can be opened directly. Remaining terminology pass needed. |
| Page 27 | Imperative reproduction instructions mean a complete runnable suite exists. | Added upfront qualification: full-suite runnable fixtures/commands remain incomplete; first checkpoint runner exists but its retained-data run failed. Removed cost-bound wording in line with the no-caps decision. |

These are teaching and accuracy findings, not a new certification of all source behavior. The repeated configuration matrices and remaining first-use terminology are still open editorial work. The guide should retain actual mechanisms and caveats, rather than merely replace technical terms with vague words.

## Understanding checks and expected answers

1. **A write returned successfully. Why might a preference still be absent?** Acceptance commits ledger input; extraction requires its session trigger, enabled User behavior, valid model output and successful graph persistence. ACK alone establishes none of those outputs.
2. **A preference links to three Events. Does each Event prove that preference, and is an exact quote available?** No. The current branch associates collected session Events and loses the extraction quote at the writer boundary. The reader must not infer sentence-level evidence.
3. **Core + PDLC + Memory is selected. Does every test-result event call an LLM and create an Episode?** No. Deterministic projection handles the reported test facts; matching prose profiles govern pack extraction; eligible consolidation produces Episodes on its own trigger/schedule.
4. **The rerun passed. Can retrieval hide the earlier failed run?** No. Distinct execution identities/outcomes and their own source evidence must remain inspectable.
5. **Can changing only the model leave a retained bound runtime's authorization unchanged?** No under the current implementation. Its interpretation digest includes model policy. Existing accepted receipts authorize the earlier contract; a default-setting edit does not activate the new model for retained events.

No human learner participated; these are source-grounded review questions, not measured learning outcomes.

## Skill correction

Updated installed `/Users/arunmenon/.codex/skills/explain-with-depth/SKILL.md` with “Check assumed knowledge and unsupported claims.” It now requires a reader-prerequisite check, first-use teaching of consequential concepts/jargon, meaning/purpose/connection rather than acronym expansion alone, separate scrutiny of behavioral assumptions, cross-page consistency and location-specific corrections. It preserves technical names after introduction and avoids repetitive glossaries. Skill structural validation passed; that does not validate teaching effectiveness.

## Verification of edits

Rebuilt the existing 27-page HTML from its pilot template (25 A candidates, 24 B candidates, 18 probes). In Chrome inspected the rendered introduction, session-extraction lesson and reproduction page; exercised the revised page-9 schema link (navigates to page 8) and page-24 graph step 3 (shows qualified provenance). This is targeted rendered verification, not a claim of exhaustive responsive/accessibility testing or new runtime evidence.

## Pilot restart boundary

Offline reconstruction against saved attempt02 final snapshots shows both Luna configurations mismatch their retained owners. See `../pilot-readiness-2026-10-15/luna-restart-preflight.json`. The receipt validator explicitly rejects unknown historical interpretations; 46 acceptance tests pass in this worktree. No live workers, API, model call or database mutation occurred for this preflight.

The stakeholder's decision on allowable derived Summary/Event updates is pending. Even after that decision, supported retained-contract activation and pending-delivery recovery must be implemented/reviewed before the next live attempt. Do not use a reset, owner rewrite or disabled receipt check to manufacture a runnable pilot.
