---
schema_version: 1
artifact_id: N-SURVEY-20261005-03
artifact_type: note
producer: triage
run_id: survey-20261005T054504Z-d350
created_at: 2026-10-05T06:30:00Z
idempotency_key: note:survey:arxiv:2607.27773
input_refs: []
pillar_primary: R1
pillar_secondary: [R2]
memory_stage: retrieval
beliefs_affected:
  supports: [B2]
  contradicts: []
evidence:
  directness: 3
  control: 3
  independence: 2
  reproducibility: 1
  applicability: 2
evidence_scale: 1 (weak) to 5 (strong), per dimension
source_url: https://arxiv.org/abs/2607.27773
found_via: survey
---

# ChronoMem: Version Control and Semantic Rollback for Large Language Model Agent Memory

- **URL:** https://arxiv.org/abs/2607.27773 (read via https://arxiv.org/html/2607.27773, v2)
- **Type:** paper
- **Author / org:** not stated in the extracted text; implementation described as integrated into Google's Agent Development Kit (ADK)
- **Date:** July 2026 (v2)
- **Retrieved:** 2026-10-05
- **Cited by evidence:** survey query for B2 (point-in-time reads)
- **Relevance to a memory stack:** medium. A point-in-time read over one agent-memory store, with commit-on-write snapshots; not heterogeneous sources.

## TL;DR
- Every memory write creates a version with a materialised whole-memory snapshot S(v_j); an append-only event log holds versions.
- Point-in-time semantics: "reads are scoped to the active version (HEAD). After rollback to v*, any subsequent memory read or retrieval must behave as if only the state at v* exists."
- Natural-language rollback ("go back to before X") maps to a version via BM25 + dense + RRF + Cohere Rerank-3.5 over commit descriptors {delta, summary, op, labels}. Version selection is weak: Recall@1 20.5% on LoCoMo, 33.4% on MemoryAgentBench.
- Rollback-consistent QA beats prompt-only, full-history and RAG-only baselines by 7 to 18 points F1 with 7B to 8B backbones.
- Storage and latency overhead: "Not reported". Code: no public link.

## What it claims / describes
Four stages: commit-on-write versioning; semantic commit descriptors; hybrid retrieval to map a rollback query to a version; deterministic `RollbackToVersion()`. Baselines: prompt-only rollback (instruction, memory unchanged), full-history prompt with an instruction to ignore post-v* information, retrieval-only (vector DB, no snapshot).

## Numbers

| metric | ChronoMem | best baseline | setup | caveat |
|---|---|---|---|---|
| version selection Recall@1 / @5 / Scope@2 | 20.5 / 38.9 / 31.2 % | Hybrid RRF 12.0 / 28.1 / 17.9 % | LoCoMo | n not extracted |
| version selection Recall@1 / @5 / Scope@2 | 33.4 / 60.2 / 58.0 % | Hybrid RRF 24.3 / 53.8 / 40.5 % | MemoryAgentBench | |
| rollback-consistent QA F1 (Llama-3.1-8B / Qwen2.5-7B / Mistral-7B) | 36.1 / 38.5 / 31.3 % | RAG-only 28.9 / 27.1 / 19.4 % | LoCoMo | |
| same | 53.8 / 55.1 / 44.6 % | RAG-only 35.5 / 34.2 / 31.0 % | MAB Accurate Retrieval | |
| summarisation ROUGE-1 | 0.25 / 0.22 / 0.17 | RAG-only 0.21 / 0.20 / 0.14 | LoCoMo | |
| summarisation F1 | 13.0 / 14.0 / 7.0 % | Full-history 8.0 / 8.0 / 1.0 % | MAB En.Sum | |
| storage / latency overhead | not reported | | | |

Judge: not stated. Wrong-memory propagation after rollback: not measured.

## Mechanism details you could implement
- Commit-on-write with a commit descriptor {delta, summary, op, labels} per version gives a searchable history.
- Scope every read to an explicit version id; this is exactly the "as of" read P0 needs, but per store.

## Limitations, caveats, counter-evidence
- Whole-memory materialised snapshots per write: storage cost unbounded and unreported (inference: impractical at our event volume without structural sharing).
- One store, conversational benchmarks; no heterogeneous sources, no access control, no engineering artefacts.
- Low version-selection Recall@1 means natural-language "as of" lookup is unreliable; explicit version ids or timestamps are needed.

## Takeaways for tuning a memory stack
- Supports B2 as stated: point-in-time reads exist inside one store (here, agent memory), still not across heterogeneous stores.
- Use explicit timestamps or version ids for replay; do not rely on semantic version lookup.

## Open questions
- Snapshot size growth per write; whether ADK integration is public.
