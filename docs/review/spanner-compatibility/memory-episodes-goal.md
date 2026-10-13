# Memory pack goal: produce and retrieve Episodes, Beliefs and Goals

Status: the bounded Episodes, Beliefs and Goals producers are implemented and verified. See [verification and stakeholder walkthrough](memory-episodes-verification.md), including 138 live Belief/Goal checks, earlier Episode acceptance, local fault probes and Astra final review. This is not pilot readiness.

## Observable behavior

A Memory-enabled tenant can ask Engram for a session timeline and receive typed Episode snapshots, their Summary, exact member Events and evidence. Existing consolidation groups events with a gap greater than 30 minutes. Core-only tenants retain Summary behavior and do not produce or return Memory artifacts. Beliefs and Goals now use explicit Memory contracts, atomic projection and evidenced public recall. #20/#29 fixes, the broader pack audit and public/concurrent tenant readiness remain separate work.

Episodes are immutable membership snapshots, not a claim that a session is permanently closed. Identity depends on session and sorted member event IDs. Repeating the same grouping reuses identities and edges. A later event changing membership creates a new snapshot; earlier snapshots remain history. Retrieval must identify this as history, not silently claim a single latest partition.

Reuse the existing consolidation worker, PackGraph storage interface, selected processing capability and `/v1/query/subgraph` API. No new service or database schema tables. Time-based grouping is deterministic; an LLM may write summary prose but cannot choose membership or fabricate source events. Summary references and CONTAINS/DERIVED_FROM evidence must resolve before a snapshot is exposed as complete.

## Agreed verification seams

Primary acceptance: authenticated `/v1/events` -> real ledger -> real worker loops -> Spanner -> `/v1/query/subgraph`. Final stored-row audit independently verifies exact identities/edges; it cannot replace retrieval acceptance. Supplementary regression: public consolidation message handling, PackGraph writes/reads and RetrievalEngine calls with reference storage. Mock only external providers/fault boundaries, and label local proofs separately.

| Case | Required expected result |
|---|---|
| M01 core only | Qualifying activity creates episode/session Summary; no Episode or CONTAINS output; read does not return Memory nodes |
| M02 core+memory | Two events within five minutes create one temporal Episode snapshot; event_count=2; exact two CONTAINS and DERIVED_FROM links, a valid Summary and source evidence in API response |
| M03 temporal boundary | A third event over 30 minutes later creates a separate one-event snapshot, not a three-event episode |
| M04 retry/reconsolidation | Exact HTTP retry creates no ledger event; repeated consolidation of unchanged membership creates no duplicate Episode/edges |
| M05 arrival order | Older source event arriving later is grouped by occurred_at; expected membership fixed independently |
| M06 snapshot history | An added event produces a new membership snapshot; old snapshot remains identifiable as history, without fabricated current-state claims |
| M07 session isolation | An unrelated session with the same agent/content does not appear in the requested session's Episode results |
| M08 projection order | Missing source Event prevents a complete Episode; after source projection and a later cycle, exact evidence converges |
| M09 interrupted write | Failure between node/edge writes does not expose a complete snapshot; retry completes exact links without duplicates |
| M10 bounded answers | max_nodes is respected; omitted data is marked truncated; no returned edge has an omitted endpoint |
| M11 core+PDLC+memory | An admitted PDLC event can be an Episode member; existing Change projection and evidence remain correct, no invented Episode-to-Change relation |
| M12 invalid input | Rejected envelope makes no ledger/artifact write |
| M13 disabled read | A core-only composed read cannot expose stored Episode data; this is a visibility check, not historical migration |

Before each live case, preserve raw input, expected literal IDs/membership/properties/edges, HTTP status, worker outcomes and expected read result. Preserve failed attempts; record oracle changes explicitly. No manual artifact repair, direct graph insertion, mocked Spanner or HTTP 200-only checks count as live acceptance. Verify the final source revision/configuration and preserve payloads, actual answers, final rows and repeat instructions.

## Resource and completion rules

Reuse only `engram-assess-1010a-pdlc`, after verified export and an owner/dataset check; no earlier goal database changes. Sequential combinations do not prove concurrent tenant isolation. Final data stays retained. No historical migration work.

Finish with a stakeholder verification walkthrough, case-by-case PASS/FAIL/BLOCKED and evidence, independent review, #42/#34/#39/#41 reconciliation and assessment of any newly discovered defects. Do not claim completion if a required scenario is missing/blocked. Do not start another goal or the developer pilot without stakeholder approval.


## Scope correction: Belief and Goal are required

Stakeholder explicitly included both producers on 13 October. Episode acceptance remains valid, but it does not complete the Memory pack. Do not describe Belief/Goal as excluded from the overall goal or count their schema/storage helpers as implemented production paths.

