---
schema_version: 1
artifact_id: N-SURVEY-20261004-02
artifact_type: note
producer: triage
run_id: survey-20261004T054506Z-478e
created_at: 2026-10-04T05:55:25Z
idempotency_key: note:survey:arxiv:2605.00447
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R3]
memory_stage: linking
priority: 3
related_notes: [N-SURVEY-20260928-13]
companion_sources: [arxiv:2508.12232]
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: high (decides the IMPLEMENTS link between a ticket and a commit, our exact trace link)
  control: high (same candidates, same split, ten retrievers and nine rerankers compared; temporal split; issue keys stripped)
  independence: high (academic, no product; models from several vendors)
  reproducibility: medium (figshare package cited; pinning not stated)
  applicability: high (open-source repositories, Jira issues and commits; no PR or design-doc nodes)
source_url: https://arxiv.org/abs/2605.00447
found_via: survey
---

# Think Harder and Don't Overlook Your Options: Revisiting Issue-Commit Linking with LLM-Assisted Retrieval (arXiv 2605.00447 v2), with LinkAnchor (arXiv 2508.12232 v5)

- **URL:** https://arxiv.org/abs/2605.00447 (HTML v2 read); companion https://arxiv.org/abs/2508.12232 (HTML v5 read)
- **Type:** paper (two)
- **Author / org:** Cole Morgan, Muhammad Asaduzzaman (University of Windsor), Shaiful Chowdhury (University of Manitoba), Shaowei Wang. Companion: Akhavan, Hoseinpour, Heydarnoori (Bowling Green State), Bagheri (Nebraska-Lincoln), Keshani (Zurich), PACMSE FSE issue.
- **Date:** 2026-06-29 (v2); companion v5 2026-06-26
- **Retrieved:** 2026-10-04 (local copies: `out/log/raw/arxiv-2605.00447.html`, `out/log/raw/arxiv-2508.12232.html`)
- **Cited by evidence:** survey question R10-1 (how well can a model decide an IMPLEMENTS link; does candidate-set size matter). Extends N-SURVEY-20260928-13's cluster on PR-issue alignment (PAIChecker, TraceLLM), which did not cover retrieve-then-rerank issue-commit recovery.
- **Relevance to a memory stack:** high. It is the largest controlled comparison of cheap trained rerankers against LLMs for the exact link we want a System One model to decide.

## TL;DR

- Ticket-to-commit linking works best as two stages. First, retrieve candidates with a dense retriever inside a time window. Second, rerank the top 20 with a small trained model.
- A random-forest reranker (RCLinker), trained in about an hour on textual and metadata features, matches or beats GPT-5.1. P@1 0.842 vs 0.822 (EasyLink), 0.936 vs 0.920 (BTLink), 0.949 vs 0.953 (Apache).
- Open 7B to 8B LLMs used as listwise rerankers are far worse (Llama-3.1-8B P@1 0.639 to 0.762; Gemma-7B 0.573 to 0.652). Qwen3-32B is close to GPT-5.1.
- Retrieval sets the ceiling: Hit@20 is 0.916 / 0.968 / 0.972. Restricting candidates to one year plus 30 days around issue closure keeps about 97% of true links.
- Companion LinkAnchor: an agentic GPT-4o-mini searches comments, commits and code and reaches mean Hit@1 0.8632 on six Apache projects, at "$0.0101" and "23.599 s" per issue. Issue comments carry most of the signal: removing them costs 17%.

## What it claims / describes

**Data (2605.00447).** Three datasets: EasyLink (20 OSS projects, 159,592 links), BTLink (14 projects, 39,051 links) and Apache (10 projects, 208,858 links, 2006 to 2025). The split is per project and chronological ("newest 20%" of issue reports as test), giving 41,203 test issues. Issue keys are stripped from commit messages so the link cannot be read off the text.

**Pipeline.** Retrievers: BM25, BM25L, SBERT semantic search (all-MiniLM-L12-v2), HNSW, ANNOY, LSH and RRF fusion. Rerankers over the top K=20: classic ML (RCLinker random forest, FRLink, Hybrid-Linker); neural (BTLink bi-encoder, cross-encoder ms-marco-MiniLM-L-6-v2); and listwise LLMs (GPT-5.1, Qwen3-32B, Gemma-7B, Llama-3.1-8B). The LLM prompt is EasyLink's: issue title and description plus candidate commit ids and messages, and the model returns an ordered id list.

**Companion (2508.12232).** LinkAnchor is an agent: GPT-4o-mini with tools over the issue, its comments, commits and the codebase. Search is limited to a "safe lifespan" of one week before issue creation to one week after resolution. Each issue gets at most 20 function calls and 200k tokens. It returns a single commit and does no training.

## Numbers

Reranking at K=20, P@1 / MRR@20 (2605.00447):

| Dataset | RCLinker (RF) | GPT-5.1 | Qwen3-32B | Cross-encoder MiniLM | Llama-3.1-8B | Gemma-7B | Hybrid-Linker |
|---|---|---|---|---|---|---|---|
| EasyLink | 0.842 / 0.871 | 0.822 / 0.863 | 0.782 / 0.836 | 0.807 / 0.843 | 0.639 / 0.716 | 0.573 / 0.664 | 0.087 / 0.215 |
| BTLink | 0.936 / 0.949 | 0.920 / 0.939 | 0.909 / 0.929 | 0.829 / 0.871 | 0.762 / 0.817 | 0.635 / 0.717 | 0.201 / 0.340 |
| Apache | 0.949 / 0.959 | 0.953 / 0.961 | 0.909 / 0.932 | 0.895 / 0.921 | 0.710 / 0.772 | 0.652 / 0.725 | 0.162 / 0.299 |

