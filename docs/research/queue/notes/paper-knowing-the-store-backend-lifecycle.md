---
schema_version: 1
artifact_id: N-SURVEY-20261007-05
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:18:00Z
idempotency_key: note:survey:arxiv:2610.04794
input_refs: []
pillar_primary: R7
pillar_secondary: [R2, R6]
memory_stage: staleness
beliefs_affected:
  supports: [B22]
  contradicts: []
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 4, applicability: 4}
source_url: https://arxiv.org/abs/2610.04794
found_via: survey
---

# Knowing the Store: What a Memory Backend Must Write Down Before an Agent Can Read It (arXiv 2610.04794)

- **URL:** https://arxiv.org/abs/2610.04794 (HTML v1 read); code github.com/ansh348/knowing-the-store (archive sha256 stated, commit not stated)
- **Type:** paper
- **Author / org:** not stated in extract
- **Date:** 2026-10-03
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2610.04794.html)
- **Cited by evidence:** survey
- **Relevance to a memory stack:** high; the first published cross-backend census of what lifecycle state stores actually expose (Mem0, A-MEM, FR-Bank), with a contract an adapter could be tested against.

## TL;DR
- Memory backends do not record the lifecycle information (active, superseded, retracted, expired) an agent needs to know its obligations before reading.
- Census of real backends: one "treats obsolete assertions as active and conflates retraction with supersession. Mem0 overwrites at the retrieval surface we evaluated, and A-MEM's links resolve to no note in our integration." FR-Bank marks 5,968 entries stale vs about 102 in the reference; 12.7 % of Mem0 entries expose only `updated_at`; A-MEM's 23,186 link references resolve to zero notes.
- Given only short attribute lists, frontier models barely beat name lookup: AUROC name lookup 0.77, Opus 5 0.84, GPT-5.6 Sol 0.85 (intervals per reader summary: [0.72, 0.81], [0.80, 0.88], [0.81, 0.88]).

## What it claims / describes
Proposes a store manifest an agent can read before retrieval: a lifecycle summary with counts by state (active, superseded, retracted, expired), per-category attribute-name lists without values, lifecycle state tags on records, and query intents (current, upcoming, past, change). Synthetic LifecycleBench: 40 personas; counterfactual set 148 questions x 3 store versions = 444 items differing in one attribute; full obligation set 661 questions. Ground truth from human-written manifests, 248 labels hand-verified; no LLM judge. 95 % bootstrap intervals, item-level and persona-grouped. Predictions frozen before runs (Appendix F).

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| AUROC, obligation detection | Opus 5 0.84, GPT-5.6 Sol 0.85 | name lookup 0.77 | short attribute lists | intervals overlap slightly |
| FR-Bank stale marks | 5,968 | reference about 102 | census | |
| Mem0 entries with only `updated_at` | 12.7 % | | census | single integration |
| A-MEM link references resolving | 0 of 23,186 | | census | "in our integration" |
| cost, latency | not stated | | | |

## Mechanism details you could implement
- Adapter contract field set for P0's swap test: per-record `lifecycle_state` in {active, superseded, retracted, expired}, distinct retraction vs supersession, and a store-level count manifest the agent sees before querying.

## Limitations
Synthetic stores, 40 personas, about 30 retraction/expiry pairs per group, matched metric chosen post hoc, some models on subsets only, explicit intent cues in questions.

## Takeaways for tuning a memory stack
- Supports B22's swap test and point-in-time reads: without explicit lifecycle state, swapping backends silently changes staleness semantics (Mem0 overwrite vs FR-Bank over-marking).
- A swap test must check lifecycle semantics, not only content and provenance.
