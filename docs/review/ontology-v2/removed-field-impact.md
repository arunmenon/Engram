# S1: Removed projection assignments require safe graph reconstruction

Goal: docs/ontology-v2-next-five-slices-goal.md. Issue #36, ARCH-8-005. Base 9013a83fe0171c31d8be62b851047f5a9725d0e0; branch fix/36-removed-field-impact.

An existing tenant's new pack stops writing a field but still declares that field. Merge-style replay leaves old values behind, although a fresh graph omits them. The agreed change is deterministic update assessment: identify removed node/relationship property assignments and use the existing breaking/version/refusal path. No automatic deletion, migration, rebuild or UI feature.

Public verification seams are the goal-approved classify_change, real MemoryEventLog/PackProjector/graph port reads, replay_event_types diagnostic, reconcile refusal and explicitly requested fresh rebuild. Reproduce the retained-versus-fresh mismatch; verify normal adoption refuses before original graph/source/completed state changes. Preserve same rules, added fields, changed value expressions, strict clear/preserve operations and normal/pre-1.0 versions. Prior admission/default checks remain intact.

This does not claim every change to conditions, lookup targets, dynamic values or transition guards converges under replay. Explicit allow-breaking administrative overrides remain unchanged and do not establish reconstruction. Contributor attribution is S5; real backend acceptance and production cutover remain separate. No fixtures/business oracles are changed.

## Implementation and verification

The comparator reuses each projection part's identity and compares assigned field names separately from values. A decrease in assignment occurrences requires the existing breaking/rebuild path. This is conservative when another assignment/default would still supply the field; it is not a general theorem of replay convergence. Unchanged parts, additional assignments and changed value expressions retain their prior classification. An explicit supported clear keeps its field assignment and remains a mapping operation.

Nine new public-seam cases cover the real node replay/fresh mismatch and refusal, real relationship fields, normal/pre-1.0 version requirements, added assignments/changed expressions and actual in-place explicit clearing. Original source documents and graph/state are checked unchanged on refusal. These fixtures have no retrieval intents; a passing fresh build is not a business-question acceptance claim. The initial strict-clear test omitted its required capability and failed declaration validation; after the harness declared that capability, the real supported operation passes. No production capability check was weakened.

146 focused/adjacent tests pass. The broader affected selection passes 956 tests including memory controls; four external backend cases are excluded. Ruff check/format, runtime-module mypy and whitespace checks pass. Local Python3.14 only; main-target Python3.12 CI/live backend/UI/human proof is not implied. Local evidence: output/implementation/ontology-v2/next-five-s1/ (not public), including red-node.txt, green-node.txt, focused-round2.txt, regression-final.txt and review-manifest.json.

## Independent review and disposition

[Fable round1](removed-field-impact-fable-round1.md) requested one medium correction: a supported strict literal-null assignment with preserve behavior also stops writing the field. Counting its set key as a write let normal replay retain an obsolete value. The new stored-outcome test reproduces the mismatch and fails on the first candidate (`red-null-preserve.txt`). Property-target comparison now omits such static non-writing assignments; explicit null-clear remains a target and a supported mapping update. The edge test also demonstrates replay retention on a disposable graph.

[Fable round2](removed-field-impact-fable-round2.md) returned **PASS, no unresolved S1 blockers**, independently ran 146 focused tests and probed strict null-preserve/clear variations. Its nonblocking stale-document comments are corrected in this final record. Both original reports are preserved unchanged. Runtime and test hashes match the second-review manifest; only documentation/report changes followed that review. Two of at most two calls used, $3.4452006 total reported; no third round.

Conservative limits: duplicate same-identity assignment reductions, a removed assignment still supplied by another default, and null-clear to null-preserve can require rebuild even when a particular example would converge. A dynamic expression that returns null at runtime still classifies mapping and can leave a replay/fresh mismatch; this is explicitly outside S1's static-removal scope and remains part of grouped #36 work. Conditions, lookups, transition guards and S5 contributor attribution are not solved here. Existing administrative overrides can bypass ordinary refusal without reconstructing data; their availability is not a safe-migration guarantee.

Status: implemented, verified and independently accepted for bounded S1; delivered in a draft PR. No merge, deployment or production-readiness claim.
