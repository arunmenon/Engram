---
schema_version: 1
artifact_id: N-20260926-17
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:18:28Z
input_refs: [{"artifact_id": "post:2103000527919575356", "file_id": null, "sha256": null}, {"artifact_id": "post:2103034639585603901", "file_id": null, "sha256": null}, {"artifact_id": "post:2103192557689942345", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27213
claim_cluster: arxiv:2609.27213
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.27213
source_commit: n/a
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R4"]
tags: {"mechanism": ["budgeted cross-encoder reranking", "Gaussian process over embedding residuals", "top-k boundary acquisition"], "workload": ["diffuse multi-document retrieval"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: nCG@100 per dataset against human judgments", "control": "high: named budgeted-rerank baselines (RGS, BAGEL) at matched CE budget, ablations of each component", "independence": "medium: industry authors (affiliation not captured), public datasets", "reproducibility": "low: no code link captured, under review", "applicability": "medium: when the context holds more items than the reranker budget can score, as in wide build-time reads"}
beliefs_affected: {"supports": ["B9"], "contradicts": [], "would_create": ["When the rerank budget B is smaller than the context capacity k, spending cross-encoder calls on the top-k boundary rather than the top of the list raises recall of relevant documents by about 3.8 points nCG@100"]}
claim_correction: The abstract states "+5.4 nCG@100 over the strongest baseline"; the body reports an "average of +3.8 pp nCG@100" over the second-best baseline at B=50, k=100 (per-dataset gains 2.4 to 3.5 points in Table 1); the 5.4 figure is not located in the fetched tables.
---

# BoundaryMORPH: Budgeted Reranking via Active Set Selection for Diffuse Retrieval (arXiv 2609.27213)

- **URL:** https://arxiv.org/abs/2609.27213 (HTML read)
- **Type:** paper (under review)
- **Author / org:** Eylon Caplan, Shamik Roy, Shib Sankar Dasgupta, Yingfan Wang, Rashmi Gangadharaiah (the citing post says Amazon; not verified in the fetched text)
- **Date:** 2026-09-23
- **Retrieved:** 2026-09-26; no code link captured
- **Cited by evidence:** https://x.com/_reachsumit/status/2103000527919575356 (@_reachsumit, "Amazon uses a Gaussian Process ...")
- **Relevance to a memory stack:** medium. Addresses a real read-path constraint: we can place k items in context but can afford to score only B < k with an expensive judge. It says where to spend those B calls.

## TL;DR
- Setting: "the CE budget B is strictly bounded by latency and is often smaller than the context window capacity k". Standard reranking wastes calls on obvious top documents.
- A GP models residuals r(d) = f_CE(q, d) - mu0(d), prior mean = the document's MIPS percentile rank, von Mises-Fisher kernel on unit embeddings; the next CE call goes to the incumbent/challenger pair with the smallest standardised boundary gap: argmin [mu(j) - mu(i)] / [sigma(j) + sigma(i)].
- At B = 50, k = 100 (Table 1, nCG@100 on human judgments): NeuCLIR 59.2% vs BAGEL 55.7%; Robust04 51.5% vs 48.0%; TravelDest 43.1% vs 40.7%; average +3.8 points.
- Ablations: no boundary acquisition -1.5 to -2.6 points; no prior -2.1 to -3.8 points.

## What it claims / describes
- Candidate pool: top 10,000 by Qwen3-Embedding-4B MIPS; datasets filtered to queries with >= 20 relevant documents: NeuCLIRBench 85 queries, Robust04 187, TravelDest 99.
- Primary pair: multilingual-e5-large embeddings + zerank-2 cross-encoder; robustness with other pairs.
- Per-query advantage correlates with how multimodal the relevant set is (Spearman rho +0.59, p = 3.5e-9).

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| nCG@100, NeuCLIR | 59.2% | BAGEL 55.7% | 85 queries, B=50, k=100 | Table 1 |
| nCG@100, Robust04 | 51.5% | BAGEL 48.0% | 187 queries | |
| nCG@100, TravelDest | 43.1% | BAGEL 40.7% | 99 queries | |
| average gain | +3.8 points | second-best baseline | | abstract says +5.4 |
| ablation: no boundary acquisition | -1.5 to -2.6 | full | | |
| ablation: no prior | -2.1 to -3.8 | full | | |
| multimodality vs advantage | Spearman +0.59, p = 3.5e-9 | | per query | |

## Mechanism details you could implement
- Use the first-stage rank as a prior and spend the expensive judge (cross-encoder, decision model) only on items near the inclusion boundary; items far above or below it keep their prior position.
- Kernel over embeddings lets one judged item update beliefs about its neighbours.

## Limitations, caveats, counter-evidence
- Sequential acquisition, GP cost O(B^3 N); capacity counted in documents, not tokens; designed for diffuse queries, "factoid queries (k=1) unsuitable"; set selection only, no ordering within context.
- Seeds/CIs not captured.

## Takeaways for tuning a memory stack
- For wide reads (many relevant memories), a boundary-targeted judge budget beats scoring the top of the list; for "find the one fact" reads, use a plain listwise rerank.

## Open questions
- Does it hold with a decision-model judge instead of a cross-encoder? Not tested.

## Grading and labels
- Directness high; control high; independence medium; reproducibility low; applicability medium.
- Pillar R3 (bounded-budget evidence selection). Secondary R4 (where to spend judge calls).
- Beliefs: supports B9 in spirit (budget-aware selection can hold quality at lower judge cost; here a different mechanism than a sufficiency stop rule). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103000527919575356 (@_reachsumit) -> arXiv 2609.27213 (HTML) -> method section, Table 1, ablations, limitations -> this note.
