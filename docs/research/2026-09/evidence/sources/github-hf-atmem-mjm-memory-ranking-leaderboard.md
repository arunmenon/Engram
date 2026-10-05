---
schema_version: 1
artifact_id: N-20260928-12
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104422828854685709", "file_id": null, "sha256": null}, {"artifact_id": "post:2104422072671998268", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:spaces/javadtaghia/atmem-mjm-leaderboard-20260928
claim_cluster: hf:spaces/javadtaghia/atmem-mjm-leaderboard-20260928
feeds: ["decision", "memory"]
primary_source: https://huggingface.co/spaces/javadtaghia/atmem-mjm-leaderboard-20260928
source_commit: f905084f38262e1e9a075f8dd187a121671715fa
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R3", "R4"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["listwise rerank", "reward model reranker", "LoRA post-training", "Bradley-Terry pairwise loss"], "workload": ["chat memory", "LoCoMo"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: aggregate metrics and paired cluster-bootstrap intervals published in leaderboard.json", "control": "high: same frozen top-10 candidate pool per question across all four arms, fresh Jev rerun", "independence": "medium: independent builder (AtMem), not TypeSafe; LoCoMo shared with Hindsight and Jev-Mem results", "reproducibility": "low: candidate pool hashed but not published; no model weights or training data in the Space", "applicability": "medium: memory-evidence ranking over a candidate pool is our rerank stage; chat data, not engineering artifacts"}
beliefs_affected: {"supports": ["B10"], "contradicts": [], "would_create": ["A 0.6B open reward model, off the shelf or LoRA-tuned on 72 synthetic pairs, does not reach Jev on memory reranking (MRR@5 0.463 vs 0.588 on LoCoMo full)"]}
claim_correction: The post describes a "classification use case" and details the 120-scenario synthetic training set; the published leaderboard is a ranking comparison on LoCoMo full (10 conversations, 1,986 questions) over a frozen top-10 candidate pool, and the synthetic set is only the (tiny) training data for AtMem-MJM.
---

# AtMem-MJM memory ranking leaderboard: Jev 1.13 vs Skywork Reward V2 0.6B (off the shelf and post-trained) on LoCoMo

- **URL:** https://huggingface.co/spaces/javadtaghia/atmem-mjm-leaderboard-20260928
- **Type:** builder report (static Hugging Face Space with `leaderboard.json`)
- **Author / org:** javadtaghia on Hugging Face; posted by @AtMemAi (AtMem, a memory product)
- **Date:** Space revision `f905084f38262e1e9a075f8dd187a121671715fa`, last modified 2026-09-27T18:00:30Z
- **Retrieved:** 2026-09-28; read `README.md` and `leaderboard.json` via `huggingface.co/spaces/.../raw/main/`. The rendered page (index.html) was not needed.
- **Cited by evidence:** @AtMemAi 2026-09-28 https://x.com/AtMemAi/status/2104422828854685709 and the near-duplicate https://x.com/AtMemAi/status/2104422072671998268
- **Relevance to a memory stack:** high. A direct, same-pool comparison of Jev against an open-weight small reranker at the memory reranking stage, with paired intervals; the open model loses clearly.

## TL;DR
- Four arms rank the same frozen top-10 memory candidates per question on LoCoMo full (10 conversations, 1,986 questions): Jev 1.13.0 (fresh API rerun) MRR@5 0.588, Recall@1 0.5433; AtMem-MJM (Skywork Reward V2 0.6B + LoRA) 0.4632 / 0.3741; Skywork off the shelf 0.454 / 0.3661; AtMem native order 0.4259 / 0.3399. Recall@10 is 0.6495 for all (same pool).
- Paired AtMem-MJM minus Jev: MRR@5 -0.1248, 95% cluster-bootstrap interval [-0.1355, -0.111]; Recall@1 -0.1692 [-0.183, -0.1508]. The open model's post-training bought about +0.009 MRR@5 over the off-the-shelf reward model.
- The author's own stated claim: "AtMem-MJM does not beat Jev on MRR@5".
- Training of AtMem-MJM was tiny: 72 synthetic training pairs, LoRA rank 4, 3 epochs, about 134 s on Apple MPS.

