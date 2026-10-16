---
schema_version: 1
artifact_id: N-SURVEY-20260929-07
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2504.15427
input_refs: []
pillar_primary: R10
pillar_secondary: [R2, R6]
memory_stage: staleness
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 4
  control: 3
  independence: 4
  reproducibility: 2
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2504.15427
secondary_sources:
  - https://arxiv.org/abs/2305.16591
  - https://arxiv.org/abs/2609.07375
found_via: survey
claim_cluster: existing-trace-links-invalid-or-decayed-and-validation
---

# Existing trace links are often wrong or dead: TVR link validation (arXiv 2504.15427), with link decay in commit messages (arXiv 2305.16591) and ADR mining (arXiv 2609.07375)

- **URL:** https://arxiv.org/abs/2504.15427 (read: html v5; replication package cited, URL not captured). Companions: https://arxiv.org/abs/2305.16591 (data https://doi.org/10.5281/zenodo.7536500), https://arxiv.org/abs/2609.07375 (code https://github.com/tommantonela/ADRminer)
- **Type:** paper (three papers)
- **Author / org:** Feifei Niu, Rongqi Pan, Lionel C. Briand, Hanyang Hu (TVR); Tao Xiao, Sebastian Baltes, Hideaki Hata, Christoph Treude and others (Empirical Software Engineering 28, 91, 2023); Nicolas Miccio Palermo, Antonela Tommasel, J. Andres Diaz-Pace (ADR mining)
- **Date:** TVR v1 2025-04-21, v5 2026-07-01; 2023-05-26; 2026-09-07
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R10 question 2 (link maintenance under change) and question 3 (decision records)
- **Relevance to a memory stack:** high for the PDLC layer. The pdlc-memory-layer draft gives every trace link a confidence but has no step that re-checks a link once written, and it plans to seed links from references already in tools. These papers measure how many such links are wrong, how many rot, and what it takes to detect a bad one.

## TL;DR
- In one automotive project, 219 of 2,132 human-maintained stakeholder-to-system requirement links (about 10%) were invalid (annotation kappa about 0.962).
- Zero-shot Claude 3.5 Sonnet found invalid links poorly (invalid-class F1 29.45%); with 3 retrieved valid and 3 retrieved invalid labelled examples (TVR) it reached 94.06% invalid-F1 and 98.87% accuracy. Few-shot with 16 fixed examples: 86.89%. The prompting method mattered more than the model.
- TVR's 24 errors were all classified correctly by the plain retrieval baseline (disjoint errors), which suggests an ensemble.
- Recovery: rules cut 30,598 candidate pairs to 1,919; 502 missing links were proposed at 85.50% correctness.
- Link decay at scale: of 6,667,207 distinct links in 18,201,165 commit messages from 23,110 repositories, 70% were inaccessible; github.com links 8%; svn.apache.org 96%. 61% of referenced Stack Overflow threads changed after being referenced.
- ADRs as artifacts: in about 4,300 ADRs from about 550 repositories, "Considered Options" is absent or misplaced in most, and an LLM classifier agreed with humans only 46% to 66% of the time.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Invalid share of existing links | 219 / 2,132 | | one automotive project | single industrial project, data not public |
| Zero-shot, Claude 3.5 Sonnet | acc 79.55%, invalid-F1 29.45%, macro-F1 58.75% | | TVR Table 1 | |
| Chain of thought | acc 76.31%, invalid-F1 42.29% | | same | |
| Few-shot, 16 examples | acc 97.47%, invalid-F1 86.89%, macro-F1 92.75% | | same | |
| Self-consistency | acc 97.61%, invalid-F1 87.15% | | same | |
| TVR (RAG, 3 valid + 3 invalid retrieved) | acc 98.87%, valid-F1 99.38%, invalid-F1 94.06%, macro-F1 96.72% | LiSSA-KISS 74.77 / 53.81; TF-IDF 78.94 / 49.40; SentenceBERT 86.30 / 57.82 (acc / macro-F1) | leave-one-out, temperature 0 | 13 models compared; per-model numbers for small models (Llama 3 8B, Mistral 7B, Claude 3 Haiku) not captured |
| Robustness, all variations | acc 97.13%, macro-F1 90.86% | | TVR Table 2 | worst variation 92.59% |
| Missing-link recovery | 502 proposed at 85.50% correct (kappa about 0.92) | | 30,598 to 1,919 by rules | rules do not transfer |
| Distinct links decayed | 70% (4,659,236 / 6,667,207) | | HTTP 2xx check | GitHub only |
| github.com links decayed | 8% (33,398 / 405,784) | svn.apache.org 96% | | |
| Same-repository github.com link targets | root 46.4%, issues 26.6%, PRs 20.3% | | 33% of github.com links | |
| Referenced content later changed | 61% of 361 Stack Overflow threads edited; median 2 edits | | | |
| ADR LLM classification agreement | 46% to 66% | | 200 hand-annotated ADRs, "GPT-4-mini" as extracted (model name unverified) | kappa not captured |

## Mechanism details you could implement
- Link validation prompt with retrieved labelled neighbours: embed the (source, target) pair, retrieve the 3 most similar valid and 3 most similar invalid labelled links, ask for valid/invalid at temperature 0 (Amazon Titan embeddings with FAISS in the paper).
- Keep a separate cheap retrieval-only classifier: its errors did not overlap with the LLM's.

## Limitations, caveats, counter-evidence
- TVR is a single project, leave-one-out, with binary outputs only; no calibration; cost and latency not captured in my read.
- Link decay counts URL reachability, not whether the target still says what it said; internal issue and PR links on one platform decay far less (8%).
- The ADR paper does not report supersession or ADR-to-ADR link frequencies in what I read.

## Takeaways for tuning a memory stack
- Links imported from tools are not gold: plan for roughly one in ten being wrong (TVR) on top of the 13.6% PR-issue misalignment already on the bus (N-SURVEY-20260928-14).
- A link needs a re-validation event when either end changes; validation works well only with labelled examples of bad links, so the graph should keep rejected links as negatives rather than delete them.
- Anchor claims about a decision to the ADR's actual text, not to its template section; sections are often misplaced.

## Open questions
- What fraction of IMPLEMENTS and VERIFIES links in a real repository stop being true after the linked code is edited, and how quickly?
- Can Jev with retrieved labelled neighbours match TVR's invalid-F1?
