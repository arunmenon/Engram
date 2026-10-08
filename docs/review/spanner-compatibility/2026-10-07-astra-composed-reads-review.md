# Composed reads implementation review

2026-10-07. Read-only inspection; no tests, probes or services executed. Scope: primitive Memory/Spanner read view, shared retrieval changes, wiring and focused tests. Neo4j scoped queries and native Spanner ANN corpus correction remain explicitly pending.

## Verdict

**Initial verdict: changes requested within the proposed primitive boundary. See recheck below for current dispositions.** Filtering complete primitive rows before shared aggregation is the appropriate architecture, but identity and endpoint validation remain incomplete. Findings below are code-inspection results, not executed reproductions.

1. **P2 — Validate canonical node identity before returning primitive rows.** `adapters/composed_reads.py:50–65` checks requested tuple membership but not the canonical ID property. A stored `('Event', 'requested')` row carrying `event_id='other'` survives; `retrieval/engine.py:653` then admits the unrequested ID. `_find_nodes` similarly passes missing/invalid IDs into shared rankings. Retain schema key metadata in the immutable scope, validate returned properties against requested keys, and reject malformed identities before ranking/limits. Defensively reject unexpected event records in `_fetch_seed_nodes`. Add mismatched-key and extra-record regression cases, including `record_access` forwarding only valid Events.

2. **P2 — Reject nonexistent or invalid endpoint rows before counts and limits.** `adapters/composed_reads.py:87–95` checks only endpoint labels/triples, not whether either endpoint exists with valid identity. A dangling Event→Entity REFERENCES row therefore affects entity-hub counts and consumes a neighbor slot; an active-typed dangling SUPERSEDES source can hide an existing artifact. Shared `graph_ops.neighbors` limits before loading far nodes, and `event_neighbors` emits empty properties for missing targets, so downstream filtering cannot recover lost slots. Resolve and validate both endpoint keys inside the primitive edge boundary before returning rows; add dangling-endpoint differential fixtures with small limits and supersession checks.

3. **P2 — Complete the artifact defensive neighbor contract.** `retrieval/artifacts.py:348–358` verifies edge membership/triples/rejection status but does not verify the requested near reference and direction, or the returned far-node label/key/properties against the corresponding endpoint. `_superseded` consumes these rows without validating the source node, so malformed allowed-label rows can change artifact admission. Centralize full row validation here, using registry key metadata and the requested batch/direction. Add recording-port regressions for an unrelated returned near key, mismatched far ID, and missing far node. This is a defensive contract finding distinct from the pending Neo4j pre-limit implementation.

## Other observations

Rejected links and inactive/invalid endpoint triples are filtered before shared limits. Shared causal/entity/cross-session endpoint typing is improved. Original stores remain available for writes/privacy, and inherited mutations on the view raise PermissionError. Explicit unresolved caller seeds are no longer assumed to be Entity IDs. Artifact explicit intents are rejected when unavailable; event intents are intersected with the active set, though explicit unavailable event overrides currently fall back rather than being rejected as the design requests. Vector IDs still use the existing untyped fusion path; no typed-vector or ANN completion claim is warranted.

Recorded `20261007-local-composed-reads-01/tests.txt` currently reports **2 failed, 50 passed**. The six new tests cover inactive labels, wrong edge endpoints, rejected links, inactive supersession, access writes and unresolved explicit seeds; they do not cover the identity/dangling/defensive cases above. Successful local rechecks and these dispositions are needed before approval of this narrow boundary. This report does not assert complete retrieval optionality, tenant isolation, Neo4j coverage or real Spanner acceptance.

## Remediation recheck

Read-only inspection on 2026-10-07 resolves original findings 1–3. ReadScope retains registry key fields; keyed reads validate canonical IDs and label reads rehydrate canonical keys. Edges resolve both valid endpoints before returning to shared counts/limits. Artifact `_valid_neighbor` now checks near-reference membership/direction and far canonical reference. Public primitive forwarding preserves backend error translation; access forwarding uses a public method after validation. Event seed responses reject unrequested IDs, unavailable explicit intents now fail, and composed vector Entity hits resolve to referencing Events before fusion.

Inspected recorded `20261007-local-composed-reads-04/tests.txt`: **96 passed, 15 warnings**, 2.96 seconds. No tests executed by this reviewer.

**Remaining P2 — choose neighbor identity solely from its validated label.** `retrieval/engine.py:_expand_neighbors` validates label-specific identity, then selects `neighbor_event_id or neighbor_entity_id` and branches on whether `neighbor_event_id` exists. Shared `event_neighbors` populates these fields from properties regardless of label. A canonical Entity row with `entity_id='good'` plus stale extra `event_id='other'` passes the Entity check but is then treated/scored as Event `other`. Canonical key validation does not reject unrelated extra properties. Derive the selected identity and node branch exclusively from the validated label, or clear all unrelated discriminator fields before processing. Add a mixed-property regression. This is a label-confusion issue, separate from the explicitly pending equal-ID mixed Atlas collision work.

**Current verdict: changes requested for this remaining identity branch.** Native ANN corpus restriction, Neo4j scoping, complete mixed Atlas collision handling and real cloud evidence remain explicitly outside this recheck.

## Final narrow identity recheck

Read-only inspection confirms the remaining P2 is **resolved**: in composed mode `_expand_neighbors` now selects Event or Entity discriminator fields exclusively from the validated label. Stale cross-type discriminator properties no longer choose identity or the node-construction branch. The parameterized regression checks Event and Entity cases, exact resulting node type/ID and edge endpoints.

Recorded `20261007-local-composed-reads-05/tests.txt` reports **98 passed, 15 warnings**, 2.76 seconds. No tests executed by this reviewer. **Current verdict: approve the reviewed composed primitive-read slice; all reported findings resolved.** Pending mixed Atlas ID collisions, Neo4j scoping, native Spanner ANN corpus correction and cloud acceptance remain separate and are not approved by this disposition.
