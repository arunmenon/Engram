# ADR-0006: MVP Query API Focuses on Context Retrieval and Lineage

Status: **Accepted — Amended**
Date: 2026-02-07
Updated: 2026-02-12
Extended-by: ADR-0007 (working memory assembly), ADR-0008 (decay scoring), ADR-0009 (intent-aware retrieval, scores in responses)

## Context
The service must provide practical retrieval for agent execution while preserving traceability. A minimal but useful API surface is needed first.

Non-goals for MVP:
- Full query language exposed to end users
- Advanced ranking personalization

## Decision
MVP public API MUST prioritize:
- Event ingest endpoints
- Session context retrieval
- Subgraph query
- Node lineage traversal

Initial endpoints:
- `POST /v1/events`
- `POST /v1/events/batch`
- `GET /v1/context/{session_id}`
- `POST /v1/query/subgraph`
- `GET /v1/nodes/{node_id}/lineage`

Context responses MUST include provenance references for returned items and SHOULD enforce bounded retrieval budgets.

## Consequences
Positive:
- Immediate utility for agent runtime integration
- Clear explainability path via lineage endpoint
- Controlled scope for first implementation

Negative:
- Limited flexibility for ad hoc analytics in MVP
- Future endpoint expansion likely required

## Alternatives Considered
1. Build generic query DSL first  
Rejected because it increases complexity before core use-cases are proven.
2. Ingest-only MVP
Rejected because it defers user-visible value and validation of graph usefulness.

## Amendments

### 2026-02-11: Expanded Endpoint Contracts and New Endpoints

**What changed:** ADR-0007, ADR-0008, and ADR-0009 expand the requirements for existing endpoints and introduce new ones.

#### Endpoint Contract Updates

**`POST /v1/events` and `POST /v1/events/batch`** (minor):
- Accept optional `importance_hint` field (SMALLINT, 1-10) per ADR-0007/ADR-0004 amendment
- No breaking changes; field is optional with DEFAULT NULL

**`GET /v1/context/{session_id}`** (significant — becomes working memory assembly):
- New query parameters: `max_nodes` (default 100), `max_depth` (default 3), `query` (optional, for relevance-anchored scoring)
- Response ordering: nodes ranked by combined decay score (`w_recency * recency + w_importance * importance + w_relevance * relevance`) per ADR-0008
- When `query` is omitted, relevance defaults to 0.5 (recency and importance drive ranking)
- Reconsolidation side-effects (incrementing `access_count`, updating `last_accessed_at`) SHOULD be performed asynchronously to preserve GET semantics

**`POST /v1/query/subgraph`** (moderate):
- New request body field: `intent` (enum: `why`, `when`, `what`, `related`, `general`; default `general`) per ADR-0009
- Intent parameter determines edge-type weighting during traversal (see ADR-0009 intent weight matrix)

**`GET /v1/nodes/{node_id}/lineage`** (moderate):
- New query parameter: `intent` (same enum as subgraph; default `why` for lineage) per ADR-0009

#### New Endpoints

| Endpoint | Purpose | Source |
|----------|---------|--------|
| `GET /v1/entities/{entity_id}` | Retrieve entity details and connected events | ADR-0009 Entity nodes |
| `POST /v1/admin/reconsolidate` | Trigger manual re-consolidation pass | ADR-0008 Stage 3 |

Planned post-MVP extensions: `GET /v1/entities` (list/search), `GET /v1/summaries/{scope}/{scope_id}` (hierarchical summaries), `GET /v1/sessions/{session_id}/episodes` (episodic groupings).

#### Atlas Response Pattern Extensions

All additions are backward-compatible (new optional fields):

**Per-node `scores` field** (always returned per ADR-0009):
```json
{
  "scores": {
    "decay_score": 0.87,
    "relevance_score": 0.92,
    "importance_score": 7
  }
}
```

**Edge `properties` field** (optional, per edge type):
```json
{
  "edges": [
    {"source": "evt-1", "target": "evt-2", "type": "FOLLOWS", "properties": {"delta_ms": 1200}},
    {"source": "evt-2", "target": "evt-1", "type": "CAUSED_BY", "properties": {"mechanism": "direct"}}
  ]
}
```

