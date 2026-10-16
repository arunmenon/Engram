---
schema_version: 1
artifact_id: N-SURVEY-20261007-04
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:14:00Z
idempotency_key: note:survey:arxiv:2610.03020
input_refs: []
pillar_primary: R6
pillar_secondary: [R2]
memory_stage: evaluation
priority: 4
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: 4, control: 3, independence: 4, reproducibility: 2, applicability: 2}
source_url: https://arxiv.org/abs/2610.03020
found_via: survey
---

# DyadMem: A Long-Term Memory Benchmark of How Agents Work with Users (arXiv 2610.03020)

- **URL:** https://arxiv.org/abs/2610.03020 (HTML v1 read)
- **Type:** paper
- **Author / org:** not stated in extract; release planned at GitHub/HF RenaissanceT/DyadMem
- **Date:** 2026-10-02
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2610.03020v1.html)
- **Cited by evidence:** survey
- **Relevance to a memory stack:** medium; personal-assistant data, but it scores the write side (capture, update, delete) separately from QA, which our PDLC benchmark needs.

## TL;DR
- Synthetic, 5 domains, "3,065 episodes, 61,210 QA instances", 50,961 sessions; four stages scored: Capture, Update (add/delete), Recall, QA.
- Gold-memory QA is near saturation (78.7 to 96.3 %); full-pipeline QA averages 47.7 (open-weight) and 57.4 (proprietary). The gap is the memory system, not the reader.
- Under-capture: open-weight models "average 54.0% precision but only 15.1% recall"; terminal banks "about 75 entries at the median, compared with 323.6 in the gold bank".
- "the unsafe-deletion rate, the fraction of predicted deletions that are incorrect, averages 84.1% and 78.1% for the two groups".

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Kimi-K3 Capture F1 / Update op-F1 / Recall@n / Gold QA / Full QA | 28.14 / 31.69 / 62.09 / 94.99 / 74.85 | n/a | Table 2 | per reader summary |
| Gemini-3.1-Pro same columns | 36.37 / 27.99 / 58.91 / 85.24 / 42.35 | n/a | Table 2 | per reader summary |
| unsafe deletion | 84.1 % open-weight, 78.1 % proprietary | n/a | 20 models | verified verbatim |
| judge | GPT-5-mini; human-LLM agreement 86.52 %, kappa 0.7099 on 5,935 outputs | n/a | | judge family overlap with GPT systems not stated |
| variance | bootstrap, 200 resamples | | | seeds not stated |
| cost, latency | not stated | | | |

## Takeaways for tuning a memory stack
- PDLC benchmark design: score capture recall and deletion precision as separate stages, and report gold-memory QA as a ceiling so pipeline loss is visible.
- Deletion is where models fail most; a typed supersede (H7) rather than delete is the safer default (inference).

## Limitations
Fully synthetic, no real users; personal rather than engineering work; data not yet released.
