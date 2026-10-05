---
schema_version: 1
artifact_id: N-20260928-26
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:06:21Z
input_refs: [{"artifact_id": "post:2104473895310954936", "file_id": null, "sha256": null}, {"artifact_id": "post:2104543599853785448", "file_id": null, "sha256": null}, {"artifact_id": "post:2104472460380754063", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:kerneta/daidocs
claim_cluster: github:kerneta/daidocs
feeds: ["memory"]
primary_source: https://github.com/Kerneta/daidocs
source_commit: 09e207ef87618d35dcd29dc0eb01c5bd5b01be86
strength: repo-pinned
pillar_primary: R6
pillar_secondary: ["R3", "R1"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["plain-text-memory-files", "observer-actor-split", "llm-fact-extraction", "embedding-rerank", "regex-question-router", "mcp-server"], "workload": ["chat-memory", "coding-assistant-sessions"], "lifecycle_stage": ["ingestion", "retrieval", "assembly"], "cross_cutting": ["per-question-verdicts", "sha256-manifest", "reader-swap", "development-set-score", "judge-shares-actor-family", "token-accounting"]}
evidence_grade: {"directness": "high: per-question judge verdicts for all five actors ship in the repo and their counts match the headline exactly", "control": "medium: retrieval held byte-identical across five readers, same judge; but one seed each, Claude readers run through a subscription subagent route with no sampling control, and the no-memory baseline is a published number, not a run", "independence": "low: author-run on a benchmark the engine was tuned on; no third-party reproduction", "reproducibility": "medium: adapter, run manifest, verdicts and hashes are public; answer texts for Claude actors not included; sha256 values not recomputed by us", "applicability": "low: chat memory; the README says agent traces convert badly"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["With retrieval held byte-identical, swapping only the answering model moves LongMemEval-S accuracy from 78.00% to 92.00%; multi-session errors are reading errors (99% content recall, 72.18% accuracy with GPT-4o)"]}
claim_correction: The "+22.4 vs the same model with no memory" is against the LongMemEval authors' published GPT-4o full-context baseline (whole history pasted), not a DaiDocs run; 83% is a development-set, single-seed score judged by the actor's own model family; 92% with Claude Fable 5 came from a subscription subagent route without sampling control; "2nd" is against self-reported third-party figures under the repo's own entry rule, and the repo itself says Mem0 and Hindsight cannot be compared.
---

# DaiDocs (Kerneta/daidocs): plain-text `.dai` memory files, LongMemEval-S 83.00% with GPT-4o and 92.00% with Claude Fable 5

- **URL:** https://github.com/Kerneta/daidocs
- **Type:** repo
- **Author / org:** Kerneta (daidocs.com); Apache-2.0
- **Date:** launch release V4.4n32, 12 September 2026 (README); MANIFEST header "V4.4n32, locked 2026-09-25"; release run started 2026-08-14T16:52:31.458Z (`run-artifacts/lme.run.json`); actor swap measured 2026-08-15
- **Retrieved:** 2026-09-28, shallow clone at `repos/daidocs`, commit `09e207ef87618d35dcd29dc0eb01c5bd5b01be86` (2026-09-25 21:35:41 +0500, "Merge pull request #25 from Kerneta/Kerneta-patch-2"). Read: README.md, RESULTS-SUMMARY.md, RESULTS-ACTORS.md, docs/RESULTS.md, docs/GAPS.md, benchmark/README.md, run-artifacts/lme.run.json, MANIFEST.sha256 (run-artifacts lines), tools/references.json (grep), and counted verdicts in all five `run-artifacts/*.eval-results-gpt-4o` files. No code was run.
- **Cited by evidence:** https://x.com/alimunirrr/status/2104473895310954936, https://x.com/alimunirrr/status/2104543599853785448, https://x.com/alimunirrr/status/2104472460380754063 (all @alimunirrr, feed memory, 2026-09-28; the third is a reply asking @grok to compare and carries no numbers)
- **Relevance to a memory stack:** medium. Best-documented LongMemEval-S run in this batch (per-question verdicts, byte-identical retrieval across five readers), and a clean observer/actor split; but it is a development-set score on chat memory.

## TL;DR
- Release run: LongMemEval-S, all 500 questions (cleaned variant, 30 abstention items included), actor `openai:gpt-4o` temperature 0, observer `openai:gpt-4.1-mini`, embedder `openai:text-embedding-3-small`, judge = the benchmark authors' `evaluate_qa.py` with snapshot `gpt-4o-2024-08-06`: 83.00% (415/500) micro, 84.02% task-averaged, binomial s.e. 1.68 points. Mean context read 10,065 tokens vs 103,601 full history (10.3x).
- Verified: each of the five verdict files has 500 `autoeval_label` lines; `"label": true` counts are 415 (gpt-4o), 460 (Fable 5), 455 (Opus 5), 428 (Sonnet 5), 390 (Haiku 4.5), matching the published tables. The MANIFEST lists sha256 for every run-artifacts file (e.g. `lme.rows.jsonl` `95bcf659c42ff063...`), but we did not recompute the hashes.
- Reader swap with retrieval held fixed: 78.00% (Haiku 4.5) to 92.00% (Fable 5). The spread sits in multi-session (69.92% to 88.72%).
- Claim correction: "+22.4 vs no memory" is against the LongMemEval authors' published full-context GPT-4o baseline (60.60%), not a DaiDocs run; single seed; development-set score with selection bias; judge is the actor's model family; the Claude numbers were produced by subagents on a Claude subscription reading queue files, with no sampling parameters. The second post's claim that DaiDocs is "better than Mem0/Hindsight/Graphiti/Cognee" is not supported by the repo, which says those figures "cannot be set beside a GPT-4o 500/500 row in either direction".

## What it claims / describes
**Format.** One `.dai` file per conversation, three plain-text zones: YAML header, fenced JSON block, text (README "Language independent"). Store layout: `*.dai`, `_index/` (manifest, facts, events, profile: what retrieval reads), `_unconverted/`, `_raw/` (originals "byte-exact, never deleted").

**Pipeline** (docs/RESULTS.md): "an extraction pass by a small observer model, embedder-ranked retrieval, and a reading prompt with per-type counting rules." Observer writes the store once; any actor reads it. A regex `classify()` routes each question to one of four reading strategies: lookup, tally, timeline, advice. Retrieval is "mostly code over an index" with one embedding call to rank files (lookup, timeline) and a second over candidate fact and profile lines (tally, advice). Read depth: top 5 files per question, top 8 above 200k source tokens.

**Write path in production.** Claude Code hooks: every 4,000 new tokens the session is converted in the background by the assistant already in the conversation; under 4,000 tokens the text sits in `_unconverted/` and is read verbatim next session. MCP tools: `save_memory`, `recall_memory`, `list_memories`, `read_memory`, `declare_project`, `brief_parent`.

**Benchmark adapter.** `benchmark/run_longmemeval.mjs`: README says the gold `question_type` is read in exactly one line after the answer is final, the gold answer is never read, no router can be injected.

**Actor swap** (RESULTS-ACTORS.md). Same stores (19,195 sessions ingested once), same rendered prompts (cache key `hash8(system + '\n' + prompt)` with no actor name), same judge; `run-artifacts/lme.rows.jsonl` "byte-identical across all five runs". Claude actors were run through `lib/providers/manual.js`: the adapter writes each prompt to a queue file, "A subagent on the target model reads a queue file and writes its answer beside it", then the adapter collects answers. No temperature control on that route; the prompt arrives as a file read, not a user message.

**Ranking** (docs/RESULTS.md "Ranking"). Entry rule: LongMemEval-S, all 500, GPT-4o answering, micro-averaged, configuration reproducible by a non-employee. Every other figure is the publisher's own, stored in `tools/references.json`.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| accuracy, gpt-4o actor (micro) | 83.00% (415/500) | GPT-4o full context 60.60% (published by LongMemEval authors) | LongMemEval-S cleaned, n=500, judge `gpt-4o-2024-08-06` via `evaluate_qa.py` (RESULTS-SUMMARY.md) | one seed; s.e. 1.68; development-set score; baseline not run by DaiDocs |
| task-averaged (macro) | 84.02% | | same | |
| gap to full-context baseline | 22.40 points | | README, docs/RESULTS.md | baseline is "their measurement on their harness, not a run of ours" (docs/GAPS.md: "we have not done it") |
| mean context read vs full history | 10,065 vs 103,601 tokens, 10.3x | | `gpt-tokenizer@3.4.0` both sides | |
| retrieval hit rate (document-only) | 94.6% | | per question `retrieval_hit` | content recall definition gives 98.0% at k=5 |
| Claude Fable 5 | 92.00% (460/500), s.e. 1.21, macro 91.94% | gpt-4o 83.00% | same store and prompts (RESULTS-ACTORS.md) | subscription subagent route, no sampling params |
| Claude Opus 5 | 91.00% (455/500), s.e. 1.28, macro 90.94% | | same | tied with Fable per the repo |
| Claude Sonnet 5 | 85.60% (428/500), s.e. 1.57, macro 86.75% | | same | |
| Claude Haiku 4.5 | 78.00% (390/500), s.e. 1.85, macro 77.66% | | same | |
| multi-session by actor | Fable 88.72% (118), Opus 87.97% (117), Sonnet 76.69% (102), gpt-4o 72.18% (96), Haiku 69.92% (93) | | n=133 | retrieval identical, so the spread is reading |
| per type, gpt-4o | SS-user 92.86% (65/70); SS-assistant 92.86% (52/56); temporal 84.96% (113/133); knowledge-update 84.62% (66/78); preference 76.67% (23/30); multi-session 72.18% (96/133) | | RESULTS-SUMMARY.md | preference n=30: one question = 3.33 points |
| by reading strategy, gpt-4o | lookup 88.03% (125/142); advice 83.02% (44/53); tally 82.55% (194/235); timeline 74.29% (52/70) | | same | |
| ranking table (third-party, self-reported) | Mastra OM 84.80%; DaiDocs 83.00%; Supermemory 81.60%; Mastra RAG topK 20 81.20%; EmergenceMem Simple Fast 79.00%; TiMem 76.88%; Zep 71.20%; Feather 69.30%; GPT-4o + Chain-of-Note 64.00%; GPT-4o full context 60.60% | | docs/RESULTS.md | held out: EmergenceMem Internal 86.00%, EmergenceMem Simple 82.40% |
| retrieval recall@5 | .dai 98.0% (content) | MemPalace 96.6%, Supermemory 86%, LongMemEval paper session baseline 70.6% (on _M) | docs/RESULTS.md | units differ per row |
| ingest cost | about $0.0009 per 1,000 tokens with gpt-4.1-mini | | docs/RESULTS.md | read-side embedding about $0.00002 per 1,000 tokens |

## Mechanism details you could implement
- Observer/actor split: a stronger model writes the store once ("The observer is the one worth spending on, because you only get to run it once"), a cheaper or local model reads. README warns: "Go higher if you like, but do not go lower."
- Deterministic regex router over question text into four reading strategies, with a tripwire tool (`tools/verify_router.mjs`) that exits non-zero if agreement with a label mapping exceeds 95% (to detect label leakage).
- Benchmark hygiene worth copying: publish per-question verdict files per reader; keep a diagnostics file (strategy, context tokens, files read, retrieval hit, tokenizer) and show it is byte-identical across reader swaps; hash every evidence file in a manifest; `tools/check_numbers.mjs` fails CI if a published number drifts from the artifacts.
- Values calibrated on the benchmark (docs/RESULTS.md, listed as such): answer budgets 220 / 350 / 400; read depth top 5 files (top 8 above 200k tokens); extraction fact cap 14.

## Limitations, caveats, counter-evidence
- Repo's own disclosures: development-set score ("Several engine variants were evaluated against the same 500 questions and the best shipped ... nothing currently bounds the inflation"); one seed per actor; judge `gpt-4o-2024-08-06` is the default actor's family; full-context baseline not run locally; one benchmark; English only; "Agent traces are not handled. Tool calls, stack traces and file dumps ... produce poor stores"; the reader has no unit tests; concurrent writes unguarded; never run on macOS.
- Instruction-bearing post in this cluster: 2104472460380754063 is addressed to an AI assistant ("@grok compare daidocs with this"); it carries no evidence and was not acted on.
- Posts overstate: "+22.4 vs the same model with no memory" compares against a published number, and that baseline had the full history in context (not "no memory" in the sense of no information). "92% with Claude Fable 5" is a different route (no temperature, subagent answers) from the gpt-4o API run.
- "2nd among systems you can actually re-run": the comparison figures are self-reported by other vendors under their own harnesses; only DaiDocs's own row is verified in this repo.
- Second post claims superiority over Mem0/Hindsight/Graphiti/Cognee and Letta/OpenViking; the repo README explicitly says Mem0 and Hindsight numbers cannot be compared "in either direction". No measured comparison exists.
- Claude actor answer texts are not in the repo ("live in the working copy under `results/replies-<actor>/`"); only hypotheses and verdicts are.
- We could not recompute sha256 values (tooling restriction in this run); the manifest's presence was verified, not its correctness.
- Instruction-bearing content: the repo ships `prompts/READER-PROMPT.txt` "to paste into any assistant" and `setup.js` writes a reading protocol into `~/.claude/CLAUDE.md`; the Claude benchmark runs had subagents follow "answering instructions carried inside that prompt". These are product features aimed at AI assistants; not read further and not followed. No instructions aimed at this triage agent were found.

## Takeaways for tuning a memory stack
- At fixed retrieval, the reader model moved LongMemEval-S by 14 points (78 to 92). Any memory-backend comparison that lets the reader vary is mostly measuring the reader. Freeze the reader in our arms (same conclusion as Atlaso).
- Multi-session synthesis is where failures remain once retrieval hits (99% content recall, 72.18% accuracy with gpt-4o): look at assembly and reading prompts before retrieval for aggregation questions.
- The byte-identical diagnostics file is a cheap proof that only the reader changed; adopt it for our frozen harness.
- Token accounting with the same pinned tokenizer on both sides of a ratio.
- Not applicable as-is to engineering agents: the author reports poor stores from agent traces.

## Open questions
- Held-out result on a second corpus (the repo names this as the most valuable missing result).
- Does the Claude route (no temperature, file-read framing) inflate or deflate the Claude numbers relative to an API run?
- Own full-context arm with the same adapter: how large is the controlled gap?
- Would a non-GPT judge change the gpt-4o row more than the Claude rows?

## Grading and labels
- Directness: high. Verdict files and counts checked against the headline.
- Control: medium. Retrieval and judge fixed across readers; single seed; baseline external; Claude route differs.
- Independence: low. Author-run, tuned on the test set.
- Reproducibility: medium. Adapter, manifests, verdicts public; hashes not recomputed; answer texts for Claude not shipped.
- Applicability: low. Chat memory; agent traces explicitly weak.
- Pillars: R6 primary (benchmark integrity and reader control); R3 secondary (retrieval and assembly token budget); R1 secondary (hash manifest and per-question evidence).
- Stage: evaluation.
- Tags: plain-text memory files, observer/actor split, regex router, per-question verdicts, sha256 manifest, reader swap, development-set score.
- B20 supports: the posts' headlines narrow on the primary read (baseline is published, not run; single seed; dev-set; Claude route).
- Would create: "At byte-identical retrieval, reader choice alone moves LongMemEval-S from 78.00% to 92.00%", grade lead (one author, one run per reader).
- Contradiction: none with a belief. Cross-source: DaiDocs records EmergenceMem Simple Fast at 79.00% and Simple at 82.40%, while Redis labels "Emergence-fast" as 82.4% reported and 81.3% reproduced; Mastra OM 84.80% micro here vs 84.2% task-averaged on Redis's page (consistent, different averaging). No Hindsight or mem0 score appears in this repo.

## Origin chain
- Posts 2104473895310954936 and 2104543599853785448 (@alimunirrr) -> https://github.com/Kerneta/daidocs (and daidocs.com, not fetched) -> RESULTS-SUMMARY.md headline and conditions tables, RESULTS-ACTORS.md headline and per-type tables, docs/RESULTS.md Ranking and Token economics, docs/GAPS.md, run-artifacts/*.eval-results-gpt-4o (500 lines each). Post 2104472460380754063 is a question to @grok with no source link and adds nothing.
- The second post quotes @RoundtableSpace's list of memory projects (Mem0, Hindsight, ...); that list is not a source for any number here.
- Independence: @alimunirrr appears to promote the project (inference: posts use install commands and "we"-style claims; affiliation not stated). Shares LongMemEval-S, the GPT-4o answer model and a GPT-4o judge with the Redis report; the third-party figures in its ranking (Supermemory 81.6, Zep 71.2, Mastra) match Redis's "reported" column, i.e. both copy the same vendor publications.