Known edge types: `FOLLOWS` (temporal), `CAUSED_BY` (causal), `SIMILAR_TO` (semantic), `REFERENCES` (entity), `SUMMARIZES` (hierarchical).

**Expanded `meta` field**:
```json
{
  "meta": {
    "query_ms": 120,
    "nodes_returned": 12,
    "truncated": false,
    "intent": "why",
    "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
    "capacity": {"max_nodes": 100, "used_nodes": 12, "max_depth": 3}
  }
}
```

### 2026-02-11: Redis Provenance Format

**What changed:** Per ADR-0010, `provenance.global_position` format changes from integer to Redis Stream entry ID string (e.g. `"1707644400000-0"`). Clients should treat as opaque cursor. `provenance.source` changes from `"postgres"` to `"redis"`. Endpoint contracts otherwise unchanged.

### 2026-02-12: System-Owned Context Retrieval Contract

**What changed:** The API contract shifts from "caller drives retrieval parameters" to "caller provides user context, system surfaces relevant context." This reflects the principle that the context graph owns retrieval intelligence (see ADR-0009 amendment: System-Owned Intent Classification).

#### Updated Endpoint Contracts

**`POST /v1/query/subgraph`** (significant — becomes the primary context retrieval endpoint):

Previous required inputs: `seed_nodes`, `intent`, `max_depth`, `max_nodes`

New contract:

```json
{
  "query": "Why do my customers' payments keep failing?",
  "session_id": "sess-4",
  "agent_id": "paypal-assistant",

  "max_nodes": 100,
  "max_depth": 3,
  "timeout_ms": 5000,

  "intent": "why",
  "seed_nodes": ["entity:card_declined"]
}
```

| Field | Required | Notes |
|-------|:--------:|-------|
| `query` | **Yes** | Raw user message or retrieval question. The system extracts entities, classifies intent, and selects seed nodes from this. |
| `session_id` | **Yes** | Identifies the user's current session. Used to locate user's Entity node and recent conversation context. |
| `agent_id` | **Yes** | Identifies the calling agent. Used to scope retrieval to the user's graph neighborhood. |
| `max_nodes` | No | Default 100. Bounds the result set. |
| `max_depth` | No | Default 3. Bounds traversal depth. |
| `timeout_ms` | No | Default 5000. Bounds query execution time. |
| `intent` | No | **Optional override.** When provided, bypasses internal intent classification. When absent, the system infers intent(s) from `query`. |
| `seed_nodes` | No | **Optional override.** When provided, used as traversal starting points. When absent, the system selects seeds from entity extraction and graph topology. |

The key change: `query` + `session_id` + `agent_id` are sufficient for a complete retrieval. The system handles everything else. `intent` and `seed_nodes` become power-user overrides for callers that want explicit control.

**`GET /v1/context/{session_id}`** (unchanged):

This endpoint remains a session-scoped ranked retrieval (working memory assembly). It does not use intent traversal — it returns all events in the session ranked by decay score. No changes needed.

**`GET /v1/nodes/{node_id}/lineage`** (minor):

The `intent` parameter becomes optional (default: system-inferred from node context, falling back to `why` for lineage). Callers can still pass `intent` as an override.

#### Response Changes

All endpoints now include retrieval reasoning in `meta` (see ADR-0009 amendment for full `meta` schema):

```json
{
  "meta": {
    "query_ms": 145,
    "nodes_returned": 18,
    "truncated": false,
    "inferred_intents": {"why": 0.7, "when": 0.4, "what": 0.5},
    "intent_override": null,
    "seed_nodes": ["entity:card_declined", "entity:marias-bakery"],
    "proactive_nodes_count": 3,
    "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
    "capacity": {"max_nodes": 100, "used_nodes": 18, "max_depth": 3}
  }
}
```

Per-node `retrieval_reason` field added (see ADR-0009 amendment):

```json
{
  "node_id": "...",
  "retrieval_reason": "direct",
  ...
}
```

Values: `"direct"` (matched query intent), `"proactive"` (system-surfaced contextually relevant node).

#### Backward Compatibility

Callers that currently pass `intent` and `seed_nodes` explicitly continue to work unchanged — these fields are respected as overrides. The new behavior only activates when these fields are omitted. This is a backward-compatible expansion, not a breaking change.
