---
schema_version: 1
artifact_id: N-SURVEY-20260929-01
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2609.34227
input_refs: []
pillar_primary: R9
pillar_secondary: [R3, R2]
memory_stage: ingestion
priority: 1
beliefs_affected:
  supports: [B7, B11]
  contradicts: []
evidence:
  directness: 5
  control: 4
  independence: 3
  reproducibility: 5
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.34227
found_via: survey
claim_cluster: raw-turns-plus-typed-selection-vs-llm-extraction
---

# When Does Selection Replace Extraction? A Pre-Registered Test of Agent Memory with a Typed Decision Model (arXiv 2609.34227)

- **URL:** https://arxiv.org/abs/2609.34227 (read: https://arxiv.org/html/2609.34227v1)
- **Type:** paper (pre-registered, code pinned by tag)
- **Author / org:** Rishabh Sharma, Rishika Lall (independent researchers)
- **Date:** 2026-09-28
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 question 2 (System One at the ingestion stage)
- **Relevance to a memory stack:** high. It is the first pre-registered, cost-accounted test of the ingestion choice "extract facts with an LLM at write time" against "store raw turns and let a System One model select at read time", with Jev as the selector.

Name clash, flag only: the authors' repository is github.com/ris3abh/Engram and their extraction system is called "engram v2". Nothing in the paper links it to our company; treat it as an unrelated project of the same name (inference).

## TL;DR
- At matched context (about 250 tokens), raw turns plus one Jev relevance call per shortlisted turn were non-inferior to gpt-4o-mini fact extraction plus Jev on LoCoMo: 77.0% vs 77.5% (judge), difference -0.5, one-sided bound -3.0 against a registered margin of -5. Human strict grading: -1.7 (bound -3.9); lenient: -2.6 (bound -4.7).
- Write cost fell from $1.865 to $0.0006 per 1,000 turns (the paper says "3,061x less to write"); read latency p50 273 ms vs 816 ms for an LLM reranker.
- The advantage is a small-budget effect: rerank gain over cosine was +17.4 points at k=3 on LoCoMo but only +1.5 at k=20. At k=20, extraction won clearly (engram v2 82.4 vs Jev 77.6).
- The rerank step drops all evidence for 10.4% of questions (22.7% of temporal, 31.4% of open-domain) and lowered correct abstention on adversarial questions at k=3 (54.1 vs 63.6 for plain cosine).
- Judge, answerer, LLM reranker and extractor are all gpt-4o-mini; human audit by the first author on discordant items only.

## What it claims / describes
Pipeline under test ("Turns+Jev"): embed every raw turn (text-embedding-3-small); at read time take a 30-turn cosine shortlist; ask Jev (jev-1.13.0, closed) one yes/no Noul question per shortlisted turn; keep the top k by probability; answer with gpt-4o-mini at temperature 0.

Jev question, verbatim: "Does memory help answer query?" True option: "It states or directly implies part of the answer." False option: "It is off-topic or only shares a keyword."

Arms: Turns+Jev; Turns+cosine; Turns+LLM (gpt-4o-mini listwise reranker); engram v2 (gpt-4o-mini extraction plus Jev); mem0 2.1.0; Jev-Mem (graph memory); full context; post-hoc "wide" variant (150-turn shortlist).

