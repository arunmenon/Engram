# ADR Review Analysis: API Layer (ADR-0002, ADR-0006)

**Reviewer**: reviewer-api
**Date**: 2026-02-11
**Scope**: ADR-0002 (Service Stack) and ADR-0006 (Query API) reviewed against ADR-0007, ADR-0008, ADR-0009

---

## 1. ADR-0002: Service Stack (Python + FastAPI)

### Verdict: **Amend** -- add dependency and compute profile acknowledgments

### Analysis

ADR-0002 was written for a straightforward event-ingest-and-query service. The new memory architecture (ADR-0007 through ADR-0009) significantly expands the computational profile of the system in ways that ADR-0002 does not address.

#### 1.1 New Dependency Requirements

ADR-0008 (Stage 2 Enrichment) and ADR-0009 (Node Enrichment Schema) introduce three classes of compute that require new dependencies:

| Capability | Required By | Likely Dependency | Notes |
|------------|-------------|-------------------|-------|
| Embedding generation | ADR-0008 Stage 2, ADR-0009 `embedding` property | `sentence-transformers` + PyTorch, or `fastembed` | 384-dim (all-MiniLM-L6-v2) or 1536-dim model |
| Keyword/entity extraction | ADR-0008 Stage 2, ADR-0009 `keywords`, Entity nodes | `spacy` or lightweight NLP pipeline | Entity extraction from event payloads |
| Summarization | ADR-0008 Stage 3, ADR-0009 Summary nodes | LLM API client (e.g., `litellm`, `anthropic`, `openai`) | Summary generation for re-consolidation |

These are not trivial additions. `sentence-transformers` pulls in PyTorch (~2GB), which affects container size, startup time, and memory footprint. This has direct implications for the "fast prototyping" benefit claimed by ADR-0002.

#### 1.2 Compute Profile Shift

ADR-0002 assumes a standard web-service profile: API request handling, database queries, async event processing. The enrichment pipeline (ADR-0008) shifts this toward a mixed workload:

- **CPU-bound**: Embedding computation, NLP entity extraction
- **I/O-bound**: Neo4j graph traversal, Postgres polling
- **Potentially GPU-accelerated**: Embedding generation at scale

Python is adequate for I/O-bound work (async/await) but is a known bottleneck for CPU-bound embedding work. The ADR-0002 "potential runtime performance tradeoffs vs compiled stacks" negative consequence understates this -- the tradeoff is specifically in embedding throughput.

#### 1.3 Worker Process Separation

ADR-0008's three-stage consolidation pipeline argues for clear process separation:
- **API process**: FastAPI, request handling, working memory assembly
- **Projection worker**: Stage 1 event projection (existing)
- **Enrichment worker**: Stage 2 embedding/entity/keyword computation (new, CPU-heavy)
- **Re-consolidation worker**: Stage 3 periodic consolidation (new, batch-oriented)

ADR-0002 does not discuss worker architecture. The "business logic framework-agnostic" requirement is satisfied (domain logic has no FastAPI imports), but the decision should acknowledge that the service is not a single-process deployment.

#### 1.4 Specific Recommendations

1. **Amend ADR-0002** to add a "Runtime Dependencies" section listing the new ML/NLP dependencies and their size/resource implications.
2. **Add a consequence**: "Enrichment pipeline introduces CPU-bound workload; embedding computation should run in a separate worker process or use a lightweight model to avoid blocking the API event loop."
3. **Add to Alternatives Considered**: Acknowledge that embedding computation could be offloaded to a dedicated microservice (e.g., a sidecar running `fastembed` or a hosted embedding API) rather than bundled in the Python worker process. This keeps the Python service lean while deferring the GPU-acceleration question.
4. **Update the dependency list** in the project CLAUDE.md to include: `sentence-transformers>=3.0` or `fastembed>=0.4`, `spacy>=3.8` (or equivalent), and an LLM client SDK for summarization.

---

## 2. ADR-0006: Query API Endpoints

### Verdict: **Amend** -- extend endpoint contracts, do not supersede

### Analysis

ADR-0006 defines five endpoints. The new ADRs require changes to three of them and potentially add new endpoints.

#### 2.1 Endpoint-by-Endpoint Impact

##### `POST /v1/events` and `POST /v1/events/batch` -- Minor Change

ADR-0007 adds an optional `importance_score` (SMALLINT, 1-10) to the event schema. The ingest endpoints must accept this field.

- **Change type**: Additive (new optional field)
- **Breaking**: No -- field is optional with DEFAULT NULL
- **Action**: Amend ADR-0006 to note that the event ingest schema includes `importance_score` as an optional field per ADR-0007

##### `GET /v1/context/{session_id}` -- Significant Change

ADR-0007 redefines this endpoint as the "working memory assembly" endpoint. The current ADR-0006 definition is minimal ("session context retrieval"). ADR-0007 adds substantial requirements:

