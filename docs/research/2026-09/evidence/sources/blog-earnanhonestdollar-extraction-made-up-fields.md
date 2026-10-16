---
schema_version: 1
artifact_id: N-20260928-18
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104415204079468940", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:earnanhonestdollar.com/bench
claim_cluster: url:earnanhonestdollar.com/bench
feeds: ["memory"]
primary_source: https://earnanhonestdollar.com/bench
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R2", "R6"]
memory_stage: ingestion
tags: {"mechanism": ["null-for-missing instruction", "twin-page traps", "LLM checker"], "workload": ["web extraction", "structured fields"], "lifecycle_stage": ["write"], "cross_cutting": []}
evidence_grade: {"directness": "high: counts of made-up fields with and without the instruction across 16 models", "control": "medium: twin pages differing by one row isolate fabrication; a single prompt sentence is the only change; one run per contestant", "independence": "medium: operator of an extraction service (inference from the site's offers API) runs the benchmark", "reproducibility": "low: synthetic pages and scoring said to exist, but code and data links point only to a quickstart and API", "applicability": "medium: memory ingestion that extracts fields from documents faces the same fabricate-vs-null choice"}
beliefs_affected: {"supports": ["B11"], "contradicts": [], "would_create": ["An explicit 'use null, do not guess' instruction cuts fabricated fields in LLM extraction from about 71% to about 20% of missing fields, but does not remove them"]}
claim_correction: none (the post's 71% to 20% matches 405/573 = 70.7% vs 116/574 = 20.2%); the page adds that 20% of missing fields are still made up with the instruction.
---

# "Calling the AI bluff": do extractors make up missing fields? (earnanhonestdollar.com/bench)

- **URL:** https://earnanhonestdollar.com/bench
- **Type:** vendor benchmark page
- **Author / org:** not named on the page (site offers an extraction API: `/openapi.json`, `/api/services`)
- **Date:** 2026-09-27
- **Retrieved:** 2026-09-28 via WebFetch (summary rendering; numbers quoted as rendered).
- **Cited by evidence:** @jreuben1 2026-09-28 https://x.com/jreuben1/status/2104415204079468940 ("Adding 'Do not guess' cut made-up fields from 71% to 20%")
- **Relevance to a memory stack:** medium. Any ingestion step that extracts structured fields (owners, versions, dates, limits) into memory risks writing invented values; this measures the size of that risk and one cheap mitigation.

## TL;DR
- Twin web pages differ by one row that holds the target information; an honest extractor returns the value on the page that has it and null on the page that does not.
- 16 LLMs (including Gemini 3.8 Flash, GPT-6 Luna, Claude Sonnet 5, DeepSeek V4.1 Flash) plus 3 paid scraping APIs (ScrapeGraphAI, ScrapingBee, Firecrawl); 42 page pairs over 7 page types (84 pages), 36 scoreable instances per contestant.
- Without the sentence "Use null for any field whose value is not on the page. Do not guess.", models made up 405 of 573 missing fields (70.7%); with it, 116 of 574 (20.2%). All 16 models improved.
- A GPT-6 Luna checker caught 38 of 49 made-up values with no false rejections of correct ones, at about $0.0049 per full run.

## What it claims / describes
- Metric: made-up fields = a non-null value returned on the twin page where the field is absent.
- Prompt arms: identical extraction instructions with vs without the null/no-guess sentence.
- Post-hoc check: an LLM checker asked to verify each extracted value against the page.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| made-up missing fields, with instruction | 116/574 (20.2%) | 405/573 (70.7%) without | 16 models, 42 page pairs | one run per contestant |
| checker recall on made-up values | 38/49 | n/a | GPT-6 Luna as checker | 0 correct values rejected |
| checker cost | about $0.0049 per full run | | | |
| scoreable instances | 36 per contestant | | 7 page types | small |

Per-model rates were not captured in this read.

## Mechanism details you could implement
- In every memory extraction prompt, state explicitly that absent fields must be null and must not be guessed.
- Add a cheap verification pass (an LLM or a typed noul "is value X stated in the source?") over extracted fields before they are written; here it caught 38 of 49 residual fabrications.
- Build twin-document tests for the ingestion stage: the same artifact with and without the field; count non-null answers on the absent twin.

## Limitations, caveats, counter-evidence
- Page's own limits: single run per contestant; synthetic test pages; paid APIs tested on free tiers; email traps excluded.
- 20% residual fabrication is still high; the instruction is a mitigation, not a fix.
- Author unnamed; data and code not published beyond an API quickstart.

## Takeaways for tuning a memory stack
- Treat extracted fields as claims needing a source check; a field without an anchor in the source should not enter memory.
- The admission question (B11: admission must allow empty) has a direct analogue at field level: extractors need an explicit null path.

## Open questions
- How do typed decision models (Jev "is X stated in the page?") compare with the LLM checker at the same cost?
- Fabrication rates on long engineering documents (design docs, tickets)?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility low; applicability medium.
- Pillars: R4 primary (when to trust an automated extraction decision; abstention), R2 and R6 secondary. Memory stage: ingestion.
- Beliefs: supports B11 (a decision that writes into memory needs an explicit empty option); would create the fabrication-rate belief.
- Contradiction rows: none.

## Origin chain
- Post 2104415204079468940 (@jreuben1) -> https://earnanhonestdollar.com/bench (results and method text) -> this note.
- Independence: no overlap with other notes' sources.
