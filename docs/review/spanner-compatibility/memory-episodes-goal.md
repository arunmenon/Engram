# Memory-only goal: produce and retrieve episodic snapshots

Status: selected Episode slice implemented and verified; see [stakeholder verification](memory-episodes-verification.md). This is not pilot readiness.

## Observable behavior

A Memory-enabled tenant can ask Engram for a session timeline and receive typed Episode snapshots, their Summary, exact member Events and evidence. Existing consolidation groups events with a gap greater than 30 minutes. Core-only tenants retain Summary behavior and do not produce or return Memory artifacts. Belief and Goal production, #20/#29 fixes, the broader pack audit and public/concurrent tenant readiness are outside this slice.

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
