---
schema_version: 1
artifact_id: N-SURVEY-20261011-04
artifact_type: note
producer: triage
run_id: survey-20261011T054529Z-bcaa
created_at: 2026-10-11T06:55:00Z
idempotency_key: note:survey:arxiv:2511.00262
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R6]
memory_stage: staleness
priority: 3
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: 4, control: 3, independence: 4, reproducibility: 2, applicability: 4}
strength: paper-ablated
source_url: https://arxiv.org/abs/2511.00262
found_via: survey
answers_watch_request: null
---

# LLM-Driven Cost-Effective Requirements Change Impact Analysis (ProReFiCIA, TOSEM 2026, arXiv 2511.00262 v6)

- **URL:** https://arxiv.org/abs/2511.00262 (HTML v6 read, first 100k of 150k characters; threats-to-validity and later sections not read)
- **Type:** paper
- **Author / org:** Romina Etezadi, Sallam Abualhaija, Chetan Arora, Lionel Briand (Ottawa, Luxembourg, Monash, Lero)
- **Date:** v6 dated 2026-09-03; TOSEM, DOI 10.1145/3844507
- **Retrieved:** 2026-10-11
- **Relevance to a memory stack:** high. "Notice a changed requirement and find what it affects" is one of the five PDLC benchmark tasks in priority 4, and the pipeline is a large model proposing plus a cheap classifier filtering, the shape of a System One stage.

## TL;DR
- Task: given a change rationale (add, delete, modify) to a requirements document, return the impacted requirements in the same document with justification. Requirements only; no design or code.
- Pipeline: whole document in one prompt (cache-augmented generation), a refinement pass that re-asks about unselected requirements, then a filter that ranks by LLM confidence and applies a fine-tuned NLI model (nli-deberta-v3-large, classifier layer only).
- On the held-out test set (11 change rationales, 33 impacted requirements): 85.7% of impacted requirements found while the analyst reviews 3.0% of requirements; 95.8% at 3.4% with RAG domain knowledge.
- Baselines: RAG plus chain-of-thought (GPT-4o) 35.1% at 8.1%; embedding similarity with fixed 0.5 cutoff 86.3% at 99.0% review cost.

## Numbers (verbatim, SAT-DLink-Test)

| Technique | TP | FN | FP | Effectiveness (recall) | Cost (share reviewed) |
|---|---|---|---|---|---|
| CoT (GPT-4o) | 15 | 18 | 156 | 35.1% | 8.1% |
| Similarity, T1 (0.5) | 31 | 2 | 2072 | 86.3% | 99.0% |
| Similarity, T2 (largest drop) | 15 | 18 | 32 | 51.7% | 2.2% |
| Similarity, T3 (NARCIA) | 19 | 14 | 785 | 66.8% | 38.1% |
| ProReFiCIA | 28 | 5 | 30 | 85.7% | 3.0% |

Ablation of stages: without post-processing 23/10/9, 73.3%, 1.5%; + refinement 28/5/49, 85.7%, 3.6%; + filtering 28/5/30, 85.7%, 3.0%. One requirement per query (iterative): 33/0/252, 100%, 35.9%. Batch 100: 30/3/76, 95.8%, 5.3%. With RAG + refinement + filtering: 30/3/35, 95.8%, 3.4%.

Prompt sensitivity (RQ1, F2 over 64 zero-shot prompts): GPT-4o WASP min 0.61 max 0.89 median 0.78; SAT-DLink min 0.34 max 0.64 median 0.52. Models: GPT-4o, deepseek-R1 (671B), llama3-405B, mistral-large, gemini-2.0-flash-lite. Token counts not reported; cost grows "approximately linearly" with requirements.

Note: the effectiveness column does not equal TP/(TP+FN) in every row (e.g. 28/33 = 84.8%, reported 85.7%; 31/33 = 93.9%, reported 86.3%), so it is likely averaged per change rationale (inference; the text and table formula disagree as read).

## Mechanism details you could implement
- Put all candidate requirements in one prompt rather than one query per requirement: 7x fewer false positives at a recall cost (95.8% batch 100 vs 100% iterative).
- Refinement prompt with a "completely certain" constraint over the unselected set, to counter lost-in-the-middle.
- Filter rule: rank by LLM confidence; if the set has more than 5 items, an item the NLI rejects is kept only if it ranks in the top 50%.

## Limitations, caveats, counter-evidence
- Test set is 11 change rationales in one satellite document; Fisher test vs iterative p = 5.3e-2. Authors: results "need to be confirmed on larger datasets".
- "The LLM frequently relies on correlational signals... rather than performing true causal reasoning."
- Datasets appear industrial and are probably not released (not stated in the part read).

## Takeaways for tuning a memory stack
- For staleness after a requirement change, a propose-then-filter design beats both similarity thresholds and per-item questioning on the recall-per-review trade-off.
- The filter slot is where a System One model could replace the fine-tuned NLI model; nobody has tested that.

## Open questions
- Does the same pipeline extend to requirement to design-section and requirement to test links?