| New Requirement | Source | Impact |
|----------------|--------|--------|
| Capacity-bounded response (`max_nodes`, `max_depth`) | ADR-0007 Tier 2 | New query parameters |
| Priority scoring (`w_recency * recency + w_importance * importance + w_relevance * relevance`) | ADR-0007, ADR-0008 | Response ordering changes |
| Episode chunking (group by `trace_id` or parent chains) | ADR-0007 Tier 2 SHOULD | Response structure addition |
| Scores per node (`decay_score`, `relevance_score`, `importance_score`) | ADR-0009 | New field in Atlas response |
| Reconsolidation side-effects (update `access_count`, `last_accessed_at`) | ADR-0008 | Read-with-side-effects |

This is the most impacted endpoint. The contract must be amended to include:

**New query parameters**:
```
GET /v1/context/{session_id}?max_nodes=100&max_depth=3&include_scores=true
```

**Response changes** (Atlas pattern additions):
- Each node gains a `scores` object (see Section 3 below)
- `meta` gains `scoring_weights` and `capacity_used` fields
- Results are ordered by combined score (descending)

**Behavioral change**: This endpoint now performs reconsolidation side-effects (incrementing access counts, updating `last_accessed_at`). This turns a pure GET into a read-with-write, which is architecturally significant. Two options:

1. Accept the impurity -- many caching/CDN systems handle this via cache-busting headers. Document the side-effect clearly.
2. Make reconsolidation side-effects async -- the API returns immediately; a background task updates access metadata. This preserves GET purity at the cost of eventual consistency on access counts.

**Recommendation**: Option 2 (async side-effects). The response should not block on Neo4j writes for access tracking.

##### `POST /v1/query/subgraph` -- Moderate Change

ADR-0009 adds the `intent` parameter for intent-aware retrieval.

**New request body fields**:
```json
{
  "seed_node_ids": ["..."],
  "max_depth": 3,
  "max_nodes": 100,
  "intent": "why",          // NEW: optional, default "general"
  "include_scores": true     // NEW: optional, default false
}
```

**Impact**: The intent parameter changes which edge types are prioritized during traversal. This is an additive change -- omitting `intent` falls back to "general" (balanced traversal), preserving backward compatibility.

**Recommendation**: Amend ADR-0006 to document the `intent` parameter with its enum values (`why`, `when`, `what`, `related`, `general`) and describe the edge-weighting behavior per ADR-0009.

##### `GET /v1/nodes/{node_id}/lineage` -- Moderate Change

ADR-0009 also makes `intent` relevant here. "Why" intent prioritizes CAUSED_BY edges; "when" intent prioritizes FOLLOWS edges.

**New query parameters**:
```
GET /v1/nodes/{node_id}/lineage?direction=ancestors&max_depth=5&intent=why&include_scores=true
```

**Recommendation**: Amend ADR-0006 to add `intent` and `include_scores` as optional query parameters.

#### 2.2 New Endpoints to Consider

The new ADRs suggest endpoints not covered in ADR-0006:

| Potential Endpoint | Source | Purpose | MVP? |
|-------------------|--------|---------|------|
| `GET /v1/entities/{entity_id}` | ADR-0009 Entity nodes | Retrieve entity details and connected events | Yes -- entity tracking is core to ADR-0009 |
| `GET /v1/entities` | ADR-0009 Entity nodes | List/search entities across sessions | Post-MVP |
| `GET /v1/summaries/{scope}/{scope_id}` | ADR-0009 Summary nodes | Retrieve hierarchical summaries | Post-MVP |
| `GET /v1/sessions/{session_id}/episodes` | ADR-0007 episode chunking | Retrieve episodic groupings | Post-MVP |
| `POST /v1/admin/reconsolidate` | ADR-0008 Stage 3 | Trigger manual re-consolidation | Yes -- operational necessity |

**Recommendation**: Amend ADR-0006 to add `GET /v1/entities/{entity_id}` and `POST /v1/admin/reconsolidate` to the MVP endpoint list. Document the others as planned post-MVP extensions.

---

## 3. Atlas Response Pattern Update

### Verdict: **Additive, non-breaking** -- but requires explicit documentation

### Analysis

ADR-0006 defines the Atlas response pattern:
```json
{
  "nodes": { "node-id": { "type": "...", "attributes": {...}, "provenance": {...} } },
  "edges": [...],
  "pagination": {...},
  "meta": {...}
}
```

ADR-0009 adds a `scores` field to each node:
```json
{
  "scores": {
    "decay_score": 0.87,
    "relevance_score": 0.92,
    "importance_score": 7
  }
}
```

#### 3.1 Breaking Change Assessment

This is **additive, not breaking**. Clients that do not expect `scores` will encounter an extra field they can ignore (standard JSON forward-compatibility). However:

- The `scores` field SHOULD be returned only when `include_scores=true` is passed, or always returned with a documented default. Always returning scores is simpler and avoids conditional response shapes.
- **Recommendation**: Always include `scores` in the response. Document it as a new field added in the ADR-0007/0008/0009 revision. Clients that do not use scoring can ignore it.

#### 3.2 Additional Atlas Pattern Changes

Beyond `scores`, the new ADRs imply further `meta` field additions:

