---
schema_version: 1
artifact_id: N-20260928-27
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:06:21Z
input_refs: [{"artifact_id": "post:2104552085987709354", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:varops.com/acropolis
claim_cluster: url:varops.com/acropolis
feeds: ["memory"]
primary_source: https://varops.com/acropolis/
source_commit: v1.0 (github.com/varops/acropolis-research b391c09f866d5e4d76b305498705e7c42e5c5278; harness acropolis-varys 93ad8b6c75d11e3679b9e7fe68c86a356fe58ccc)
strength: paper-ablated
pillar_primary: R6
pillar_secondary: ["R9", "R3", "R4"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["claims-with-evidence", "model-seat-placement", "open-weight-local-model", "escalation-on-refusal", "agentic-answer-loop", "coverage-states", "abstention"], "workload": ["chat-memory", "long-context-1m"], "lifecycle_stage": ["ingestion", "reranking", "assembly"], "cross_cutting": ["self-hosting", "per-question-reports", "noise-floor", "corrections-log", "judge-shares-answer-model", "cost-per-question"]}
evidence_grade: {"directness": "high: technical report with per-question run reports for every September row and placement tables in text", "control": "medium: one harness, same brains, same judge across placements, paired analysis rule; but September rows are single runs, own-everything is best-of-two configs, and the frontier judge is the frontier answerer", "independence": "low: vendor evaluating its own product; no third party re-ran it", "reproducibility": "medium: harness tag, commits, model pins, dataset hashes and 2,539 reports published; August headline figures only partially retained; dataset text redacted to hashes", "applicability": "medium: directly tests self-hosted open-weight seats, but on conversational benchmarks, not engineering artifacts"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["A 31B open-weight extractor building the memory record costs 1 to 2 points on LongMemEval-S, LoCoMo and BEAM 100K when a frontier model reads (single runs); the loss from local models is in the reading seats and grows with context length", "Renting only the answer seat recovers 96 to 99 percent of all-frontier accuracy on these benchmarks"]}
claim_correction: The post and site call the frontier model unnamed; the repo pins it as gemini-3.7-flash, which is also the judge for every row; the September placement rows are single runs, "own everything" is the better of two local configurations, the website's frontier numbers (89.2/90.5/91.6) differ from the report's reference row (91.4) and are only partially retained, and "BEAM 100K->1M" means the local comparison was run on BEAM 100K only (1M is frontier-only).
---

# VarOps Acropolis "Own the Knowledge, Rent the Thinking" (Technical Report 01): fully local vs local+frontier vs all-frontier on LongMemEval-S, LoCoMo and BEAM

- **URL:** https://varops.com/acropolis/ ; report and reports bundle https://github.com/varops/acropolis-research ; DOI 10.5281/zenodo.22775192
- **Type:** vendor technical report (paper with methodology appendix) plus results repo
- **Author / org:** Ran Aroussi, VarOps LLC
- **Date:** Technical Report 01, v1.0, September 2026 (site says September 15, 2026)
- **Retrieved:** 2026-09-28; shallow clone at `repos/acropolis-research`, commit `b391c09f866d5e4d76b305498705e7c42e5c5278` (2026-09-16 09:51:19 +0100, "README: DOI and license badges"). Read: README.md, paper/README.md (Sections 1 to 2, Figure 2 tables), paper/methodology.md (A.1 to A.3, A.6 to A.14), paper/figures/table-2-head-to-head.md, reproduction/README.md, manifests (grep). Report JSONs not opened individually. No code run.
- **Cited by evidence:** https://x.com/aroussi/status/2104552085987709354 (@aroussi, the report's author, feed memory, 2026-09-28, reply to @boardyai @ainativedev)
- **Relevance to a memory stack:** high for CTO priority 2 (self-hosting: keeping memory text in-house with an open-weight model in the extractor and reading seats) and priority 4 (benchmark methodology). Not a System One decision model: Gemma-4-31B is a general LLM.

## TL;DR
- Three seats: understanding (extractor builds a claims record), retrieval (rewrite + rerank), answer. Local = gemma-4-31b-it on one NVIDIA H200 via vLLM with local nomic embeddings; frontier = gemini-3.7-flash (pinned in reproduction/README.md; the website only says "frontier"); judge = gemini-3.7-flash for every row, with gemma-4-31b-it re-judging for agreement.
- Placement table (paper/README.md, Figure 2): all-frontier reference LongMemEval-S 91.4, LoCoMo 81.8, BEAM 100K 56.2 strict / 67.5 protocol. Own everything 87.4 / 76.3 / 47.2 / 57.3. Rent the thinking (frontier answer seat only) 90.0 / 79.3 / 53.8 / 66.4. Rent only on refusal 88.6 / 80.5 / 48.5 (27, 40 and 8 questions sent out).
- Extractor seat: local-built brains score within 1 to 2 points once frontier reads (89.6 vs 91.4, 81.8 vs 81.8, 55.2 vs 56.2); the loss is in reading seats and grows with length (2.2, 5.5, 8.0 points).
- Claim correction: frontier model is named in the repo (gemini-3.7-flash) and is also the judge; September rows are single runs; "own everything" is best-of-two; site's LongMemEval 89.2 / 90.5 / 91.6 are August figures only partially retained; the local comparison uses BEAM 100K, not 1M.
- No mem0, Hindsight, Letta or Zep numbers; one unnamed "Vendor X" (LongMemEval-S 98.0, LoCoMo 92.5, BEAM 1M 64.1) is cited from its own publications, and the report argues 98.0 is incompatible with the official abstention rule (a never-refuse system caps at 94.0).

## What it claims / describes
**System.** Acropolis holds "claims rather than chunks": each claim carries evidence, time of validity and source; "nothing is silently overwritten"; graphs, vectors and summaries are "disposable projections" of a canonical record. Components (reproduction/README.md): Parthenon (the record), Eunomia (identity), Pythia (answering loop), harness `varys bench` in acropolis-varys.

**Harness** (methodology A.3). `varys bench ingest` provisions one fresh brain per conversation, sends every message through the production signed-intake door, runs triage, extraction, claim proposal, validation. `varys bench ask` retrieves against that brain, composes under a named contract, scores. Retrieval reads projections (lexical, semantic, graph, synopsis).

**Configurations** (A.7). Core: one composition call under contract `assembly_v2`, with coverage states (answered, searched-and-empty, outside-the-ontology); reply `UNANSWERABLE` when material does not cover the question (an instruction, not a hard gate). Agentic (Pythia): bounded loop with tools ask, compute, extract and a mandatory `asked_at` anchor. Rent on refusal: derived by joining two stored runs on question id; local answer kept where it answered, frontier answer taken where local declined an answerable question; no re-asking. Governed composite (BEAM 1M only): deterministic routing, direct pass's refusals and contradiction declarations ship (150 of 700 rows), frontier loop answers the rest.

**Scoring** (A.6). LongMemEval and LoCoMo: fixed one-word yes/no judge vs gold, precision-first; answer starting `unanswerable` = abstention, wrong on answerable. BEAM: per-item rubric judge; `event_ordering` = tau_b_norm x F1. Retrieval scored by document identity against evidence annotations.

**Noise floor** (A.8). Two full-700 BEAM runs of byte-identical code differ by plus or minus 2 to 5 points per category and about 1 point overall. "A category delta under about 5 points on a single run is not reported as a result." Paired gains/losses required. "The September rows are single full runs." Bands where repeats exist: LongMemEval core 89.2 (88.4 to 89.6), agentic 90.5 (90.4 to 90.6, four runs), BEAM core 60.2 (59.0 to 60.6).

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| LongMemEval-S accuracy: own everything / rent thinking / rent on refusal / frontier on local brains | 87.4 / 90.0 / 88.6 / 89.6 | reference 91.4 | n=500 (30 traps), paper/README.md Figure 2 table | single runs; judge gemini-3.7-flash; own-everything = single call (loop 86.0) |
| LoCoMo accuracy, same order | 76.3 / 79.3 / 80.5 / 81.8 | reference 81.8 | n=435 (88 unanswerable) | own-everything = loop (single call 73.6) |
| BEAM 100K strict, same order | 47.2 / 53.8 / 48.5 / 55.2 | reference 56.2 | n=400 (40 unanswerable) | own-everything = loop (single call 42.0); abilities n=40 |
| BEAM 100K own protocol: own / rent thinking / frontier on local brains | 57.3 / 66.4 / 66.8 | reference 67.5 | same | rubric fraction |
| share of all-frontier | LME 95.6% / 98.5% / 96.9%; LoCoMo 93.3% / 96.9% / 98.4%; BEAM strict 84.0% / 95.7% / 86.3%; BEAM protocol 84.9% / 98.4% | 100% | paper/README.md | "84 to 96" and "96 to 99" headline ranges come from here |
| questions sent out on refusal | 27 of 500; 40 of 435; 8 of 400 | | same | |
| local rented answer + escalation on its refusals | 91.4 on LongMemEval, 21 escalated | | paper/README.md | equals the reference |
| retrieval Hit@5, local vs published brains | 99.2 vs 99.0 (LME); 91.2 vs 90.7 (LoCoMo); 39.2 vs 40.6 (BEAM) | | paper/README.md | frontier reads both |
| retrieval, website | LME Hit@10 99.8%, Hit@5 99.0%, MRR 0.985; LoCoMo Hit@10 93.1%, Hit@5 90.7%, MRR 0.823; BEAM 100K Hit@10 49.6%, Hit@5 40.6%, MRR 0.315; BEAM 1M Hit@10 44.0%, Hit@5 35.84%, MRR 0.2546 | | varops.com/acropolis | "99.8% ... is not an answering score" |
| website frontier LongMemEval | core 89.2, agentic 90.5, agentic+escalation 91.6 | | August runs | partially retained per question (A.12) |
| BEAM 1M governed composite | 61.1 overall; abstention 75.7, contradiction 62.1, extraction 71.8, summarization 56.4 | core 60.2 (band 59.0 to 60.6) | about 700 questions, frontier only | cross-formula caveat (A.6); composite stated as "+3.5 paired" in Table 2 |
| Vendor X (unnamed), own published figures | LME 98.0; LoCoMo 92.5; BEAM 1M 64.1 | Acropolis core 89.2 / 81.8 / 60.2 | table-2-head-to-head.md | cross-protocol; never-refuse; not re-run; source page not found in the published manifests |
| never-refuse probe | all 500: 87.2 vs 88.0; traps refused 0 vs 29 of 30; answerable-only 92.8 vs 87.4 | assembly_v2 | A.11, frontier single call over local brains | removing refusal gained 29, lost 33 |
| judge agreement gemma vs gemini | 98.7 to 99.2% on 2,223 LME answers; 95.2% on 1,531 LoCoMo answers | | A.6 | local judge stricter by 0.4 to 2.8 points, preserves orderings |
| fabrication on traps | 1 in 120 trap rows (4 banked agentic runs) | | A.6 | manually classified; not a general hallucination rate |
| extractor swap (gemini-3.7-flash for gpt-4.1-mini) | core 87.4 vs 89.2; agentic 89.2 vs 90.5 | | A.9 2026-09-04 | called a tie (paired 15/16) |
| cross-encoder reranker vs local LLM ranking | 28 points below on the same LoCoMo pool | | paper/README.md | site: Hit@5 52.5 vs 80.6 |
| cost | ingest $8.24 per 35M-token corpus; $0.0021 per claim; $0.0037 per question; LongMemEval frontier ingest about $3, ask pass about $7 | | website; reproduction/README.md | |
| latency, BEAM 100K local | median 746 (single) to 917 (loop) s per question, 14 conversations sharing one GPU; frontier 54 to 60 s | | reproduction/README.md | shared-box throughput, not single-user latency; website says 12 to 15 min |

## Mechanism details you could implement
- Seat separation with a question-sized evidence envelope: only one question's claims and excerpts (a few thousand tokens) go to a rented model; the envelope is stored with the answer (supports our replay goal, B1-style).
- Escalation on refusal as a join of two runs: keep the local answer unless it declined an answerable question; report the number escalated.
- Coverage state in the context envelope: answered / searched-and-empty / outside-the-ontology.
- Retrieval budgets: 100 lexical / 300 semantic / 100 rerank-pool candidates (120 on BEAM 100K); observation excerpts 2,000 characters (raising from 500 moved LongMemEval 83.4 -> 89, A.9 2026-08-23).
- Extractor flags from the harness command: `--extractor-max-output-tokens 1500 --confidence-floor 0.3 --extractor-profile episodic`.
- Local serving: vLLM, bf16 weights, fp8 KV cache, thinking enabled, `--max-model-len 65536` (131072 for BEAM 100K).
- Evaluation rules to copy: paired gains/losses; no category claims under about 5 points from one run; no half-set previews; a dated corrections log; per-report dataset sha256 and harness commit with dirty flag.

## Limitations, caveats, counter-evidence
- Report's own list (A.14 and site): fixtures, not live organizations; all three datasets are conversational, "None of the three datasets is enterprise-shaped"; one open-weight model and one GPU class; "A second open-weight model in the reading seats" not done; supersession tests on authored corpora not done.
- Judge = frontier answerer (gemini-3.7-flash) in frontier rows; the gemma re-judge agreement (98.7 to 99.2% LME) mitigates but the co-judge is the local answerer in local rows (inference: each judge shares a model with one arm).
- September rows are single runs; the report's own noise floor (about 1 point overall, 2 to 5 per category on BEAM) means the 87.4 vs 90.0 vs 88.6 LongMemEval differences are near noise; paired views are described but not all printed.
- "Own everything" takes the better of single call and loop per benchmark: a small selection effect in the local row's favour.
- The website's "BEAM 100K->1M" framing: local placement was measured on BEAM 100K only; BEAM 1M is frontier-only and "the two are not compared".
- August headline figures (89.2, 90.5, 91.6; BEAM 1M 60.2 and composite) are not auditable per question from the bundle (shard files overwritten, one gate run lost).
- A.11 says the bundle manifest records Vendor X's source page; no such entry was found in `reproduction/manifests/manifest.md` or `manifest.json` (it may be in the unredacted bundle, not published).
- Local latency is minutes per question on a shared GPU, which rules out interactive use at that setting.
- Vendor evaluating its own product; no third party has re-run it.
- Instruction-bearing content: the web page has "Discuss with: OpenAI | Claude | Gemini | Grok | Perplexity" links with prefilled query parameters that send a prompt about Acropolis to AI chat services. Not followed. No instructions aimed at this agent were found in the repo files grepped.

## Takeaways for tuning a memory stack
- For priority 2: the extractor (write) seat looks like the safest place to self-host; this report found 1 to 2 points lost when a 31B open-weight model builds the record and a frontier model reads. The reading seats lose more, and more with longer context (2.2 / 5.5 / 8.0 points).
- Cross-encoders are a weak rerank baseline over long excerpts here (28 points below an LLM ranker on LoCoMo); ranking long excerpts is "a reading job". Relevant to our reranking-stage arms.
- Refusal posture moves points between abstention and coverage rather than creating them (three BEAM contract variants 56.4 / 57.4 / 57.1); report answerable-only and trap metrics separately in our PDLC benchmark.
- Excerpt length at assembly mattered more than the model swap (500 -> 2,000 characters: 83.4 -> 89).

## Open questions
- Same placement result with a different open-weight model (Qwen, Llama class) or a smaller one (a System One model in the rerank seat)?
- Paired gains/losses for the September placement rows: are 87.4 vs 90.0 and 88.6 vs 90.0 outside noise?
- Does the extractor-seat parity hold on engineering artifacts (design docs, PRs, tickets), where claims are denser than chat?
- Who is Vendor X and where is the source page recorded?

## Grading and labels
- Directness: high. Tables in text with per-question reports.
- Control: medium. Same harness, brains and judge across placements; single runs; best-of-two local row; judge shares a model with the frontier answerer.
- Independence: low. Vendor-authored; the post is by the author.
- Reproducibility: medium. Commits, pins, hashes, 2,539 reports; August figures partial; datasets redacted to hashes (by licence).
- Applicability: medium. Tests self-hosted seats, our priority 2 question, but on chat benchmarks.
- Pillars: R6 primary (a multi-benchmark evaluation claim); R9 secondary (self-hosted model per memory stage, although not a System One model); R3 secondary (retrieval budgets, reranking); R4 secondary (abstention and escalation on refusal).
- Stage: evaluation (the claim spans ingestion, reranking and answer seats).
- Tags: model-seat placement, open-weight local model, escalation on refusal, coverage states, abstention, noise floor, corrections log, self-hosting.
- Priority: 4 by match terms; also directly relevant to priority 2 (self-host, open weight), which the frontmatter cannot carry as a second value.
- B20 supports: the post's framing narrows on a primary read (single runs, frontier model named and also judge, 1M is frontier-only).
- Would create: "A 31B open-weight extractor costs 1 to 2 points when a frontier model reads; local loss is in the reading seats and grows with length", grade lead.
- Would create: "Renting only the answer seat recovers 96 to 99% of all-frontier accuracy on chat memory benchmarks", grade lead.
- Contradiction: none. No mem0 or Hindsight numbers to compare with the Redis, Atlaso or DaiDocs notes; answer models differ (gemini-3.7-flash vs GPT-4o or Qwen 3.5-9B), so LongMemEval-S levels across these notes are not comparable.

## Origin chain
- Post https://x.com/aroussi/status/2104552085987709354 (@aroussi, author) -> t.co -> https://varops.com/acropolis/ -> "Primary Sources" -> https://github.com/varops/acropolis-research (paper/README.md Figure 2 tables; paper/methodology.md A.6, A.7, A.8, A.9, A.11, A.12, A.14; reproduction/README.md model seats and commands) and Zenodo DOI 10.5281/zenodo.22775192 (not fetched).
- Independence: single author and vendor. Shares LongMemEval-S with the Redis, Atlaso and DaiDocs notes and LoCoMo with Atlaso; shares no answer model or judge with them. Dataset files pinned by sha256 (`longmemeval_s.json` 08d8dad4...; DaiDocs used the cleaned variant `longmemeval_s_cleaned.json`, so the files differ).
