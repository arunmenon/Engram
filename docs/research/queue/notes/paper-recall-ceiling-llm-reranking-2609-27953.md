---
schema_version: 1
artifact_id: N-20260926-13
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103000397124431946", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27953
claim_cluster: arxiv:2609.27953
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.27953
source_commit: 124bb20aeebc07fc53288e86e70d076298102094
strength: paper-ablated
pillar_primary: R6
pillar_secondary: ["R3", "R4"]
tags: {"mechanism": ["oracle candidate injection", "closed-candidate bound", "recall-aware NDCG", "LLM listwise rerank"], "workload": ["recommendation reranking"], "lifecycle_stage": ["read", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: oracle vs realistic NDCG per dataset with bootstrap CIs", "control": "high: nine LLMs over a 168x size range, supervised rerankers, fine-tuned model, CF baseline, Holm-corrected tests", "independence": "high: single academic author, public datasets", "reproducibility": "high: code, processed data and result JSONs at a pinned commit, seed 42", "applicability": "medium: recommendation, not evidence retrieval; the protocol flaw (injecting the gold item into the candidate pool) applies directly to rerank benchmarks we cite"}
beliefs_affected: {"supports": ["B11", "B20"], "contradicts": [], "would_create": ["Rerank benchmarks that inject the gold item into the candidate pool overstate realistic quality by an order of magnitude when first-stage recall is low; report first-stage recall@K with every rerank number"]}
claim_correction: none
---

# The Recall Ceiling of LLM Recommendation Reranking (arXiv 2609.27953)

- **URL:** https://arxiv.org/abs/2609.27953 (HTML read); code https://github.com/GeoffreyWang1117/recall-ceiling-cikm2026
- **Type:** paper (CIKM 2026, oral)
- **Author / org:** Zhaohui Wang
- **Date:** 2026-08-27
- **Retrieved:** 2026-09-26; repo HEAD `124bb20aeebc07fc53288e86e70d076298102094` (2026-09-17) via GitHub API; not cloned
- **Cited by evidence:** https://x.com/_reachsumit/status/2103000397124431946 (@_reachsumit)
- **Relevance to a memory stack:** medium. Our rerank evidence (B10: Hindsight 0.94 recall@1 on LoCoMo-200) is a within-pool number. This paper quantifies how much a candidate-pool protocol can overstate end-to-end quality when first-stage recall is low.

## TL;DR
- Injecting the held-out item into the candidate set ("injection-oracle") vs realistic candidates from upstream retrieval: NDCG@10 drops **92.4% (Beauty), 93.5% (Movies), 94.9% (Electronics)**.
- Realistic first-stage recall is tiny: "realistic retrieval covers only 2--19% of relevant items at K=100 across eight datasets in three domains".
- Under realistic retrieval, "No configuration significantly beats CF on primary Amazon datasets"; on Movies, reasoning models trend worse (V4-Pro-think -43%, p = .004).
- Proposed RAEP protocol: classify recall regime first, report recall-aware NDCG and ceiling utilisation.

## What it claims / describes
- **Closed-candidate bound (Theorem 1):** no reranker can exceed Recall@|window| of its candidate set under leave-one-out evaluation.
- **RAEP:** (1) recall diagnosis: CRITICAL r < 5%, LOW 5 to 15%, MODERATE 15 to 30%, ADEQUATE >= 30%; (2) RA-NDCG = NDCG@k(u) / NDCG*k(u); (3) ceiling utilisation eta; (4) adaptive-K per user from CF score distribution, K in [50, 500].
- **Rerankers:** Gemma3-4B, Qwen3-8B, GPT-4o-mini, Qwen3-32B, Llama-3.3-70B, DeepSeek-V3-671B, DeepSeek-V4-Pro and V4-Flash (with and without reasoning), Kimi-K2-Turbo; LambdaMART, RankNet, MLP; LoRA-LLaMA-3.2-3B.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| NDCG@10 Beauty | oracle .0856 [.069-.103] vs realistic .0065 [.003-.012] | CF .0050 | n = 500 users | gap 92.4% (Table 3) |
| NDCG@10 Movies | .1039 [.095-.113] vs .0067 [.004-.009] | CF .0086 | | gap 93.5% |
| NDCG@10 Electronics | .0971 [.088-.107] vs .0050 [.003-.008] | CF .0042 | | gap 94.9% |
| best Recall@100 | Beauty 12.33% (LightGCN); Movies 4.81% (DirectAU); Electronics 3.13% | | Table 4, 12 retrievers | |
| realistic rerank, Beauty | Qwen3-8B .0051; Llama-3.3-70B .0038; DeepSeek-V3 .0016; LambdaMART .0086; LoRA-3B .0078 | CF-Score .0051 | Table 5, n = 500 | none significant after Holm |
| MovieLens-25M | "All five cloud LLMs perform below CF baseline" | CF | recall 17.4% | |
| API cost | $1.24 total | | 7 models x 5 datasets | |

## Mechanism details you could implement
- Always report first-stage recall@K next to any rerank metric; compute the closed-candidate ceiling and the fraction of it a reranker uses.
- Never evaluate a reranker with the gold item injected into its pool as the only protocol.
- Size K adaptively from the retriever's score distribution rather than a fixed K.

## Limitations, caveats, counter-evidence
- Recommendation with implicit feedback, recall 2 to 19%; "production systems operating at substantially higher recall sit outside the measured regime".
- Rerankers lack industrial signals; offline only; n = 500 cannot detect d < 0.10; density model R^2 = 0.39 on eight points.

## Takeaways for tuning a memory stack
- For H5-rerank, measure memory retrieval recall@K on our set first; if recall@K is low, invest in retrieval (fusion, anchoring) before reranker sophistication (the paper's conclusion: "improving retrieval is more consequential than increasing reranker sophistication" in low-recall regimes).
- Re-read vendor rerank numbers (Hindsight, Supermemory) for whether the gold evidence was guaranteed to be in the pool (inference: LoCoMo-200 candidate pools likely contain gold; not stated in our local notes).

## Open questions
- What is our retrieval recall@K on build-time reads? Unknown; needs measurement.

## Grading and labels
- Directness high; control high; independence high; reproducibility high (commit 124bb20a); applicability medium.
- Pillar R6 (evaluation protocol overstates quality). Secondary R3 (retrieval ceiling) and R4 (reranker choice).
- Beliefs: supports B11 (rerank vs admission are separate decisions; a reranker cannot recover evidence the pool lacks, inference) and B20 (headline rerank claims narrow on protocol). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103000397124431946 (@_reachsumit) -> arXiv 2609.27953 (HTML) -> Tables 3, 4, 5, RAEP section, limitations -> repo GeoffreyWang1117/recall-ceiling-cikm2026 @ 124bb20a. Independence: single author, public datasets (Amazon, MovieLens-25M, MIND).