```json
{
  "meta": {
    "query_ms": 120,
    "nodes_returned": 12,
    "truncated": false,
    "intent": "why",                    // NEW: echoes the query intent used
    "scoring_weights": {                // NEW: transparency on scoring
      "recency": 1.0,
      "importance": 1.0,
      "relevance": 1.0
    },
    "capacity": {                       // NEW: working memory capacity info
      "max_nodes": 100,
      "used_nodes": 12,
      "max_depth": 3
    }
  }
}
```

These are all additive. The Atlas pattern remains backward-compatible.

#### 3.3 Edge Type Representation

ADR-0009's four edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES) plus SUMMARIZES need to be represented in the Atlas response's `edges` array. The current pattern has `"type": "..."` which accommodates this naturally:

```json
{
  "edges": [
    { "source": "evt-1", "target": "evt-2", "type": "FOLLOWS", "properties": { "delta_ms": 1200 } },
    { "source": "evt-2", "target": "evt-1", "type": "CAUSED_BY", "properties": { "mechanism": "direct" } }
  ]
}
```

**Recommendation**: Amend the Atlas pattern specification in ADR-0006 to include edge `properties` as an optional field and enumerate the known edge types.

---

## 4. Working Memory Assembly Impact on ADR-0006

### Verdict: **Most significant change** -- amend ADR-0006 with a dedicated section

### Analysis

ADR-0007 transforms `GET /v1/context/{session_id}` from a simple retrieval endpoint into a sophisticated working memory assembly engine. This is the most impactful change and deserves explicit treatment.

#### 4.1 Assembly Pipeline

The endpoint must now perform:

1. **Retrieve** candidate nodes from Neo4j (events + entities for the session, within `max_depth` hops)
2. **Score** each candidate using the decay formula: `w_r * recency + w_i * importance + w_v * relevance`
3. **Rank** by combined score (descending)
4. **Chunk** into episodes (group by `trace_id` or parent chains) -- SHOULD requirement
5. **Truncate** to capacity bounds (`max_nodes`, paginate overflow)
6. **Annotate** with provenance and scores
7. **Side-effect** (async): update `access_count` and `last_accessed_at` on returned nodes

Steps 2-3 require the scoring infrastructure from ADR-0008. Step 4 requires episode detection logic. Step 7 requires an async write path from a read endpoint.

#### 4.2 Performance Concerns

This assembly pipeline is significantly more expensive than a simple session query. Key concerns:

- **Scoring requires embedding similarity** when relevance is used, but the context endpoint does not take a query string. What is the relevance anchor? Options: (a) relevance defaults to 0.5 (neutral) for context assembly, (b) the endpoint accepts an optional `query` parameter for relevance scoring.
- **Episode chunking** requires traversing parent_event_id chains, which is a graph operation on top of the initial retrieval.
- **Combined latency** of retrieve + score + chunk + truncate must stay within acceptable bounds (target: p95 < 200ms for typical sessions).

**Recommendation**: Amend ADR-0006 to add an optional `query` parameter to `GET /v1/context/{session_id}` for relevance-anchored scoring. When omitted, relevance defaults to 0.5 (recency and importance drive ranking). This aligns with ADR-0008's fallback behavior.

#### 4.3 Response Structure for Episodes

If episode chunking is implemented (ADR-0007 SHOULD requirement), the Atlas response should support grouping:

```json
{
  "nodes": { ... },
  "edges": [ ... ],
  "episodes": [
    {
      "trace_id": "abc-123",
      "node_ids": ["evt-1", "evt-2", "evt-3"],
      "summary": "Agent invoked search tool and processed results",
      "time_range": ["2026-02-11T10:00:00Z", "2026-02-11T10:05:00Z"]
    }
  ],
  "pagination": { ... },
  "meta": { ... }
}
```

The `episodes` field is additive and optional. Clients that do not need episode grouping can use `nodes` directly.

---

## 5. Summary of Recommendations

| ADR | Verdict | Key Changes |
|-----|---------|-------------|
| **ADR-0002** | **Amend** | Add dependency section for ML/NLP libraries; acknowledge CPU-bound enrichment workload; document multi-process deployment model |
| **ADR-0006** | **Amend** | (1) Add `intent` parameter to subgraph and lineage endpoints; (2) Add `scores` to Atlas response; (3) Expand context endpoint contract with `max_nodes`, `max_depth`, `query` params; (4) Add `episodes` to Atlas response; (5) Add entity and admin endpoints; (6) Document edge `properties` and enumerate edge types |
| **Atlas Pattern** | **Additive** | `scores` per node, `episodes` array, `properties` on edges, expanded `meta` -- all backward-compatible |

Neither ADR-0002 nor ADR-0006 needs to be superseded. Both can be amended in-place because their core decisions remain valid:
- Python+FastAPI is still the right stack choice (with acknowledged ML dependency overhead)
- The five original endpoints remain correct (with expanded contracts and two new endpoints added)

The amendments should cross-reference ADR-0007, ADR-0008, and ADR-0009 as the source of new requirements.
