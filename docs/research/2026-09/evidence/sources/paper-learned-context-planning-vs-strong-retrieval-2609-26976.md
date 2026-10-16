---
schema_version: 1
artifact_id: N-20260926-04
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103703772249641412", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26976
claim_cluster: arxiv:2609.26976
feeds: ["decision", "memory"]
primary_source: https://arxiv.org/abs/2609.26976
source_commit: c154f97fc5a08035ca4831f811a6adabe557ebcc
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R4", "R6"]
tags: {"mechanism": ["learned context planner", "BM25", "anchored hybrid RRF", "planner-guided rerank", "learned router"], "workload": ["long-context multiple-choice QA"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: accuracy per method with bootstrap intervals and a held-out test split", "control": "high: matched character budgets (6k, 9k, 18k), strong lexical and hybrid controls, leakage-safe routers", "independence": "medium: two authors, no shared authors with our sources; single benchmark and model", "reproducibility": "high: public MIT repo with split ids, configs and per-example predictions at a pinned commit", "applicability": "medium: evidence selection under a fixed budget is our curate step, but MCQ on LongBench-v2 with a 7B model is far from build-time reads of structured artifacts"}
beliefs_affected: {"supports": ["B13", "B23"], "contradicts": [], "would_create": ["At a matched character budget, a learned (outcome-supervised) evidence planner did not beat BM25 or anchored hybrid retrieval; planning is a weak relevance signal, best used as a reranking feature"]}
claim_correction: none
---

# When Learned Context Planning Fails to Beat Strong Retrieval (arXiv 2609.26976)

- **URL:** https://arxiv.org/abs/2609.26976 (HTML read); code https://github.com/aapplepku/context-planning-vs-retrieval
- **Type:** paper (Insights from Negative Results in NLP workshop 2026, accepted)
- **Author / org:** Yingrui Li, Han Chen (affiliations not stated in the fetched text)
- **Date:** 2026-09-22
- **Retrieved:** 2026-09-26; repo HEAD `c154f97fc5a08035ca4831f811a6adabe557ebcc` (2026-08-02) via GitHub API; not cloned
- **Cited by evidence:** https://x.com/HEI/status/2103703772249641412 (@HEI, arXiv feed bot)
- **Relevance to a memory stack:** high for R3. It is a clean negative result on the question "should a learned planner pick the evidence before answering, or should strong retrieval?", at matched budgets, with routers tested for leakage.

## TL;DR
- 503 LongBench-v2 MCQ questions, Qwen2.5-7B-Instruct answers; planner is a LoRA on the same model trained by outcome-supervised SFT on 140 train + 28 dev questions.
- At an 18k-character evidence budget: **anchored hybrid 36.18% [32.10, 40.47], BM25 35.98% [31.91, 40.27], best planner-guided 34.19% [30.18, 38.45]**, dense 30.22%.
- On 152 untouched test questions: anchored hybrid 42.11% vs planner-guided 36.84% (-5.26 points, p = 0.215).
- Planner as a **reranker** at a 6k budget: "+1.79-point estimate", but "the paired interval crosses zero and p=0.478"; tie at 9k.
- **Routing:** an oracle choosing per question between hybrid and planner reaches 46.52%, but "leakage-safe routers ... fail to improve over the best single method" under five-fold and leave-domain-out validation.

## What it claims / describes
- **Evidence units:** documents are split into atoms; each method fills a fixed character budget (primary 18k; tight 6k and 9k).
- **Retrieval controls:** BM25 with alphanumeric tokenisation; dense; hybrid (reciprocal-rank fusion); **anchored hybrid**, which "places top BM25 atoms before hybrid fill", i.e. lexical hits first, then RRF fill.
- **Planner variants:** plan-guided hybrid, planner+BM25, planner+hybrid anchor, planner-rerank (planner scores reorder retrieved atoms).
- **Router variants:** oracle (post-hoc, uses gold correctness) and learned, leakage-safe routers under stratified five-fold and leave-domain-out validation.
- **Training:** LoRA rank 16, alpha 32, three epochs, learning rate 5e-5.
- **Conclusion (verbatim):** "learned planning is a weak relevance signal rather than a replacement for strong retrieval."

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| accuracy, anchored hybrid | 36.18% [32.10, 40.47] | | 503 Q, 18k chars | 95% CI |
| accuracy, BM25 | 35.98% [31.91, 40.27] | | 503 Q, 18k | |
| accuracy, planner + hybrid anchor | 34.19% [30.18, 38.45] | anchored hybrid 36.18% | 503 Q, 18k | best planner-guided |
| accuracy, planner + BM25 | 32.21% [28.27, 36.41] | BM25 35.98% | 503 Q, 18k | |
| accuracy, dense | 30.22% [26.37, 34.37] | | 503 Q, 18k | |
| held-out test | 42.11% vs 36.84% | anchored hybrid vs planner-guided | 152 Q | -5.26 points, p = 0.215 |
| planner-rerank vs non-planner rerank | +1.79 points | | 6k chars | CI crosses zero, p = 0.478 |
| oracle routing | 46.52% | best single 36.18% | post-hoc | not deployable |
| learned routers | no improvement over best single method | | five-fold and leave-domain-out | |

## Mechanism details you could implement
- **Anchored hybrid** as the strong baseline for any curated read: put the top lexical (BM25) evidence first, then fill with RRF(hybrid) up to the budget.
- Compare any learned or LLM-driven evidence selection **at the same character or token budget**, with bootstrap CIs and a held-out split never used in development.
- Use planner or curation scores as a **reranking feature** on top of strong retrieval, not as the selector.
- Report the oracle-router gap (here about 10 points) only as headroom, and test learned routers leave-domain-out.

## Limitations, caveats, counter-evidence
- Verbatim: "Our conclusions are restricted to LongBench-v2 MCQ, Qwen2.5-7B-Instruct, one outcome-supervised planner recipe ... We do not evaluate open-ended QA, other model scales, alternative supervision sources, or real-world deployment, and we have no external replication."
- "LongBench-v2 supplies no gold atom-level evidence labels", so evidence recall of each method is not measured.
- Planner trained on only 168 questions; a larger model or a zero-shot frontier planner (as in JITMem-style curation) is not tested (inference: B7 is not directly tested).
- Accuracies are low overall (30 to 42%), so the answering model is a bottleneck.

## Takeaways for tuning a memory stack
- Our H3 "curate at Spec time" arm must beat an anchored-hybrid control at matched tokens, not top-k dense.
- Expect the gain from learned selection to be small (a rerank feature), and budget the eval to detect a 2-point effect (this paper's +1.79 was not significant at n = 503).
- Routing between retrieval strategies has large oracle headroom but learned routers fail to realise it here; combine with N-20260926-03 (group memorisation) before trusting any router.

## Open questions
- Would a frontier-model, task-conditioned curator (not a 7B SFT planner) change the result? Not tested.
- On structured artifacts with exact identifiers, does anchoring on lexical hits matter even more? (inference; not tested)

## Grading and labels
- Directness high; control high; independence medium; reproducibility high (commit c154f97f); applicability medium.
- Pillar R3 (request-time evidence selection under a budget). Secondary R4 (routing as a decision) and R6 (leakage-safe router evaluation, bootstrap CIs, negative-results venue).
- Beliefs: supports B23 (RRF fusion is a reasonable baseline; here strengthened by lexical anchoring); supports B13 (a learned escalation/route is not automatically better). Bears on B7 without contradicting it: B7 concerns task-conditioned read-time curation vs write-time distillation (JITMem); this paper compares learned selection vs strong retrieval (inference: a warning that H3 needs a strong-retrieval control). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103703772249641412 (@HEI) -> arXiv 2609.26976 (HTML) -> main results table (18k budget), held-out test paragraph, reranking and routing sections, limitations section -> repo aapplepku/context-planning-vs-retrieval @ c154f97f. Independence: no shared authors, datasets or harnesses with our local sources.
