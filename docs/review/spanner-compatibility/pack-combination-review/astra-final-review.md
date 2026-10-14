# Independent final pack-combination / #62 review

2026-10-14 — **The bounded five-combination checkpoint is accepted; no remaining blocker for closing #62.** Keep #34, #39, #41 and #42 open. This does not close all G8–G11 work or authorize isolation/pilot execution.

## Accepted matrix

Accepted evidence: [pack-combination-1014-02](../runs/pack-combination-1014-02/manifest.json).

| Selection | Assertions passed | Accepted Events | Final nodes / edges |
| --- | ---: | ---: | ---: |
| Core | 85 | 5 | 13 / 26 |
| Core + User | 113 | 5 | 17 / 37 |
| Core + User + Memory | 216 | 9 | 28 / 77 |
| Core + PDLC | 133 | 8 | 24 / 42 |
| Core + PDLC + Memory | 246 | 12 | 33 / 89 |

Total **793 assertions across five configurations and 39 accepted Events**, not 793 independent journeys. Every configuration reports normal five-worker joins, no shutdown errors, no pending deliveries or dead letters, and matching final/retained snapshots. No runtime/harness source changed during the accepted run; all 218 recorded hashes independently match current files.

## Independent source and evidence findings

The #62 correction carries the selected stored Entity identity through exact, fuzzy and semantic resolution. The writer validates that identity before matched-target writes and uses it directly; no normalized-name fallback remains. The final `canonical_id` initialization is a typing/control-flow clarification, not a change to the validated matched-key choice.

I independently reconstructed the exact REFERENCES set in each configuration: all five accepted Alice-session Events point to `entity:ResetToken`, with no `entity:resettoken` shadow. The original mixed-case fixture remains intact. This proves preservation of the existing whole-window Entity reference contract, not quote-granular evidence or general entity-resolution quality.

User selections contain the canonical profile and exact positive/negative preference identities. Support counts remain one after the overlapping trigger; the predecessor retains its evidence and explicit successor relation. Active User/personalization reads expose the replacement. The fresh applied-receipt replay passes whole-application-table fingerprint equality and makes no extra model call.

Memory selections contain exactly the explicitly stated/confirmed Belief and created/completed Goal with revision1 and the declared two-source evidence sets. Actual source receipts and owner/session checks pass. No Belief/Goal is inferred automatically from the PDLC Decision. Complete full-membership Alice Episodes—and PR Episodes where applicable—are present alongside legitimate history.

I independently checked every stored historical Summary identity, source membership, count and time range, and every Episode identity, accepted session membership and exact CONTAINS/DERIVED_FROM/Summary evidence set. Intermediate snapshots differ legitimately across configurations/timing; the runner requires the full predeclared snapshots rather than treating arbitrary history as completion. Memory-off legacy episode-summary scope and Memory-on hashed Episode scope remain distinct.

PDLC selections preserve main PR7 as merged and unrelated-repository PR7 as open, with exactly the declared Changes and Decision. I independently verified exact stored source edges and actual Artifact API newest-source provenance against submitted UUID/owner/session/trace values. The Artifact API intentionally excludes DERIVED_FROM traversal edges; stored exact evidence plus public newest-source provenance is its correct contract. Memory subgraph evidence retains its separately required edge checks.

Accepted Event identities and deterministic keywords match submitted inputs. The declared centrality-derived importance buckets do not imply scoring quality. Disabled/malformed admissions and accepted HTTP duplicates pass whole-table no-write checks after worker joins. Public subgraph Event provenance matches frozen inputs, responses are untruncated, and private User receipts remain hidden. Non-access Event properties, non-Event properties and the declared other table/physical-column comparisons survive reads unchanged.

## Retention and failure dispositions

All five previous-export file digests independently verify. The [post-process recheck](../runs/pack-combination-1014-02/post-process-recheck.json) exactly matches final owner epoch48 and all seven fingerprints. Final composed data remains retained. The sequence preserves the original epoch43 evidence before advancing through epochs44–48.

Matrix01 is **not accepted**: its first four configurations had only two of the required five Entity references, and its PDLC stop also exposed an incorrect public Artifact API edge oracle. The original harness/source manifest and assessment disposition remain retained; PDLC+Memory was not run there. The runtime Entity fix and separate API-oracle correction are both disclosed, rather than rewriting that attempt into success.

Saved broad tests report **2848 passed/13 skipped**, excluding the known baseline PDLC evaluation-gate file. Final affected tests report **117 passed**, including the focused identity regressions; the larger selected preflight suite reports159 passed. The matched-ID initialization followed the broad start; final targeted coverage checked the final form. These logs were inspected, not rerun for this review. Ruff/mypy results are supplemental local evidence.

## Scope of acceptance

External extraction, pack-extraction and summary outputs are frozen providers; admission, five shared workers, receipts, validation, actual Spanner and authenticated read APIs remain real. This establishes these five useful pack-composition journeys with their selected outputs and disabled boundaries. It does not establish model quality, all pack combinations/catalog cases, concurrent tenant isolation, concurrent counter atomicity, general interrupted-work recovery, historical migration, live Neo4j or controlled-pilot readiness.

Close #62 on this evidence and reconcile the bounded checkpoint under the open umbrellas. Stop after this slice; subsequent isolation/pilot work requires the next stakeholder decision.
