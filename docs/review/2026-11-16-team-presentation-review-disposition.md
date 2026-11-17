# Presentation structure — Fable review disposition

2026-11-16. Implementer response to `2026-11-16-team-presentation-fable-review.md`. Updated only the presentation plan and this disposition. Original review preserved. No slides, recordings, product changes, provider calls or cloud runs in this revision.

Plan: `docs/engram-pack-workbench-team-presentation-plan.md`.

| Finding | Applied change | Remaining check |
| --- | --- | --- |
| 1. Example before definition and inconsistent identity scope | Slide 1 opens on request 42 in east/west units; slide 2 introduces a graph. “Unit” retained throughout. Incorrect merge explicitly illustrative because procurement has no executable pack. | Inspect final visual/narration for the same distinction. |
| 2. Unconfirmed clip sources | Added source registry with snapshot, fixture/reconstruction script, truthful claim and recording gate for each clip/saved example. Clip 2 explicitly uses the incident fixture success control; completion may return the same pack. Clip 3 uses the existing Support investigation story/incident fixture, never PDLC. | Reconstruct and rehearse identified artifacts on recording build. M5 clarity recheck and M6 gates remain. Existing files are not proof of a currently running service. |
| 3. Journey/story drift | “Story” throughout teaching sequence/narration. One explicit note for legacy journey labels if visible. | Match final clips to actual controls. |
| 4. Missing pack testing and recovery | Slide 12 explicitly covers steps 4/5: questions, expected answers, sample events and observed comparisons. Slide 11 covers failed/stale request and reload recovery using named historical fixture captures. | Current-build recovery rehearsal; historical capture labels if reused. |
| 5. Density | Adopted 17-slide sequence; composition detail moved to appendix, runtime/workbench boundary merged, run/failure combined, domain comparison folded into final status. | Rehearse 36 minutes plus reading pauses; clips included in time budget. |
| 6. Ambiguous evidence vocabulary | Separate source material, where-this-came-from references, test results and approved package. | Apply consistently to slide copy and voiceover. |

Additional points:
- Producer trust is shown with tenant setup, not only described architecturally.
- Name the proposal screen once; thereafter use proposal review.
- Explain the evaluation gate as checking answers on the tenant's own data, a production step the workbench does not perform.
- State that the recorded live procurement run was guided to notice missing linkage/conflict; do not claim unprompted detection.
- Identify CRM precisely. Current source check found `src/context_graph/workbench/packs/crm.pack.yaml`, explicitly described as an adaptation of the original test fixture with payload contracts. `catalog.py` combines built-in and workbench pack directories; capabilities list core/memory/user roots and activation false. Therefore the plan does not repeat “only PDLC is available in the workbench.” Slide 17 uses this bundled CRM example, not the sales intake draft and not a newly authored pack. Original fixture remains identified as its origin. No new runtime catalog query was made.

Verification: checked 17 consecutively numbered slide rows; checked existence of named source snapshots, fixture files, recovery captures and author/recheck records; read relevant fixture reconstruction scripts and current catalog/capability definitions. No new browser run or video inspection. Review documents remain historical observations of their stated builds.

Status: all six requested structural changes applied. Independent re-review of revised plan is not claimed. Slides may be drafted from this structure under the existing authorization; final artifact review remains required. M5-1/2 independent recheck, M6 live-agent/Spanner/human gates and all open product findings remain unchanged.
