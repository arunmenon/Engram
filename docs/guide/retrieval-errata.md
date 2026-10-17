# Retrieval corrections for the study book

These statements describe the current implementation; they are not a future retrieval design.

- **Event retrieval expands one step.** Engine1's graph-store subgraph call expands one hop from its Event seeds. Accepting or reporting a depth setting does not prove iterative traversal. Artifact retrieval (Engine2) has a separate bounded multi-level traversal.
- **Diversity scoring does not currently determine membership or ordering.** Engine1 calls its MMR helper and writes a relevance score, but then orders and paginates by `decay_score`. The computed diversity score therefore does not change which candidates are returned or their order in that path. Do not present this as effective diversity reranking.
- **Low-confidence proposals are visible, not silently discarded.** Artifact admission retains proposed links with their confidence. Completeness checks classify them as proposed-only, never confirmed. A confidence label is not an approval or a verified fact.
- **Supersession needs explicit context.** Issue#85 showed a trace silently removing an explicitly requested old design and leaving its approval detached. The correction keeps that named design labelled superseded, reports exclusions, and removes traversal branches disconnected by filtering. If an approval itself was separately requested, omitted-relationship metadata identifies its exact original target. Trace still filters other discovered historical versions; status/why keep their existing history behavior.

Code anchors: `retrieval/engine.py` (graph expansion, `_apply_mmr`, final decay-score sort); `retrieval/artifacts.py` (`_admit`, `_missing_links`); `domain/models.py` (`QueryMeta`). All paths are under `src/context_graph/`. The decision and boundary are documented in [ADR0018](../adr/0018-ontology-packs.md). These corrections do not establish stronger traversal, authorization, ranking quality or semantic discovery than the code and recorded checks prove.
