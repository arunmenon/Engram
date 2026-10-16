---
schema_version: 1
artifact_id: N-SURVEY-20260929-06
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2607.23610
input_refs: []
pillar_primary: R10
pillar_secondary: [R9, R6]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 4
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2607.23610
secondary_sources:
  - https://arxiv.org/abs/2509.05585
  - https://arxiv.org/abs/2604.22432
  - https://arxiv.org/abs/2606.11834
  - https://arxiv.org/abs/2608.15726
found_via: survey
claim_cluster: cheap-ranker-with-metadata-vs-llm-for-trace-links
---

# Deciding trace links without a large model: LinkRank (arXiv 2607.23610), with NL-PL traceability (2509.05585), R2Code (2604.22432) and requirements quality (2606.11834, 2608.15726)

- **URL:** https://arxiv.org/abs/2607.23610 (code https://github.com/merealone2516/LinkRank). Companions: https://arxiv.org/abs/2509.05585 (code https://github.com/Zou-Zhiyuan/NL-PL-TLR), https://arxiv.org/abs/2604.22432 (no code), https://arxiv.org/abs/2606.11834 (replication https://github.com/JulianFrattini/rq4tlr), https://arxiv.org/abs/2608.15726 (abstract only)
- **Type:** paper (five papers, one claim cluster)
- **Author / org:** Abhishek Kumar, Tuhin Mondal, Partha Pratim Das, Partha Pratim Chakrabarti (LinkRank); Zhiyuan Zou, Bangchao Wang, Peng Liang, Tingting Bi, Huan Jin (2509.05585); Yifei Wang, Jacky Keung and others (R2Code, IEEE COMPSAC 2026); Tobias Hey (KIT), Julian Frattini (Chalmers) (IEEE RE 2026)
- **Date:** 2026-07-26; 2025-09-06; 2026-04-24; 2026-06-10; 2026-08-16
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R10 question 1 (link accuracy; VERIFIES) and the priority 3 slice "a System One model deciding the links"
- **Relevance to a memory stack:** high. N-SURVEY-20260928-14 established what frontier LLM checkers cost per IMPLEMENTS link. This cluster shows a cheaper arm that nobody on our side has considered: a learning-to-rank model over text similarity plus repository metadata, which beat GPT-4o and GPT-OSS-120B agents.

