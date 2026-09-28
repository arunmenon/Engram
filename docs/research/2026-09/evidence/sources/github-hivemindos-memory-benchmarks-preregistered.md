---
schema_version: 1
artifact_id: N-20260928-09
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104130682016694680", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:liamvisionary/hivemindos-memory-benchmarks
claim_cluster: github:liamvisionary/hivemindos-memory-benchmarks
feeds: ["memory"]
primary_source: https://github.com/LiamVisionary/hivemindos-memory-benchmarks
source_commit: 0cee0d92695861a348918ee6750e042b4770150e
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R3", "R1"]
tags: {"mechanism": ["pre-registration", "McNemar test", "context receipts sha256", "hosted memory recall"], "workload": ["conversational memory", "LongMemEval_S", "LongMemEval Oracle", "LoCoMo"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: every answer, context and judge verdict published with a tally script", "control": "medium: pre-registered, same reader and judge on both sides, exact McNemar tests; one run per side, deviations (duplicate runners) disclosed, HivemindOS answers produced before pre-registration", "independence": "low: vendor-run comparison of its own product against a competitor it ran itself; the product is promoted alongside a crypto token", "reproducibility": "medium: scoring recomputable from files; HivemindOS memory source is private (hivemindos-core ac0980b named for auditors only)", "applicability": "low-medium: chat-memory benchmarks, but the receipt protocol is directly applicable to our eval harness"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["A memory layer returning about 12,100 tokens scored as well as a whole-journal reading architecture using about 111,700 tokens on LongMemEval_S (94.3% vs 92.1%, p = 0.16): equal accuracy at about a ninth of the read tokens, difference not significant"]}
claim_correction: The post calls these "very solid bench tests of LongMemEval and LoCoMo" in a token promotion; the repo's own results say neither headline difference is established beyond chance (LongMemEval_S p = 0.16, LoCoMo before/after p = 0.38), 30 preference questions are excluded from the 94.3%, and the LoCoMo test was a before/after of the vendor's own versions, not against competitors.
---

# HivemindOS memory benchmarks: pre-registered LongMemEval and LoCoMo receipts (LiamVisionary/hivemindos-memory-benchmarks)

- **URL:** https://github.com/LiamVisionary/hivemindos-memory-benchmarks (summary page https://hivemindos.app/superagent-api/docs/benchmarks)
- **Type:** vendor benchmark repo
- **Author / org:** HivemindOS (GitHub LiamVisionary)
- **Date:** commit `0cee0d92695861a348918ee6750e042b4770150e`, 2026-09-25 17:13:18 +0800 ("LongMemEval_S, all 500: HivemindOS 94.3% vs Sibyl-Memory's published architecture 92.1% (Opus 4.6 both sides, p = 0.16), with every answer and run record")
- **Retrieved:** 2026-09-28; docs page via WebFetch; shallow clone `repos/hivemindos-memory-benchmarks`; read README.md, `longmemeval-s-sibyl-native-2026-09-25/RESULTS.md`, `locomo-heldout-2026-09-25/RESULTS.md`. Scripts not executed.
- **Cited by evidence:** @based_elnen, https://x.com/based_elnen/status/2104130682016694680 (a reply promoting a Base-chain token contract, "Very solid bench tests of LongMemEval and LoCoMo")
- **Relevance to a memory stack:** medium. The product claims are weak (non-significant), but the evaluation protocol is unusually good for a vendor: pre-registration, per-answer context receipts with sha256, exact McNemar tests, disclosed deviations and honest "what it does not show" statements. A template for our own harness.

## TL;DR
- LongMemEval_S, all 500 questions, Claude Opus 4.6 reading on both sides, official per-type judge prompts with `gpt-4o-2024-08-06`: HivemindOS 443/470 (94.3%) vs Sibyl-Memory native architecture 433/470 (92.1%) excluding preference; all 500: 470 (94.0%) vs 457 (91.4%). Exact McNemar p = 0.16 (470) and p = 0.085 (500).
- Read tokens per question: HivemindOS 12,096 vs Sibyl-Memory 111,675 ("about a ninth of the text").
- LoCoMo held-out (500 sampled questions, Mem0's pinned prompts, gpt-4o judge): HivemindOS before 467 (93.4%) vs after 472 (94.4%), McNemar p = 0.38: "no overfitting shown, no gain shown". The "after" version hands the reader about twice the text (median 45,250 vs 22,253 characters).
- LongMemEval Oracle: Opus 4.6 96.6% (454/470) vs Sibyl-Memory 95.3%; Sonnet 4.5 95.1% (447/470) vs 92.8%.
- The pre-registered LoCoMo secondary run failed for a setup reason (empty contexts, 32.6% vs 31.2%) and was published as run, not redesigned.

## What it claims / describes
"Published receipts for HivemindOS Superbrain memory benchmarks: every model answer, every judge verdict, the method, and a script that recomputes the score from the files." `tally.py` checks that each answer was given its published context (sha256) and recomputes every number.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| LongMemEval_S excl. preference | 94.3% (443/470) | Sibyl-Memory native 92.1% (433/470) | Opus 4.6 both sides, gpt-4o-2024-08-06 judge | McNemar p = 0.16; one run per side |
| LongMemEval_S all 500 | 94.0% (470) | 91.4% (457) | same | p = 0.085 |
| updated facts subset | 74/78 | 70/78 | same | knowledge-update category |
| counting across chats | 116/133 | 118/133 | same | competitor ahead |
| read tokens per question | 12,096 | 111,675 | same | competitor total includes cached reads across turns |
| LoCoMo held-out, before vs after | 93.4% vs 94.4% | own previous version | 500 questions, Mem0 pinned prompts | p = 0.38; after uses about 2x context |
| LongMemEval Oracle, Opus 4.6 | 96.6% (454/470) | Sibyl-Memory 95.3% | official gpt-4o judge | |
| LongMemEval Oracle, Sonnet 4.5 | 95.1% (447/470) | 92.8% | same | |
| reader/judge variance | 5 of 475 flipped on re-answering unchanged contexts | | LongMemEval Oracle, temperature 0 | noise floor about 1% |

## Mechanism details you could implement
- Pre-register (commit the plan and hash before any answer), publish `contexts.jsonl` (exactly what memory handed the reader) and `answers.jsonl` with the judge reply, and verify with sha256 that each answer saw its published context. This is a served-context receipt (R1) applied to evaluation.
- Report paired exact McNemar on discordant questions, and the re-answer flip rate as a noise floor.
- Report read tokens per question next to accuracy.

## Limitations, caveats, counter-evidence
- Vendor ran the competitor itself; two runner copies answered 200 competitor questions twice (first valid answer kept, rule applied after the fact); HivemindOS answers were produced before the pre-registration (disclosed).
- HivemindOS memory source is private, so the mechanism behind the 12,096-token context cannot be inspected.
- Preference questions excluded from the headline; the LoCoMo judge is Mem0's lenient one ("absolute LoCoMo scores here are not comparable").
- The citing post is token promotion ("Emerging memory play on Base", a contract address); the benchmark results are about "Superbrain recall, not on the HivemindOS NFT miner" (README).

## Takeaways for tuning a memory stack
- Adopt the receipt protocol (context hash per answer, pre-registration, McNemar, flip-rate noise floor) in our frozen harness.
- A result of "equal accuracy at a ninth of the read tokens" is the claim worth testing, not the accuracy gap.
- Headline memory-benchmark gaps of 1 to 2 points on 470 to 500 questions are routinely not significant; require paired tests (supports B20 on narrowing on primary read).

## Open questions
- Would the token saving hold against a strong hybrid-retrieval baseline rather than a whole-journal reader?
- Independent re-run by a party other than the vendor.

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium; applicability low-medium.
- Pillars: R6 primary (evaluation integrity and statistics), R3 secondary (accuracy at a read-token budget), R1 secondary (per-answer context receipts). Tags: cost.
- Beliefs: supports B20 (the promoted claim narrows on primary read: non-significant differences). Would create a belief on matched accuracy at about one ninth of read tokens (vendor-run, needs independent check). No contradiction.

## Origin chain
post 2104130682016694680 (@based_elnen, token promotion reply) -> hivemindos.app docs benchmarks page -> GitHub search -> repo at 0cee0d9 -> README and two RESULTS.md files -> this note. Independence: vendor self-report; Sibyl-Memory comparison run by the vendor; judge prompts are LongMemEval's and Mem0's public ones.
