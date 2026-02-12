# ADR-0002: Service Stack is Python + FastAPI

Status: **Accepted — Amended**
Date: 2026-02-07
Updated: 2026-02-11
Related: ADR-0008 (enrichment pipeline compute requirements)

## Context
The context graph service requires rapid API iteration, event processing, and integration with agent tooling. Python has strong ecosystem fit for agent systems and data tooling.

Non-goals for MVP:
- Polyglot service architecture
- Framework benchmarking program

## Decision
The context graph service SHOULD be implemented using Python + FastAPI for MVP.

The service MUST expose typed HTTP APIs for ingest and retrieval, and MUST keep business logic framework-agnostic enough to support future extraction if needed.

## Consequences
Positive:
- Fast prototyping and integration with agent ecosystems
- Mature libraries for validation, async APIs, and data processing
- Low friction for internal experimentation

Negative:
- Potential runtime performance tradeoffs vs some compiled stacks
- Requires discipline to avoid framework lock-in in domain logic

## Alternatives Considered
1. TypeScript + Node  
Rejected for MVP due to current preference and Python agent ecosystem leverage.
2. Framework-agnostic from day one
Rejected as premature; adds architecture overhead before validating product shape.

## Amendments

### 2026-02-11: Runtime Dependencies and Compute Profile

**What changed:** ADR-0008 and ADR-0009 introduce an enrichment pipeline (embedding generation, entity extraction, summarization) that significantly expands the computational profile beyond a standard web-service workload.

**New dependency classes:**

| Capability | Required By | Likely Dependency | Impact |
|------------|-------------|-------------------|--------|
| Embedding generation | ADR-0008 Stage 2, ADR-0009 | `sentence-transformers` or `fastembed` | 384-dim (all-MiniLM-L6-v2); PyTorch dependency adds ~2GB to container |
| Keyword/entity extraction | ADR-0008 Stage 2, ADR-0009 | `spacy` or lightweight NLP pipeline | Entity extraction from event payloads |
| Summarization | ADR-0008 Stage 3, ADR-0009 | LLM API client (e.g., `litellm`) | Summary generation for re-consolidation |

**Multi-process deployment model:** The enrichment pipeline introduces CPU-bound workloads (embedding computation, NLP extraction) alongside the existing I/O-bound workloads (API handling, database queries). The service SHOULD be deployed as multiple processes:
- **API process**: FastAPI, request handling, working memory assembly
- **Projection worker**: Stage 1 event projection (I/O-bound)
- **Enrichment worker**: Stage 2 embedding/entity/keyword computation (CPU-bound)
- **Re-consolidation worker**: Stage 3 periodic consolidation (batch-oriented)

**Additional negative consequence:** Enrichment pipeline introduces CPU-bound workload; embedding computation should run in a separate worker process or use a lightweight model to avoid blocking the API event loop. Container size increases significantly due to ML dependencies.

**Mitigation:** Embedding computation can be offloaded to a dedicated microservice, a sidecar running `fastembed`, or a hosted embedding API rather than bundled in the Python worker process. This keeps the API service lean while deferring the GPU-acceleration question.

### 2026-02-11: Redis Replaces asyncpg

**What changed:** asyncpg replaced by redis-py (async mode) per ADR-0010. Alembic removed — no SQL migrations needed with Redis.
