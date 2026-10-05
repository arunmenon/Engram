---
schema_version: 1
artifact_id: N-20260930-04
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2104939608484282449", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:tigerdata.com/blog/agent-memory-search-problem-not-storage-problem
claim_cluster: url:tigerdata.com/blog/agent-memory-search-problem-not-storage-problem
feeds: ["memory"]
primary_source: https://www.tigerdata.com/blog/agent-memory-search-problem-not-storage-problem
source_commit: github.com/timescale/lab-conversational-memory 52799a61963a20b55da55100b8a1487a82bd437b (HEAD 2026-09-28, not cloned)
strength: vendor-benchmark
pillar_primary: R3
pillar_secondary: ["R6", "R2"]
tags: {"mechanism": ["agentic search over raw turns", "hybrid semantic plus BM25 plus regex plus tree plus temporal tools", "no fact extraction at write time"], "workload": ["long conversational memory", "LoCoMo"], "lifecycle_stage": ["retrieval", "ingestion", "evaluation"], "cross_cutting": ["cost"]}
memory_stage: retrieval
priority: 4
evidence_grade: {"directness": "high: full LoCoMo run with per-category F1 and experiment logs", "control": "medium: ablations with 95% CIs on the full benchmark, but the comparison to the prior best is model-confounded (Claude vs GPT-5.1) and changes were selected on one conversation", "independence": "medium: database vendor evaluating its own architecture; baseline number taken from another paper", "reproducibility": "medium: public harness and logs at a known HEAD; exact Claude model versions not recorded", "applicability": "medium: chat memory, but raw-turn storage with agent-chosen search tools is a design option for PDLC artifacts"}
beliefs_affected: {"supports": ["B8", "B16"], "contradicts": [], "would_create": ["On LoCoMo, removing atomic fact extraction from ingestion changed F1 by 0 while halving ingestion time; raw turns plus agent-chosen search tools matched or beat extraction pipelines", "LoCoMo accuracy under a Mem0-style generous judge prompt is about 14 points higher than under a neutral prompt for identical predictions (85.1% vs 70.9%)"]}
claim_correction: The post says "F1 0.665 on LoCoMo, vs 0.613 for the prior best"; the blog states the comparison is model-confounded (Claude Sonnet vs Omni-SimpleMem's GPT-5.1 number), design choices were tuned on conversation conv-26, and 164 benchmark-error questions were excluded for the error-corrected table; the raw 0.665 includes them.
---

# Agent memory is a search problem, not a storage problem (Tiger Data blog): one Postgres table, three MCP search tools, LoCoMo F1 0.665

- **URL:** https://www.tigerdata.com/blog/agent-memory-search-problem-not-storage-problem
- **Type:** vendor blog (builder write-up with a public harness)
- **Author / org:** Matvey Arye, Tiger Data (Timescale). Harness: https://github.com/timescale/lab-conversational-memory
- **Date:** published 2026-09-29 (updated same day)
- **Retrieved:** 2026-09-30. Repo HEAD `52799a61963a20b55da55100b8a1487a82bd437b` (2026-09-28) recorded via the GitHub API, not cloned.
- **Cited by evidence:** memory feed 2026-09-29, @TimescaleDB (https://x.com/TimescaleDB/status/2104939608484282449)
- **Relevance to a memory stack:** high. A measured argument for storing raw records and investing in read-time tools instead of write-time extraction, with ablation intervals and a judge-prompt sensitivity measurement. What is new relative to the existing bus note `tigerdata.com/blog/41-experiments-6-days-what-human-was-for` (N on the bus, same team, probably the same experiment series; inference): the final architecture, the full per-category table, the error-corrected numbers, the judge-prompt 85.1% vs 70.9% measurement and the extraction ablation.

## TL;DR
- Store every conversation turn as a row (no extraction, no summaries, no entity resolution); expose three MCP tools; let Claude (Sonnet or Haiku via the Claude Code CLI) choose its own retrieval strategy.
- LoCoMo raw F1: Sonnet 0.665, Haiku 0.638 vs Omni-SimpleMem (GPT-5.1) 0.613. Error-corrected: Sonnet 0.694, Haiku 0.666.
- Largest single gain: fixed pipeline to agentic search, +0.103 (0.481 to 0.584) on the tuning conversation. Removing a tool-call cap: +0.031 (95% CI +0.018 to +0.044).
- Atomic fact extraction: "0 difference", removed; saved about 50% of ingestion time.
- Judge sensitivity: the same predictions score 85.1% with the Mem0 "generous" grading prompt and 70.9% with a neutral one (GPT-4o-mini judge).
- "Adversarial rejection is the binding constraint": most answering gains reduced refusal accuracy (grep filtering +0.046 multi-hop, -0.036 adversarial).

## What it claims / describes
**Store.** One table:
```sql
CREATE TABLE memory (
    id          uuid PRIMARY KEY,
    content     text NOT NULL,
    meta        jsonb NOT NULL,
    tree        ltree NOT NULL,
    temporal    tstzrange,
    embedding   halfvec(1536),
    created_at  timestamptz DEFAULT now()
);
```
Indexes: HNSW (halfvec_cosine_ops), BM25 (pg_textsearch), GIST on tree paths and temporal ranges, GIN on metadata. Each raw turn is a row with speaker text plus image captions (1,226 turns enriched with captions); `prev_id`/`next_id` links in metadata; ltree path `conv.{speaker}.s{session_number}`; embeddings OpenAI text-embedding-3-small (1536 dims stored as halfvec). Ingest cost: zero LLM calls, one embedding per turn.

**Tools (MCP).** `me_memory_search` (hybrid: semantic, fulltext BM25, grep regex, tree, temporal), `me_memory_get` (by id with a 2-turn context window), `me_memory_tree` (hierarchy). "The policy did not vanish. It became text": retrieval behaviour lives in the system prompt, not code.

**Evaluation.** LoCoMo, 1,986 questions, 10 conversations, 5,882 turns. Categories: single-hop 841, multi-hop 282, temporal 321, open-domain 96, adversarial 446. Metric: token-level F1 with Porter stemming, as in the original LoCoMo. 164 questions (8.3%) identified as benchmark errors (corrections file `adversarial-errors.json`, 5 of 7 corrections in adversarial).

## Numbers
| method | model | multi-hop | single-hop | temporal | open-domain | adversarial | overall F1 |
|---|---|---|---|---|---|---|---|
| Omni-SimpleMem (Liu et al., 2026) | GPT-5.1 | 0.598 | 0.367 | 0.307 | 0.676 | 0.747 | 0.613 |
| Tiger Data | Claude Haiku | 0.420 | 0.645 | 0.567 | 0.311 | 0.883 | 0.638 |
| Tiger Data | Claude Sonnet | 0.453 | 0.673 | 0.625 | 0.400 | 0.870 | 0.665 |

Error-corrected (full 10 conversations): overall F1 Haiku 0.666, Sonnet 0.694; Sonnet accuracy 0.887 and recall 0.831; per category Sonnet F1 multi-hop 0.485, single-hop 0.696, temporal 0.648, open-domain 0.441, adversarial 0.880.

| experiment | effect | interval / setup |
|---|---|---|
| fixed pipeline to agentic search | +0.103 (0.481 to 0.584) | tuning conversation only |
| remove tool-call cap | +0.031 | 95% CI +0.018 to +0.044, full benchmark |
| grep filtering | +0.046 multi-hop; -0.036 adversarial | CIs +0.015 to +0.079; -0.058 to -0.014 |
| tree paths + captions + context window (bundle) | +0.024 (Haiku) | CI +0.010 to +0.039 |
| atomic fact extraction | 0 difference | removed; ~50% ingestion time saved |
| judge prompt | 85.1% (Mem0 generous) vs 70.9% (neutral) | same predictions, GPT-4o-mini judge |
| tool calls per question | mean 3.9 Sonnet, 2.6 Haiku; median 3 / 2 | 4 to 5 model turns per question vs 1 for a fixed pipeline |

Dollar cost per question: not stated.

## Mechanism details you could implement
- Raw record per turn with deterministic structure only (ltree path per speaker and session, prev/next links, temporal range); embeddings plus BM25 plus regex plus tree plus time filters behind one search tool.
- Give the agent a `get(id, window=2)` expansion tool rather than packing neighbours at retrieval time.
- Do not cap tool calls (+0.031 with interval above zero).
- Track adversarial (should-refuse) accuracy alongside answer F1 for every change; the blog found most answering gains cost refusals.
- Report LoCoMo with a neutral judge prompt; the generous Mem0 prompt ("touches on same topic = CORRECT") inflates accuracy by about 14 points on identical predictions.

## Limitations, caveats, counter-evidence
- Self-stated: "The comparison is model-confounded, and we cannot fully control for it. Every baseline runs GPT; ours runs Claude." Exact Sonnet/Haiku versions not recorded (CLI alias only).
- All design changes chosen on one conversation (conv-26), then validated on the other nine.
- Bundled changes cannot be attributed individually (findings 5 to 7).
- LoCoMo is about 5,882 turns; no data on degradation at larger corpora.
- Query cost moves to read time: 4 to 5 model turns per question.
- Consistent with the Lore note (`blog-lore-fact-sheets-vs-source-sessions-longmemeval.md`, card PC-20260928-03) and survey card PC-SURVEY-20260929-01 (raw turns plus typed selection vs extraction), which already propose the extraction-off test; no new card from this note.

## Takeaways for tuning a memory stack
- Treat write-time extraction as optional until it beats raw storage on your own set: here it added nothing and doubled ingestion time.
- Put engineering effort into the read-time tool interface (hybrid modes, expansion by id, hierarchy browsing) and let the agent plan retrieval.
- Pin the judge prompt and model in any memory benchmark you publish or compare against; ask vendors which grading prompt they used.

## Open questions
- Cost per question (dollars and latency) for 3.9 tool calls with Sonnet vs a single-pass pipeline? Not stated.
- Does the design hold on engineering artifacts where exact identifiers matter more (grep helped multi-hop here)?
- Same experiment with a GPT-5.1 agent to remove the model confound?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility medium; applicability medium.
- Pillars: R3 primary (read-time retrieval via tools), R6 (judge prompt sensitivity, benchmark errors), R2 (no extraction at write). Memory stage: retrieval. Priority 4 (LoCoMo, benchmark integrity).
- Beliefs: supports B8 (no graph needed for top LoCoMo score; hybrid tools over raw turns win on a chat benchmark). Supports B16 (raw records beat distilled facts here: extraction added 0). Would create two beliefs (extraction null on LoCoMo; generous-judge inflation of about 14 points).
- Contradiction rows: none.

## Origin chain
@TimescaleDB post (2104939608484282449) -> tigerdata.com blog by Matvey Arye (2026-09-29) -> primary results table, error-corrected table, experiment list, cost table, limitations list -> this note. Independence: vendor evaluating its own Postgres-based design; baseline Omni-SimpleMem number copied from Liu et al. 2026 (different model); LoCoMo shared with most memory vendors; GPT-4o-mini judge differs from the Claude answerer.