Retrieval only, P@1 / R@1 / R@10 / R@20:

| Dataset | SBERT | BM25 | RRF |
|---|---|---|---|
| EasyLink | 0.650 / 0.556 / 0.824 / 0.861 | 0.505 / 0.431 / 0.698 / 0.749 | 0.620 / 0.529 / 0.819 / 0.865 |
| BTLink | 0.780 / 0.671 / 0.883 / 0.909 | 0.658 / 0.565 / 0.756 / 0.809 | 0.758 / 0.650 / 0.852 / 0.894 |
| Apache | 0.768 / 0.699 / 0.878 / 0.902 | 0.690 / 0.630 / 0.773 / 0.808 | 0.780 / 0.710 / 0.880 / 0.913 |

| Metric | Value | Setup | Caveat |
|---|---|---|---|
| Hit@20 (retrieval ceiling) | 0.916 / 0.968 / 0.972 | three datasets | one table cell (Gemma, Apache) reads 0.975, a small inconsistency |
| True links inside 1 year | 97% / 91.6% / 94.1% | EasyLink / BTLink / Apache | 1 year + 30 days around closure reaches 97% on all three |
| True links inside 7 days of closure | 87.6% / 74.7% / 87.5% | same | |
| GPT-5.1 cost | "$128.10 USD in total, or approximately $0.004 USD per issue" | 41,203 test issues, batch API at 50% discount | latency not stated; Qwen3-32B hardware not stated |
| RCLinker / cross-encoder training | under an hour to a few hours | | |
| LinkAnchor mean Hit@1 | 0.8632 (std 0.0532) | 6 Apache Jira projects, 56,000+ issues | baselines EasyLink 0.6118, EALink 0.5390 at Hit@1 |
| LinkAnchor Hit@1 vs baselines Hit@10 | 0.8632 vs EasyLink 0.79075, EALink 0.7633 | | asymmetric comparison; EasyLink here is far weaker than in 2605.00447 |
| LinkAnchor ablation | comments removed: 17% drop; codebase removed: 4%; both: 21% | | |
| LinkAnchor post-cutoff | mean Hit@1 0.89 (Python 0.93, Go 0.85) | 120 GitHub issues resolved after Oct 2023 | the only leakage-controlled slice |
| LinkAnchor cost and latency | 23.599 s, 115,295.73 tokens, $0.0101 per issue | range 9.983 s / $0.0037 to 41.537 s / $0.0174 | |
| LinkAnchor failure causes | non-determinism and hallucination 78%, misleading information 35%, structural irregularities 23%, noisy data 4% (overlapping) | 363 sampled failures | |

Judge shared with system: not applicable (exact match against mined ground truth). The two papers' text and tables agree on the points checked. The paper's own wording: classic rerankers "which leverage textual and metadata features can perform competitively with more complex techniques, while some models, such as Hybrid-Linker, may degrade reranking quality".

## Mechanism details you could implement

- Candidate generation: a dense retriever (all-MiniLM-L12-v2) over commit messages, filtered to a window of issue creation to closure plus 30 days, keeping the top 20.
- Rerank: a random forest on textual similarity and metadata features (RCLinker-style: author overlap, time gap, file overlap). Or a MiniLM cross-encoder trained on our own mined links, where commit messages with issue keys give free labels.
- Escalate only low-margin cases to a large LLM or an agent that reads issue comments. LinkAnchor shows comments are the biggest single signal.
- Strip issue keys before training, and split by time, or the model learns to read the key.

## Limitations, caveats, counter-evidence

- Neither paper calibrates a confidence or threshold. Both output a ranking or a single commit, so there is no "no link" decision and no abstention (inference: our graph needs a confidence-scored link, not top-1).
- Reranking was evaluated only at K=20, so there is no data on how rerankers degrade as candidate lists grow. This is relevant to the ordinal and list-length biases reported for System One models (N-20260930-01).
- Pretraining contamination: GPT-5.1 and Qwen may have seen these public Apache repositories. Only LinkAnchor's 120-issue post-cutoff slice is protected.
- Open-source Jira and commit data only. There are no pull requests, design documents or tests, and no multi-commit or partial implementations (LinkAnchor notes 46% of issues have several resolving commits).
- No System One decision model (Jev or open-weight) was tested.

## Takeaways for tuning a memory stack

- For the IMPLEMENTS link, start with retrieval inside a time window, then a cheap trained reranker. A frontier LLM buys little over a random forest here (P@1 within 0.02), and 7B to 8B generative rerankers lose 0.2 to 0.3.
- A typed decision model has to beat RCLinker-class baselines on our own data, not only an LLM. This is the alternative the R9 thesis requires us to name.
- Ingest ticket comments as first-class content, because they carry most of the linking signal.

## Open questions

- Does a System One model scoring each (ticket, commit) pair as a `noul` question match RCLinker's P@1 and also give a usable "no link" threshold?
- How well does this transfer to PR-level links and to design-section-to-PR links, where no mined ground truth exists?
