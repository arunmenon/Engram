# Pack integration: published implementation context

Parent feature: [#34](https://github.com/arunmenon/Engram/issues/34). This is the persisted context index for every native GitHub sub-issue. No runtime code is included in this documentation publication. Open checklists and prior passing scoped checks do not establish completion or Spanner compatibility.

## Reading order

1. [Master plan](../2026-10-06-spanner-compatibility-plan.md), especially detailed design, Step10 implementation slices, pack-neutral diagram and review dispositions.
2. [Astra medium review](2026-10-07-astra-pack-engine-design-review.md) and [approved review prompt](2026-10-07-astra-pack-engine-design-review-prompt.md).
3. [PDLC event inventory](pdlc-event-contract-inventory.csv), [payload experiment matrix](pdlc-payload-experiment-matrix.csv), [public corpus discovery](public-payload-corpus/discovery-pass.md) and [source manifest](public-payload-corpus/manifest.json).
4. [Issue/bucket map](pack-integration-subissue-map.csv), [existing implementation waves](implementation-waves.csv) and individual contexts below. The five older waves and six newer design slices are distinct: use the master plan's slice gates for feature34; older wave labels preserve existing defect planning history.

## Slice sequence and gates

|Slice|Work and exit gate|
|---|---|
|1|Contracts, capability/version/duplicate/update decisions and exact fixtures. Account for every PDLC event and an unfamiliar pack. No unresolved blocking policy deferred into runtime changes.|
|2|Shared all-route ingress, trust and interpretation metadata. Valid and invalid paths through actual Engram/Spanner; old-worker compatibility/refusal gate before accepting new records.|
|3|Recovery, retries, processing obligations and retention. No loss or false completion under failures/restart.|
|4|Exact artifacts and evidence, convergent ordering, missing-reference repair and shared worker handoffs.|
|5|Retrieval truth, claim-specific evidence, pagination/budgets and actual deadline behavior.|
|6|Historical replay/rebuild/cutover and full bounded conformance acceptance with review evidence.|

Feature foundation has priority. Execute bounded paths and fix linked defects required by each path; do not wait for all29 tasks before proving the first journey. No new orchestration service, runtime adapter generator or Redis-to-Spanner migration is selected.

## Evidence boundaries

The public corpus is collected source material, not executed ingestion. All23 matrix rows still need exact acceptance oracles and execution. Astra medium review ran no tests. Earlier cloud/run results and scoped code reviews keep their original limited scope. This publication includes planning, review reports, inventories, corpus and aggregate historical ledger/status; raw files under `runs/` and local scratch scripts are not part of this design-document commit. Ledger references to those files are historical pointers, not GitHub-hosted evidence. Runtime fixes/harness source remain uncommitted. Do not treat this commit as a runnable snapshot of those fixes or as preservation of every raw execution artifact.

## Individual sub-issue contexts

### Issue 4

[Validate pack-specific event payloads before ledger append](https://github.com/arunmenon/Engram/issues/4)

- Bucket: Pack contracts and activation.
- Implementation slices: 1;2.
- Master-plan design references: Steps0–4,8; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-04;PE-05;PE-06;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `4`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 5

[Bind pack source trust to authenticated ingress identity, not caller-supplied agent_id](https://github.com/arunmenon/Engram/issues/5)

- Bucket: Pack contracts and activation.
- Implementation slices: 1;2.
- Master-plan design references: Steps0–4,8; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-04;PE-05;PE-06;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `5`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 35

[Feature: check pack capabilities and API/worker interpretation compatibility](https://github.com/arunmenon/Engram/issues/35)

- Bucket: Pack contracts and activation.
- Implementation slices: 1;2;6.
- Master-plan design references: Steps0–4,8; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-05;PE-06.
- Scope and gate: Define required/optional capabilities, owner/subscriber permissions, interpretation metadata and historical artifacts. Gate slice2 on API/worker N/N−1 compatibility or controlled refusal. Full historical rebuild remains slice6.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `35`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 17

[Validate webhook source shapes and normalized envelopes through the shared ingestion boundary](https://github.com/arunmenon/Engram/issues/17)

- Bucket: Source mapping and ingestion.
- Implementation slices: 1;2.
- Master-plan design references: Steps1–4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-04;PE-05;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `17`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 28

[Handle first-chunk Spanner storage failures deliberately in ingestion APIs](https://github.com/arunmenon/Engram/issues/28)

- Bucket: Source mapping and ingestion.
- Implementation slices: 1;2.
- Master-plan design references: Steps1–4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-04;PE-05;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `28`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 37

[Feature: reject conflicting same-ID events and pin source normalization identity](https://github.com/arunmenon/Engram/issues/37)

- Bucket: Source mapping and ingestion.
- Implementation slices: 1;2.
- Master-plan design references: Steps1–4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-04.
- Scope and gate: Choose immutable duplicate/conflict and source binding identity policy; test changed content, split/reordered delivery and committed-but-response-lost retries.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `37`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 8

[Make pack projection lookups complete and prefix-constrained latest selection correct](https://github.com/arunmenon/Engram/issues/8)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `8`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 9

[Preserve provenance for pack-driven lifecycle changes on non-upserted nodes](https://github.com/arunmenon/Engram/issues/9)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `9`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 18

[Compute session FOLLOWS lineage correctly across projection replicas](https://github.com/arunmenon/Engram/issues/18)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `18`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 20

[Allow entity-interest provenance writes to complete session extraction on Spanner](https://github.com/arunmenon/Engram/issues/20)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `20`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 29

[Preserve enrichment when its worker runs before Event projection](https://github.com/arunmenon/Engram/issues/29)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `29`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 30

[Repair CAUSED_BY links when the accepted causal parent projects later](https://github.com/arunmenon/Engram/issues/30)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02;PE-03.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `30`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 36

[Feature: define pack projection update, fan-out and ordering rules](https://github.com/arunmenon/Engram/issues/36)

- Bucket: Projection, ordering and evidence.
- Implementation slices: 1;3–4.
- Master-plan design references: Steps2,5–6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-01;PE-02.
- Scope and gate: Choose missing/null behavior, list cardinality bounds, ordering/tie/stale policy and property authority. Verify exact deltas, A/B/A and competing subscribers.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `36`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 10

[Preserve pack extraction evidence when extraction runs before projection](https://github.com/arunmenon/Engram/issues/10)

- Bucket: Worker completion and recovery.
- Implementation slices: 1;3–4.
- Master-plan design references: Step6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-02;PE-07.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `10`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 14

[Retry failed live deliveries and reclaim orphaned work without requiring worker restart](https://github.com/arunmenon/Engram/issues/14)

- Bucket: Worker completion and recovery.
- Implementation slices: 1;3–4.
- Master-plan design references: Step6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-02;PE-07.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `14`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 19

[Protect unprocessed ingestion documents from retention and never silently ACK missing content](https://github.com/arunmenon/Engram/issues/19)

- Bucket: Worker completion and recovery.
- Implementation slices: 1;3–4.
- Master-plan design references: Step6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-02;PE-07.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `19`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 38

[Feature: expose correlated pack-processing outcomes for accepted events](https://github.com/arunmenon/Engram/issues/38)

- Bucket: Worker completion and recovery.
- Implementation slices: 1;3–4.
- Master-plan design references: Step6; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-07.
- Scope and gate: Define minimal correlated applied/skipped/deferred/failed/unknown outcomes and obligations using existing state before adding support; test disabled workers, partial failure, restart and retention.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `38`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 11

[Do not mark a pack mapping upgrade complete after replay write failures](https://github.com/arunmenon/Engram/issues/11)

- Bucket: Versioning and replay.
- Implementation slices: 1–2 compatibility gate;6 historical work.
- Master-plan design references: Step4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-05.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `11`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 12

[Make incomplete ontology rebuilds fail closed unless explicitly accepted](https://github.com/arunmenon/Engram/issues/12)

- Bucket: Versioning and replay.
- Implementation slices: 1–2 compatibility gate;6 historical work.
- Master-plan design references: Step4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-05.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `12`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 13

[Preserve the original Spanner ledger during ontology blue/green graph cutover](https://github.com/arunmenon/Engram/issues/13)

- Bucket: Versioning and replay.
- Implementation slices: 1–2 compatibility gate;6 historical work.
- Master-plan design references: Step4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-05.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `13`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 21

[Make Spanner admin replay advance across tied event timestamps](https://github.com/arunmenon/Engram/issues/21)

- Bucket: Versioning and replay.
- Implementation slices: 1–2 compatibility gate;6 historical work.
- Master-plan design references: Step4; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-05.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `21`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 6

[Do not report missing artifact links when completeness reads are incomplete](https://github.com/arunmenon/Engram/issues/6)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `6`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 7

[Exclude rejected relationships from artifact traversal and returned evidence](https://github.com/arunmenon/Engram/issues/7)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `7`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 22

[Count ontology pack nodes and relationships in graph stats and totals](https://github.com/arunmenon/Engram/issues/22)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `22`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 24

[Bound lineage nodes and advance pagination beyond the first path prefix](https://github.com/arunmenon/Engram/issues/24)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `24`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 25

[Hydrate Entity vector seeds and retrieve their event reference evidence](https://github.com/arunmenon/Engram/issues/25)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `25`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 31

[Keep context cursor ordering consistent across distinct event timestamps](https://github.com/arunmenon/Engram/issues/31)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `31`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 32

[Enforce retrieval graph read budgets through Spanner SDK deadlines](https://github.com/arunmenon/Engram/issues/32)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1 oracle design;5 retrieval;6 full acceptance.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-03;PE-08.
- Scope and gate: Preserve the original failure evidence and scoped acceptance criteria in this issue. Apply the shared review gates relevant to its boundary; avoid expanding it into unrelated feature work.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `32`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).

### Issue 39

[Feature: add reusable whole-pack artifact and retrieval conformance fixtures](https://github.com/arunmenon/Engram/issues/39)

- Bucket: Conformance and retrieval acceptance.
- Implementation slices: 1;2–6.
- Master-plan design references: Steps7–9; Step10 gates and Astra design dispositions.
- Review findings to consult: PE-08; all gates.
- Scope and gate: Create exact fixture/oracle coverage for all23 PDLC events, CRM and unfamiliar pack; distinguish source capture, synthetic wrappers, local tests and tracked actual Spanner acceptance.
- Acceptance source: current GitHub issue body and [publication-time snapshot](pack-integration-published-issue-snapshot.json), entry `39`; [Astra findings and conformance checklist](2026-10-07-astra-pack-engine-design-review.md).
