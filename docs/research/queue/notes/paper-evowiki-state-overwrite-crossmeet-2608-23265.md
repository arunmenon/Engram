---
schema_version: 1
artifact_id: N-SURVEY-20260928-15
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:35:00Z
idempotency_key: note:survey:arxiv:2608.23265
input_refs: []
pillar_primary: R10
pillar_secondary: [R2, R3, R6]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 4
  control: 4
  independence: 3
  reproducibility: 3
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2608.23265
found_via: survey
claim_cluster: explicit-state-overwrite-for-evolving-decisions
---

# EvoWiki: Incremental State Overwriting and Traceable Question Answering for Cross-Meeting Knowledge Evolution (with the CrossMeet benchmark)

- **URL:** https://arxiv.org/abs/2608.23265 (HTML read at https://arxiv.org/html/2608.23265)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** 2026-08-24
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R10 question 3 (schema and state evolution) and question 5 (benchmark)
- **Relevance to a memory stack:** high. Decisions and risks revised across project meetings is the PDLC "decision behind a design, weeks later" problem. It ablates an explicit supersession protocol, which is the core of our SUPERSEDES design.

## TL;DR
- BUILD keeps, per entity-attribute pair, a version chain; a replaced state is closed with an "Overturned" label, the new one is "Active", and a replacement edge links them; at most one active version per pair; each state carries a provenance anchor `(meeting, evidence span)`.
- READ skips top-k similarity retrieval: deterministic entity addressing, temporal resolution by validity interval, and multi-hop aggregation over the whole wiki.
- Macro judge accuracy over six datasets: 60.09 vs 50.37 for the best baseline (LogicRAG) with a DeepSeek-V4-Flash reader (+9.72 pp); 63.02 vs 53.02 with Qwen3.5-397B-A17B (+10.00 pp).
- Removing the overwrite protocol costs 8.63 pp (60.09 -> 51.46); removing lifecycle tags costs 10.30 pp.
- Judge (Gemini 3.1 Pro) differs from the readers; cross-judge agreement kappa 0.901 (Claude Opus 4.7) and 0.887 (DeepSeek-V4-Pro).

## What it claims / describes
An incremental QA architecture for long, evolving multi-meeting text. BUILD captures within-meeting micro-evolution from proposal to decision and applies a State-Overwrite Protocol. READ answers from valid states by entity, attribute and lifecycle label; a query at time tau reads the version whose validity interval contains tau.

CrossMeet: 100 projects, 500 consecutive meetings, 2,000 QA pairs, English and Chinese built independently (not translated), average 26,861 (EN) and 29,480 (ZH) tokens of context. Question mix: factual consistency 50%, timeline reasoning 30%, multi-hop 20%; average 2.84 / 2.77 hops, maximum 5. Built by Claude Opus 4.5 from "project blueprints"; cross-validated by Gemini 3.1 Pro, Claude Opus 4.7 and DeepSeek-V4-Pro. Synthetic meetings.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Judge accuracy, DeepSeek-V4-Flash reader | CM-EN 68.78; CM-ZH 69.55; ELITR 60.77; LongMemEval 61.60; MeetingQA 39.16; MuSiQue 60.67; macro 60.09 | LogicRAG macro 50.37 | 0 / 0.5 / 1 rubric | baselines: Direct LLM, BM25/Dense/Hybrid RAG, RAPTOR, GraphRAG, HippoRAG 2, LightRAG, LogicRAG; no Zep/Graphiti or Mem0 |
| Macro, Qwen3.5-397B-A17B reader | 63.02 | LogicRAG 53.02 | | |
| Ablation w/o overwrite | 51.46 (-8.63) | full 60.09 | DeepSeek-V4-Flash | |
| Ablation w/o coreference | 50.93 (-9.16) | | | |
| Ablation w/o entity | 53.73 (-6.36) | | | |
| Ablation w/o lifecycle tags | 49.79 (-10.30) | | | |
| Latency | 3.60 s per query | Direct LLM 6.54 s | | |
| Read tokens | 17,143 per query | not stated for baselines in extract | | |
| Build tokens | 114,016 per project (amortised) | | | |
| Human faithfulness win rate | 31.0% to 51.5% vs baselines | | 200 CrossMeet-EN questions | ties not reported in extract |

## Mechanism details you could implement
- Lifecycle labels on every state (`Active`, `Overturned`) with an explicit replacement edge and at most one active version per entity-attribute pair: a direct template for SUPERSEDES on `:Decision` and `:Requirement`, with the invariant enforced at write time.
- Provenance anchor per state `(source, span)`; pairs with EA-Graph's content-hash anchors already in the landscape.
- Temporal read: pick the version whose validity interval contains the query time; answers "what did we decide as of the design review?"

## Limitations, caveats, counter-evidence
- CrossMeet is synthetic and built by one model family; two of the six datasets (LongMemEval, MuSiQue) are not meeting data.
- Compared against RAG and graph-RAG baselines, not against bitemporal memory stores (Zep/Graphiti) that already implement supersession; the gain over those is unknown.
- The overwrite decision (is this new state a replacement?) is made by an LLM; its precision is not reported separately in the extract.

## Takeaways for tuning a memory stack
- Evidence at paper-ablated strength that an explicit supersession protocol matters: about 9 pp on evolving-knowledge QA. Supports keeping SUPERSEDES as a write-time decision rather than resolving conflicts at read time.
- CrossMeet's question mix (consistency, timeline, multi-hop over revised decisions) is a template for the "notice a changed requirement" part of our PDLC benchmark; replace synthetic meetings with SpecMine spec histories (N-SURVEY-20260928-13).
- The overwrite decision is a binary, typed decision: a natural System One candidate (inference; untested).

## Open questions
- Precision and recall of the overwrite decision itself, and how errors propagate (a wrong "Overturned" hides a still-valid decision).
- Gain over a bitemporal store with the same supersession semantics.
