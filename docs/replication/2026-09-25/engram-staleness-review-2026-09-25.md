# Engram repository staleness review

Reviewed: 2026-09-25. Reference: the user-supplied ADR transcripts and active companion LLD catalog. Superseded LLD transcripts were excluded. This is a repository comparison, not a production certification or a review of the user's newer private/local codebase.

## Conclusion

The shared repository contains a substantial implementation of Engram's original memory architecture. It is materially behind the supplied API, authorization, privacy, configuration, integration, and evaluation contracts. Updating documentation alone will not close the gap. The ontology exists; its executable enforcement and tenant identity rules need work against the latest LLD.

The strongest candidate starting point for reconciliation is `dev`, after reviewing its divergence from `main`. The newer evaluation branch has the same application source, SDKs, and ADRs as `dev`; it adds evaluation tooling rather than the missing production contracts. Do not assume a branch merge completes replication.

## 1. What was compared

| Branch | Pinned commit | Commit date | Numbered ADR files |
|---|---|---|---:|
| main | `f641a0f96c39f0808d5e017e915bb9e3d5187394` | 2026-03-06 | 17: 0001–0017 |
| dev | `a1aed9b3c078955eb6433618d0f0c1d98e0e120d` | 2026-03-13 | 18: 0001–0018 |
| feature/autoresearch-eval-scoring | `9df84ed7cb211aba42c8f287c7c52145931f7ce1` | 2026-04-06 | 18: 0001–0018 |

All seven remote branch tips were inventoried. None contains numbered ADRs 0019 onward or files identifiable by path as the companion LLD collection. Other design/research documents exist; the absence of LLD files does not mean the absence of all low-level design documentation. Branch tips match the earlier inspection. `main` and `dev` diverge: 5 commits are unique to main, 15 to dev. This is not a simple fast-forward update.