Data: LoCoMo held-out conversations conv-44, 47, 48, 49, 50 (3,122 turns, 778 scored questions plus 209 adversarial); LongMemEval 470 scored plus 30 abstention; exploratory replication on conv-30, 41, 42, 43 (610 questions). Every design choice was made on conv-26 only. Pre-registration: doi 10.5281/zenodo.22970745 (tag v3-frozen); amendment 10.5281/zenodo.22977848.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| H1 accuracy, judge | 77.0% | engram v2 77.5% | LoCoMo, Jev k=6 at 265 tokens vs v2 at 251 | diff -0.5, bound -3.0, CI [-3.5, +2.5] |
| H1, human strict | 76.3% | 78.0% | same | diff -1.7, bound -3.9 |
| H1, human lenient | 77.4% | 79.9% | same | diff -2.6, bound -4.7, CI [-5.1, -0.03] |
| H1 on Llama 3.3 70B answerer | 75.3 | 75.6 | same | bound -2.9 |
| S1 vs cosine, k=3 | 77.2 | 59.9 | LoCoMo | wins 152/17, Holm p 1.9e-27 |
| S3 vs mem0, k=3 | 77.2 | 68.5 | LoCoMo | Holm p 7.6e-6; mem0 routed via OpenRouter/Azure (deviation) |
| S4 vs LLM reranker (non-inferiority) | 77.2 | 77.6 | LoCoMo k=3 | bound -2.0 |
| S7 vs cosine, LongMemEval 470 q | 66.8 | 57.7 | k=3 | Holm p 7.6e-6 |
| S6 vs cosine, 70 q | 68.6 | 65.7 | LongMemEval | not significant |
| k=20, LoCoMo | Jev 77.6 (496 tok) | engram v2 82.4 (1,238 tok), mem0 78.7, Jev-Mem k=40 80.3 | Table 3 | extraction wins at larger budget |
| Full context LoCoMo | 78.3 at 23,631 tokens | | Table 3 | |
| LongMemEval knowledge-update, k=3 | Jev 77.8 | cosine 58.3 | Table 4 | |
| Write cost per 1k turns | $0.0006 | engram v2 $1.865 (LLM 1.322, Jev 0.542); mem0 $1.321; Jev-Mem $0.212 | Table 5 | list prices |
| Write latency p50 | 0.2 s | v2 2.0 to 2.1 s | Table 5 | |
| Read latency p50 / p90 | 273 / 359 ms | LLM reranker 816 / 1,107; Jev-Mem 1,329 / 1,622 | Table 5 | hardware not stated |
| Total cost per question | $0.00030 | engram v2 $0.00778 | text | does not reproduce exactly from table rows (my arithmetic about $0.00020 and $0.00764) |
| Shortlist holds all evidence | 76.9% | | 1,388 questions | multi-hop only 42.8% |
| Rerank drops all evidence | 10.4% | | same | temporal 22.7%, open-domain 31.4% |
| Wide variant (post-hoc) | 81.5% at 2,000 tokens | | 150-turn shortlist | rerank losses 0.9% |
| Adversarial abstention k=3 | Turns+Jev 54.1 | cosine 63.6, engram v2 59.8 | Table 6 | "Reranking lowered correct abstention at k=3" |

Pre-registration outcome: H1, S1 to S4 and S7 confirmed; S5, S6 not significant; a registered descriptive multi-hop expectation came out reversed (Turns+Jev 74.3 vs engram v2 72.1). No registered test failed outright.

## Mechanism details you could implement
- One Noul per candidate, neutral-to-positive option wording as quoted above; rank by P(true); keep top k by a token budget, not a probability threshold.
- Shortlist width matters more than the selector at generous budgets: the post-hoc 150-turn shortlist lifted accuracy to 81.5% by raising all-evidence recall to 91.9%.
- Store raw turns with an embedding only; no LLM at write time.

## Limitations, caveats, counter-evidence
- Chat memory (LoCoMo dialogues are LLM-generated), not engineering artifacts; categories are small.
- Same model family for judge, answerer, LLM reranker and extractor; the human grader built the systems and graded only judge-discordant items.
- engram v2 was not run on LongMemEval.
- Adversarial text untested; raw turns go into Jev's question, so injected text could steer selection (see N-SURVEY-20260928-09 on JevAdvBench).
- Results hold for the closed jev-1.13.0 only.
- At k=20 the extraction system wins by 4.8 points; the non-inferiority claim is at about 250 tokens.

## Takeaways for tuning a memory stack
- For small context budgets, raw storage plus System One selection is a credible replacement for LLM extraction at roughly 1/3,000 of the write cost. For larger budgets, extraction still adds accuracy.
- Keep the ranker away from abstention: selection reduced correct "no answer" behaviour, which supports keeping the recall gate as a separate decision (B11).
- Supports B7 (read-time curation over write-time distillation) on chat memory; says nothing yet about long structured engineering artifacts.

## Open questions
- Does the result hold when the stored unit is a PR description, ADR section or ticket rather than a chat turn?
- Would an open-weight selector (Laya, Intern-Decision, Jev-Style-2B) hold the non-inferiority margin?