## TL;DR
- Ticket-to-commit (IMPLEMENTS, one-to-many): LinkRank, a LightGBM LambdaMART over 17 features (TF-IDF+SVD, BM25, SBERT all-mpnet-base-v2 about 110M, and 6 metadata features such as time proximity, diff size, file overlap), averaged F1 73.17 with K known against 48.39 for LinkAnchor (a GPT-4o-mini agent adapted to GPT-OSS-120B) and 35.88 for EasyLink (SBERT plus GPT-4o rerank). Test time 19.6 min vs 421 min.
- Metadata is the biggest single contributor: on PyTorch, all features 76.38 F1, SBERT only 44.69, metadata only 38.73, SBERT+metadata 64.84; "Removing metadata...leads to the largest performance drop."
- Requirement-to-code: a small supervised RoBERTa+GraphCodeBERT model (HGT-All, F1 0.7155) beat plain Gemini 2.5 Pro (0.5874); Gemini needed added code dependencies, feedback and decomposition to reach 0.7471 (2509.05585; tables disagree, 0.6383 vs 0.7471).
- R2Code with DeepSeek-V3.1-Terminus reached average F1 0.7313 vs 0.6812 best baseline over five classic datasets at $0.2472 per true positive on iTrust; BM25 got about 84% of its F1 on iTrust for $0.
- Requirements text quality moves results: on eTour a GPT-4o pipeline (LiSSA) scored F1 0.526 vs 0.548 for the non-LLM FTLR; specific defects (no leading noun phrase, length, anaphora, negatives, scattered requirements) hurt; normalising requirements helps ambiguous ones and hurts good ones (2608.15726).
- VERIFIES links: no 2024 to 2026 paper found that measures model accuracy on test-to-code or test-to-requirement links. 2509.05585 shows textual similarity separates true from false test-to-code links best of all pair types (difference ratio +885.19%) and requirement-to-test worst (+86.00%).

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| LinkRank F1, K known | 73.17 | LinkAnchor 48.39, EasyLink 35.88, MPLinker 23.96, EALink 18.52 | 6 projects (Beam, DataFusion, Dubbo, Iceberg, MXNet, PyTorch), 3,103 issues, 7,688 commits, pool +-365 days, pos:neg 1:65 to 1:410 | abstract says 74.54; table 73.17 |
| LinkRank F1, K unknown, ABS stop | 65.94 | LinkAnchor 59.12, EasyLink 44.71 | Table 5 | abstract 68.84 |
| LinkRank F1, K unknown, REL stop | 62.19 | LinkAnchor 40.72, EasyLink 45.35 | Table 5 | abstract 67.02 |
| LinkRank MRR / NDCG@K | 87.19 / 74.87 | LinkAnchor MRR 50.75 | Table 6 | Wilcoxon p=0.031, Cliff's delta 1.00 |
| Test time | 19.6 min | LinkAnchor 421, EasyLink 58.0, MPLinker 83.0, EALink 99.0 | | training 164.1 min |
| ABS threshold | best around 0.8 to 0.9 on min-max-normalised scores | | per-issue pool | no calibration |
| Req-to-code F1 (2509.05585) | HGT-All 0.7155 | Gemini 2.5 Pro plain 0.5874; Gemini-All 0.7471 (T9) or 0.6383 (T8) | 12 projects | tables disagree |
| Textual separability (2509.05585 T3) | test-code +885.19%, issue-commit +465.19%, req-code +93.86%, req-test +86.00% | | 99 projects from 50 studies | avg F1 column repeats 0.5602 for two rows; unverified |
| R2Code avg F1 | 0.7313 | best baseline 0.6812 | iTrust, eTour, SMOS, eANCI, RETRO.NET | TP column in cost table inconsistent with recall |
| R2Code cost, iTrust | $285.79, $0.2472 per TP, 987.3 s | RAG+LLM $463.16; BM25 $0, F1 0.6158 | Table VI | |
| LiSSA GPT-4o vs FTLR, eTour F1 | 0.526 | 0.548 | 2606.11834 T3 | iTrust 0.276 vs 0.238 |

## Mechanism details you could implement
- Candidate pool per ticket: every commit within +-365 days; features: TF-IDF+SVD cosine, BM25, SBERT cosine, time proximity, diff size, file overlap with files named in the ticket, and others; LambdaMART ranking; stop by absolute threshold on normalised score (about 0.8 to 0.9) or relative to the top score.
- Test-to-code heuristics: naming conventions and "last call before assert".
- R2Code confidence: the LLM explains each link, the explanation's consistency with the requirement is scored 0 to 1, threshold 0.7; no calibration reported.

## Limitations, caveats, counter-evidence
- LinkRank gold links come from developer issue references, which the authors call "often inconsistent or incomplete"; large Apache and PyTorch projects only; K at most 7.
- Classic traceability datasets (iTrust, eTour) are old, small and differ in granularity, so F1 is not comparable across papers (iTrust F1 0.24 in 2606.11834 vs 0.73 in R2Code).
- No paper here reports calibrated link confidence (ECE or reliability).

## Takeaways for tuning a memory stack
- Before paying a model per candidate link, rank candidates with cheap features we already hold in the event ledger: time proximity, file overlap, diff size, lexical similarity. A System One model or LLM then decides only the top few.
- VERIFIES links from tests to code are mostly recoverable by naming and call-site rules; requirement-to-test links are the hardest and the least studied.
- Requirement text quality should be a stratum in our PDLC benchmark: link accuracy differs by defect type.

## Open questions
- Does a metadata ranker plus one Jev call on the top 5 match an LLM checker on SpecMine PR-to-requirement pairs?
