# S5: Version requirements belong to the changed contributor

Goal: docs/ontology-v2-next-five-slices-goal.md, S5. #87 / ARCH-1-003, Pillar1 supporting8. Branch fix/87-contributor-version-impact starts from accepted, unmerged S1 c831f18; its draft PR will target the S1 branch as an explicit shallow stack. Both modify the comparator; this keeps the S5 diff focused and preserves the accepted static-assignment safeguard. Neither merge is authorized.

An unchanged pack owns a relationship/event; another dependent pack extends its endpoints or contributes projection rules. Removing that contribution can be breaking, but the current comparator charges the original owner and misses the contributor's required version increase. Fix deterministic comparison attribution, not the authoring agent, UI extension builder or a runtime data migration.

Public acceptance seams: compose actual validated packs, classify_change/as_dict, normal/pre-1.0 version problems and reconcile refusal where applicable. Cover foreign-edge extension removal/addition, foreign-event rule edits/removal, unchanged owners, multiple changed contributors and prior admission/default/static-field gates. Retain the overall breaking guard and do not charge an unchanged dependency. Effective endpoints and per-contributor rule changes determine causality; notes alone must not acquire another pack's breaking requirement.

No original pack/fixture/oracle changes. At most two Fable reviews at $5 each. Live backend, deployment, automatic graph changes and broad issue closure remain out of scope. Status: corrections awaiting final independent recheck.


## Implemented distinction

Effective endpoint deltas retain their global graph classification, but responsibility comes from the pack's actual endpoint contribution, including wildcard/provenance expansion. Projection rules are compared by event and contributor, retaining S1's static-assignment behavior; the aggregate event rules still determine replay/rebuild.

A separate contributor_changes map records per-pack declaration compatibility for version checks. This extra axis is justified by a failing overlap witness: bb withdraws an extension that cc still supplies, leaving the graph identical. bb must still publish the appropriate major version, but forcing reconstruction would be unnecessary. A real normal-reconcile control with an adequate major version proves existing records stay unchanged and history is never read. Moving rules between contributors can change their execution order. Ordered rule lists are now preserved for comparison; a transfer of disjoint writes conservatively requires replay when its composed order changes. A stored-outcome witness proves a reordered pair changes the final label from N to L and normal replay matches a fresh graph. This is not a new activation gate.

Twenty-one new public-seam cases and 155 focused checks pass after the first review corrections. The final broader affected selection passes 1090 tests, two skipped; Ruff check/format, module mypy and purity checks pass. Evidence in output/implementation/ontology-v2/next-five-s5/ includes red-extension, red-rules, red-overlap, red-review-findings, focused-round2, regression-round2 and source hashes. Local paths are not public artifacts. No original fixtures/oracles changed; local Python3.14 memory/fake-adapter evidence is not live backend or CI3.12 proof.

Conservative bounds inherited from the existing comparator, including duplicate static assignments and qualified-versus-bare rule identities, remain. Per-contributor compatibility is not a general proof of source/worker activation safety. Explicit administrative overrides and broader evaluation invalidation remain outside S5.

## First review and corrections

Fable round1 requested two medium fixes: implicit provenance retargeting wrongly charged unchanged domains, and removing an entire edge skipped the withdrawing extension's contract. Both are reproduced in red-review-findings.txt and corrected. Implicit contributions require participation on both sides; explicit declarations remain authoritative. Endpoint effects without a changed contributor fall back to the owner. Extension withdrawal is checked even when the edge disappears.

A low finding exposed sorted rule lists concealing changed execution order; this is corrected, rather than retaining the earlier no-replay transfer claim. The old S5-only transfer assertion was adjusted because an actual stored N-versus-L outcome disproved its premise. Original shipped business expectations remain unchanged. Endpoint reasons are emitted once while actor impacts remain separate. Withdrawing a redundant explicit extension remains conservatively breaking for that contributor.

Ruff check/format and module mypy pass. Broader affected checks are recorded separately. Status: Fable final round2 PASS, no blockers; 613 independent selected checks passed. Both paid rounds used, $5.764019 total. Runtime/test hashes match the final manifest; this concluding documentation update occurred after peer review. No third call. Ready for a draft PR; no merge or deployment.

## Final review residuals

Dropping a pack's last node type or removing it entirely can still attribute implicit provenance loss to unchanged core; a concurrent core documentation-only version bump can consequently be over-restricted. This narrowed preexisting fallback limitation remains open; it is not a claim of complete provenance ownership handling. Pure reorder wording can say "added". Order-preserving transfers correctly avoid replay. Fable's additional witnesses were ad hoc and are not committed tests; bundle-order-only changes were not exercised. Broader real-backend, Python3.12 CI and rollout gates remain open.