Sources: [main ADR directory](https://github.com/arunmenon/Engram/tree/f641a0f96c39f0808d5e017e915bb9e3d5187394/docs/adr), [dev ADR directory](https://github.com/arunmenon/Engram/tree/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/docs/adr), [evaluation branch](https://github.com/arunmenon/Engram/tree/9df84ed7cb211aba42c8f287c7c52145931f7ce1/tests/eval).

### Exact document gap

- Latest reference received: **23 complete ADR transcripts**, **one partial ADR-0030**, and **Artifact-0025**, which is an open issue rather than an ADR.
- Of those 23 complete ADR transcripts, **13 have corresponding repository ADR files**. **10 have no corresponding ADR file** on any checked branch: **0019–0024 and 0026–0029**.
- Partial ADR-0030 and Artifact-0025 are also absent as corresponding numbered documents.
- Active companion LLDs: **0001–0016 complete; 0017 title only**. No corresponding companion LLD collection was found in the repository.
- ADR-0011, 0012, 0013, and 0015 have repository ADRs and active LLD transcripts, although separate full ADR transcripts have not been supplied. ADR-0018 exists on dev but has no supplied transcript. These are coverage limits, not deletions to make.
- A commit timestamp establishes repository age, not the age of the user's latest source system. Exact commit distance to that newer system cannot be calculated without its revision history.

## 2. Coverage against the supplied decisions

“Present” below means code was located, not that every acceptance test in the latest LLD passed.

| ADR / active LLD | Repository evidence and drift | Assessment |
|---|---|---|
| 0001–0003: provenance, service boundaries, dual store | Event and Atlas models, domain/ports/adapters, projection and lineage are present. Python requirement is >=3.12. Full deterministic replay/provenance equivalence was not exercised against live stores. | Core architecture present; conformance still to prove |
| 0004: immutable ingestion | Redis Lua coordinates deduplication and writes. The existing duplicate branch returns the old position without comparing incoming content. It does not enforce the newer conflicting-content rejection expectation. | Partial against latest LLD |
| 0005: workers and replay | Consumer-group processing, retries, reclamation, DLQ and projection exist. No event-upcasting implementation was located in the inspected source. Crash-window acceptance still needs live tests. | Substantial implementation; stronger contract incomplete |
| 0006–0009: Atlas, tiers, lifecycle, retrieval | Atlas, bounded query models, lineage, decay, consolidation, intent, hybrid retrieval, PPR and reranking exist. This is more than a vector-only memory store. Signed tenant/resource-bound cursors belong to later ADR-0026 and are absent. | Core present; latest end-to-end invariants not fully established |
| 0010: Redis event store | Redis Stack, Streams, JSON, search, ingestion script and retention paths exist. dev adds tenant prefixes, batching and scaling work. Duplicate conflict handling and pending-safe behavior across all trimming paths need reconciliation. | Present with contract gaps |
| 0011–0012: ontology and personalization | 11 node types, 20 edge types, entity resolution, personalization and contradiction logic exist. Tenant-qualified uniqueness and a unified executable schema registry are missing from inspected paths. | Vocabulary present; enforcement gap |
| 0013: extraction pipeline | Separate projection, extraction, enrichment and consolidation workers exist. Exhausted model failures can become empty successful extraction results, conflicting with the latest recoverable-work requirement. | Concrete behavioral gap |
| 0014: archival | Archive adapters and archive-before-delete path exist. Deletion can also occur without an archive adapter; no explicit archive verification receipt/checksum gate is present in the lifecycle contract inspected. | Partial safety guarantee |
| 0015: SDKs/adapters | Python core, MCP, LangChain and CrewAI packages exist. dev additionally has a separate kg-memory-mcp package. The broader set named in the LLD—such as TypeScript, LangGraph, LlamaIndex, AutoGen, Pydantic AI and Vercel—is not shipped as corresponding packages here. Ambiguous dictated names need confirmation before defining exact package targets. | Material integration gap |
| 0016: security | Static standard/admin keys; dev adds caller-header tenant selection. Latest LLD describes tenant-scoped key records; ADR-0026 requires credential-derived tenancy. Neither is provided by these guards. | Material trust-boundary gap |
| 0017: observability | Metrics/logging/health exist; dev actively updates consumer lag. Do not repeat the transcript's older “gauge defined but not populated” caveat as a universal current-code finding. The companion LLD is title-only. | Partial alignment; exact production coverage unverified |
| 0018: scale | Proposed ADR exists on dev, with scaling code and tests. No latest transcript received. | Cannot compare to latest source |
| 0019: LLM gateway | LiteLLM calls exist, but a shared optional API-base/API-key configuration passed consistently to model call sites was not found. Library-level environment routing is not proof of this application contract. | Missing documented gateway abstraction |
| 0020–0024: evaluation | The evaluation branch adds a real harness, datasets and experiment output. That is useful evidence, but not the supplied full benchmark-family, domain-pack and cross-system adapter protocol. No corresponding ADR files or Mem0/Graphiti/Cognee adapter suite was located. | Partial evaluation foundation |
| Artifact-0025 | Contradiction/supersession logic exists; the supplied version-5 issue and its run evidence are absent. | Cannot claim the issue resolved |
| 0026: API v1 contract | Existing narrower routes do not provide the broad capability register, HTTP response idempotency, signed cursors, distributed quotas and durable job surface described. | Major contract gap |
| 0027: grants | No corresponding event-sourced resource-grant/cascade subsystem found. | Missing from inspected implementation |
| 0028: suppression and crypto-shred | Existing user deletion delegates to Neo4j deletion/anonymization. No subject-key destruction and monotonic suppression subsystem found. | Major privacy lifecycle gap |
| 0029: tenant configuration | Global typed settings and tenant defaults exist; no event-sourced allowlisted tenant set/reset resolver with versioned overrides and platform caps found. | Missing described subsystem |
| 0030: disaster recovery | Only title and prototype status supplied. Event archival does not establish full backup/restore behavior. | Insufficient latest reference to assess fidelity |

## 3. Highest-priority implementation differences

### A. Tenant identity is selected by a header on dev

`require_api_key` validates one global key independently of `require_tenant`, which accepts the configured tenant header. A local probe passed the same valid dummy API key with tenant-a and tenant-b and obtained both tenant contexts. This verifies the guards' behavior; it is not a live cross-tenant data-access penetration test.

Latest target: LLD-0016's tenant-scoped credentials and ADR-0026's credential-derived tenant identity. The superseded cell LLDs were not used to add requirements.

Source: [dependencies.py](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/api/dependencies.py#L40).

### B. Neo4j identity is not tenant-qualified

Uniqueness is defined on `event_id` alone. Event MERGE also matches `event_id` alone and then sets `tenant_id`. Consequently, a reused event identifier from another tenant targets the same graph identity rather than a distinct tenant-qualified identity. This follows from the Cypher; it was not exercised against a live Neo4j instance. Tenant-filtered reads do not repair this write identity problem.

Source: [constraints](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/adapters/neo4j/queries.py#L16), [MERGE](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/adapters/neo4j/queries.py#L213).

### C. Ontology definition exceeds executable validation

The ontology ADR includes PROV-O grounding, PG-Schema documentation, non-destructive resolution and later Belief/Goal/Episode amendments. It is still marked Proposed, consistent with the supplied LLD. There is no need to invent this ontology from scratch.

However, `Edge` has untyped endpoint strings and an arbitrary properties dictionary. A probe accepted `REFERENCES` with an invalid role. Cypher templates provide some endpoint-label checks, so this does not mean every invalid edge is persisted; it shows that the generic model is not the machine-readable validation registry required by the latest LLD. Tenant-qualified keys, legal endpoint combinations, relationship property validation and schema conformance tests should become one consistent contract. OWL/RDF tooling is not required by this finding.

Sources: [ontology ADR](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/docs/adr/0011-ontological-foundation.md#L387), [Edge model](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/domain/models.py#L499).

### D. Model failure can be acknowledged as empty success

After retries, extraction returns `_empty_result` on model or JSON parsing failure. The extraction worker treats that result normally; the consumer acknowledges a normally returning handler. A simulated model outage reproduced the empty return without an exception. This differs directly from LLD-0013's requirement to preserve recoverable work rather than acknowledge fabricated empty success.

Sources: [failure handling](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/adapters/llm/client.py#L719), [consumer acknowledgement](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/worker/consumer.py#L428).

### E. Archive safety is conditional

The normal lifecycle archives when an archive store exists, but directly deletes expired documents otherwise. The archive path treats a successful adapter return as permission to delete; it does not consume an explicit verified manifest/checksum receipt. This falls short of the supplied mandatory archive-before-delete and verification guarantee. GCS client transport checks, if enabled, are not equivalent to a cross-adapter replay-verification contract.

Sources: [lifecycle branch](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/worker/consolidation.py#L556), [archive/delete sequence](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/adapters/redis/trimmer.py#L298).

### F. New API and privacy contracts require implementation

Cursors are base64 timestamp/ID pairs without a signature, expiry or tenant/resource binding. Redis event deduplication does not supply HTTP idempotency with exact response replay and body-conflict detection. Existing user erasure is graph-side work, not the later suppression/key-destruction design. These are concrete scope additions rather than terminology corrections.

Sources: [pagination](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/domain/pagination.py#L12), [event deduplication](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/adapters/redis/lua/ingest.lua#L27), [user deletion route](https://github.com/arunmenon/Engram/blob/a1aed9b3c078955eb6433618d0f0c1d98e0e120d/src/context_graph/api/routes/users.py#L143).

## 4. How to close the gap

1. **Reconcile the baseline.** Review main/dev divergence and separately assess the evaluation branch. Preserve the transcript source and exact revision provenance.
2. **Turn the latest contracts into acceptance fixtures.** Freeze event conflicts, Atlas evidence, tenant identity, schema rules, crash recovery and archive safety first. Distinguish reference-system behavior from proposed design and future acceptance gates.
3. **Close foundational correctness gaps.** Tenant-bound credentials and graph identities; duplicate content conflicts; failed-extraction retry semantics; archive verification and deletion policy; executable ontology validation.
4. **Implement the newer product contracts.** ADR-0019 and 0026–0029, using a capability register that accurately marks partial/disabled features. Accepted does not mean production-complete in the supplied transcripts either.
5. **Expand integrations and evaluation.** Ship/test actual packages, preserve Atlas provenance, then implement comparable experiment adapters and structural metrics. Keep proposed evaluation work labeled Proposed until accepted.
6. **Finish collecting the reference.** Obtain the rest of ADR-0030 and the remaining companion LLDs before claiming full replication, especially disaster recovery and later production controls.

No implementation or GitHub writes were performed for this review.

## 5. Verification and limits

- Fresh GitHub branch inventory plus full isolated clone.
- Application source/SDK/ADR diff between dev and the evaluation branch is empty; the latter adds evaluation files, documentation and dependency changes.
- Targeted unit tests on pinned dev with Python 3.12: **197 passed, 13 skipped**. Covered models, hexagonal purity, ingest Lua checks, tenant context/query checks, pagination and settings security.
- Independent local probes verified 11 node types / 20 edge types, caller-selected tenants under one key, unsigned cursor encoding, unconstrained generic relationship role, and empty extraction return on model failure.
- No Redis/Neo4j deployment, restore drill, full SDK matrix, end-to-end benchmark or production security certification was run. Passing the existing unit suite does not prove compliance with newer contracts; it describes tests of the older implementation.
- Evidence is saved under `review-evidence/`: branch snapshots, source locations, test output and the reproducible local probe script/output.

A percentage such as “70% current” would be misleading without a weighted capability register. The defensible description is: **the memory/retrieval foundation is implemented; the newer trust and product contract layer is substantially behind; several foundational acceptance guarantees also need correction.**
