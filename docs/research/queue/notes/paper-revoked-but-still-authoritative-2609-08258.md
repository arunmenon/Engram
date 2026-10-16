---
schema_version: 1
artifact_id: N-SURVEY-20260927-03
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2609.08258
input_refs: []
pillar_primary: R1
pillar_secondary: [R8, R2]
beliefs_affected:
  supports: [B2]
  contradicts: []
  note: none of five mainstream memory systems exposes an as-of read; retrieval is similarity-only
evidence:
  directness: 3
  control: 4
  independence: 4
  reproducibility: 4
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2609.08258
found_via: survey
---

# Revoked but Still Authoritative: An Empirical Study of Revocation Enforcement in Agent-Memory Systems

- **URL:** https://arxiv.org/abs/2609.08258 (HTML read at https://arxiv.org/html/2609.08258); code https://github.com/VulcanLab/Memory-Rebirth-Attack
- **Type:** paper
- **Author / org:** Yi Ting Shen, Kentaroh Toyoda, Alex Leung (Vulcan Research, AIFT, Singapore)
- **Date:** 8 Sep 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R1 question on B2 (point-in-time reads) and P0's "never silently substitute" fixture
- **Relevance to a memory stack:** high. A measured, open-source test of whether revoked facts are still served by Graphiti, Zep CE, mem0, langmem and cognee, and whether agents act on them.

## TL;DR
- Seeds each system with a revoked policy rule and its replacement, then asks ordinary questions.
- Graphiti and mem0 (experimental path) returned the revoked record in 81/81 cells at rank 1; agents then took unsafe actions 44.2 % (358/810) and 42.1 % (341/810) of the time.
- cognee, langmem and mem0 (default) returned no revoked record in 0/81.
- A retrieval-time filter cut unsafe actions to 0.0 % (0/1,620).
- The systems' retrieval "takes a query q, a store M and a result size k, and returns k records ranked by similarity alone": no as-of or snapshot read exists in any of them.

## What it claims / describes
Revocation of policy facts (organisational rules), not of access permissions. 9 scenarios x 9 models x 10 trials per condition, several defence conditions; 44,550 decision-model calls in the main grid.

## Numbers

Table 6, direct insertion, no defence (as extracted):

| System | Exposure | Rank | Unsafe rate |
|---|---|---|---|
| Graphiti | 81/81 | 1 | 44.2 % (358/810) |
| mem0 (exp.) | 81/81 | 1 | 42.1 % (341/810) |
| cognee, langmem, mem0 | 0/81 | n/a | no revoked record returned |

| Metric | Value | Caveat |
|---|---|---|
| Unsafe rate with retrieval filter | 0.0 % (0/1,620) | across exposed systems |
| Versions / commits of tested systems | not stated | |
| Cost, latency | not stated | |

## Mechanism details you could implement
- Test fixture shape: pair a revoked record with its replacement, query in ordinary language, measure (a) exposure: was the revoked record returned, (b) rank, (c) unsafe action rate downstream. This maps directly onto P0 mutation step "update a source" and the "no silent substitution" pass criterion.
- The defence that worked is a filter at retrieval, not a better ranker.

## Limitations, caveats, counter-evidence
- Revocation of facts, not of reader permissions; P0's "revoke the reviewer's access" fixture is a different case.
- Whether summarised or derived items inherit revocation is not studied (AuthMem-Bench in the September landscape covers the consolidation side).
- Findings described by the authors as descriptive of their fixed grid; system versions not pinned in the text read.

## Takeaways for tuning a memory stack
- B2 gains an outside data point: five widely used memory systems, none with a point-in-time read; the only validity mechanism is whether the write path removed or marked the old fact.
- Silent substitution in the opposite direction (serving the stale fact as current) is the measured failure: 42 to 44 % unsafe actions once exposed. P0's fixture should include a revoked-fact case and report exposure and rank separately from downstream action.

## Open questions
- Does a snapshot-pinned replay (L1/L2 in P0 terms) serve the revoked fact correctly for a decision made before revocation while excluding it after? No system here can express that question.
