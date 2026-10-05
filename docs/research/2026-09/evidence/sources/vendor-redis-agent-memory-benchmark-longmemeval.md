---
schema_version: 1
artifact_id: N-20260928-24
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:06:21Z
input_refs: [{"artifact_id": "post:2104514094241886483", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:redis.io/resources/agent-memory-benchmark-report
claim_cluster: url:redis.io/resources/agent-memory-benchmark-report
feeds: ["memory"]
primary_source: https://redis.io/resources/agent-memory-benchmark-report/
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R3", "R2"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["hybrid-retrieval", "bm25-plus-dense", "llm-fact-extraction", "raw-plus-extracted-context", "neighbor-expansion"], "workload": ["chat-memory"], "lifecycle_stage": ["ingestion", "retrieval", "assembly"], "cross_cutting": ["reproduction", "cost-per-session", "sponsored-post", "judge-shares-answer-model"]}
evidence_grade: {"directness": "medium: vendor report reproduces several systems on one LongMemEval split, but the harness is not linked and per-type numbers are chart-only", "control": "medium: common GPT-4o answer model and one GPT-4o judge prompt across reproduced systems; single run, no intervals, managed services are black boxes", "independence": "low: Redis ranks its own strategies first; the post is paid by Redis", "reproducibility": "low: page says every reproduced number can be re-run from the harness, but no link is given; two table rows contain placeholder values", "applicability": "low: multi-session chat QA, not engineering-agent artifacts"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["Serving raw retrieved chunks and extracted facts together in one labelled context beats either alone on LongMemEval-S with GPT-4o (vendor, single run)"]}
claim_correction: Sponsored post; the 86.5% is a single unreplicated GPT-4o run judged by GPT-4o with no intervals, the harness is not linked, and the Instruct-alone and LangMem rows on the page hold placeholder values (95.4% in every cell), so the "beats either alone" claim rests on a chart only.
---

# Redis "How Redis Agent Memory stacks up": LongMemEval-S benchmark of agent memory systems (Remis + Instruct 86.5%)

- **URL:** https://redis.io/resources/agent-memory-benchmark-report/ (reached from http://fandf.co/4hdlNkg -> https://fandf.co/4hdlNkg -> redis.io with `utm_medium=paid-post`, `utm_content=m-denic-x`)
- **Type:** vendor blog / report (full web text, not gated)
- **Author / org:** Redis (no individual author line on the page)
- **Date:** Sep. 21, 2026 (page date)
- **Retrieved:** 2026-09-28, web page, no version or commit (read via WebFetch three times, including a raw markdown proxy, to check the table verbatim)
- **Cited by evidence:** https://x.com/denicmarko/status/2104514094241886483 (@denicmarko, feed memory, 2026-09-28; the post ends "Thanks to @Redisinc for sponsoring this post")
- **Relevance to a memory stack:** medium. A concrete, cheap design (keep raw chunks AND extracted facts, serve both in one labelled block) and a reproduction table showing vendor numbers moving by up to 27.6 points; weak as evidence because of single run, shared judge and missing harness.

## TL;DR
- Redis ran LongMemEval (small split, 500 questions, 6 question types, about 24 prior sessions per question) with GPT-4o answering for every reproduced system and "A standardized GPT-4o binary judge". Headline: "Remis + instruct k=5 cw=1 (Redis)" reproduced 86.5% task-averaged at $0.0703 per session.
- Remis = no LLM extraction, sessions split at topic-shift breakpoints, dense + BM25 scored 0.7 x cosine + 0.3 x BM25, top-k chunks expanded with neighbours. Instruct = LLM extractor that creates, updates or deletes facts against the current store. Combined = both run at ingest, one answer call over a context with two labelled sections.
- Reproduction gaps: Google Vertex Memory Bank ~70% reported vs 42.4% reproduced; Oracle Agent Memory 93.8% vs 86.0% (different answer model); Amazon Bedrock AgentCore 73.6% vs 77.0%.
- Claim correction: single run, no intervals, answer model and judge are the same model (GPT-4o), no harness link, and the leaderboard rows for "Redis instruct" and "LangMem" contain the placeholder value 95.4% in every column, so Instruct alone cannot be read from the table. The post is sponsored by Redis.
- Mem0 appears only as a gray "reported" 49.0% (not reproduced). This disagrees with the Atlaso page, which cites mem0's published LongMemEval-S number as 93.4% (see `vendor-atlaso-mem0-reader-matched-longmemeval-s.md`).

## What it claims / describes
**Benchmark setup (page text, "Methodology").** LongMemEval (Wu et al., ICLR 2025), small split, 500 questions, six categories: single-session-user, single-session-assistant, single-session preference, knowledge-update, multi-session, temporal-reasoning. Metric: task-averaged accuracy (mean over the six types). For each example: reset the store, ingest all haystack sessions, query with the test question, send (question, predicted answer, gold answer) to the judge, capture ingest and query token usage, report dollar cost. Answer LLM GPT-4o for all reproduced systems; judge "A standardized GPT-4o binary judge scores each answer for correctness". Number of runs, seeds and confidence intervals: not stated. Embedding model for Remis: not stated. Extraction model and prompt for Instruct: not stated.

**Remis (hybrid semantic RAG).** No LLM at ingest. Chunk sessions at topic-shift breakpoints; index dense vectors plus BM25; score = 0.7 x cosine + 0.3 x BM25; expand top-k chunks with neighbouring chunks. Page framing: nothing is thrown away, exact numbers, quotes and timestamps survive, but context is noisier.

**Instruct (LLM-extracted).** An extractor reads each session plus the current memory store and creates, updates or deletes individual facts, handling changes across sessions. Page framing: deduplicated, contradiction-aware facts, but loses narrative detail, exact quotes and timestamps; "anything extractor skips is gone".

**Remis + Instruct.** Both run at ingest; both are retrieved at query time; one context block with two sections, "Conversation excerpts" (Remis chunks) and "Extracted memories" (Instruct facts). No router, one answer call. Leaderboard config label: `k=5 cw=1` (k = top-k; cw presumably the neighbour context window, inference).

**Complementarity claim.** "Raw chunks preserve exact numbers, quotes, and dates that an extractor would compress away, while" extracted facts consolidate scattered evidence and resolve contradictions. The combination is said to gain in every category, "most sharply on verbatim assistant recall (72% -> 100%) and on the two hardest types, multi-session and temporal". The per-type breakdown (Figure 3) is a chart; no per-type table is in the text.

**Cost model.** Total $/sess = Ingest $/sess + 5.13 x Query $/Q, 5.13 being the average user turns per session in LongMemEval; counts answer-LLM prompt and completion tokens at list pricing. For managed services, ingest cost is server-side and the ">" values are lower bounds.

## Numbers
All from the leaderboard table on the page (verified verbatim through two separate fetches; column headers "Reported | Reproduced | Ingest/ex | Q lat | Total $/sess"). Page colour key: red = Redis strategies, yellow = third-party reproduced, gray = self-reported, unverified.

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Remis + instruct k=5 cw=1, reproduced task-averaged accuracy | 86.5% | Remis 83.4%, Mastra OM 84.2% reproduced | LongMemEval small split, n=500, GPT-4o answer, GPT-4o judge | single run, no CI; judge = answer model |
| Remis + instruct: ingest / query latency / $ per session | 247.8s / 1.78s / $0.0703 | Remis 1.4s / 3.5s / $0.1066 | same | cost modelled with 5.13 queries per session |
| Remis (Redis) reproduced | 83.4% | | same | |
| Redis instruct (Redis) reproduced | "95.4%" in every cell | | same | placeholder or template error: the same value appears in the latency and cost columns; unusable |
| LangMem reproduced | "95.4%" in every cell | | same | same placeholder problem; Atlaso measured LangMem v0.0.30 at 8.6% under its own protocol |
| Redis AMS (Redis) | 64.0%, 0.54s, 1.89s, >$0.0103 | | same | |
| RAG-mem k=20 (Redis) | 61.5%, 8.27s, 1.88s, $0.1195 | | same | |
| Mastra OM (gemini + gpt4o) | 84.2% reported, 84.2% reproduced, 187.8s, 4.12s, $0.3650 | | same | DaiDocs lists Mastra OM at 84.80% micro (84.23% task-averaged), consistent |
| Emergence-fast | 82.4% reported, 81.3% reproduced, 8.78s, 4.6s, $0.2488 | | same | DaiDocs records EmergenceMem "Simple" at 82.40% and "Simple Fast" at 79.00%: the two sources label the 82.4 figure differently |
| Oracle Agent Memory | 93.8% reported, 86.0% reproduced | | same | page: Oracle's own figure used a stronger answer model (GPT-5.5 xhigh per the fetched text) |
| Amazon Bedrock AgentCore | 73.6% reported, 77.0% reproduced, 1.99s, $0.0229 | | same | page: improved with all three strategies enabled |
| Google Vertex Memory Bank | ~70% reported, 42.4% reproduced, 937.5s, 1.35s, $0.0202 | | same | -27.6 points; page says the ~70% came from a research paper, not Google's product figure |
| OMEGA (GPT-4.1) | 95.4% reported, not reproduced | | self-reported | different answer model |
| PwC Chronos (GPT-4o) | 92.6% reported, not reproduced | | self-reported | |
| Supermemory | 81.6% reported, not reproduced, "<300ms / ~6s", ">0.0257" | | self-reported | DaiDocs also records Supermemory at 81.60% |
| Zep/Graphiti (gpt-4o) | "71.2$" reported (typo on page), 2.58s, >$0.0205 | | self-reported | DaiDocs also records Zep 71.20% |
| Mem0 | 49.0% reported, not reproduced | | self-reported, gray | disagrees with Atlaso, which cites mem0's published figure as 93.4% and measured 44.2% to 47.0% itself |
| single-session-assistant, Remis -> Remis + Instruct | "72% -> 100%" | | text sentence, n per type not stated | only per-type number in the text; the rest is chart-only |

## Mechanism details you could implement
- Hybrid chunk score: `score = 0.7 * cosine + 0.3 * bm25` (normalisation of BM25 not stated), then expand each of the top k=5 chunks with neighbours (cw=1, inference: one chunk either side).
- Chunk at topic-shift breakpoints rather than fixed windows (detector not stated).
- Keep two stores built at ingest from the same sessions: raw chunks and extracted facts (extractor creates, updates or deletes facts given the current store). At read, retrieve from both and render one prompt with two labelled sections, "Conversation excerpts" and "Extracted memories". No router, one answer call.
- Cost accounting formula worth copying for our own benchmark: `Total $/sess = Ingest $/sess + turns_per_session * Query $/Q`, with managed-service ingest marked as a lower bound.

## Limitations, caveats, counter-evidence
- Sponsored: the post is a paid Redis promotion (UTM `utm_medium=paid-post`); the report ranks Redis's own strategy first.
- Single run, no seeds, no confidence intervals (not stated anywhere on the page). At n=500 one binomial s.e. is about 1.6 to 1.8 points (inference), so 86.5 vs 86.0 (Oracle) vs 84.2 (Mastra) is within noise.
- The judge (GPT-4o) is the same model as the answerer (GPT-4o) for every reproduced row; self-preference is not discussed.
- The page says "Every reproduced number in this document can be re-run from our evaluation harness" but gives no link; no code, prompts, or per-question outputs are published.
- Two leaderboard rows (Redis instruct, LangMem) carry the placeholder value 95.4% in all five columns, and Zep's cell reads "71.2$". The Instruct-alone reproduced score is therefore not readable from the text, and "combination matched or beat either approach alone across all six question types" can only be checked against a chart.
- Task-averaged accuracy weights the n=30 preference type equal to the n=133 types (per-type n taken from the DaiDocs note on the same dataset), so one preference question moves the macro score by about 0.56 points (inference: 3.33/6).
- Reported vs reproduced numbers mix answer models (OMEGA on GPT-4.1, Oracle's own on a stronger model), so the "does not reproduce" examples are partly model changes, not pipeline failures; the page says so for Oracle.
- Chat QA benchmark; nothing about coding, review or incident agents, long structured artifacts, or build-time reads.
- No instruction-bearing content aimed at AI systems was found on the page.

## Takeaways for tuning a memory stack
- Cheap arm worth testing on our workload: raw chunks only vs extracted facts only vs both served in one labelled context, with the reader and judge frozen. The Redis direction (both > either) matches the Lore note's argument for keeping source sessions (`blog-lore-fact-sheets-vs-source-sessions-longmemeval.md`), but neither is independent of its author.
- Do not copy vendor LongMemEval numbers across answer models; Redis itself shows swings of -27.6 to +3.4 points on reproduction.
- Record ingest and query cost per session with an explicit queries-per-session multiplier; the ranking by cost differs from the ranking by accuracy (Mastra OM 84.2% at $0.3650 vs Remis + Instruct 86.5% at $0.0703).
- Use a judge that is not the answering model when we run our own arms.

## Open questions
- What is the Instruct-alone score, and the per-type table behind Figure 3?
- Where is the harness, and which embedding model, extractor model and prompts were used?
- How many runs, and what is the variance of the 86.5%?
- Does the both-stores design keep its edge when the reader is stronger (Claude Fable 5 class), as DaiDocs suggests reader choice alone moves scores by 14 points?

## Grading and labels
- Directness: medium. Primary vendor report read directly, but per-type data is chart-only and two rows are placeholders.
- Control: medium. Same answer model and same judge prompt across reproduced systems; single run; managed services not inspectable; judge shares the answer model.
- Independence: low. Redis measures itself and competitors; post is sponsored.
- Reproducibility: low. No harness link, no per-question outputs.
- Applicability: low. Conversational memory QA, not engineering-agent artifacts.
- Pillars: R6 primary (a benchmark and reproduction claim); R3 secondary (hybrid retrieval and context assembly); R2 secondary (extracted facts with update/delete).
- Stage: evaluation.
- Tags: hybrid retrieval, BM25 + dense fusion, LLM fact extraction, raw plus extracted context, reproduction, cost per session, sponsored.
- B20 supports: the post's headline narrows on a primary read (single run, shared judge, placeholder rows, no harness).
- Would create: "Raw chunks plus extracted facts in one labelled context beat either alone on LongMemEval-S (GPT-4o, vendor, single run)", grade lead.
- Contradiction: none with a belief. Cross-source disagreement: Mem0's "reported" LongMemEval figure is 49.0% here vs 93.4% cited as mem0's published figure by Atlaso; LangMem is a 95.4% placeholder here vs 8.6% measured by Atlaso.

## Origin chain
- Post https://x.com/denicmarko/status/2104514094241886483 (@denicmarko, sponsored by @Redisinc) -> t.co -> http://fandf.co/4hdlNkg -> https://fandf.co/4hdlNkg -> https://redis.io/resources/agent-memory-benchmark-report/ -> leaderboard table, "Methodology", "Published results that did not reproduce", Figure 3 (chart).
- Independence: Redis authored the systems it ranks first. Shares the LongMemEval-S dataset with Atlaso, DaiDocs and Acropolis notes in this run; shares the GPT-4o answer model and a GPT-4o judge with DaiDocs (DaiDocs uses the benchmark's official `evaluate_qa.py` with `gpt-4o-2024-08-06`; Redis's judge prompt is not published, so whether it is the same judge is unknown). Third-party figures for Supermemory (81.6), Zep (71.2) and Mastra OM (84.2) match those DaiDocs records, which suggests both copy the same vendor publications rather than independent measurements (inference).
