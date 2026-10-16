---
schema_version: 1
artifact_id: N-SURVEY-20261009-01
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2609.10263
input_refs: []
pillar_primary: R2
pillar_secondary: [R6]
memory_stage: retrieval
priority: 4
beliefs_affected:
  supports: [B3]
  contradicts: [B6]
evidence: {directness: 4, control: 3, independence: 2, reproducibility: 1, applicability: 3}
source_url: https://arxiv.org/abs/2609.10263
found_via: survey
---

# What Should an Agent Forget? Separating What Is Stored from What Is Used (RD-Forget)

- **URL:** https://arxiv.org/abs/2609.10263 (HTML v1 read)
- **Type:** paper
- **Author / org:** Yuhang Li (Beihang University), Yuchen Li (East China Normal University)
- **Date:** 2026-09-09
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2609.10263.html)
- **Cited by evidence:** top-down survey, R2 question on B3 and B6
- **Relevance to a memory stack:** high. It is the first ablation we have that switches off only the suppression of superseded values, at a fixed token budget, and shows a large drop on knowledge-update questions.

## TL;DR
- Keep everything in an archive, but build a per-query view: same-slot replacement links mark old values SUPERSEDED, and superseded values are only served when the question has historical intent.
- At a fixed 2,048-token answer budget, turning off the suppression (older revisions stay active, link cleared) drops LongMemEval knowledge-update accuracy from 93.59 to 60.26 (GPT-5.6-Luna, n=78).
- This is "forgetting as suppression at read time, not deletion". It is the matched-budget accuracy gain that belief B6 says no source shows.
- Weak points: the judge is the same model family as the system, n is small (78 to 100 per benchmark), one backbone for ablations, no code.

## What it claims / describes
Four stages over an archive H of all observations:
1. Curation: a frozen LM curator extracts "the smallest complete evidence set needed by the question", groups facts into slots keyed `subject|relation|scope`, keeps relations needed for multi-hop.
2. Supersession (Eq. 4): an older fact becomes SUPERSEDED when a newer ACTIVE fact shares its slot; it keeps `superseded_by`.
3. Eligibility (Eq. 5): ACTIVE always eligible; DEPRECATED only with rescue flag r=1; SUPERSEDED only if r=1 and the query has historical intent h(q)=1.
4. Selection and packing: lexical overlap rank, +0.4 bonus for ACTIVE, an LM selector orders ids, greedy pack to budget B = 2,048 tokens, cost per entry Tok(text)+8 (o200k_base).

## Numbers
Table 1 (%, AMB-Text n=86 from LoCoMo / LME-KU n=78 / MAB-FC n=100):

| Backbone | ACE | ReasoningBank | RD-Forget |
|---|---|---|---|
| Qwen3.5-flash | 52.33 / 60.26 / 34.00 | 54.65 / 60.26 / 23.00 | 74.42 / 74.36 / 51.00 |
| GPT-5.6-Luna | 67.44 / 83.33 / 51.00 | 75.58 / 71.79 / 46.00 | 89.53 / 93.59 / 77.00 |
| MiniMax-M2.5 | 69.77 / 61.54 / 42.00 | 62.79 / 51.28 / 46.00 | 87.21 / 87.18 / 57.00 |
| Kimi-K2.5 | 81.40 / 70.51 / 41.00 | 80.23 / 62.82 / 45.00 | 82.56 / 76.92 / 59.00 |

Table 2 ablations (Luna only, same budget, AMB-Text / LME-KU / MAB-FC):

| Variant | Scores | Delta vs matched full |
|---|---|---|
| Matched full | 91.86 / 93.59 / 74.00 | 0 |
| minus FORGET (old revisions stay active, link cleared) | 68.60 / 60.26 / 51.00 | -23.26 / -33.33 / -23.00 |
| minus QC (curator does not see the question) | 77.91 / 82.05 / 56.00 | -13.95 / -11.54 / -18.00 |
| minus RESCUE | 88.37 / 91.03 / 65.00 | |
| minus SLOT | 86.05 / 89.74 / 64.00 | |
| minus CLOSURE | 87.21 / 89.74 / 71.00 | |

Table 3 (BEAM n=150 / PersonaMem n=579), Luna: RD-Forget 70.58 / 79.97 vs ACE 56.97 / 65.46.

Cost, latency, seeds, confidence intervals: not stated.

## Mechanism details you could implement
- Slot key `subject|relation|scope`; same-slot newer ACTIVE fact sets old to SUPERSEDED with `superseded_by`.
- Serve SUPERSEDED only when a historical-intent classifier fires; never delete from the archive.
- +0.4 rank bonus for ACTIVE entries before LM selection.

## Limitations, caveats, counter-evidence
- Text vs table: Luna full model is 89.53 / 93.59 / 77.00 in Table 1 but 91.86 / 93.59 / 74.00 in the Table 2 "matched full" batch; LME-KU agrees, the other two do not.
- Judge shares the model family with curator, selector and answerer (authors call it within-protocol evaluation).
- Baselines (ACE, ReasoningBank) are procedural-memory methods, not the strongest update-aware systems (no Zep, REALM, Mem0 comparison).
- minus FORGET also changes what the packer fills the budget with, so it is a "suppression on/off" ablation, not a "link written at write time vs inferred at read time" ablation (inference).
- No code released.

## Takeaways for tuning a memory stack
- B3: supports that supersession matters a lot on knowledge-update questions in isolation (-33 points when removed, everything else fixed), larger than PC-20260926-C05's predeclared 5 points. Same-model judging keeps it at lead strength for us.
- B6: contradicts the wording "no source shows forgetting improving end-task accuracy at matched budget" if forgetting includes read-time suppression. B6 should be split: deletion or decay (still no evidence) vs suppression of superseded values from the served view (now one same-judge ablation with a large effect).

## Open questions
- Does the effect survive an independent judge and a stronger baseline?
- How accurate is the historical-intent classifier, and what does a false negative cost?
