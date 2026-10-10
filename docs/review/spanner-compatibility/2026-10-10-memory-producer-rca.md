# RCA: did the pack refactor lose Memory projection?

## Answer

Earlier Engram did implement memory behavior. The available source history does **not** show a working Belief/Goal/Episode producer being removed by the pack refactor. It shows those three types added as models, constraints and storage helpers, without an event-to-artifact caller. The refactor preserved that schema and its existing gap.

The original episodic behavior grouped events and wrote **Summary** nodes with `scope="episode"`; it did not create **Episode** nodes. That summary path still exists. Calling all Memory projection absent was too broad: it confused the named Memory pack's three types with Engram's broader event-context, personalization and summary features.

This conclusion is grounded in fetched available branches and history. It is not proof about an unavailable branch or an external application that may have directly called storage helpers.

## Investigation and evidence

Source baseline: `b31f1c0`. No runtime edits, database writes, new cloud runs or migration work were performed for this RCA.

1. Fetched origin and inspected 45 available local/remote branch references and historical checkpoints. AST inspection found zero direct constructor or writer calls for Belief/Goal/Episode in their `src` Python files. Definitions/imports exist; no parse errors occurred. [Pinned refs, files, definitions and call results](runs/20261010-memory-producer-rca/source-call-audit.json).
2. Searched available worker/API history for additions/removals of the constructors and merge calls: no matching commits. Inspected the original Memory Intelligence commit, the type-introduction commit and the boundary immediately before pack extraction.
3. Compared the original and current consolidation paths, checked the pack declarations and processing-provider registry, and inspected the SDK's use of the word Memory.
4. Ran existing consolidation and composition tests: **74 passed**. [Command and limits](runs/20261010-memory-producer-rca/test-receipt.json), [test log](runs/20261010-memory-producer-rca/tests.log). These are local unit tests using mocked/reference storage, not a fresh Spanner proof.

The audit script is [preserved](runs/20261010-memory-producer-rca/source-call-audit.py). Its negative-call search does not cover dynamic dispatch, unavailable branches, external producers or arbitrary direct Cypher outside the matched files. Manual inspection of the known historical Neo4j creation queries located them in adapter helpers, rather than a worker producer.

## What happened over time

| Checkpoint | What the implementation contains | What that establishes |
|---|---|---|
| `d49ded4` — Memory Intelligence | Consolidation groups session events into temporal episodes, calls `create_summary_from_events(scope="episode")`, then `write_summary_with_edges`; also creates session summaries | Real episodic summarization, stored as Summary/SUMMARIZES, not Episode/CONTAINS |
| `797f799` — schema evolution | Introduces BeliefNode, GoalNode, EpisodeNode, uniqueness constraints, merge helpers and belief-contradiction utilities | Storage/schema support, without a worker/API producer for these types |
| `b4a94d9` — immediately before ontology phase 0 | Same helpers and summary behavior; no producer callers found | The missing typed producer predates the pack split |
| `0507231` — schema packaged into packs | Memory YAML declares the three types and relationships; no projection rules or extraction profile | Packages vocabulary; does not add its missing production path |
| Current `b31f1c0` | Merge helpers remain in GraphOperations/Neo4j; consolidation still writes Summary; resolved processing has core/user/domain providers but no typed Memory producer | No evidence of a removed producer; the inherited gap remains visible under optional pack selection |

Historical source links: [original consolidation](https://github.com/arunmenon/Engram/blob/d49ded4e0c92eab32b822197669254b31e14aed5/src/context_graph/worker/consolidation.py), [type introduction](https://github.com/arunmenon/Engram/commit/797f79981a666805e21fd05b08ed0fe17f43c43e), [pre-pack consolidation](https://github.com/arunmenon/Engram/blob/b4a94d9fa9486bb847b638b56df117071559ceb4/src/context_graph/worker/consolidation.py), [initial Memory pack](https://github.com/arunmenon/Engram/blob/05072319dec3ef164560693c889cfd1a017ab393/src/context_graph/ontology/packs/memory.pack.yaml).

## Root cause and contributing factors

**Direct technical cause:** there is no registered producer that turns an admitted event or extraction result into a Belief, Goal or Episode and persists its evidence. Models and merge methods supply the destination, not the producer. Current Memory YAML has neither projection mappings nor an extraction profile; the processing registry has no corresponding handler.

**Historical origin:** the type-introduction change completed schema/storage scaffolding but did not wire these types into the ingestion/worker path. The inspected pre-pack source already had this separation. Packaging the schema later did not close it. The evidence supports an inherited integration gap, rather than a demonstrated refactor regression for these three types.

**Why the terminology misled us:** “memory” describes several different things in this repository. Event retrieval and user personalization are memory features; consolidation's episode grouping writes Summary nodes; the SDK `Memory` is a search-result model, and its simple `add()` records an `observation.output` event. None of those names establishes production of the Memory pack's three artifact types.

**Verification gap:** schema parity tests verify that pack types equal existing enums/models. Consolidation tests verify summary writes. Both can pass without a Belief/Goal/Episode being produced from an API event. This explains how schema preservation and working summary tests fail to establish the missing capability. It is a coverage diagnosis, not a claim about the original author's intent.

**What is not established:** this RCA does not certify every earlier memory feature as behaviorally preserved. User extraction currently fails under #20 and enrichment under #29; those are separate defects. The recent live assessment did not trigger and prove the full consolidation lifecycle. Source-preserved summaries and passing unit tests are not fresh end-to-end cloud evidence.

## Current path, in plain language

| Input/selection | Implemented path | Missing path |
|---|---|---|
| Enough session activity to qualify for consolidation | Events → episode-sized groups → episode/session Summary → SUMMARIZES evidence | A separately identified Episode → CONTAINS → Event |
| User-selected prose extraction | Events → extracted profile/preferences/entities through specialized code | This is not automatic Belief/Goal production; #20 currently interrupts some results |
| Enable Memory alongside core or PDLC | Adds Belief/Goal/Episode vocabulary to the composed schema | No producer is enabled for those types; no automatic PDLC-to-Memory join |

## Bounded corrective direction

1. Preserve existing core event/entity/summary behavior; do not rewrite it or rename every Summary as Episode. Do not disable core consolidation when Memory is absent.
2. Track the missing typed producer under **#42**, linked to #34. The feature must distinguish schema support from supported write/read behavior. No additional feature bucket is needed for this RCA alone.
3. Before implementing, agree the exact input and expected artifacts for each desired type. For Episode, reuse existing grouping and summary work if approved, adding stable Episode identity and CONTAINS/source evidence. Belief and Goal need explicit producer semantics, identity, updates and evidence; they cannot safely be inferred from every preference or ticket.
4. Verify the selected contract through authenticated Engram writes → ledger → real workers → Spanner → Engram retrieval, with enabled/disabled selections and retry checks. A schema test or direct storage-helper call is insufficient.

This RCA authorizes no implementation. No new Memory service/framework, historical migration or pilot stage is proposed as part of the investigation. Runtime fixes and the minimum useful Memory contract remain the next stakeholder checkpoint.

## Tracking

The live composition report is [here](2026-10-10-pack-composition-assessment.md). The earlier historical check in the [pilot brief](2026-10-08-controlled-pilot-discovery-brief.md#follow-up-was-memory-projection-removed-by-the-refactor) is retained; this RCA expands it with a fetched branch/call audit and targeted test evidence. No independent Astra review of this RCA is claimed.