## What it claims / describes
- **Candidate pool:** "Same frozen top-10 candidate IDs/text per question across every arm" (leaderboard.json `candidate_pool`), `candidate_pool_sha256: 7b5b54df...b505`; dataset `LoCoMo full (10 conversations, 1,986 questions)`, `dataset_sha256: 79fa87e9...8ff4`.
- **Jev rerun:** `model: jev-1.13.0`, `batch_size: 50`, `requests: 40`, `successful_cases: 1986`, `errors: 0`, `omitted_candidate_probabilities: 0`. README: "The fresh Jev 1.13.0 API rerun used 40 batches of 50 questions, matching the historical request grouping, and completed all 1,986 cases with all ten candidate scores per case." The exact Jev question (choice vs per-candidate noul) is not stated.
- **AtMem-MJM training (post text):** 120 synthetic memory scenarios across 10 scenario families and eight preference rules (explicit vs inferred facts, current vs stale, conflicts, task relevance); split by whole family: 72 training pairs, 24 validation, 24 audit; input = task plus two candidate memories; Bradley-Terry pairwise loss; LoRA on attention q_proj and v_proj, rank 4, alpha 8, dropout 0.05; reward head saved with adapter; 3 epochs, LR 5e-5, AdamW, pair batch 1, max length 256, Apple MPS float32 (float16 gave NaNs); about 134 s, peak about 2.41 GB.
- **Bootstrap:** unit = conversation, 10 clusters, 10,000 replicates, seed 20260928.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| MRR@5, Jev 1.13.0 | 0.588 | native order 0.4259 | LoCoMo full, 1,986 q, frozen top-10 pool | ranking only |
| Recall@1, Jev | 0.5433 | native 0.3399 | same | |
| MRR@5, AtMem-MJM | 0.4632 | Skywork off the shelf 0.454 | same | 72 train pairs |
| Recall@1, AtMem-MJM | 0.3741 | Skywork 0.3661 | same | |
| Recall@10, all arms | 0.6495 | n/a | same pool | ceiling for any reranker here |
| MJM minus Jev, MRR@5 | -0.1248 [-0.1355, -0.111] | | paired, cluster bootstrap, 10 clusters | coarse |
| MJM minus Jev, Recall@1 | -0.1692 [-0.183, -0.1508] | | same | |
| MJM minus Skywork, MRR@5 | +0.0092 [0.0044, 0.0158] | | same | |
| MJM minus Skywork, Recall@1 | +0.008 [-0.0005, 0.0212] | | same | interval crosses 0 |
| MJM minus native, MRR@5 | +0.0373 [0.0165, 0.0571] | | same | |
| Jev rerun errors | 0 of 1,986 | | 40 requests of 50 | |

## Mechanism details you could implement
- A fair reranker bake-off: freeze the candidate ids and text per question, hash the pool, give every arm the same pool, report MRR@5 and Recall@1 with a paired cluster bootstrap by conversation (or by repository, for us).
- Batch 50 questions per Jev request (40 requests for 1,986 cases) and verify that every candidate got a probability (`omitted_candidate_probabilities: 0`).
- If trying an open reward model as a cheap reranker: Skywork Reward V2 0.6B scored a query-plus-two-memories pair; the LoRA recipe above is small enough to run on a laptop, but here it added under 0.01 MRR@5.

## Limitations, caveats, counter-evidence
- leaderboard.json `limitations`: "Ranking evidence only; not answer or agent-task quality." "Only ten conversation clusters; cluster bootstrap intervals are coarse." "Four historical LoCoMo evidence-reference anomalies remain included." "AtMem-MJM used 72 synthetic train pairs, 24 validation pairs, and 24 audit pairs from two held-out families; this is a small, templated pilot." "No benchmark questions, candidate text, evidence identifiers, private memories, training examples, or model weights are included in this Space."
- The candidate pool generator (AtMem native retrieval) caps Recall@10 at 0.6495, so a third of questions have no gold in the pool.
- How the open model scored 10 candidates from a pairwise model (pairwise tournament vs pointwise reward) is not stated.
- The Jev question wording and whether a "none" option was offered are not stated.

## Takeaways for tuning a memory stack
- Evidence against swapping Jev for a tiny off-the-shelf reward model at the rerank stage without substantial training data; 72 synthetic pairs did not close a 0.12 MRR@5 gap.
- A priority-2 comparison (open-weight vs Jev) should budget real labelled pairs from our own traffic, and measure on a frozen pool with paired intervals, as here.

## Open questions
- Would an open typed-decision model (od1, Julia-1, Laya) rather than a reward model close the gap on the same pool?
- How much of Jev's lead survives on engineering artifacts?

## Grading and labels
- Directness high; control high (same frozen pool, paired intervals); independence medium; reproducibility low (pool and weights not published); applicability medium.
- Pillars: R9 primary (which System One model at the rerank stage), R3 and R4 secondary. Memory stage: reranking. Priority 1 (Jev at reranking) and 2 (open-weight comparison). Products named: Jev, AtMem.
- Beliefs: supports B10 (single Jev call as a strong listwise reranker on LoCoMo-style pools, second independent builder); would create the open-reward-model belief in the frontmatter.
- Contradiction rows: none.

## Origin chain
- Posts 2104422828854685709 and 2104422072671998268 (@AtMemAi) -> HF Space javadtaghia/atmem-mjm-leaderboard-20260928@f905084 -> `leaderboard.json` (leaderboard, paired_comparisons, jev_rerun, limitations) and `README.md` -> this note.
- Independence: LoCoMo is shared with Hindsight (B10 source) and Jev-Mem; the builder is not TypeSafe or Vectorize.