Before coding these producers, ground the contract in the existing BeliefNode/GoalNode models, Memory pack declarations, extraction/projection workers and public read paths. Define the supported event inputs, stable scope/identity, ownership, evidence, retry behavior, lifecycle and retrieval expectations. Reuse the shared workers and pack contracts; do not turn a PDLC ticket into a Memory Goal merely because both describe work. Distinguish stated beliefs from model inference and evidence-backed confirmation from truth. A test passing is not automatic completion of a user Goal.

Required remaining acceptance journeys:

| Area | Observable behavior to implement and verify |
|---|---|
| Belief production | An admitted supported input produces a typed Belief with category, bounded confidence, declared ownership and real source evidence; public retrieval returns it with that evidence |
| Belief confirmation | A distinct supporting event adds evidence once; redelivery and worker retries do not inflate confirmation_count |
| Belief correction | A correction targets an exact prior belief; replacement/history and supersedes/contradicts behavior are explicit and retrievable; unrelated beliefs remain unchanged |
| Goal production | An admitted supported input produces a typed Goal with stable identity, ownership, status and source evidence; public retrieval returns it |
| Goal lifecycle | Active, completed, abandoned and superseded behavior is defined against existing statuses; state changes require supported evidence, and unrelated PDLC artifacts do not drive transitions implicitly |
| Recovery | Missing references, late events and interrupted writes have explicit outcomes; incomplete evidence cannot be reported as a fully verified memory |
| Composition | Core+Memory and core+PDLC+Memory preserve their existing behavior; user pack is not implicitly required; Memory-off processing and reads exclude these capabilities |
| Boundaries | Cross-session recall scope is explicitly defined; unrelated owners/sessions and any tenant outside the authorized binding do not leak into answers |

Apply the same standard as Episodes: declare exact expected results before execution, write regressions, review with Astra, exercise accepted journeys through authenticated Engram writes, real workers, Spanner and public retrieval, preserve failures, independently audit rows, reconcile #42/#34/#39/#41, and produce the stakeholder walkthrough. Label local fault probes separately from live cloud results. Reuse the authorized assessment database only with its current retained owner/fingerprint record and verified export; retain final data. No historical migration work.

Completion requires Episodes, Beliefs AND Goals to meet their declared acceptance journeys. The pilot stays paused until the remaining Memory work and the other pilot prerequisites are resolved; do not start another goal automatically.

## Grounded implementation boundary for Belief/Goal

Use structured `memory.belief.*` and `memory.goal.*` events, with explicit stated/inferred origin and explicit lifecycle commands, through the existing event contracts and projection worker. Natural-language inference is not silently represented as an authoritative state change. Native Belief/Goal identities remain owner- and scope-qualified; default session scope, explicit agent scope for cross-session recall. Confirmation counts include distinct supporting Events only (stated assertion starts at one; inferred proposal at zero).

A narrow atomic graph-storage action is necessary: validate owner and expected state revision, detect already-applied Event identity, update subject/count/state, and write its evidence/history in the same transaction. Existing generic pack node/state/edge calls are separate and cannot enforce this across workers. Reuse the current graph tables and backend transactions; an in-process lock alone is not the Spanner guarantee. Wrong revision/terminal conflicts must be explicit, not last-writer-wins. Missing references require bounded recovery or an explicit failure outcome. Public `/v1/query/subgraph` will return validated owner-scoped Memory context; a tenant-wide artifact query without an owner selector is not an adequate substitute.

The already agreed test seams remain authenticated HTTP ingestion/retrieval, public projection handling and graph-storage operations. Start with one stated Belief end to end through the storage seam, then confirmation/correction and Goal lifecycle; prove Spanner atomicity with competing updates before claiming verification.

## Belief/Goal live verification plan (13 October)

Runner: `scripts/engram_memory_actions_demo.py`, reusing the Episode harness's exact-target export, owner/fingerprint reset and shutdown safeguards. Core-only must reject Memory actions without ledger writes. Core+Memory and Core+PDLC+Memory must independently exercise stated/inferred Beliefs, distinct confirmation, same-revision conflict, explicit correction/history, all four Goal states, session versus explicit agent scope, a different owner, missing-parent recovery, invalid-contract rejection and bounded retrieval. Five real workers run; the final dataset remains retained.

Expected states, source receipts and exact DERIVED_FROM/SUPERSEDES/CONTRADICTS sets are reconstructed from submitted inputs, excluding only the independently checked revision-conflict loser. API answers and a separate final Spanner row audit must match. Equivalent timezone formats are compared as datetimes. All groups must settle; the exact expected conflict is the only permitted dead letter. Both review findings about false-positive harness checks and failed attempts remain evidence.

Concurrent HTTP submission to one projection consumer proves deterministic revision conflict handling, not concurrent-worker transaction safety. That backend concurrency claim needs its own probe and must not be inferred from the HTTP check. Structured `inferred` inputs are producer proposals, not a claim that an autonomous LLM inferred a belief. No pilot or other goal starts automatically.
