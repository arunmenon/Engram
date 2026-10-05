---
schema_version: 1
artifact_id: N-SURVEY-20260930-04
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:57:00Z
idempotency_key: note:survey:arxiv:2609.38021
input_refs: []
pillar_primary: R6
pillar_secondary: [R3, R1]
memory_stage: evaluation
priority: 4
beliefs_affected:
  supports: [B20, B19]
  contradicts: []
evidence: {directness: high, control: medium, independence: low, reproducibility: medium, applicability: medium}
strength: repo-pinned
source_url: https://arxiv.org/abs/2609.38021
found_via: survey
---

# Auditable Long-Term Memory: A Deterministic Retrieval Chain Measured at 479/475 of 500 on LongMemEval-S

- **URL:** https://arxiv.org/abs/2609.38021 (HTML v1 read: https://arxiv.org/html/2609.38021v1); evidence repository https://github.com/cjchanh/longmemeval-evidence (MIT, not cloned)
- **Type:** paper
- **Author / org:** Christopher J. Chanhnourack (Centennial Defense Systems)
- **Date:** 2026-09-29
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2609.38021.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R6 question 1 (judge integrity) and question 3 (saturation of LongMemEval)
- **Relevance to a memory stack:** high for evaluation practice. It measures the noise floor at the top of the LongMemEval-S leaderboard: run-to-run spread, judge flips on identical answers, a second judge, gold-answer defects and tool leakage.

## TL;DR
- Same system, same frozen packets, same reader, two full passes: 479/500 and 475/500. The published comparator (Chronos High) is 478/500. The author states the pair establishes "neither superiority nor equivalence".
- The official GPT-4o judge "flips three verdicts when re-scoring byte-identical pass-1 answers". A second judge (GLM-5.3) agrees on 493/500 rows (98.6 %) in each pass and scores both passes 472/500.
- Reader choice moves the score by 14 points among the four strongest readers on identical packets (465 to 479); a 30B open model scores 93/500.
- A tool-enabled reader variant leaked: in 12 pass-1 rows and 16 pass-2 rows the session made a call outside its prompt and workspace, and one web search returned "a public issue thread quoting the question's expected answer".
- One strict gold-answer defect and seven boundary cases are documented in the 500 questions.

## What it claims / describes
The system is a retrieval chain with "hybrid candidate retrieval, cross-encoder reranking, coverage-first packet compilation, and deterministic reasoning scaffolds; an LLM is used only as a replaceable final reader". Retrieval coverage: all gold sessions in the candidate pool for 468/470 answerable questions; gold-complete packets for 462/470.

Evaluation discipline described:
- A "pass" is one full run of all 500 questions through a reader and the official judge. Every configuration is run as a pair of passes.
- Every scoring run executes positive and negative judge-control verdicts against a 0.9 pass threshold (12/12 and 12/12 for the headline pair).
- A pre-committed acceptance rule rejected a verifier stage: it "recovered 3 previously-wrong rows" but "flipped 11 of 58 correct drafts to wrong" on a 60-row negative-control set, and the rule required zero control flips.
- A gold-defect dossier is kept separately and scores are also reported with those 8 rows removed.

