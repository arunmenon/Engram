---
schema_version: 1
artifact_id: N-SURVEY-20261009-03
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2608.07622
input_refs: []
pillar_primary: R2
pillar_secondary: [R8]
memory_stage: write and retrieval
beliefs_affected:
  supports: [B24]
  contradicts: []
evidence: {directness: 4, control: 4, independence: 3, reproducibility: 4, applicability: 3}
source_url: https://arxiv.org/abs/2608.07622
found_via: survey
---

# Controlled Memory Interference in Continual LLM Agents (CMI)

- **URL:** https://arxiv.org/abs/2608.07622 (HTML v1 read); code https://github.com/Dawn-Buendia/Controlled-Memory-Interference-in-Continual-LLM-Agents (MIT, per the paper; repo not fetched)
- **Type:** paper
- **Author / org:** Ao Ding, Hongzong Li, Shiqin Tang, Li Zhang, Liang Chen, Xuyang Chen, Zi Liang (CUG Beijing, NWPU, HKUST, CAS, PolyU, EPFL, NUS)
- **Date:** 2026-08-07
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2608.07622.html)
- **Cited by evidence:** top-down survey, R2/R8 question on update authority
- **Relevance to a memory stack:** high. A planted memory phrased as a persistent update is accepted about ten times more often than the same content without update framing; recency alone has no effect.

## TL;DR
- Poison acceptance at fixed load L3: lexical .02 (control) / .02 (recency only) / .23 (framed as persistent update) / .26 (authoritative correction wording); dense .00 / .00 / .12 / .14. 100 paired items per condition.
- Same-slot conflicts and repeated history suppress valid-update adoption (plasticity) sharply; benign unrelated accumulation barely matters.
- Lexical retrieval loses the target update far more than dense across four external sources (plasticity loss .72 to .94 vs .04 to .12).
- Training a retrieval selector on CMI examples raised noisy-update answer success by +.114 to +.614 with paired CIs excluding zero.

## What it claims / describes
Holds query, target state and expected decision fixed, then varies the memories around them: target, competing and other sets, at loads L0 to L6 (3 to 135 memories), with relationship types matched neutral, unrelated, repeated history, same-slot conflict. Update-authority protocol P0 to P3 varies only how a planted update describes itself. Retrieval: BM25 (k1=1.5, b=0.75), Qwen3-Embedding-8B dense, fixed fusion alpha=0.25, RRF kappa=60, top-3. Answerer DeepSeek-v4-pro / v4-flash at temperature 0; scoring by decision matching, not an LLM judge. Cluster bootstrap over base_id, 5,000 replicates.

## Numbers

| Setting | Metric | Value | Baseline | Caveat |
|---|---|---|---|---|
| TravelPlanner count 8, lexical same-slot conflict | plasticity P8 | .34 | .84 | n=50 bases |
| same, dense | P8 / stability S8 | .40 / .54 | .84 / .92 | |
| lexical same-slot conflict | target recall@3 / P(adopt given target retrieved) | .34 / 1.000 | | pure retrieval failure |
| L0 to L6 displacement, LongMemEval | lexical dP / dense dP | -.826 / -.043 | | |
| Poison acceptance L3, lexical | P0 / P1 / P2 / P3 | .02 / .02 / .23 / .26 | | 100 paired per condition |
| Poison acceptance L3, dense | P0 / P1 / P2 / P3 | .00 / .00 / .12 / .14 | | |
| CMI-augmented selector, LongMemEval | answer success | 1.000 | .886 clean-only | ceiling |
| CMI-augmented selector, MEME Tracking | answer success | .929 | .314 | CI [.429, .757] on delta |

Resolver prompt quoted: "You are a strict memory-state resolver. Use only the stored memories below to answer the query. If memories conflict, use the latest applicable stable update for same traveler/day/slot."

## Mechanism details you could implement
- Treat "this replaces X" language in an incoming memory as a claim that needs provenance, not as a supersession trigger.
- Diagnose update failures by splitting retrieval (was the update in top-k?) from adoption (given it was, did the model use it?).

## Limitations, caveats, counter-evidence
- Selector calibration is backend-specific; a frozen selector transferred from +.144 to -.053 across encoders.
- Covers recoverable state transitions only; no full memory system (no supersession links) is tested.
- Table J.1 load curve is non-monotone and could not be reconciled with Table 3's large displacements from the extract.

## Takeaways for tuning a memory stack
- Any supersession design that lets the content of a new item decide that it supersedes an old one (write-time "supersede" edge from extractor output) hands poisoning its strongest lever. The supersede decision should depend on source_class (P5), not on the item's own wording.
- Supports B24 (extracted memories are untrusted) with a specific mechanism: self-described authority.

## Open questions
- Does a System One supersession decider show the same P2 jump?