Setup: LongMemEval-S cleaned release (September 2025), 470 answerable plus 30 abstention questions. Judge gpt-4o-2024-08-06. Headline reader Claude Opus "called through an unpinned CLI alias" (resolved after the fact to claude-opus-5 from transcripts). Reader and judge are different models. The 72 knowledge-update rows used "a substantively modified scoring prompt whose effect under the official text has not been measured".

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Headline pair, Opus reader | 479/500 and 475/500 | Chronos High 478/500 (published) | GPT-4o judge, modified knowledge-update prompt | Wilson 95 % for 479: [93.7 %, 97.2 %]; for 478: [93.4 %, 97.1 %] |
| grok-4.6-high reader, same packets | 476/500 and 474/500 | | | |
| Max-reasoning agentic variant | 461/500 and 465/500 | | tools enabled | after removing 28 leaking rows: 451/488 and 451/484 |
| With 8 dossier rows removed | Opus 474/492 and 471/492; grok 475/492 and 474/492 | | | |
| Strict abstention reading | 476 and 472 | 479 and 475 | three premise-repair answers removed | |
| Per type, pass 1 / pass 2 | single-session-assistant 56/56, 56/56; single-session-user 64/64, 63/64; knowledge-update 69/72, 70/72; preference 30/30, 28/30; temporal 123/127, 123/127; multi-session 110/121, 109/121; abstention 27/30, 25/30 | | | multi-session and abstention carry most errors |
| Judge self-consistency | 3 verdict flips on byte-identical pass-1 answers | | official judge re-run | about 0.6 % of rows |
| Second judge agreement | 493/500 (98.6 %) in each pass; second judge scores 472/500 and 472/500 | official 479 and 475 | GLM-5.3 | 5 of 7 pass-1 disagreements are official-judge-only credits on abstention rows |
| Reader spread on identical packets | Nemotron-3.5-Lightning 30B 93/500; DeepSeek V4 Pro 436; GPT-5.6 Sol 455; Kimi K3 465; GLM-5.3 471; grok-4.6-high 476; Opus 479 | | single pass each | 14 points among the four strongest |
| Build history | dense retrieval plus flat reading 452; plus chain and early scaffolds 468; plus cross-encoder rerank 473; v3.4 operators 476/474; reader upgrade to Opus 479/475 | | different readers per rung | rungs are not one-variable |
| Gold defects | 1 strict (gold says 15 weeks, the dated gap is 81 days) and 7 boundary rows | 500 questions | author audit | |
| Retrieval coverage | 468/470 gold in pool; 462/470 gold-complete packets | | | |
| Re-scoring cost | about $1.28 per full run | | GPT-4o judge | |
| Latency, tokens | not stated | | | operator context of about 59,000 to 62,000 characters per call is mentioned |

Text versus table: none found. The title's "479/475" is two passes, not two judges.

## Mechanism details you could implement
- Two-pass rule: report every configuration as a pair of full passes and treat the gap as the floor. Here the floor (4 questions) exceeds the margin to the published best (1 question).
- Judge controls in every scoring run: a fixed set of known-correct and known-wrong answers that the judge must classify with at least 0.9 pass rate, else the run is void.
- Re-judge byte-identical answers once to count judge flips; re-judge with a second model family to get agreement and the direction of disagreement.
- Pre-commit the acceptance rule for any new stage (here: zero flips on a negative-control set) before measuring it.
- Keep a gold-defect dossier and report scores with and without those rows.
- Closed-book audit: search reader transcripts for tool calls outside the workspace and for gold strings. Here 252 of 500 gold answers are shorter than 12 characters and could not be string-matched.
- Release verdicts and packets so counts can be re-derived without an API key (the repository is said to do this).

## Limitations, caveats, counter-evidence
- Stated: "Every component that moves the score" was developed against the same 500 questions. There is no held-out set.
- Stated: the headline reader lane was not closed-book. The operator context (global instruction file, memory index, hook output, MCP server instructions) went with each call and "the complete outbound requests were not retained".
- Stated: the reader was not pinned in the run receipt; the comparator used a different reader generation.
- Stated: knowledge-update rows were judged with a modified prompt; effect unmeasured.
- Single author; retrieval, rerank, packet compiler and scaffold sources are withheld. Only outputs, verdicts, scaffolds and the judge harness are released. Independence is low and the system itself cannot be re-run.
- One benchmark only.
- Counter-evidence to "the judge does not matter": on this benchmark a cross-family re-judge elsewhere (arXiv 2606.16707, as summarised by search, not read this run) reports kappa 0.89 to 0.97 and under 2 points of difference. That is consistent with the 98.6 % agreement here. The judge effect is small in absolute terms and still larger than the gaps between leading entries.

## Takeaways for tuning a memory stack
- LongMemEval-S is saturated for ranking purposes at the top. Differences under about 1 point (5 questions of 500) are inside reader variance plus judge flips. Do not use it to choose between strong configurations.
- The reader accounts for more of the score than the memory system near the top (14 points across strong readers on identical packets). Any comparison of memory arms must hold the reader fixed and pinned by snapshot id.
- Adopt the two-pass rule and judge controls in P3's replacement harness. They cost one extra run and one small control set.
- For our PDLC benchmark: plan a gold audit (this one found 8 disputable rows in 500, 1.6 %), a closed-book check, and an abstention scoring rule decided in advance, since abstention rows drew most judge disagreement.
- An agentic reader with tools lowered the score (461 and 465) and leaked. Keep tools off for benchmark readers.

## Open questions
- What is the judge flip rate on our own judge prompt and model? It bounds the smallest effect H1 to H10 can report.
- How large is the knowledge-update prompt change's effect?
- Would the ranking among memory systems survive a fixed weaker reader, where retrieval quality matters more?
